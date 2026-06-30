from django.urls import reverse
from rest_framework.test import APITestCase
from shop.models import AppUser, Category, Product, Store, Address, Recipient, Order

class DatabasePerformanceTestCase(APITestCase):
    def setUp(self):
        self.store = Store.objects.create(name="شعبه ۱", base_delivery_fee=10000)
        self.user = AppUser.objects.create()
        self.category = Category.objects.create(title="تنقلات")
        
        # ثبت ۱۲ محصول
        for i in range(12):
            Product.objects.create(
                category=self.category, title=f"چیپس {i}", price=15000, stock=50
            )
            
        # ثبت آدرس‌ها و گیرنده‌ها
        for i in range(3):
            Address.objects.create(user=self.user, title=f"آدرس {i}", address="...")
            Recipient.objects.create(user=self.user, name=f"گیرنده {i}", phone="0912...")

        self.client.credentials(HTTP_X_USER_KEY=str(self.user.user_key))

    def test_home_endpoint_query_count(self):
        """تست عدم تجاوز کوئری‌های دیتابیس در اندپوینت صفحه اصلی از حد نصاب ۵ کوئری"""
        url = reverse('home')
        with self.assertNumQueries(4): # با توجه به کوئری‌های Store، Category، New و Discount
            self.client.get(url)

    def test_profile_endpoint_query_count(self):
        """تست کارایی صفحه پروفایل و عدم تجاوز از حداکثر ۷ کوئری"""
        url = reverse('profile')
        with self.assertNumQueries(6): # برای جداول User، Addresses، Recipients، Orders و OrderItems
            self.client.get(url)