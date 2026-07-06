from django.core.cache import cache
from rest_framework import authentication
from rest_framework import exceptions
from rest_framework.permissions import BasePermission
from .models import AppUser

class XUserKeyAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request):
        user_key = request.META.get('HTTP_X_USER_KEY')
        if not user_key:
            return None
        
        # ۱. بررسی هویت کاربر از طریق کش
        cache_key = f"user_key_{user_key}"
        app_user = cache.get(cache_key)
        
        if not app_user:
            # ۲. اگر در کش نبود، یک بار دیتابیس را صدا بزن و ذخیره کن
            try:
                app_user = AppUser.objects.get(user_key=user_key)
                cache.set(cache_key, app_user, timeout=3600)  # ذخیره برای ۱ ساعت
            except (AppUser.DoesNotExist, ValueError):
                raise exceptions.AuthenticationFailed('شناسه کاربری معتبر نیست.')
        
        return (app_user, None)


class IsAuthenticatedAppUser(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and isinstance(request.user, AppUser))