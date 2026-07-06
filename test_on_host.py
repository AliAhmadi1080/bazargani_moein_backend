import sys
import requests
import argparse

def run_smoke_tests(base_url):
    base_url += '/api/'
    # حذف اسلش آخر در صورت وجود برای یکپارچگی آدرس‌ها
    if base_url.endswith('/'):
        base_url = base_url[:-1]

    print(f"🚀 شروع تست صحت عملکرد روی هاست: {base_url}\n" + "="*50)
    
    passed_tests = 0
    total_tests = 0
    user_key = None

    def assert_status(response, expected_statuses, test_name):
        nonlocal passed_tests, total_tests
        total_tests += 1
        status_code = response.status_code
        
        # اگر وضعیت دریافتی جزو وضعیت‌های مورد انتظار بود
        if status_code in expected_statuses:
            print(f"✅ {test_name}: موفق (کد {status_code})")
            passed_tests += 1
            return True
        else:
            print(f"❌ {test_name}: ناموفق! (انتظار {expected_statuses} داشتیم ولی کد {status_code} دریافت شد)")
            # نمایش جزییات خطا برای عیب‌یابی راحت‌تر
            try:
                print(f"   پیام سرور: {response.json()}")
            except Exception:
                print(f"   متن پاسخ: {response.text[:200]}")
            return False

    # ۱. تست اتصال اولیه و تنظیمات (GET /settings/)
    try:
        res = requests.get(f"{base_url}/settings/")
        assert_status(res, [200], "۱. اتصال به اندپوینت تنظیمات (/settings/)")
    except requests.exceptions.ConnectionError:
        print(f"🚨 خطا: امکان برقراری ارتباط با هاست {base_url} وجود ندارد. مطمئن شوید سرور روشن و آدرس درست است.")
        sys.exit(1)

    # ۲. تست دریافت اطلاعات فروشگاه (GET /store/)
    res_store = requests.get(f"{base_url}/store/")
    assert_status(res_store, [200, 404], "۲. دریافت اطلاعات فروشگاه (/store/)")

    # ۳. تست دریافت دسته‌بندی‌ها (GET /categories/)
    res_cat = requests.get(f"{base_url}/categories/")
    assert_status(res_cat, [200], "۳. دریافت لیست دسته‌بندی‌ها (/categories/)")

    # ۴. تست دریافت محصولات (GET /products/)
    res_prod = requests.get(f"{base_url}/products/")
    assert_status(res_prod, [200], "۴. دریافت لیست محصولات (/products/)")

    # ۵. تست ساخت کاربر جدید و دریافت کلید امنیتی (POST /users/)
    res_user = requests.post(f"{base_url}/users/")
    if assert_status(res_user, [201], "۵. ثبت کاربر جدید (POST /users/)"):
        try:
            user_key = res_user.json().get('user_key')
            print(f"   🔑 شناسه کاربری ایجاد شده: {user_key}")
        except Exception:
            print("   ⚠️ خطا در استخراج user_key از پاسخ سرور")

    # تست‌های نیازمند هدر احراز هویت
    if user_key:
        headers = {'X-USER-KEY': user_key}

        # ۶. تست صفحه اصلی تجمیعی با هدر کاربر (GET /home/)
        res_home = requests.get(f"{base_url}/home/", headers=headers)
        assert_status(res_home, [200], "۶. دریافت اطلاعات صفحه اصلی تجمیعی (/home/)")

        # ۷. تست امنیت: تلاش برای دسترسی به پروفایل بدون هدر (باید ۴۰۱ یا ۴۰۳ بدهد)
        res_profile_no_header = requests.get(f"{base_url}/profile/")
        assert_status(res_profile_no_header, [401, 403], "۷. تست امنیت: تلاش برای دسترسی به پروفایل بدون هدر")

        # ۸. تست دسترسی به پروفایل با هدر صحیح (GET /profile/)
        res_profile = requests.get(f"{base_url}/profile/", headers=headers)
        assert_status(res_profile, [200], "۸. دریافت اطلاعات پروفایل با هدر معتبر (/profile/)")

        # ۹. تست ثبت آدرس جدید (POST /addresses/)
        address_data = {
            "title": "آدرس تستی هاست",
            "address": "خیابان تست، پلاک ۱",
            "is_default": True
        }
        res_addr = requests.post(f"{base_url}/addresses/", json=address_data, headers=headers)
        assert_status(res_addr, [201], "۹. ثبت آدرس جدید برای کاربر (/addresses/)")

        # ۱۰. تست پیش‌فاکتور (POST /checkout/)
        checkout_data = {
            "delivery_type": "delivery",
            "items": []
        }
        res_checkout = requests.post(f"{base_url}/checkout/", json=checkout_data, headers=headers)
        assert_status(res_checkout, [400], "۱۰. تست ساختار ورودی محاسبات مالی (/checkout/)")

        # ======================================================================
        # 🧪 پیاده‌سازی بخش جدید تست‌های یکپارچه‌سازی، ردیابی زنده و امنیت کَش 🧪
        # ======================================================================
        
        # استخراج آدرس ثبت شده در گام ۹ از متغیر مجزای res_addr
        address_id = None
        try:
            if res_addr.status_code == 201:
                address_id = res_addr.json().get('id')
        except Exception:
            pass

        # تلاش برای پیدا کردن محصولی با موجودی مناسب جهت ثبت سفارش آزمایشی
        product_id = None
        try:
            if res_prod.status_code == 200:
                products = res_prod.json().get('results', [])
                for p in products:
                    if p.get('is_available') and p.get('stock', 0) > 0:
                        product_id = p.get('id')
                        break
        except Exception:
            pass

        if address_id and product_id:
            print("\n🔍 شروع تست‌های ردیابی زنده، امنیت کَش و تفکیک وضعیت‌ها...")
            
            # ۱۱. ثبت کاربر دوم (مهاجم تستی) برای سنجش امنیت مرزهای داده کلاینت‌ها
            res_b = requests.post(f"{base_url}/users/")
            user_key_b = None
            if res_b.status_code == 201:
                user_key_b = res_b.json().get('user_key')
                
            if user_key_b:
                # ۱۲. ثبت سفارش واقعی توسط کاربر اول با محصول و آدرس تستی
                order_data = {
                    "delivery_type": "delivery",
                    "address_id": address_id,
                    "items": [{"product_id": product_id, "count": 1}]
                }
                res_order = requests.post(f"{base_url}/orders/", json=order_data, headers=headers)
                
                if assert_status(res_order, [201], "۱۱. ثبت سفارش آزمایشی با محصول واقعی (POST /orders/)"):
                    order_id = res_order.json().get('order_id')
                    
                    if order_id:
                        # ۱۳. تست امنیت کش: تلاش کاربر دوم برای ردیابی سفارش کاربر اول
                        headers_b = {'X-USER-KEY': user_key_b}
                        res_spy = requests.get(f"{base_url}/orders/{order_id}/tracking/", headers=headers_b)
                        assert_status(res_spy, [404], "۱۲. امنیت ردیابی (عدم دسترسی کاربر دوم به سفارش کاربر اول)")
                        
                        # ۱۴. ردیابی سفارش توسط خودِ کاربر اول (مالک اصلی)
                        res_track = requests.get(f"{base_url}/orders/{order_id}/tracking/", headers=headers)
                        if assert_status(res_track, [200], "۱۳. ردیابی موفق سفارش توسط مالک اصلی (GET /orders/{id}/tracking/)"):
                            tracking_info = res_track.json()
                            print(f"   📊 وضعیت کلان سفارش: {tracking_info.get('status_display')}")
                            print(f"   🏍️ وضعیت ترانزیت پیک: {tracking_info.get('courier_status_display')}")
            else:
                print("⚠️ خطا در ایجاد کاربر دوم برای انجام تست امنیت.")
        else:
            print("\n⚠️ هشدار: آدرس معتبر یا محصول با موجودی بزرگتر از صفر روی هاست یافت نشد.")
    else:
        print("⚠️ به دلیل عدم دریافت user_key، تست‌های مرحله دوم انجام نشدند.")

    # خلاصه وضعیت
    print("\n" + "="*50)
    print(f"📊 خلاصه نتایج: {passed_tests} تست از {total_tests} تست با موفقیت انجام شد.")
    if passed_tests == total_tests:
        print("🎉 تبریک! هاست شما با موفقیت راه‌اندازی شده و تمامی سرویس‌ها در وضعیت پایدار هستند.")
    else:
        print("⚠️ برخی از بخش‌ها نیاز به بررسی دارند. لطفاً لاگ‌های (Logs) هاست خود را بررسی کنید.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="اسکریپت تست سلامت اپلیکیشن روی هاست واقعی")
    parser.add_argument("--url", required=True, help="آدرس کامل هاست (مثال: https://api.moein.com)")
    args = parser.parse_args()
    
    run_smoke_tests(args.url)