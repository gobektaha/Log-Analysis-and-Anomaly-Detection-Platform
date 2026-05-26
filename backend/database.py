from sqlalchemy import create_engine, Column, Integer, String, Boolean, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime

# SQLite veritabanı dosya yolu
DATABASE_URL = "sqlite:///db.sqlite3"

# Thread çakışmalarını önlemek için check_same_thread=False ekliyoruz (FastAPI multi-threading destekler)
engine = create_engine(
    DATABASE_URL, 
    connect_args={"check_same_thread": False}
)

# Her istek için izole veritabanı oturumu oluşturucu
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Tablo tanımları için taban sınıf
Base = declarative_base()

class LogEntryModel(Base):
    """Sistemde üretilen tüm HTTP sunucu loglarını temsil eden SQLite tablosu."""
    __tablename__ = "log_entries"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    ip_address = Column(String(45), index=True)
    method = Column(String(10))
    endpoint = Column(String(255))
    status_code = Column(Integer)
    is_anomaly = Column(Boolean, default=False, index=True)


class AnomalyAlertModel(Base):
    """Kural motoru tarafından saptanan güvenlik alarmlarını temsil eden SQLite tablosu."""
    __tablename__ = "anomaly_alerts"

    id = Column(String(36), primary_key=True)  # UUID string formatında
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    type = Column(String(100))
    severity = Column(String(20))
    ip_address = Column(String(45), index=True)
    details = Column(Text)
    triggering_logs = Column(Text)  # Tetikleyen loglar listesinin JSON dökümü (Text formatında)
