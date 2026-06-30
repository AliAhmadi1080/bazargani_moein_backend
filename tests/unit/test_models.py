from django.test import TestCase
from shop.models import AppUser, Category, Product, Address, Recipient

class ModelUnitTestCase(TestCase):
    def setUp(self):
        self.user = AppUser.objects.create()
        self.category = Category.objects.create(title="لبنیات")

    def test_product_discounted_price_calculation(self):
        """تست محاسبه درست قیمت پس از تخفیف بر روی مدل محصول"""
        product_no_discount = Product.objects.create(
            category=self.category, title="شیر معمولی", price=10000, discount_percent=0, stock=10
        )
        product_with_discount = Product.objects.create(
            category=self.category, title="شیر تخفیف‌دار", price=20000, discount_percent=15, stock=10
        )
        self.assertEqual(product_no_discount.discounted_price, 10000)
        self.assertEqual(product_with_discount.discounted_price, 17000)

    def test_address_default_logic(self):
        """
        تست منطق آدرس پیش‌فرض:
        تغییر آدرس پیش‌فرض جدید باید آدرس‌های قبلی را غیرفعال کند.
        """
        addr1 = Address.objects.create(user=self.user, title="خانه", address="تهران...", is_default=True)
        self.assertTrue(addr1.is_default)

        addr2 = Address.objects.create(user=self.user, title="محل کار", address="تهران...", is_default=False)
        self.assertFalse(addr2.is_default)

        # ثبت آدرس سوم به عنوان پیش‌فرض جدید
        addr3 = Address.objects.create(user=self.user, title="خانه دوم", address="تهران...", is_default=True)
        
        addr1.refresh_from_db()
        addr2.refresh_from_db()
        
        self.assertFalse(addr1.is_default)
        self.assertFalse(addr2.is_default)
        self.assertTrue(addr3.is_default)