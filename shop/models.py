import uuid
from django.db import models

class AppUser(models.Model):
    user_key = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    name = models.CharField(max_length=255, null=True, blank=True)
    phone = models.CharField(max_length=20, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name or str(self.user_key)


class Store(models.Model):
    name = models.CharField(max_length=255)
    logo_url = models.URLField(null=True, blank=True)
    phone = models.CharField(max_length=20)
    working_hours = models.CharField(max_length=100)
    min_order_amount = models.DecimalField(max_digits=10, decimal_places=0, default=0)
    base_delivery_fee = models.DecimalField(max_digits=10, decimal_places=0, default=0)
    is_open = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Category(models.Model):
    title = models.CharField(max_length=255)

    def __str__(self):
        return self.title


class Product(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    title = models.CharField(max_length=255)
    image_url = models.URLField(null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=0)
    discount_percent = models.IntegerField(default=0)  # درصد تخفیف مثلاً 15 برای 15%
    is_available = models.BooleanField(default=True)
    description = models.TextField(null=True, blank=True)
    weight_or_volume = models.CharField(max_length=100, null=True, blank=True)
    brand = models.CharField(max_length=100, null=True, blank=True)
    stock = models.IntegerField(default=0)

    @property
    def discounted_price(self):
        if self.discount_percent > 0:
            discount_amount = (self.price * self.discount_percent) / 100
            return self.price - discount_amount
        return self.price

    def __str__(self):
        return self.title


class Address(models.Model):
    user = models.ForeignKey(AppUser, on_delete=models.CASCADE, related_name='addresses')
    title = models.CharField(max_length=100)  # مثل خانه، محل کار
    address = models.TextField()
    is_default = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if self.is_default:
            Address.objects.filter(user=self.user).update(is_default=False)
        super().save(*args, **kwargs)


class Recipient(models.Model):
    user = models.ForeignKey(AppUser, on_delete=models.CASCADE, related_name='recipients')
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20)
    is_default = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if self.is_default:
            Recipient.objects.filter(user=self.user).update(is_default=False)
        super().save(*args, **kwargs)


class Order(models.Model):
    STATUS_CHOICES = (
        ('waiting', 'در انتظار تایید'),
        ('preparing', 'در حال آماده‌سازی'),
        ('shipped', 'تحویل به پیک'),
        ('delivered', 'تحویل داده شد'),
        ('canceled', 'لغو شده'),
    )
    user = models.ForeignKey(AppUser, on_delete=models.CASCADE, related_name='orders')
    delivery_type = models.CharField(max_length=20, default='delivery')  # delivery یا pickup
    address = models.ForeignKey(Address, on_delete=models.SET_NULL, null=True, blank=True)
    recipient_name = models.CharField(max_length=255, null=True, blank=True)
    recipient_phone = models.CharField(max_length=20, null=True, blank=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='waiting')
    
    # مبالغ نهایی ثبت‌شده در زمان خرید
    items_price = models.DecimalField(max_digits=12, decimal_places=0)
    discount = models.DecimalField(max_digits=12, decimal_places=0)
    delivery_price = models.DecimalField(max_digits=12, decimal_places=0)
    total = models.DecimalField(max_digits=12, decimal_places=0)
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"سفارش شماره {self.id} - کاربر {self.user.id}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    product_title = models.CharField(max_length=255)  # برای نگهداری نام محصول در صورت حذف آن
    count = models.IntegerField(default=1)
    price_at_purchase = models.DecimalField(max_digits=10, decimal_places=0)  # قیمت با تخفیف زمان خرید

    def __str__(self):
        return f"{self.count} عدد {self.product_title}"