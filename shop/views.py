from django.db import transaction
from django.db.models import Q
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, viewsets
from rest_framework.pagination import PageNumberPagination

from .models import AppUser, Store, Category, Product, Address, Recipient, Order, OrderItem
from .serializers import (
    AppUserSerializer, StoreSerializer, CategorySerializer, 
    ProductSerializer, AddressSerializer, RecipientSerializer, OrderSerializer
)
from .authentication import XUserKeyAuthentication, IsAuthenticatedAppUser
from .services import calculate_checkout_totals

# --- ۱. ساخت کاربر اولیه ---
class UserCreateView(APIView):
    """
    اولین درخواستی که اپلیکیشن در صورت نداشتن UUID ارسال می‌کند.
    """
    authentication_classes = [] # بدون نیاز به احراز هویت
    
    def post(self, request):
        new_user = AppUser.objects.create()
        return Response({'user_key': str(new_user.user_key)}, status=status.HTTP_201_CREATED)


# --- ۲. اطلاعات فروشگاه ---
class StoreDetailView(APIView):
    authentication_classes = []
    
    def get(self, request):
        store = Store.objects.first()
        if not store:
            return Response({"detail": "اطلاعات فروشگاه ثبت نشده است."}, status=status.HTTP_404_NOT_FOUND)
        serializer = StoreSerializer(store)
        return Response(serializer.data)


# --- ۳. دسته‌بندی‌ها ---
class CategoryListView(APIView):
    authentication_classes = []
    
    def get(self, request):
        categories = Category.objects.all()
        serializer = CategorySerializer(categories, many=True)
        return Response(serializer.data)


# --- ۴. محصولات همراه با صفحه‌بندی و فیلترها ---
class ProductPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class ProductListView(APIView):
    authentication_classes = []
    
    def get(self, request):
        queryset = Product.objects.filter(is_available=True)
        
        # فیلتر دسته‌بندی
        category_id = request.query_params.get('category')
        if category_id:
            queryset = queryset.filter(category_id=category_id)
            
        # جستجو در نام، برند یا توضیحات
        search_query = request.query_params.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(title__icontains=search_query) | 
                Q(brand__icontains=search_query) | 
                Q(description__icontains=search_query)
            )
            
        # مرتب‌سازی
        sort = request.query_params.get('sort')
        if sort == 'price_asc':
            queryset = queryset.order_by('price')
        elif sort == 'price_desc':
            queryset = queryset.order_by('-price')
        elif sort == 'newest':
            queryset = queryset.order_by('-id')
        elif sort == 'discount_desc':
            queryset = queryset.order_by('-discount_percent')
        else:
            # تغییر در این بخش: افزودن مرتب‌سازی پیش‌فرض در صورت نبود هیچ پارامتری برای جلوگیری از هشدار جنگو
            queryset = queryset.order_by('id')
            
        paginator = ProductPagination()
        paginated_queryset = paginator.paginate_queryset(queryset, request)
        serializer = ProductSerializer(paginated_queryset, many=True)
        return paginator.get_paginated_response(serializer.data)
    

class ProductDetailView(APIView):
    authentication_classes = []
    
    def get(self, request, pk):
        try:
            product = Product.objects.get(pk=pk, is_available=True)
        except Product.DoesNotExist:
            return Response({"detail": "محصول یافت نشد."}, status=status.HTTP_404_NOT_FOUND)
        serializer = ProductSerializer(product)
        return Response(serializer.data)


# --- ۵. تجمیع صفحه اصلی (Home) ---
class HomeView(APIView):
    """
    برای بارگذاری یکجای اطلاعات صفحه اول فقط با ۱ درخواست.
    """
    authentication_classes = []
    
    def get(self, request):
        store = Store.objects.first()
        categories = Category.objects.all()[:8]  # نمایش محدود دسته‌بندی‌ها در هوم
        discount_products = Product.objects.filter(is_available=True, discount_percent__gt=0).order_by('-discount_percent')[:10]
        new_products = Product.objects.filter(is_available=True).order_by('-id')[:10]
        
        return Response({
            "store": StoreSerializer(store).data if store else {},
            "categories": CategorySerializer(categories, many=True).data,
            "discount_products": ProductSerializer(discount_products, many=True).data,
            "new_products": ProductSerializer(new_products, many=True).data,
        })


# --- ۶. محاسبه سبد خرید (Checkout) ---
class CheckoutView(APIView):
    authentication_classes = [XUserKeyAuthentication]
    permission_classes = [IsAuthenticatedAppUser]
    
    def post(self, request):
        items_data = request.data.get('items', [])
        delivery_type = request.data.get('delivery_type', 'delivery')
        
        if not items_data:
            return Response({"detail": "سبد خرید خالی است."}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            totals = calculate_checkout_totals(items_data, delivery_type)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
            
        return Response({
            "items_price": totals['items_price'],
            "discount": totals['discount'],
            "delivery_price": totals['delivery_price'],
            "total": totals['total']
        })


# --- ۷. ثبت نهایی سفارش ---
class OrderView(APIView):
    authentication_classes = [XUserKeyAuthentication]
    permission_classes = [IsAuthenticatedAppUser]
    
    def post(self, request):
        items_data = request.data.get('items', [])
        delivery_type = request.data.get('delivery_type', 'delivery')
        address_id = request.data.get('address_id')
        recipient_name = request.data.get('recipient_name')
        recipient_phone = request.data.get('recipient_phone')
        
        if not items_data:
            return Response({"detail": "لیست اقلام ارسالی خالی است."}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            # ۱. انجام محاسبات مالی و اعتبارسنجی موجودی در تراکنش
            with transaction.atomic():
                totals = calculate_checkout_totals(items_data, delivery_type)
                
                # بررسی صحت آدرس
                address = None
                if delivery_type == 'delivery':
                    if not address_id:
                        return Response({"detail": "انتخاب آدرس برای ارسال پیک الزامی است."}, status=status.HTTP_400_BAD_REQUEST)
                    try:
                        address = Address.objects.get(id=address_id, user=request.user)
                    except Address.DoesNotExist:
                        return Response({"detail": "آدرس مورد نظر یافت نشد."}, status=status.HTTP_404_NOT_FOUND)
                
                # ۲. ایجاد رکورد سفارش
                order = Order.objects.create(
                    user=request.user,
                    delivery_type=delivery_type,
                    address=address,
                    recipient_name=recipient_name,
                    recipient_phone=recipient_phone,
                    items_price=totals['items_price'],
                    discount=totals['discount'],
                    delivery_price=totals['delivery_price'],
                    total=totals['total']
                )
                
                # ۳. ذخیره اقلام سفارش و کسر از موجودی انبار
                for validated_item in totals['validated_items']:
                    product = validated_item['product']
                    count = validated_item['count']
                    
                    # ذخیره در جدول اقلام فاکتور
                    OrderItem.objects.create(
                        order=order,
                        product=product,
                        product_title=product.title,
                        count=count,
                        price_at_purchase=validated_item['price_at_purchase']
                    )
                    
                    # کسر موجودی انبار
                    product.stock -= count
                    product.save()
                    
            return Response({
                "order_id": order.id,
                "status": order.status,
                "detail": "سفارش شما با موفقیت ثبت شد."
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


# --- ۸. پروفایل و اطلاعات همراه کاربر ---
class ProfileView(APIView):
    authentication_classes = [XUserKeyAuthentication]
    permission_classes = [IsAuthenticatedAppUser]
    
    def get(self, request):
        user = request.user
        addresses = Address.objects.filter(user=user)
        recipients = Recipient.objects.filter(user=user)
        orders = Order.objects.filter(user=user).order_by('-id')
        
        default_address = addresses.filter(is_default=True).first()
        default_recipient = recipients.filter(is_default=True).first()
        
        return Response({
            "user": AppUserSerializer(user).data,
            "default_address": AddressSerializer(default_address).data if default_address else None,
            "addresses": AddressSerializer(addresses, many=True).data,
            "default_recipient": RecipientSerializer(default_recipient).data if default_recipient else None,
            "recipients": RecipientSerializer(recipients, many=True).data,
            "orders": OrderSerializer(orders, many=True).data
        })
        
    def patch(self, request):
        user = request.user
        serializer = AppUserSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# --- ۹. مدیریت آدرس‌ها و گیرنده‌ها ---
class AddressViewSet(viewsets.ModelViewSet):
    serializer_class = AddressSerializer
    authentication_classes = [XUserKeyAuthentication]
    permission_classes = [IsAuthenticatedAppUser]
    
    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)
        
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class RecipientViewSet(viewsets.ModelViewSet):
    serializer_class = RecipientSerializer
    authentication_classes = [XUserKeyAuthentication]
    permission_classes = [IsAuthenticatedAppUser]
    
    def get_queryset(self):
        return Recipient.objects.filter(user=self.request.user)
        
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


# --- ۱۰. تنظیمات عمومی برنامه ---
class SettingsView(APIView):
    authentication_classes = []
    
    def get(self, request):
        return Response({
            "min_supported_version": "1.0.0",
            "is_under_maintenance": False,
            "contact_support": "021-XXXXXX",
            "terms_url": "https://example.com/terms"
        })