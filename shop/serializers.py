from rest_framework import serializers
from .models import AppUser, Store, Category, Product, Address, Recipient, Order, OrderItem

class AppUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = AppUser
        fields = ['user_key', 'name', 'phone']


class StoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Store
        fields = ['name', 'logo_url', 'phone', 'working_hours', 'min_order_amount', 'base_delivery_fee', 'is_open']


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'title']


class ProductSerializer(serializers.ModelSerializer):
    discounted_price = serializers.ReadOnlyField()

    class Meta:
        model = Product
        fields = [
            'id', 'title', 'image_url', 'price', 'discount_percent', 
            'discounted_price', 'is_available', 'description', 
            'weight_or_volume', 'brand', 'stock'
        ]


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = ['id', 'title', 'address', 'is_default']
        read_only_fields = ['id']


class RecipientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recipient
        fields = ['id', 'name', 'phone', 'is_default']
        read_only_fields = ['id']


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'product_title', 'count', 'price_at_purchase']


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    address = AddressSerializer(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'delivery_type', 'address', 'recipient_name', 'recipient_phone',
            'status', 'status_display', 'items_price', 'discount', 
            'delivery_price', 'total', 'created_at', 'items'
        ]