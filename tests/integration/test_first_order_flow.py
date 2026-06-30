from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from shop.models import Category, Product, Store, Address

class FirstOrderIntegrationTestCase(APITestCase):
    def setUp(self):
        # تغییر در این بخش: حذف فیلد price و افزودن فیلدهای phone و working_hours
        self.store = Store.objects.create(
            name="فروشگاه مرکزی",
            phone="021-12345678",
            working_hours="8:00 - 22:00",
            base_delivery_fee=30000,
            min_order_amount=10000
        )
        self.category = Category.objects.create(title="مواد غذایی")
        self.product = Product.objects.create(
            category=self.category, title="نان تست", price=40000, discount_percent=10, stock=20
        )

    def test_complete_user_journey_flow(self):
        # گام اول: ثبت کاربر جدید و دریافت شناسه امنیتی
        user_url = reverse('user-create')
        user_res = self.client.post(user_url)
        self.assertEqual(user_res.status_code, status.HTTP_201_CREATED)
        user_key = user_res.data['user_key']
        
        # اتصال شناسه به درخواست‌های بعدی کلاینت
        self.client.credentials(HTTP_X_USER_KEY=user_key)
        
        # گام دوم: دریافت صفحه اصلی و مشاهده محصولات تخفیفی
        home_url = reverse('home')
        home_res = self.client.get(home_url)
        self.assertEqual(home_res.status_code, status.HTTP_200_OK)
        
        # گام سوم: کاربر آدرس خود را ثبت می‌کند
        addr_url = reverse('address-list') # روت پیش‌فرض ViewSet آدرس‌ها
        addr_res = self.client.post(addr_url, {
            "title": "خانه",
            "address": "تهران، میدان ونک...",
            "is_default": True
        }, format='json')
        self.assertEqual(addr_res.status_code, status.HTTP_201_CREATED)
        address_id = addr_res.data['id']
        
        # گام چهارم: ارسال سبد خرید برای پیش‌فاکتور (Checkout)
        checkout_url = reverse('checkout')
        checkout_data = {
            "delivery_type": "delivery",
            "address_id": address_id,
            "items": [{"product_id": self.product.id, "count": 2}]
        }
        checkout_res = self.client.post(checkout_url, checkout_data, format='json')
        self.assertEqual(checkout_res.status_code, status.HTTP_200_OK)
        # قیمت کالا: 2 * 36,000 = 72,000 | پیک: 30,000 | جمع نهایی: 102,000
        self.assertEqual(checkout_res.data['total'], 102000)

        # گام پنجم: نهایی کردن سفارش
        order_url = reverse('orders')
        order_res = self.client.post(order_url, checkout_data, format='json')
        self.assertEqual(order_res.status_code, status.HTTP_201_CREATED)
        
        # گام ششم: بررسی مشخص شدن این سفارش درون پروفایل کاربر
        profile_url = reverse('profile')
        profile_res = self.client.get(profile_url)
        self.assertEqual(profile_res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(profile_res.data['orders']), 1)
# تغییر این خط: تبدیل رشته دریافتی از سریالایزر به عدد صحیح (int) جهت مقایسه درست
        self.assertEqual(int(profile_res.data['orders'][0]['total']), 102000)