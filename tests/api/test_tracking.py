import uuid
from django.urls import reverse
from django.core.cache import cache
from rest_framework.test import APITestCase
from rest_framework import status
from shop.models import AppUser, Order

class OrderTrackingAPITestCase(APITestCase):
    def setUp(self):
        # پاک کردن کش قبل از اجرای هر تست جهت اطمینان از صحت محاسبات کش
        cache.clear()
        
        # ایجاد کاربر تستی اول و ست کردن هدر احراز هویت
        self.user_a = AppUser.objects.create(name="کاربر الف")
        self.client.credentials(HTTP_X_USER_KEY=str(self.user_a.user_key))
        
        # ثبت سفارش تستی برای کاربر اول
        self.order_a = Order.objects.create(
            user=self.user_a,
            delivery_type='delivery',
            items_price=100000,
            discount=0,
            delivery_price=30000,
            total=130000,
            status='waiting',
            courier_status='pending'
        )

    def test_tracking_unauthorized_fails(self):
        """تست امنیت: درخواست ردیابی بدون هدر احراز هویت باید خطای ۴۰۳ یا ۴۰۱ بدهد."""
        self.client.credentials()  # حذف هدرهای احراز هویت
        url = reverse('order-tracking', kwargs={'pk': self.order_a.id})
        response = self.client.get(url)
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def test_cannot_track_other_users_order(self):
        """
        تست امنیت و جداسازی داده‌ها:
        کاربر الف نباید بتواند سفارش کاربر ب را ردیابی کند (باید خطای ۴۰۴ بگیرد تا وجود سفارش لو نرود).
        """
        # ایجاد کاربر دوم و سفارش او
        user_b = AppUser.objects.create(name="کاربر ب")
        order_b = Order.objects.create(
            user=user_b,
            delivery_type='delivery',
            items_price=50000,
            discount=0,
            delivery_price=30000,
            total=80000,
            status='waiting',
            courier_status='pending'
        )
        
        # تلاش کاربر الف برای ردیابی سفارش کاربر ب
        url = reverse('order-tracking', kwargs={'pk': order_b.id})
        response = self.client.get(url)
        
        # با اینکه سفارش وجود دارد، اما چون متعلق به این کاربر نیست باید ۴۰۴ دریافت شود
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_tracking_endpoint_populates_and_uses_cache(self):
        """
        تست کارایی (Performance):
        تست صحت ذخیره در کَش و اطمینان از اینکه درخواست دوم بدون کوئری دیتابیس (Query Count = 0) اجرا می‌شود.
        """
        url = reverse('order-tracking', kwargs={'pk': self.order_a.id})
        
        # خالی کردن مجدد کش برای اطمینان
        cache.clear()
        
        # درخواست اول: کش خالی است، پس باید دیتابیس خوانده شود
        response1 = self.client.get(url)
        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        self.assertEqual(response1.data['status'], 'waiting')
        self.assertEqual(response1.data['courier_status'], 'pending')
        
        # بررسی اینکه فیلد کش به درستی ساخته شده است
        cache_key = f"order_tracking_{self.order_a.id}"
        self.assertIsNotNone(cache.get(cache_key))
        
        # درخواست دوم: اطلاعات باید مستقیماً از حافظه کش خوانده شوند بدون زدن هیچ کوئری به دیتابیس
        with self.assertNumQueries(0):
            response2 = self.client.get(url)
            self.assertEqual(response2.status_code, status.HTTP_200_OK)
            self.assertEqual(response2.data['status'], 'waiting')
            self.assertEqual(response2.data['courier_status'], 'pending')

    def test_signal_invalidates_and_updates_cache_on_save(self):
        """
        تست یکپارچگی داده‌ها (Data Integrity):
        سیگنال تغییر وضعیت باید در لحظه، حافظه کش را رونویسی کند تا کلاینت هرگز دیتای منقضی شده نبیند.
        """
        url = reverse('order-tracking', kwargs={'pk': self.order_a.id})
        
        # لود اولیه برای ایجاد کش
        self.client.get(url)
        
        # تغییر فیزیکی وضعیت سفارش در دیتابیس (شبیه‌سازی تغییر وضعیت توسط ادمین)
        self.order_a.status = 'preparing'
        self.order_a.courier_status = 'moving_to_store'
        self.order_a.save()  # در این لحظه سیگنال جنگو باید کش را به‌روز کند
        
        # درخواست سوم: باید بلافاصله وضعیت جدید را بدون دخالت دیتابیس (از کش) برگرداند
        with self.assertNumQueries(0):
            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data['status'], 'preparing')
            self.assertEqual(response.data['courier_status'], 'moving_to_store')