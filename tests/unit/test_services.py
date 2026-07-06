from django.test import TestCase
from rest_framework.exceptions import ValidationError
from shop.models import Category, Product, Store
from shop.services import calculate_checkout_totals

class ServicesUnitTestCase(TestCase):
    def setUp(self):
        # تغییر در این بخش: حذف فیلد price و افزودن فیلدهای phone و working_hours
        self.store = Store.objects.create(
            name="فروشگاه مرکزی",
            phone="021-12345678",
            working_hours="8:00 - 22:00",
            base_delivery_fee=30000,
            min_order_amount=50000
        )
        self.category = Category.objects.create(title="کالای اساسی")
        self.product1 = Product.objects.create(
            category=self.category, title="برنج", price=100000, discount_percent=10, stock=5
        )
        
    def test_calculate_checkout_totals_valid(self):
        """تست محاسبه مالی برای اقلام معتبر سبد خرید"""
        items = [{"product_id": self.product1.id, "count": 2}]
        totals = calculate_checkout_totals(items, "delivery")
        
        # قیمت اصلی: 200,000 | تخفیف: 20,000 | پیک: 30,000 | نهایی: 210,000
        self.assertEqual(totals['items_price'], 200000)
        self.assertEqual(totals['discount'], 20000)
        self.assertEqual(totals['delivery_price'], 30000)
        self.assertEqual(totals['total'], 210000)

    def test_calculate_checkout_totals_out_of_stock(self):
        """تست عدم تایید نهایی در صورت درخواست بیش از موجودی انبار"""
        items = [{"product_id": self.product1.id, "count": 10}]
        with self.assertRaises(ValidationError):
            calculate_checkout_totals(items, "delivery")

    def test_calculate_checkout_totals_under_min_amount(self):
        """تست خطا در صورتی که مبلغ نهایی زیر حداقل سفارش فروشگاه باشد"""
        self.product1.price = 10000
        self.product1.discount_percent = 0
        self.product1.save()
        
        items = [{"product_id": self.product1.id, "count": 1}]
        with self.assertRaises(ValidationError):
            calculate_checkout_totals(items, "delivery")

    # افزودن این متدها به کلاس ServicesUnitTestCase در shop/test_services.py

    def test_calculate_checkout_totals_when_store_closed(self):
        """تست ایجاد خطا در صورت محاسبه سبد خرید زمانی که فروشگاه بسته است"""
        self.store.is_open = False
        self.store.save()
        
        items = [{"product_id": self.product1.id, "count": 1}]
        
        with self.assertRaises(ValidationError) as context:
            calculate_checkout_totals(items, "delivery")
            
        self.assertIn("فروشگاه در حال حاضر بسته است", str(context.exception))

    def test_calculate_checkout_totals_when_store_open(self):
        """تست عبور موفق محاسبات زمانی که فروشگاه باز است"""
        self.store.is_open = True
        self.store.save()
        
        items = [{"product_id": self.product1.id, "count": 1}]
        totals = calculate_checkout_totals(items, "delivery")
        
        self.assertEqual(totals['total'], 120000) # (100k - 10k discount) + 30k delivery = 120k