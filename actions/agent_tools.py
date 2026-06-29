import os
import subprocess
import webbrowser
import shutil
import urllib.request
import platform
from datetime import datetime
from tkinter import Tk

# ==========================================
# GÜVENLİ YOL TEMİZLEME FONKSİYONU (YOL HATALARINI ÇÖZER)
# ==========================================
def safe_path(path: str, default_filename: str = None) -> str:
    if not path:
        desktop = os.path.join(os.environ['USERPROFILE'], 'Desktop')
        return os.path.normpath(os.path.join(desktop, default_filename or "dosya.txt"))
        
    if "KullaniciAdin" in path or "..." in path:
        desktop = os.path.join(os.environ['USERPROFILE'], 'Desktop')
        filename = os.path.basename(path) if "." in os.path.basename(path) else (default_filename or "dosya.txt")
        path = os.path.join(desktop, filename)
        
    if path.startswith(("Masaüstü", "Desktop")):
        desktop = os.path.join(os.environ['USERPROFILE'], 'Desktop')
        path = path.replace("Masaüstü", desktop, 1).replace("Desktop", desktop, 1)

    return os.path.normpath(path)


# ==========================================
# 1. DOSYA VE KLASÖR YÖNETİMİ
# ==========================================

def read_file(path: str) -> str:
    try:
        path = safe_path(path)
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"HATA: {e}"


def write_file(path: str, content: str) -> str:
    try:
        path = safe_path(path)
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Yazıldı: {path}"
    except Exception as e:
        return f"HATA: {e}"


def create_directory(path: str) -> str:
    try:
        path = safe_path(path)
        os.makedirs(path, exist_ok=True)
        return f"Klasör oluşturuldu: {path}"
    except Exception as e:
        return f"HATA: {e}"


def list_directory(path: str = ".") -> str:
    try:
        path = safe_path(path) if path != "." else "."
        items = os.listdir(path)
        result = []
        for item in items:
            full = os.path.join(path, item)
            icon = "📁" if os.path.isdir(full) else "📄"
            result.append(f"{icon} {item}")
        return "\n".join(result) if result else "Boş klasör"
    except Exception as e:
        return f"HATA: {e}"


def run_command(command: str) -> str:
    try:
        desktop = os.path.join(os.environ['USERPROFILE'], 'Desktop')
        command = command.replace("C:\\Users\\KullaniciAdin\\Desktop", desktop)
        command = command.replace("C:\\Users\\...\\Desktop", desktop)
        
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, timeout=30
        )
        output = (result.stdout + result.stderr).strip()
        return output if output else "Komut tamamlandı (çıktı yok)"
    except subprocess.TimeoutExpired:
        return "HATA: Komut 30 saniyede bitmedi"
    except Exception as e:
        return f"HATA: {e}"


def delete_file(path: str) -> str:
    try:
        path = safe_path(path)
        if os.path.isdir(path):
            shutil.rmtree(path)
            return f"Klasör ve içeriği başarıyla silindi: {path}"
        os.remove(path)
        return f"Silindi: {path}"
    except Exception as e:
        return f"HATA: {e}"


# ==========================================
# 2. GELİŞMİŞ SİSTEM VE ASİSTAN ARAÇLARI
# ==========================================

def open_website(url: str) -> str:
    try:
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        webbrowser.open(url)
        return f"Web sitesi tarayıcıda açıldı: {url}"
    except Exception as e:
        return f"HATA: {e}"


def take_screenshot(path: str = None) -> str:
    try:
        path = safe_path(path, f"ekran_goruntusu_{int(datetime.now().timestamp())}.png")
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        
        # Windows .NET API kullanarak ekranı doğrudan hafızaya alıp diske kaydeden PowerShell kodu
        ps_cmd = (
            f"Add-Type -AssemblyName System.Windows.Forms, System.Drawing;"
            f"$screen = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds;"
            f"$bmp = New-Object System.Drawing.Bitmap $screen.Width, $screen.Height;"
            f"$graphics = [System.Drawing.Graphics]::FromImage($bmp);"
            f"$graphics.CopyFromScreen($screen.X, $screen.Y, 0, 0, $bmp.Size);"
            f"$bmp.Save('{path}', [System.Drawing.Imaging.ImageFormat]::Png);"
            f"$graphics.Dispose(); $bmp.Dispose();"
        )
        
        subprocess.run(["powershell", "-Command", ps_cmd], shell=True, capture_output=True)
        
        if os.path.exists(path) and os.path.getsize(path) > 0:
            return f"Ekran görüntüsü başarıyla kaydedildi: {path}"
        else:
            return "HATA: Windows ekran görüntüsünü oluşturamadı."
            
    except Exception as e:
        return f"HATA: Ekran görüntüsü alınamadı: {e}"


def search_file(filename: str, search_path: str = None) -> str:
    try:
        search_path = safe_path(search_path) if search_path else os.path.join(os.environ['USERPROFILE'], 'Desktop')
        found_files = []
        for root, dirs, files in os.walk(search_path):
            for file in files:
                if filename.lower() in file.lower():
                    found_files.append(os.path.join(root, file))
                    if len(found_files) >= 10:
                        break
            if len(found_files) >= 10:
                break
                
        if found_files:
            return "Eşleşen Dosyalar:\n" + "\n".join(found_files)
        return f"'{filename}' ifadesini içeren bir dosya bulunamadı."
    except Exception as e:
        return f"HATA: {e}"


def system_control(action: str) -> str:
    try:
        action = action.lower()
        if "kapat" in action:
            os.system("shutdown /s /t 60")
            return "Sistem uyarısı: Bilgisayar 60 saniye içinde kapatılacak."
        elif "iptal" in action:
            os.system("shutdown /a")
            return "Sistem uyarısı: Kapatma işlemi iptal edildi."
        elif "kilitle" in action:
            subprocess.run("rundll32.exe user32.dll,LockWorkStation", shell=True)
            return "Sistem uyarısı: Bilgisayar kilitlendi."
        return "HATA: Bilinmeyen aksiyon. Sadece 'kapat', 'iptal' veya 'kilitle' geçerlidir."
    except Exception as e:
        return f"HATA: {e}"


def get_system_summary() -> str:
    try:
        info = [
            f"İşletim Sistemi: {platform.system()} {platform.release()}",
            f"İşlemci Mimarisi: {platform.architecture()[0]}",
            f"İşlemci: {platform.processor()}",
            f"Kullanıcı Profili: {os.environ.get('USERNAME')}"
        ]
        return "\n".join(info)
    except Exception as e:
        return f"HATA: {e}"


def clipboard_control(action: str, text: str = None) -> str:
    try:
        root = Tk()
        root.withdraw()
        if action.lower() == "set" and text:
            root.clipboard_clear()
            root.clipboard_append(text)
            root.update()
            root.destroy()
            return "Metin başarıyla panoya kopyalandı."
        elif action.lower() == "get":
            result = root.clipboard_get()
            root.destroy()
            return f"Panodaki mevcut metin:\n{result}"
        root.destroy()
        return "HATA: Geçersiz pano işlemi."
    except Exception as e:
        return f"HATA: Pano boş veya erişilemiyor: {e}"


def open_application(app_name: str) -> str:
    try:
        apps = {
            "not defteri": "notepad.exe",
            "hesap makinesi": "calc.exe",
            "boyama": "mspaint.exe",
            "görev yöneticisi": "taskmgr.exe",
            "cmd": "cmd.exe"
        }
        target = apps.get(app_name.lower(), app_name)
        subprocess.Popen(target, shell=True)
        return f"'{app_name}' uygulaması başlatıldı."
    except Exception as e:
        return f"HATA: Uygulama başlatılamadı: {e}"


def get_weather(city: str) -> str:
    try:
        url = f"https://wttr.in/{city}?format=3&lang=tr"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            return response.read().decode('utf-8').strip()
    except Exception as e:
        return f"HATA: Hava durumu alınamadı: {e}"


def download_file(url: str, save_path: str) -> str:
    try:
        save_path = safe_path(save_path)
        os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response, open(save_path, 'wb') as out_file:
            out_file.write(response.read())
        return f"Dosya başarıyla indirildi ve kaydedildi: {save_path}"
    except Exception as e:
        return f"HATA: İndirme başarısız: {e}"


def manage_archive(action: str, archive_path: str, source_path: str = None) -> str:
    try:
        archive_path = safe_path(archive_path)
        if source_path: source_path = safe_path(source_path)
        
        if action.lower() == "zip":
            if not source_path: return "HATA: Zip için kaynak klasör (source_path) gerekli."
            shutil.make_archive(archive_path.replace(".zip", ""), 'zip', source_path)
            return f"Klasör başarıyla sıkıştırıldı: {archive_path}"
        elif action.lower() == "unzip":
            if not source_path:
                source_path = os.path.dirname(archive_path)
            shutil.unpack_archive(archive_path, source_path)
            return f"Arşiv başarıyla klasöre çıkartıldı: {source_path}"
        return "HATA: Geçersiz arşiv işlemi."
    except Exception as e:
        return f"HATA: Arşiv işlemi başarısız: {e}"


def list_processes() -> str:
    try:
        result = subprocess.run("tasklist", capture_output=True, text=True, shell=True)
        lines = result.stdout.split("\n")
        return "\n".join(lines[:25]) + "\n... (Liste devam ediyor)"
    except Exception as e:
        return f"HATA: Süreç listesi alınamadı: {e}"


def kill_process(process_name: str) -> str:
    try:
        if not process_name.endswith(".exe") and not process_name.isdigit():
            process_name += ".exe"
        
        flag = "/PID" if process_name.isdigit() else "/IM"
        cmd = f"taskkill /F {flag} {process_name}"
        result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
        return result.stdout.strip() or result.stderr.strip()
    except Exception as e:
        return f"HATA: Süreç sonlandırılamadı: {e}"


def get_time_info() -> str:
    try:
        now = datetime.now()
        gunler = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
        return f"Tarih: {now.strftime('%d.%m.%Y')} | Saat: {now.strftime('%H:%M:%S')} | Gün: {gunler[now.weekday()]}"
    except Exception as e:
        return f"HATA: {e}"


def get_file_info(path: str) -> str:
    try:
        path = safe_path(path)
        if not os.path.exists(path):
            return "HATA: Belirtilen dosya bulunamadı."
        size = os.path.getsize(path)
        m_time = datetime.fromtimestamp(os.path.getmtime(path)).strftime('%d.%m.%Y %H:%M:%S')
        
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                readable_size = f"{size:.2f} {unit}"
                break
            size /= 1024
            
        return f"Dosya: {os.path.basename(path)}\nBoyut: {readable_size}\nSon Değiştirilme: {m_time}"
    except Exception as e:
        return f"HATA: {e}"


# ==========================================
# MANTIKSAL HARİTALANDIRMA VE UYUMLU ŞEMALAR
# ==========================================

TOOL_MAP = {
    "read_file": read_file,
    "write_file": write_file,
    "create_directory": create_directory,
    "list_directory": list_directory,
    "run_command": run_command,
    "delete_file": delete_file,
    "open_website": open_website,
    "take_screenshot": take_screenshot,
    "search_file": search_file,
    "system_control": system_control,
    "get_system_summary": get_system_summary,
    "clipboard_control": clipboard_control,
    "open_application": open_application,
    "get_weather": get_weather,
    "download_file": download_file,
    "manage_archive": manage_archive,
    "list_processes": list_processes,
    "kill_process": kill_process,
    "get_time_info": get_time_info,
    "get_file_info": get_file_info
}

TOOL_DECLARATIONS = [
    {"type": "function", "function": {"name": "read_file", "description": "Bir dosyanın içeriğini okur.", "parameters": {"type": "object", "properties": {"path": {"type": "string", "description": "Dosya yolu"}}, "required": ["path"]}}},
    {"type": "function", "function": {"name": "write_file", "description": "Bir dosyaya içerik yazar, yoksa oluşturur.", "parameters": {"type": "object", "properties": {"path": {"type": "string", "description": "Dosya yolu"}, "content": {"type": "string", "description": "İçerik"}}, "required": ["path", "content"]}}},
    {"type": "function", "function": {"name": "create_directory", "description": "Yeni klasör oluşturur.", "parameters": {"type": "object", "properties": {"path": {"type": "string", "description": "Klasör yolu"}}, "required": ["path"]}}},
    {"type": "function", "function": {"name": "list_directory", "description": "Klasördeki öğeleri listeler.", "parameters": {"type": "object", "properties": {"path": {"type": "string", "description": "Klasör yolu"}}, "required": []}}},
    {"type": "function", "function": {"name": "run_command", "description": "Terminal komutu çalıştırır.", "parameters": {"type": "object", "properties": {"command": {"type": "string", "description": "Komut"}}, "required": ["command"]}}},
    {"type": "function", "function": {"name": "delete_file", "description": "Dosya veya klasörü tamamen siler.", "parameters": {"type": "object", "properties": {"path": {"type": "string", "description": "Yol"}}, "required": ["path"]}}},
    {"type": "function", "function": {"name": "open_website", "description": "Web sitesi açar.", "parameters": {"type": "object", "properties": {"url": {"type": "string", "description": "URL"}}, "required": ["url"]}}},
    {"type": "function", "function": {"name": "take_screenshot", "description": "Ekran görüntüsü alır.", "parameters": {"type": "object", "properties": {"path": {"type": "string", "description": "Yol (Boşsa masaüstü)"}}, "required": []}}},
    {"type": "function", "function": {"name": "search_file", "description": "Dosya ismi arar.", "parameters": {"type": "object", "properties": {"filename": {"type": "string", "description": "Dosya adı"}, "search_path": {"type": "string", "description": "Aranacak üst klasör"}}, "required": ["filename"]}}},
    {"type": "function", "function": {"name": "system_control", "description": "Bilgisayarı kilitleme, kapatma komutları.", "parameters": {"type": "object", "properties": {"action": {"type": "string", "description": "'kilitle', 'kapat', 'iptal'"}}, "required": ["action"]}}},
    {"type": "function", "function": {"name": "get_system_summary", "description": "Sistem özet donanım bilgisini döner.", "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {"name": "clipboard_control", "description": "Panoya yazı yazar veya panodaki yazıyı okur.", "parameters": {"type": "object", "properties": {"action": {"type": "string", "description": "'set' veya 'get'"}, "text": {"type": "string", "description": "Yazılacak metin"}}, "required": ["action"]}}},
    {"type": "function", "function": {"name": "open_application", "description": "Not defteri, hesap makinesi gibi sistem uygulamalarını açar.", "parameters": {"type": "object", "properties": {"app_name": {"type": "string", "description": "Uygulama adı"}}, "required": ["app_name"]}}},
    {"type": "function", "function": {"name": "get_weather", "description": "Belirtilen şehrin canlı hava durumunu çeker.", "parameters": {"type": "object", "properties": {"city": {"type": "string", "description": "Şehir adı"}}, "required": ["city"]}}},
    {"type": "function", "function": {"name": "download_file", "description": "İnternetteki bir URL'den dosya indirir.", "parameters": {"type": "object", "properties": {"url": {"type": "string", "description": "Dosya linki"}, "save_path": {"type": "string", "description": "Kaydedilecek tam yol"}}, "required": ["url", "save_path"]}}},
    {"type": "function", "function": {"name": "manage_archive", "description": "Klasörleri zip yapar veya zip dosyalarını dışarı çıkartır (unzip).", "parameters": {"type": "object", "properties": {"action": {"type": "string", "description": "'zip' veya 'unzip'"}, "archive_path": {"type": "string", "description": "Zip dosya yolu"}, "source_path": {"type": "string", "description": "Kaynak klasör yolu"}}, "required": ["action", "archive_path"]}}},
    {"type": "function", "function": {"name": "list_processes", "description": "Bilgisayarda o an çalışan arka plan uygulamalarını (Süreçleri) listeler.", "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {"name": "kill_process", "description": "Çalışan bir uygulamayı isminden veya PID kodundan zorla kapatır.", "parameters": {"type": "object", "properties": {"process_name": {"type": "string", "description": "Uygulama adı (örn: notepad.exe) or PID"}}, "required": ["process_name"]}}},
    {"type": "function", "function": {"name": "get_time_info", "description": "Detaylı gün, saat ve tarih bilgisini getirir.", "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {"name": "get_file_info", "description": "Bir dosyanın boyutunu ve ne zaman düzenlendiğini söyler.", "parameters": {"type": "object", "properties": {"path": {"type": "string", "description": "Dosya yolu"}}, "required": ["path"]}}}
]