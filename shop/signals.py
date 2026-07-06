from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.cache import cache
from .models import Order

@receiver(post_save, sender=Order)
def update_order_tracking_cache(sender, instance, **kwargs):
    cache_key = f"order_tracking_{instance.id}"
    tracking_data = {
        "order_id": instance.id,
        "user_id": instance.user_id,  # اضافه شدن برای اعتبار سنجی هویت در لایه کش
        "status": instance.status,
        "status_display": instance.get_status_display(),
        "courier_status": instance.courier_status,
        "courier_status_display": instance.get_courier_status_display(),
        "delivery_type": instance.delivery_type,
    }
    cache.set(cache_key, tracking_data, timeout=1800)