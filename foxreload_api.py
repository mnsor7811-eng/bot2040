import requests

API_BASE_URL = "https://public-api.foxreload.com/api"
API_KEY = "dmk_m-3CgPjnjmeZekypX98vbE7O-6yRZ3ToyJfric2eTJ8"

# نسبة الربح المئوية التي تريد إضافتها على السعر الأصلي (مثلاً 15% ربح)
PROFIT_MARGIN_PERCENTAGE = 15 

def get_headers():
    return {
        "X-API-Key": API_KEY,
        "X-Language": "en",
        "X-Currency": "usd",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

def calculate_price(original_price):
    """إضافة نسبة الربح تلقائياً على السعر القادم من الموقع"""
    try:
        price = float(original_price)
        final_price = price + (price * PROFIT_MARGIN_PERCENTAGE / 100)
        return round(final_price, 2)
    except:
        return original_price

def fetch_categories():
    """جلب الأقسام الرئيسية وتصنيفاتها"""
    url = f"{API_BASE_URL}/categories/?limit=20"
    try:
        response = requests.get(url, headers=get_headers())
        if response.status_code == 200:
            return response.json()
        return []
    except Exception as e:
        print(f"Error fetching categories: {e}")
        return []

def search_products_by_category(query):
    """البحث أو جلب المنتجات حسب القسم أو الكلمة المعينة (لإظهار الألعاب في زر الألعاب وغيرها)"""
    url = f"{API_BASE_URL}/products/search?query={query}&limit=20"
    try:
        response = requests.get(url, headers=get_headers())
        if response.status_code == 200:
            data = response.json()
            # تطبيق نسبة الربح على الأسعار المعروضة للمستخدمين
            if isinstance(data, list):
                for item in data:
                    if 'price' in item:
                        item['original_price'] = item['price']
                        item['price'] = calculate_price(item['price'])
            return data
        return []
    except Exception as e:
        print(f"Error searching products: {e}")
        return []

def get_account_balance():
    """التحقق من الرصيد الحالي في حسابك على الموقع"""
    url = f"{API_BASE_URL}/access/me/balances/"
    try:
        response = requests.get(url, headers=get_headers())
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        print(f"Error fetching balance: {e}")
        return None

def create_and_pay_order(product_id, quantity=1):
    """خطوات الشراء التلقائي: إنشاء الطلب ثم دفعه فوراً وجلب الكود"""
    orders_url = f"{API_BASE_URL}/orders/"
    payload = {
        "items": [
            {
                "itemId": str(product_id),
                "quantity": int(quantity)
            }
        ]
    }
    
    try:
        # 1. إنشاء الطلب
        res = requests.post(orders_url, headers=get_headers(), json=payload)
        if res.status_code != 200 and res.status_code != 201:
            return {"success": False, "error": "فشل في إنشاء الطلب من المزود"}
        
        order_data = res.json()
        order_id = order_data.get("id") or order_data.get("orderId")
        
        if not order_id:
            return {"success": False, "error": "لم يتم استلام رقم الطلب"}

        # 2. دفع الطلب أوتوماتيكياً من رصيدك
        pay_url = f"{API_BASE_URL}/orders/{order_id}/pay/"
        pay_payload = {"paymentProvider": None}
        pay_res = requests.post(pay_url, headers=get_headers(), json=pay_payload)
        
        if pay_res.status_code != 200:
            return {"success": False, "error": "فشل في عملية دفع الطلب من رصيدك"}

        # 3. جلب تفاصيل الطلب والأكواد المسلمة
        get_order_url = f"{API_BASE_URL}/orders/{order_id}/"
        final_res = requests.get(get_order_url, headers=get_headers())
        
        if final_res.status_code == 200:
            completed_order = final_res.json()
            return {"success": True, "data": completed_order}
            
        return {"success": False, "error": "تم الدفع ولكن فشل جلب تفاصيل الأكواد"}
        
    except Exception as e:
        return {"success": False, "error": str(e)}
