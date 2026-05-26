# 🛡️ E-Commerce Log Analysis & Anomaly Detection Platform

## 📖 Proje Hakkında
Bu proje, e-ticaret altyapılarında meydana gelebilecek siber güvenlik tehditlerini ve operasyonel hataları gerçek zamanlı simüle eden, kural tabanlı (rule-based) bir log analizi platformudur. Hantal SIEM ürünlerinin aksine, izole bir ortamda kendi sahte log verisini üretir ve bu veriler üzerinden tehdit avcılığı (threat hunting) yapar.

## ✨ Temel Özellikler
* **Mock Data Engine:** Python tabanlı motor ile `/login`, `/products`, `/checkout` gibi kritik uç noktalara (endpoint) rastgele ancak mantıklı HTTP durum kodları üreterek sürekli log akışı sağlar.
* **Kural Motoru (Rule Engine):**
  * *Brute Force Tespiti:* Aynı IP'den kısa sürede gelen çoklu 401 hatalarını tespit ederek alarm üretir.
  * *Bot/Scraping Aktivitesi:* Saniyede anormal sayıda sayfa isteği atan IP'leri siber tehdit olarak işaretler.
  * *Kritik Hata Monitörleme:* Ödeme sayfasındaki 500 Internal Server Error çöküşlerini anında raporlayarak ciro kaybı riskini gösterir.
* **Kalıcı Veri Depolama:** Tespit edilen anomaliler ve üretilen normal loglar, SQLAlchemy yapısı kullanılarak hafif ve performanslı SQLite veritabanına kaydedilir.
* **Canlı Dashboard:** React.js ile geliştirilmiş, dark/light mode destekli arayüz sayesinde sistemdeki aktif loglar ve kırmızı alarmlar anlık olarak takip edilebilir.

## 💻 Kullanılan Teknolojiler
* **Backend:** Python, SQLAlchemny
* **Frontend:** React.js, HTML/CSS
* **Veritabanı:** SQLite
* **Proje Yönetimi:** Jira (Kanban), Git & GitHub

## 🚀 Kurulum ve Çalıştırma

Aşağıdaki adımları takip ederek projeyi lokal ortamınızda ayağa kaldırabilirsiniz.

### 1. Repoyu Klonlayın
```bash
git clone [https://github.com/gobektaha/Log-Analysis-and-Anomaly-Detection-Platform.git)
cd Log-Analysis-and-Anomaly-Detection-Platform.git

### 2. Backend Kurulumu
Python sanal ortamınızı oluşturun ve aktifleştirin.
Gerekli bağımlılıkları yükleyin:
```bash
pip install -r requirements.txt
Log simülasyonunu ve kural motorunu başlatın:
```bash
python run.py

