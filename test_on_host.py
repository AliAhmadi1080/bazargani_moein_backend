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
    res = requests.get(f"{base_url}/store/")
    # اگر هنوز فروشگاهی نساخته باشید، خطای ۴۰۴ می‌دهد که از نظر فنی درست است (خطای سرور ۵۰۰ نیست)
    assert_status(res, [200, 404], "۲. دریافت اطلاعات فروشگاه (/store/)")

    # ۳. تست دریافت دسته‌بندی‌ها (GET /categories/)
    res = requests.get(f"{base_url}/categories/")
    assert_status(res, [200], "۳. دریافت لیست دسته‌بندی‌ها (/categories/)")

    # ۴. تست دریافت محصولات (GET /products/)
    res = requests.get(f"{base_url}/products/")
    assert_status(res, [200], "۴. دریافت لیست محصولات (/products/)")

    # ۵. تست ساخت کاربر جدید و دریافت کلید امنیتی (POST /users/)
    res = requests.post(f"{base_url}/users/")
    if assert_status(res, [201], "۵. ثبت کاربر جدید (POST /users/)"):
        try:
            user_key = res.json().get('user_key')
            print(f"   🔑 شناسه کاربری ایجاد شده: {user_key}")
        except Exception:
            print("   ⚠️ خطا در استخراج user_key از پاسخ سرور")

    # تست‌های نیازمند هدر احراز هویت
    if user_key:
        headers = {'X-USER-KEY': user_key}

        # ۶. تست صفحه اصلی تجمیعی با هدر کاربر (GET /home/)
        res = requests.get(f"{base_url}/home/", headers=headers)
        assert_status(res, [200], "۶. دریافت اطلاعات صفحه اصلی تجمیعی (/home/)")

        # ۷. تست امنیت: تلاش برای دسترسی به پروفایل بدون هدر (باید ۴۰۱ یا ۴۰۳ بدهد)
        res = requests.get(f"{base_url}/profile/")
        assert_status(res, [401, 403], "۷. تست امنیت: تلاش برای دسترسی به پروفایل بدون هدر")

        # ۸. تست دسترسی به پروفایل با هدر صحیح (GET /profile/)
        res = requests.get(f"{base_url}/profile/", headers=headers)
        assert_status(res, [200], "۸. دریافت اطلاعات پروفایل با هدر معتبر (/profile/)")

        # ۹. تست ثبت آدرس جدید (POST /addresses/)
        address_data = {
            "title": "آدرس تستی هاست",
            "address": "خیابان تست، پلاک ۱",
            "is_default": True
        }
        res = requests.post(f"{base_url}/addresses/", json=address_data, headers=headers)
        assert_status(res, [201], "۹. ثبت آدرس جدید برای کاربر (/addresses/)")

        # ۱۰. تست پیش‌فاکتور (POST /checkout/) - کاملاً امن و بدون ایجاد سفارش واقعی در دیتابیس
        checkout_data = {
            "delivery_type": "delivery",
            "items": [] # لیست خالی ارسال می‌کنیم تا فرمت بررسی شود
        }
        res = requests.post(f"{base_url}/checkout/", json=checkout_data, headers=headers)
        # به دلیل خالی بودن سبد خرید انتظار خطای ۴۰۰ منطقی (نه خطای ۵۰۰ سرور) داریم
        assert_status(res, [400], "۱۰. تست ساختار ورودی محاسبات مالی (/checkout/)")
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