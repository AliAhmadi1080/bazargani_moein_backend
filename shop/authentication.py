from rest_framework import authentication
from rest_framework import exceptions
from rest_framework.permissions import BasePermission
from .models import AppUser

class XUserKeyAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request):
        user_key = request.META.get('HTTP_X_USER_KEY')
        if not user_key:
            return None  # اگر هدر نبود، به عنوان کاربر ناشناس عبور می‌دهد (برای متدهای عمومی)
        
        try:
            app_user = AppUser.objects.get(user_key=user_key)
        except (AppUser.DoesNotExist, ValueError):
            raise exceptions.AuthenticationFailed('شناسه کاربری معتبر نیست.')
        
        return (app_user, None)


class IsAuthenticatedAppUser(BasePermission):
    """
    مجوز دسترسی برای Endpointهایی که وجود User Key در آن‌ها اجباری است.
    """
    def has_permission(self, request, view):
        return bool(request.user and isinstance(request.user, AppUser))