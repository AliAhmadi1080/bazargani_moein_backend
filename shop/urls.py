from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    UserCreateView, StoreDetailView, CategoryListView, 
    ProductListView, ProductDetailView, HomeView, 
    CheckoutView, OrderView, ProfileView, 
    AddressViewSet, RecipientViewSet, SettingsView
)

router = DefaultRouter()
router.register(r'addresses', AddressViewSet, basename='address')
router.register(r'recipients', RecipientViewSet, basename='recipient')

urlpatterns = [
    # عمومی (بدون User Key)
    path('users/', UserCreateView.as_view(), name='user-create'),
    path('store/', StoreDetailView.as_view(), name='store-detail'),
    path('categories/', CategoryListView.as_view(), name='category-list'),
    path('products/', ProductListView.as_view(), name='product-list'),
    path('products/<int:pk>/', ProductDetailView.as_view(), name='product-detail'),
    path('settings/', SettingsView.as_view(), name='settings'),
    
    # تجمیعی و اختصاصی کاربر (نیاز به هدر X-USER-KEY)
    path('home/', HomeView.as_view(), name='home'),
    path('checkout/', CheckoutView.as_view(), name='checkout'),
    path('orders/', OrderView.as_view(), name='orders'),
    path('profile/', ProfileView.as_view(), name='profile'),
    
    # آدرس‌ها و گیرنده‌ها (ViewSet CRUD)
    path('', include(router.urls)),
]