from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.cache import cache
from .models import Order

@receiver(post_save, sender=Order)
def update_order_tracking_cache(sender, instance, **kwargs):
    """
    هر زمان سفارشی در دیتابیس ذخیره یا ویرایش شد (مثلاً تغییر وضعیت توسط مدیر)،
    کش مربوط به ردیابی آن بلافاصله با اطلاعات جدید رونویسی می‌شود.
    """
    cache_key = f"order_tracking_{instance.id}"
    tracking_data = {
        "order_id": instance.id,
        "status": instance.status,
        "status_display": instance.get_status_display(),
        "courier_status": instance.courier_status,
        "courier_status_display": instance.get_courier_status_display(),
        "delivery_type": instance.delivery_type,
    }
    # رونویسی در کش
    cache.set(cache_key, tracking_data, timeout=1800)