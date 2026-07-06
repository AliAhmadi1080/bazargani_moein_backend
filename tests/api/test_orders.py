from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from unittest.mock import patch
from shop.models import AppUser, Category, Product, Address, Order, OrderItem

class OrdersAPITestCase(APITestCase):
    def setUp(self):
        self.user = AppUser.objects.create()
        self.category = Category.objects.create(title="لبنیات")
        self.product = Product.objects.create(
            category=self.category, title="ماست", price=50000, discount_percent=0, stock=5
        )
        self.address = Address.objects.create(
            user=self.user, title="محل ارسال", address="خیابان آزادی...", is_default=True
        )
        self.client.credentials(HTTP_X_USER_KEY=str(self.user.user_key))

    def test_create_order_success(self):
        """تست ثبت موفق سفارش و کسر صحیح از انبار کالا"""
        url = reverse('orders')
        print(url)
        data = {
            "delivery_type": "delivery",
            "address_id": self.address.id,
            "items": [{"product_id": self.product.id, "count": 2}]
        }
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 3) # موجودی باید از ۵ به ۳ رسیده باشد.
        self.assertEqual(Order.objects.count(), 1)

    def test_create_order_rollback_on_failure(self):
        """
        تست بازگشت تراکنش (Rollback):
        اگر وسط ثبت سفارش خطایی پیش آید، هیچ رکوردی نباید تغییر کند یا سفارش ایجاد شود.
        """
        url = reverse('orders')
        data = {
            "delivery_type": "delivery",
            "address_id": self.address.id,
            "items": [{"product_id": self.product.id, "count": 2}]
        }
        
        # با شبیه‌سازی خطا هنگام ذخیره‌سازی آیتم‌های سفارش
        with patch('shop.models.OrderItem.objects.create', side_effect=Exception("خطای ناگهانی دیتابیس")):
            response = self.client.post(url, data, format='json')
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            
            # موجودی انبار نباید کسر شده باشد
            self.product.refresh_from_db()
            self.assertEqual(self.product.stock, 5)
            # رکوردی نباید در جدول سفارشات ذخیره شده باشد
            self.assertEqual(Order.objects.count(), 0)

    # افزودن این متد به کلاس OrdersAPITestCase در shop/test_orders.py

    def test_order_courier_status_auto_assignment(self):
        """تست تخصیص خودکار وضعیت پیک بر اساس نوع تحویل حضوری یا ارسال با پیک"""
        # ثبت سفارش با پیک (Delivery)
        url = reverse('orders')
        data_delivery = {
            "delivery_type": "delivery",
            "address_id": self.address.id,
            "items": [{"product_id": self.product.id, "count": 1}]
        }
        res_delivery = self.client.post(url, data_delivery, format='json')
        self.assertEqual(res_delivery.status_code, status.HTTP_201_CREATED)
        order_delivery = Order.objects.get(id=res_delivery.data['order_id'])
        self.assertEqual(order_delivery.courier_status, 'pending')

        # ثبت سفارش تحویل حضوری (Pickup)
        data_pickup = {
            "delivery_type": "pickup",
            "items": [{"product_id": self.product.id, "count": 1}]
        }
        res_pickup = self.client.post(url, data_pickup, format='json')
        self.assertEqual(res_pickup.status_code, status.HTTP_201_CREATED)
        order_pickup = Order.objects.get(id=res_pickup.data['order_id'])
        self.assertEqual(order_pickup.courier_status, 'not_applicable')

    @patch('shop.views.calculate_checkout_totals')
    def test_create_order_concurrency_stock_depletion(self, mock_calculate):
        """
        تست جلوگیری از خرید همزمان (Race Condition):
        موجودی کالا ۵ عدد است. کاربر سفارش ۳ عدد را آغاز می‌کند.
        با شبیه‌سازی و پچ کردن محاسبات مالی، از فیلتر اولیه عبور کرده
        اما زمان ویرایش اتمیک دیتابیس به دلیل تغییر ناگهانی موجودی با خطا مواجه می‌شود.
        """
        # تنظیم خروجی ساختگی برای شبیه‌سازی تأیید اولیه سبد خرید
        mock_calculate.return_value = {
            'items_price': 150000,
            'discount': 0,
            'delivery_price': 30000,
            'total': 180000,
            'validated_items': [{
                'product': self.product,
                'count': 3,
                'price_at_purchase': self.product.discounted_price
            }]
        }

        # شبیه‌سازی خرید کاربر دیگر و کاهش ناگهانی موجودی به ۱ عدد در دیتابیس
        self.product.stock = 1
        self.product.save()

        url = reverse('orders')
        data = {
            "delivery_type": "delivery",
            "address_id": self.address.id,
            "items": [{"product_id": self.product.id, "count": 3}]
        }
        
        response = self.client.post(url, data, format='json')

        
        # بررسی لغو ثبت سفارش (Rollback کامل دیتابیس)
        self.assertEqual(Order.objects.count(), 0)
        self.assertEqual(OrderItem.objects.count(), 0)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error_code'], 'OUT_OF_STOCK')
        
        # تبدیل مقدار رشته‌ای ErrorDetail به int جهت مقایسه عددی صحیح
        self.assertEqual(int(response.data['product_id']), self.product.id)
