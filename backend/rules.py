from datetime import datetime, timedelta
import uuid

class Anomaly:
    """Tespit edilen anomalileri temsil eden veri sınıfı."""
    def __init__(self, type_: str, severity: str, ip_address: str, details: str, triggering_logs: list[dict]):
        self.id = str(uuid.uuid4())
        self.timestamp = datetime.now().isoformat()
        self.type = type_
        self.severity = severity
        self.ip_address = ip_address
        self.details = details
        self.triggering_logs = triggering_logs

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "type": self.type,
            "severity": self.severity,
            "ip_address": self.ip_address,
            "details": self.details,
            "triggering_logs": self.triggering_logs
        }


class RuleEngine:
    """Log akışını gerçek zamanlı analiz ederek kuralları işleten sınıf."""

    def __init__(self):
        # Mükerrer alarmları önlemek için son tetiklenen alarmların zamanını tutar
        # IP_Address -> {AnomalyType -> LastTriggeredTime}
        self.alert_cooldowns = {}

    def check_rules(self, new_log: dict, all_recent_logs: list[dict]) -> Anomaly | None:
        """Yeni gelen logu geçmiş loglar penceresiyle karşılaştırarak anomali kontrolü yapar."""
        ip = new_log["ip_address"]
        now_dt = datetime.fromisoformat(new_log["timestamp"])

        # Cooldown kontrol yardımcı fonksiyonu
        # Aynı tipteki anomalinin peş peşe saniyede bir tetiklenmesini önler (örn. 5 saniye cooldown)
        def is_in_cooldown(anomaly_type: str, cooldown_seconds: int = 5) -> bool:
            if ip in self.alert_cooldowns and anomaly_type in self.alert_cooldowns[ip]:
                last_time = self.alert_cooldowns[ip][anomaly_type]
                if now_dt - last_time < timedelta(seconds=cooldown_seconds):
                    return True
            return False

        def set_cooldown(anomaly_type: str):
            if ip not in self.alert_cooldowns:
                self.alert_cooldowns[ip] = {}
            self.alert_cooldowns[ip][anomaly_type] = now_dt

        # -------------------------------------------------------------
        # KURAL A: Brute Force Tesbiti
        # Koşul: Aynı IP'den son 10 saniye içinde /login endpoint'ine 3 veya daha fazla 401 hatası
        # -------------------------------------------------------------
        if new_log["endpoint"] == "/login" and new_log["status_code"] == 401:
            if not is_in_cooldown("Brute Force", cooldown_seconds=6):
                # Son 10 saniyedeki ilgili logları filtrele
                ten_seconds_ago = now_dt - timedelta(seconds=10)
                matching_logs = []
                for log in all_recent_logs:
                    log_dt = datetime.fromisoformat(log["timestamp"])
                    if (log["ip_address"] == ip and 
                        log["endpoint"] == "/login" and 
                        log["status_code"] == 401 and 
                        log_dt >= ten_seconds_ago):
                        matching_logs.append(log)

                # Eğer yeni log henüz all_recent_logs içinde değilse ve kriteri sağlıyorsa ekle
                if new_log not in matching_logs:
                    matching_logs.append(new_log)

                if len(matching_logs) >= 3:
                    set_cooldown("Brute Force")
                    # En eski log ile en yeni log arasındaki süreyi hesapla
                    times = [datetime.fromisoformat(l["timestamp"]) for l in matching_logs]
                    duration = (max(times) - min(times)).total_seconds()
                    
                    return Anomaly(
                        type_="Brute Force",
                        severity="high",
                        ip_address=ip,
                        details=f"Aynı IP adresinden son {duration:.1f} saniye içerisinde /login sayfasına {len(matching_logs)} başarısız giriş denemesi (401 Unauthorized) saptandı.",
                        triggering_logs=matching_logs[-5:]  # Maksimum son 5 tetikleyici logu ekle
                    )

        # -------------------------------------------------------------
        # KURAL B: Scraping / Bot Tesbiti
        # Koşul: Aynı IP'den son 5 saniye içinde /products endpoint'ine 10 veya daha fazla istek
        # -------------------------------------------------------------
        if new_log["endpoint"] in ["/products", "/products/detail"]:
            if not is_in_cooldown("Scraping/Bot", cooldown_seconds=5):
                five_seconds_ago = now_dt - timedelta(seconds=5)
                matching_logs = []
                for log in all_recent_logs:
                    log_dt = datetime.fromisoformat(log["timestamp"])
                    if (log["ip_address"] == ip and 
                        log["endpoint"] in ["/products", "/products/detail"] and 
                        log_dt >= five_seconds_ago):
                        matching_logs.append(log)

                if new_log not in matching_logs:
                    matching_logs.append(new_log)

                if len(matching_logs) >= 10:
                    set_cooldown("Scraping/Bot")
                    # İstek sıklığını saniye bazında hesapla
                    times = [datetime.fromisoformat(l["timestamp"]) for l in matching_logs]
                    duration = max((max(times) - min(times)).total_seconds(), 0.1)
                    req_rate = len(matching_logs) / duration

                    return Anomaly(
                        type_="Scraping/Bot",
                        severity="medium",
                        ip_address=ip,
                        details=f"Aynı IP'den son {duration:.1f} saniyede /products sayfasına anormal sayıda ({len(matching_logs)} adet, orantı: {req_rate:.1f} istek/sn) istek saptandı.",
                        triggering_logs=matching_logs[-10:]
                    )

        # -------------------------------------------------------------
        # KURAL C: Kritik Sunucu Hatası (Checkout 500)
        # Koşul: /checkout endpoint'inde 500 Internal Server Error durumu
        # -------------------------------------------------------------
        if new_log["endpoint"] == "/checkout" and new_log["status_code"] == 500:
            # Kritik sistem hatalarında cooldown uygulamıyoruz çünkü her 500 hatası kritiktir ve bağımsız incelenmelidir
            return Anomaly(
                type_="Kritik Hata (Checkout 500)",
                severity="critical",
                ip_address=ip,
                details="Satın alma (checkout) adımında kritik 500 Internal Server Error (Sunucu Hatası) tespit edildi! Ödeme kanalı veya veritabanı kesintisi olabilir.",
                triggering_logs=[new_log]
            )

        return None
