import random
from datetime import datetime
import time

# E-ticaret sunucusu için yaygın kullanılan endpointler, metodlar ve durum kodları
ENDPOINTS = {
    "/home": {"methods": ["GET"], "status_codes": [200, 200, 200, 200, 404]},
    "/products": {"methods": ["GET"], "status_codes": [200, 200, 200, 200, 404]},
    "/products/detail": {"methods": ["GET"], "status_codes": [200, 200, 200, 404]},
    "/cart": {"methods": ["GET", "POST"], "status_codes": [200, 200, 200, 200]},
    "/login": {"methods": ["GET", "POST"], "status_codes": [200, 200, 401, 401]},
    "/register": {"methods": ["GET", "POST"], "status_codes": [200, 200, 400]},
    "/checkout": {"methods": ["GET", "POST"], "status_codes": [200, 200, 200, 500]}
}

# Normal IP havuzu (Güvenilir kullanıcıları simüle etmek için)
NORMAL_IPS = [
    "192.168.1.15", "192.168.1.22", "85.105.42.12", "176.43.90.8",
    "95.8.101.44", "46.196.32.7", "78.180.200.11", "213.14.88.5"
]

# Saldırı IP'leri (Anomali tespitini kolaylaştırmak için belirgin IP'ler)
ATTACK_IPS = {
    "brute_force": "185.220.101.5",
    "scraping": "194.29.110.12",
    "critical_error": "88.241.10.89"
}

class LogGenerator:
    """E-ticaret sunucusu için gerçekçi mock log verisi üreten sınıf."""

    @staticmethod
    def generate_single_log(ip=None, endpoint=None, method=None, status_code=None) -> dict:
        """Tek bir log satırı üretir. Parametreler boş geçilirse rastgele normal veri oluşturur."""
        # Rastgele normal IP seç
        if not ip:
            ip = random.choice(NORMAL_IPS)

        # Rastgele normal endpoint seç
        if not endpoint:
            endpoint = random.choice(list(ENDPOINTS.keys()))

        # Endpoint'e uygun metod seç
        if not method:
            method = random.choice(ENDPOINTS[endpoint]["methods"])

        # Endpoint'e uygun durum kodu seç
        if not status_code:
            # Normal akışta 500 veya 401 çıkma ihtimalini düşürüyoruz
            weights = [0.85 if code == 200 else 0.05 for code in ENDPOINTS[endpoint]["status_codes"]]
            # Eğer ağırlıklar hepsi 0 ise eşit dağıt
            if sum(weights) == 0:
                status_code = random.choice(ENDPOINTS[endpoint]["status_codes"])
            else:
                status_code = random.choices(ENDPOINTS[endpoint]["status_codes"], weights=weights, k=1)[0]

        return {
            "timestamp": datetime.now().isoformat(),
            "ip_address": ip,
            "method": method,
            "endpoint": endpoint,
            "status_code": status_code
        }

    @classmethod
    def simulate_brute_force(cls) -> list[dict]:
        """Brute Force saldırısı simüle eder: Aynı IP'den kısa sürede çok sayıda 401 /login hatası."""
        logs = []
        ip = ATTACK_IPS["brute_force"]
        # 10 saniye içine yayılmış 5 başarısız giriş denemesi simüle edelim
        # Sunumda hemen gözükmesi için zaman damgalarını birkaç saniye geriden başlatarak sıralı üretiyoruz
        base_time = time.time() - 4
        for i in range(5):
            t = datetime.fromtimestamp(base_time + (i * 0.8)).isoformat()
            logs.append({
                "timestamp": t,
                "ip_address": ip,
                "method": "POST",
                "endpoint": "/login",
                "status_code": 401
            })
        return logs

    @classmethod
    def simulate_scraping(cls) -> list[dict]:
        """Scraping/Bot simüle eder: Aynı IP'den saniyede anormal sayıda /products isteği."""
        logs = []
        ip = ATTACK_IPS["scraping"]
        # Çok kısa sürede (örn 1 saniye içinde) /products sayfasına 15 adet istek
        base_time = time.time() - 1
        for i in range(15):
            t = datetime.fromtimestamp(base_time + (i * 0.05)).isoformat()
            logs.append({
                "timestamp": t,
                "ip_address": ip,
                "method": "GET",
                "endpoint": "/products",
                "status_code": 200
            })
        return logs

    @classmethod
    def simulate_critical_error(cls) -> list[dict]:
        """Kritik Hata simüle eder: /checkout endpoint'inde 500 durum kodu."""
        ip = random.choice(NORMAL_IPS)  # Herhangi bir normal kullanıcı bu hatayı alabilir
        # 1 adet kritik hata logu üret
        return [{
            "timestamp": datetime.now().isoformat(),
            "ip_address": ip,
            "method": "POST",
            "endpoint": "/checkout",
            "status_code": 500
        }]
