from django.contrib import admin
from django.utils.safestring import mark_safe
from django.urls import reverse
from django.utils.html import format_html
from .models import AppUser, Store, Category, Product, Address, Recipient, Order, OrderItem

# --- ۱. ثبت خطی (Tabular Inlines) برای مدیریت یکپارچه ---

class AddressInline(admin.TabularInline):
    model = Address
    extra = 0
    fields = ['title', 'address', 'is_default']


class RecipientInline(admin.TabularInline):
    model = Recipient
    extra = 0
    fields = ['name', 'phone', 'is_default']


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    fields = ['product', 'product_title', 'count', 'price_at_purchase']
    readonly_fields = ['product_title', 'price_at_purchase']
    
    def has_add_permission(self, request, obj=None):
        # جلوگیری از اضافه کردن دستی آیتم به فاکتور ثبت شده جهت حفظ یکپارچگی مالی
        return False


# --- ۲. طراحی پیشرفته پنل کاربران (AppUser) ---

@admin.register(AppUser)
class AppUserAdmin(admin.ModelAdmin):
    list_display = ['id', 'user_key', 'name', 'phone', 'created_at']
    search_fields = ['id', 'user_key', 'name', 'phone']
    list_filter = ['created_at']
    readonly_fields = ['user_key', 'created_at']
    
    # نمایش آدرس‌ها و گیرنده‌های کاربر در صفحه ویرایش پروفایل کاربر
    inlines = [AddressInline, RecipientInline]


# --- ۳. طراحی پنل اطلاعات فروشگاه (Store) ---

@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    list_display = ['name', 'phone', 'working_hours', 'min_order_amount_formatted', 'base_delivery_fee_formatted', 'is_open']
    list_editable = ['is_open']
    
    fieldsets = [
        ('اطلاعات کلی و تماس', {
            'fields': ('name', 'logo_url', 'phone', 'working_hours')
        }),
        ('قوانین مالی و ارسال', {
            'fields': ('min_order_amount', 'base_delivery_fee', 'is_open')
        }),
    ]

    def min_order_amount_formatted(self, obj):
        return f"{int(obj.min_order_amount):,} تومان"
    min_order_amount_formatted.short_description = "حداقل خرید"

    def base_delivery_fee_formatted(self, obj):
        return f"{int(obj.base_delivery_fee):,} تومان"
    base_delivery_fee_formatted.short_description = "هزینه پایه پیک"


# --- ۴. طراحی پنل محصولات (Product) ---

# --- ۴. طراحی پنل محصولات (Product) ---

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    # تغییر در این خط: استفاده از فیلد عددی مستقیم 'price' به جای 'price_formatted'
    list_display = ['image_preview', 'title', 'category', 'price', 'discount_percent', 'discounted_price_formatted', 'stock', 'is_available']
    
    list_filter = ['category', 'is_available', 'discount_percent', 'brand']
    search_fields = ['title', 'brand', 'description']
    
    # حالا تمام فیلدهای این لیست به درستی در list_display بالا وجود دارند
    list_editable = ['price', 'discount_percent', 'stock', 'is_available']
    
    readonly_fields = ['image_preview', 'discounted_price_formatted']

    fieldsets = [
        ('مشخصات و دسته‌بندی کالا', {
            'fields': ('title', 'category', 'brand', 'weight_or_volume', 'description')
        }),
        ('مدیریت قیمت و انبار', {
            'fields': ('price', 'discount_percent', 'discounted_price_formatted', 'stock', 'is_available')
        }),
        ('رسانه و تصاویر', {
            'fields': ('image_url', 'image_preview')
        }),
    ]

    # پیش‌نمایش تصویر محصول در پنل مدیریت
    def image_preview(self, obj):
        if obj.image_url:
            return mark_safe(f'<img src="{obj.image_url}" width="45" height="45" style="object-fit: cover; border-radius: 4px; border: 1px solid #ddd;" />')
        return "بدون تصویر"
    image_preview.short_description = 'تصویر کالا'

    # این متد دیگر در list_display استفاده نمی‌شود، اما در بخش نمایش فیلدها (fieldsets) همچنان کاربرد دارد
    def price_formatted(self, obj):
        if obj.price is None:
            return "۰ تومان"
        return f"{int(obj.price):,} تومان"
    price_formatted.short_description = "قیمت اصلی"

    def discounted_price_formatted(self, obj):
        if obj.price is None or obj.discounted_price is None:
            return "پس از ثبت محاسبه می‌شود"
        return f"{int(obj.discounted_price):,} تومان"
    discounted_price_formatted.short_description = "قیمت با تخفیف"

    # عملیات‌های انبوه (Bulk Actions)
    actions = ['make_available', 'make_unavailable', 'set_discount_10', 'set_discount_20']

    def make_available(self, request, queryset):
        queryset.update(is_available=True)
    make_available.short_description = "موجود کردن کالاهای انتخاب شده"

    def make_unavailable(self, request, queryset):
        queryset.update(is_available=False)
    make_unavailable.short_description = "ناموجود کردن کالاهای انتخاب شده"

    def set_discount_10(self, request, queryset):
        queryset.update(discount_percent=10)
    set_discount_10.short_description = "اعمال تخفیف ۱۰٪ بر روی کالاهای انتخاب شده"

    def set_discount_20(self, request, queryset):
        queryset.update(discount_percent=20)
    set_discount_20.short_description = "اعمال تخفیف ۲۰٪ بر روی کالاهای انتخاب شده"

# --- ۵. طراحی پنل مدیریت سفارشات (Order) ---

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'user_link', 'recipient_name', 'status', 'total_formatted', 'delivery_type', 'created_at']
    list_filter = ['status', 'delivery_type', 'created_at']
    search_fields = ['id', 'recipient_name', 'recipient_phone', 'user__name', 'user__phone']
    
    # غیر قابل ویرایش کردن مشخصات مالی در پنل ادمین جهت عدم مغایرت با تراکنش‌های ثبت شده
    readonly_fields = ['id', 'user_link', 'items_price', 'discount', 'delivery_price', 'total', 'created_at']
    
    inlines = [OrderItemInline]

    fieldsets = [
        ('وضعیت فاکتور', {
            'fields': ('id', 'user_link', 'status', 'created_at')
        }),
        ('نحوه ارسال و اطلاعات تحویل‌گیرنده', {
            'fields': ('delivery_type', 'address', 'recipient_name', 'recipient_phone')
        }),
        ('جزییات تراکنش مالی', {
            'fields': ('items_price', 'discount', 'delivery_price', 'total')
        }),
    ]

    def total_formatted(self, obj):
        # بررسی خالی بودن فیلد قیمت نهایی در فرم جدید
        if obj.total is None:
            return "پس از ثبت محاسبه می‌شود"
        return f"{int(obj.total):,} تومان"
    total_formatted.short_description = "مبلغ پرداختی"

    # ساخت لینک پویای جابه‌جایی سریع از سفارش به پروفایل کاربر
    def user_link(self, obj):
        try:
            # بررسی ایمنی برای حالتی که سفارش هنوز ثبت نشده یا فاقد کاربر است (مانند فرم سفارش جدید)
            if not obj.pk or not obj.user:
                return "کاربر مشخص نشده"
            
            url = reverse("admin:shop_appuser_change", args=[obj.user.id])
            return format_html('<a href="{}" style="font-weight: bold; color: #1e88e5;">{}</a>', url, obj.user.name or f"کاربر شماره {obj.user.id}")
        except Exception:
            return "کاربر مشخص نشده"
    user_link.short_description = "مشتری"

    # عملیات‌های انبوه برای تغییر سریع وضعیت سفارشات توسط مدیر
    actions = ['set_preparing', 'set_shipped', 'set_delivered', 'set_canceled']

    def set_preparing(self, request, queryset):
        queryset.update(status='preparing')
    set_preparing.short_description = "تغییر وضعیت به: در حال آماده‌سازی"

    def set_shipped(self, request, queryset):
        queryset.update(status='shipped')
    set_shipped.short_description = "تغییر وضعیت به: تحویل به پیک"

    def set_delivered(self, request, queryset):
        queryset.update(status='delivered')
    set_delivered.short_description = "تغییر وضعیت به: تحویل داده شد"

    def set_canceled(self, request, queryset):
        queryset.update(status='canceled')
    set_canceled.short_description = "تغییر وضعیت به: لغو شده"


# --- ۶. ثبت ساده بقیه مدل‌ها جهت دسترسی‌های موردی ---

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['id', 'title']
    search_fields = ['title']


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'title', 'address', 'is_default']
    list_filter = ['is_default']
    search_fields = ['title', 'address', 'user__name']


@admin.register(Recipient)
class RecipientAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'name', 'phone', 'is_default']
    list_filter = ['is_default']
    search_fields = ['name', 'phone', 'user__name']