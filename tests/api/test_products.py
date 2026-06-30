from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from shop.models import Category, Product


class ProductsAPITestCase(APITestCase):
    def setUp(self):
        self.category = Category.objects.create(title="نوشیدنی")
        for i in range(25):
            Product.objects.create(
                category=self.category,
                title=f"نوشابه {i}",
                price=10000 + (i * 1000),
                discount_percent=5 if i % 2 == 0 else 0,
                stock=100
            )

    def test_products_pagination_and_schema(self):
        """تست بررسی ساختار خروجی و صفحه‌بندی محصولات"""
        url = reverse('product-list')
        response = self.client.get(url, {'page': 1, 'page_size': 10})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 10)
        
        # صحت وجود فیلدها حتی در صورت عدم تخفیف
        item = response.data['results'][0]
        self.assertIn('id', item)
        self.assertIn('discount_percent', item)
        self.assertIn('discounted_price', item)

    def test_products_edge_case_pages(self):
        """تست صفحات نامعتبر و صفحات خالی"""
        url = reverse('product-list')
        # صفحه بسیار بزرگ
        response = self.client.get(url, {'page': 9999})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        
        # صفحه منفی
        response = self.client.get(url, {'page': -1})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)