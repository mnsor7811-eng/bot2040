import requests

# قائمة المزودات الـ 22 الكاملة مع الروابط من الملفات القديمة
PROVIDERS_CONFIG = {
    "5sim": {"url": "https://5sim.biz/v1/user", "type": "header_auth"},
    "SmsLive": {"url": "https://smslive.pro/stubs/handler_api.php", "type": "query_auth"},
    "SmsOnline": {"url": "https://sms-online.pro/stubs/handler_api.php", "type": "query_auth"},
    "SmsMan": {"url": "https://sms-man.ru/stubs/handler_api.php", "type": "query_auth"},
    "VakSms": {"url": "https://vak-sms.com/stubs/handler_api.php", "type": "query_auth"},
    "SmsAcktiwator": {"url": "https://sms-acktiwator.ru/stubs/handler_api.php", "type": "query_auth"},
    "PVAPins": {"url": "https://pvapins.com/stubs/handler_api.php", "type": "query_auth"},
    "BotSms": {"url": "https://bot-sms.shop/stubs/handler_api.php", "type": "query_auth"},
    "OnlineSim": {"url": "https://onlinesim.io/api", "type": "custom"},
    "SuperSmsTech": {"url": "https://supersmstech.com/stubs/handler_api.php", "type": "query_auth"},
    "ViOTP": {"url": "https://viotp.com/api", "type": "custom"},
    "SimSms": {"url": "https://simsms.org/stubs/handler_api.php", "type": "query_auth"},
    "GrizzlySms": {"url": "https://grizzlysms.com/stubs/handler_api.php", "type": "query_auth"},
    "SmsCode": {"url": "https://sms-code.ru/stubs/handler_api.php", "type": "query_auth"},
    "TigerSms": {"url": "https://tiger-sms.com/stubs/handler_api.php", "type": "query_auth"},
    "2ndLine": {"url": "https://2ndline.io/stubs/handler_api.php", "type": "query_auth"},
    "ReceiveSmsStore": {"url": "https://receivesms.store/stubs/handler_api.php", "type": "query_auth"},
    "FastPVA": {"url": "https://sms.fastpva.com/stubs/handler_api.php", "type": "query_auth"},
    "DropSms": {"url": "https://dropsms.ru/stubs/handler_api.php", "type": "query_auth"},
    "24Sms7": {"url": "https://24sms7.com/stubs/handler_api.php", "type": "query_auth"},
    "SellOTP": {"url": "https://sellotp.com/stubs/handler_api.php", "type": "query_auth"},
    "DurainCloud": {"url": "https://mm.duraincloud.com/stubs/handler_api.php", "type": "query_auth"}
}

class ProviderAPI:
    def __init__(self, provider_name, api_key):
        self.provider_name = provider_name
        self.api_key = api_key
        self.config = PROVIDERS_CONFIG.get(provider_name, {})

    # طلب رقم جديد
    def get_number(self, service, country):
        url = self.config.get("url")
        if not url:
            return {"status": False, "message": "المزود غير مدعوم"}
            
        params = {
            'api_key': self.api_key,
            'action': 'getNumber',
            'service': service,
            'country': country
        }
        try:
            res = requests.get(url, params=params, timeout=10).text
            if "ACCESS_NUMBER" in res:
                parts = res.split(":")
                return {"status": True, "id": parts[1], "number": parts[2]}
            return {"status": False, "response": res}
        except Exception as e:
            return {"status": False, "error": str(e)}

    # جلب حالة الكود واستقبال SMS
    def get_status(self, activation_id):
        url = self.config.get("url")
        params = {
            'api_key': self.api_key,
            'action': 'getStatus',
            'id': activation_id
        }
        try:
            res = requests.get(url, params=params, timeout=10).text
            if "STATUS_OK" in res:
                code = res.split(":")[1]
                return {"status": "completed", "code": code}
            elif "STATUS_WAIT_CODE" in res:
                return {"status": "waiting"}
            return {"status": "failed", "response": res}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    # حظر الرقم أو إلغاؤه (addBlack)
    def set_status(self, activation_id, status_code=8):
        url = self.config.get("url")
        params = {
            'api_key': self.api_key,
            'action': 'setStatus',
            'id': activation_id,
            'status': status_code
        }
        try:
            res = requests.get(url, params=params, timeout=10).text
            return res
        except Exception as e:
            return str(e)
