# shop/services.py

from rest_framework.exceptions import ValidationError
from .models import Product, Store

def calculate_checkout_totals(items_data, delivery_type):
    # ۱. بررسی باز بودن فروشگاه در بالاترین لایه برای جلوگیری از کوئری‌های اضافه
    store = Store.objects.first()
    if store and not store.is_open:
        raise ValidationError("فروشگاه در حال حاضر بسته است و امکان ثبت سفارش وجود ندارد.")

    items_price = 0
    discount = 0
    validated_items = []
    
    for item in items_data:
        product_id = item.get('product_id')
        count = int(item.get('count', 1))
        
        try:
            product = Product.objects.get(id=product_id, is_available=True)
        except Product.DoesNotExist:
            raise ValidationError(f"محصول با شناسه {product_id} یافت نشد یا در دسترس نیست.")
            
        if product.stock < count:
            raise ValidationError(f"موجودی محصول '{product.title}' کافی نیست. موجودی فعلی: {product.stock}")
            
        raw_price = product.price * count
        discounted_price = product.discounted_price * count
        
        items_price += raw_price
        discount += (raw_price - discounted_price)
        
        validated_items.append({
            'product': product,
            'count': count,
            'price_at_purchase': product.discounted_price
        })
        
    delivery_price = 0
    if delivery_type == 'delivery' and store:
        delivery_price = store.base_delivery_fee
        
    total = items_price - discount + delivery_price
    
    if store and (items_price - discount) < store.min_order_amount:
         raise ValidationError(f"حداقل مبلغ سفارش برای ارسال {store.min_order_amount} تومان است.")

    return {
        'items_price': int(items_price),
        'discount': int(discount),
        'delivery_price': int(delivery_price),
        'total': int(total),
        'validated_items': validated_items
    }