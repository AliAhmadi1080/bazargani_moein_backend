import uuid
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status

class UsersAPITestCase(APITestCase):
    def test_create_user_success(self):
        """تست ایجاد کاربر جدید و تایید فرمت UUID"""
        url = reverse('user-create')
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('user_key', response.data)
        
        # بررسی صحت فرمت UUID
        try:
            uuid_obj = uuid.UUID(response.data['user_key'])
        except ValueError:
            self.fail("ساختار برگشت‌داده شده UUID معتبر نیست.")

    def test_users_invalid_methods(self):
        """تست ممانعت از اعمال متدهای غیرمجاز بر روی اندپوینت‌ها"""
        url = reverse('user-create')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)