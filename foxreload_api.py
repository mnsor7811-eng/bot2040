import requests
import time

API_BASE_URL = "https://public-api.foxreload.com/api"
API_KEY = "dmk_m-3CgPjnjmeZekypX98vbE7O-6yRZ3ToyJfric2eTJ8"

# نسبة الربح المئوية المضافة على السعر الأصلي (مثلاً 15%)
PROFIT_MARGIN_PERCENTAGE = 15

# التخزين المؤقت للمنتجات
PRODUCTS_CACHE = {}
CACHE_TIMESTAMP = {}

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
        if original_price is None:
            return None
        price = float(original_price)
        final_price = price + (price * PROFIT_MARGIN_PERCENTAGE / 100)
        return round(final_price, 2)
    except:
        return original_price

def translate_product_name(name):
    """تعريب المسميات الشائعة للمنتجات الرقمية"""
    if not name:
        return "منتج رقمي"
    
    t = str(name)
    replacements = {
        "Gift Card": "بطاقة هدايا",
        "GiftCard": "بطاقة هدايا",
        "Gift": "هدية",
        "Card": "بطاقة",
        "Digital Card": "بطاقة رقمية",
        "Delivery Service": "خدمة توصيل",
        "Service": "خدمة",
        "Game of the Year Edition": "نسخة لعبة العام",
        "Edition": "نسخة",
        "Games": "ألعاب",
        "Game": "لعبة",
        "Simulator": "محاكي",
        "Challenge": "تحدي"
    }
    for en, ar in replacements.items():
        t = t.replace(en, ar)
    return t

def fetch_categories():
    """جلب الأقسام الرئيسية وتصنيفاتها"""
    url = f"{API_BASE_URL}/categories/?limit=50"
    try:
        response = requests.get(url, headers=get_headers(), timeout=12)
        if response.status_code == 200:
            return response.json()
        return []
    except Exception as e:
        print(f"Error fetching categories: {e}")
        return []

def search_products_by_category(query):
    """جلب جميع المنتجات المتاحة مع فلترة الأسعار الصالحة وإضافة الربح والتعريب"""
    global PRODUCTS_CACHE, CACHE_TIMESTAMP
    q = query.lower().strip()
    now = time.time()

    # كاش لمدة 10 دقائق لتسريع التصفح
    if q in PRODUCTS_CACHE and (now - CACHE_TIMESTAMP.get(q, 0) < 600):
        return PRODUCTS_CACHE[q]

    url = f"{API_BASE_URL}/products/search?query={q}&limit=100"
    try:
        response = requests.get(url, headers=get_headers(), timeout=15)
        if response.status_code == 200:
            data = response.json()
            items = data.get("data", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
            
            valid_products = []
            for item in items:
                raw_price = item.get('price')
                # استبعاد المنتجات غير المحددة السعر أو المنتهية (None)
                if raw_price is not None:
                    try:
                        p_val = float(raw_price)
                        if p_val > 0:
                            item['original_price'] = p_val
                            item['price'] = calculate_price(p_val)
                            item['display_name'] = translate_product_name(item.get('name', 'منتج رقمي'))
                            valid_products.append(item)
                    except:
                        continue
            
            PRODUCTS_CACHE[q] = valid_products
            CACHE_TIMESTAMP[q] = now
            return valid_products
        return []
    except Exception as e:
        print(f"Error searching products ({query}): {e}")
        return []

def get_account_balance():
    """التحقق من الرصيد الحالي في حسابك على الموقع"""
    url = f"{API_BASE_URL}/access/me/balances/"
    try:
        response = requests.get(url, headers=get_headers(), timeout=10)
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
        res = requests.post(orders_url, headers=get_headers(), json=payload, timeout=15)
        if res.status_code not in [200, 201]:
            return {"success": False, "error": f"فشل في إنشاء الطلب من المزود: {res.text}"}
        
        order_data = res.json()
        order_id = order_data.get("id") or order_data.get("orderId")
        
        if not order_id:
            return {"success": False, "error": "لم يتم استلام رقم الطلب"}

        # 2. دفع الطلب أوتوماتيكياً من رصيدك في الموقع
        pay_url = f"{API_BASE_URL}/orders/{order_id}/pay/"
        pay_payload = {"paymentProvider": None}
        pay_res = requests.post(pay_url, headers=get_headers(), json=pay_payload, timeout=15)
        
        if pay_res.status_code not in [200, 201]:
            return {"success": False, "error": f"فشل في عملية دفع الطلب من رصيدك: {pay_res.text}"}

        # 3. جلب تفاصيل الطلب والأكواد المسلمة
        get_order_url = f"{API_BASE_URL}/orders/{order_id}/"
        final_res = requests.get(get_order_url, headers=get_headers(), timeout=15)
        
        if final_res.status_code == 200:
            completed_order = final_res.json()
            return {"success": True, "data": completed_order}
            
        return {"success": True, "data": order_data}
        
    except Exception as e:
        return {"success": False, "error": str(e)}
