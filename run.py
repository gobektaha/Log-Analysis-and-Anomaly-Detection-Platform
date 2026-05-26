import os
import sys
import subprocess
import threading
import time
import webbrowser

def install_dependencies():
    """Gerekli bağımlılıkları requirements.txt üzerinden otomatik yükler."""
    print("=" * 60)
    print("   LogShield Platformu Başlatılıyor...")
    print("=" * 60)
    print("[*] Bağımlılıklar kontrol ediliyor...")
    
    requirements_path = os.path.join(os.path.dirname(__file__), "requirements.txt")
    if not os.path.exists(requirements_path):
        print("[!] requirements.txt dosyası bulunamadı!")
        return False
        
    try:
        # pip install çalıştır
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", requirements_path])
        print("[+] Bağımlılıklar başarıyla kuruldu/doğrulandı.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[!] Bağımlılıklar yüklenirken hata oluştu: {e}")
        return False

def open_browser():
    """Uygulama sunucusu başladıktan sonra tarayıcıyı otomatik açar."""
    print("[*] Tarayıcı yönlendirmesi bekleniyor (1.5 saniye)...")
    time.sleep(1.5)
    url = "http://127.0.0.1:8000"
    print(f"[+] Tarayıcı açılıyor: {url}")
    webbrowser.open(url)

def start_server():
    """Uvicorn ASGI sunucusunu başlatır."""
    import uvicorn
    print("[*] Uvicorn sunucusu başlatılıyor...")
    # backend.main:app olarak çalıştırırız
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)

if __name__ == "__main__":
    # 1. Bağımlılıkları yükle
    if install_dependencies():
        # 2. Tarayıcıyı ayrı bir kanalda otomatik aç
        browser_thread = threading.Thread(target=open_browser, daemon=True)
        browser_thread.start()
        
        # 3. Sunucuyu başlat (Ana thread'i bloke eder)
        start_server()
    else:
        print("[!] Başlatma işlemi bağımlılık hatası nedeniyle iptal edildi.")
        sys.exit(1)
