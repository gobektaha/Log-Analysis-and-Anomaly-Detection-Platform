import asyncio
import random
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Dict, Any
from contextlib import asynccontextmanager

from backend.database import engine, SessionLocal, Base, LogEntryModel, AnomalyAlertModel
from backend.generator import LogGenerator
from backend.rules import RuleEngine, Anomaly

# Tabloları otomatik olarak SQLite veritabanında oluştur (eğer yoksa)
try:
    Base.metadata.create_all(bind=engine)
    print("[+] SQLite veritabanı tabloları başarıyla doğrulandı/oluşturuldu.")
except Exception as e:
    print(f"[!] Veritabanı tabloları oluşturulurken hata: {e}")

# Küresel durum yönetimi
logs_history: List[Dict[str, Any]] = []
anomalies_history: List[Dict[str, Any]] = []
stats = {
    "total_requests": 0,
    "total_anomalies": 0,
    "critical_errors": 0,
    "distribution": {
        "Brute Force": 0,
        "Scraping/Bot": 0,
        "Kritik Hata (Checkout 500)": 0
    }
}

rule_engine = RuleEngine()
MAX_LOGS_LIMIT = 500
background_task_running = True

def process_log(log: Dict[str, Any]) -> Anomaly | None:
    """Tek bir logu sisteme işler, kuralları denetler ve istatistikleri günceller."""
    global stats
    stats["total_requests"] += 1
    
    # Kural motorunu çalıştır
    anomaly = rule_engine.check_rules(log, logs_history)
    
    # SQLAlchemy Oturumu aç
    db = SessionLocal()
    
    try:
        if anomaly:
            anomaly_dict = anomaly.to_dict()
            anomalies_history.insert(0, anomaly_dict) # En yeni alarm en üstte dursun
            
            # Log objesine anomali bilgilerini enjekte et (Frontend renklendirmesi için)
            log["is_anomaly"] = True
            log["anomaly_type"] = anomaly.type
            log["anomaly_severity"] = anomaly.severity
            log["anomaly_id"] = anomaly.id

            # İstatistikleri güncelle
            stats["total_anomalies"] += 1
            if anomaly.type == "Kritik Hata (Checkout 500)":
                stats["critical_errors"] += 1
                
            stats["distribution"][anomaly.type] = stats["distribution"].get(anomaly.type, 0) + 1

            # --- ANOMALİ ALARMINI SQLite'A KAYDET ---
            import json
            import datetime
            db_alert = AnomalyAlertModel(
                id=anomaly.id,
                timestamp=datetime.datetime.fromisoformat(anomaly.timestamp),
                type=anomaly.type,
                severity=anomaly.severity,
                ip_address=anomaly.ip_address,
                details=anomaly.details,
                triggering_logs=json.dumps(anomaly.triggering_logs) # JSON listesini string sakla
            )
            db.add(db_alert)
        else:
            log["is_anomaly"] = False
            
        # Log geçmişine ekle (başa ekleyelim ki en güncel log en üstte olsun)
        logs_history.insert(0, log)
        
        # --- LOG KAYDINI SQLite'A KAYDET ---
        import datetime
        db_log = LogEntryModel(
            timestamp=datetime.datetime.fromisoformat(log["timestamp"]),
            ip_address=log["ip_address"],
            method=log["method"],
            endpoint=log["endpoint"],
            status_code=log["status_code"],
            is_anomaly=log["is_anomaly"]
        )
        db.add(db_log)
        
        # SQLite'a kaydet (commit)
        db.commit()
    except Exception as db_err:
        print(f"[!] Veritabanı kayıt hatası: {db_err}")
        db.rollback()
    finally:
        db.close()
        
    # Bellek taşmasını önlemek için listeyi sınırla
    if len(logs_history) > MAX_LOGS_LIMIT:
        logs_history.pop()
        
    return anomaly


async def normal_traffic_simulator():
    """Arka planda periyodik olarak normal ve organik olarak anomali logları üreten döngü."""
    global background_task_running
    print("LogShield trafik simülatörü ve anomali üreteci başlatıldı.")
    while background_task_running:
        try:
            # Daha aktif bir akış hissi için 0.3sn ile 1.2sn arasında rastgele bekle
            await asyncio.sleep(random.uniform(0.3, 1.2))
            
            # %15 olasılıkla organik bir siber güvenlik olayı / anomali tetikle
            if random.random() < 0.15:
                scenario = random.choice(["brute_force", "scraping", "critical_error"])
                if scenario == "brute_force":
                    logs = LogGenerator.simulate_brute_force()
                elif scenario == "scraping":
                    logs = LogGenerator.simulate_scraping()
                else:
                    logs = LogGenerator.simulate_critical_error()
                
                # Oluşan logları gerçekçi bir akışla hafif gecikmeli olarak sisteme işle
                for log in logs:
                    process_log(log)
                    await asyncio.sleep(0.08)
            else:
                # Normal log üret
                log = LogGenerator.generate_single_log()
                process_log(log)
        except Exception as e:
            print(f"Simülatör hatası: {e}")
            await asyncio.sleep(2)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Uygulama başlarken arka plan görevini tetikle
    global background_task_running
    background_task_running = True
    asyncio.create_task(normal_traffic_simulator())
    yield
    # Uygulama kapanırken arka plan görevini durdur
    background_task_running = False
    print("Arka plan görevleri sonlandırıldı.")


app = FastAPI(
    title="Log Analiz ve Anomali Tespit Platformu API",
    description="E-ticaret senaryosuna dayalı kural tabanlı anomali tespit backend'i.",
    version="1.0.0",
    lifespan=lifespan
)

# CORS ayarları
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic Modelleri
class SimulationRequest(BaseModel):
    scenario: str # "brute_force", "scraping", "critical_error"

# API Endpoint'leri

@app.get("/api/logs", response_model=List[Dict[str, Any]])
def get_logs(limit: int = 100):
    """Son üretilen log akışını getirir."""
    return logs_history[:limit]

@app.get("/api/alerts", response_model=List[Dict[str, Any]])
def get_alerts():
    """Tespit edilen tüm anomalileri/alarmları getirir."""
    return anomalies_history

@app.get("/api/stats")
def get_stats():
    """Platform istatistiklerini ve anomali oranlarını hesaplar."""
    total = stats["total_requests"]
    anomalies = stats["total_anomalies"]
    rate = (anomalies / total * 100) if total > 0 else 0.0
    
    return {
        "total_requests": total,
        "total_anomalies": anomalies,
        "critical_errors": stats["critical_errors"],
        "anomaly_rate": round(rate, 2),
        "distribution": stats["distribution"]
    }

@app.post("/api/simulate")
def trigger_simulation(request: SimulationRequest, background_tasks: BackgroundTasks):
    """Özel bir saldırı veya kritik hata senaryosunu simüle eder."""
    scenario = request.scenario
    
    if scenario == "brute_force":
        logs = LogGenerator.simulate_brute_force()
    elif scenario == "scraping":
        logs = LogGenerator.simulate_scraping()
    elif scenario == "critical_error":
        logs = LogGenerator.simulate_critical_error()
    else:
        raise HTTPException(status_code=400, detail="Geçersiz senaryo türü. Seçenekler: 'brute_force', 'scraping', 'critical_error'")
    
    # Simülasyon loglarını sırayla ve hafif zaman gecikmeleriyle ekleyerek akış hissi verelim
    async def process_simulation_logs(logs_to_process):
        for log in logs_to_process:
            process_log(log)
            # Mikro gecikme
            await asyncio.sleep(0.1)

    background_tasks.add_task(process_simulation_logs, logs)
    return {"status": "success", "message": f"'{scenario}' senaryosu simülasyonu başlatıldı."}

@app.post("/api/clear")
def clear_data():
    """Tüm log geçmişini, alarmları ve istatistikleri sıfırlar."""
    global logs_history, anomalies_history, stats, rule_engine
    logs_history.clear()
    anomalies_history.clear()
    stats["total_requests"] = 0
    stats["total_anomalies"] = 0
    stats["critical_errors"] = 0
    stats["distribution"] = {
        "Brute Force": 0,
        "Scraping/Bot": 0,
        "Kritik Hata (Checkout 500)": 0
    }
    # Kural motorunu yeniden ilklendirerek cooldown hafızasını sıfırla
    rule_engine = RuleEngine()
    
    # --- SQLite VERİTABANI TABLOLARINI TEMİZLE ---
    db = SessionLocal()
    try:
        db.query(LogEntryModel).delete()
        db.query(AnomalyAlertModel).delete()
        db.commit()
        print("[+] SQLite veritabanı kayıtları başarıyla sıfırlandı.")
    except Exception as db_err:
        print(f"[!] Veritabanı temizleme hatası: {db_err}")
        db.rollback()
    finally:
        db.close()
        
    return {"status": "success", "message": "Tüm veriler başarıyla sıfırlandı."}

# Statik dosyaları en son aşamada mount ediyoruz (HTML/CSS/JS)
# Böylece /api rotaları çakışmadan çalışmaya devam eder
app.mount("/", StaticFiles(directory="frontend", html=True), name="static")
