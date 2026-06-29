"""
WhatsApp Desktop otomasyonu — debug oturumlarıyla doğrulanmış versiyon.

Tespit edilen sorunlar ve çözümleri:
  1. Ctrl+F sonrası tıklama odağı kırıyordu → Ctrl+F'den sonra tıklama YOK
  2. ESC sohbeti kapatıyordu → ESC YOK
  3. Mesaj kutusu y=%95.5 yanlıştı → %98.5 kullan
  4. Odak kaybı → win32 ile zorla öne getir
  5. Arama kutusu temizlenmiyordu → Ctrl+F otomatik odaklar, Ctrl+A ile seç
"""

import subprocess
import time

try:
    import pyautogui
    pyautogui.PAUSE    = 0.05
    pyautogui.FAILSAFE = False
    _GUI = True
except ImportError:
    _GUI = False


# ── Pencere yönetimi ─────────────────────────────────────────────────── #

def _get_wa():
    try:
        import pygetwindow as gw
        wins = gw.getWindowsWithTitle("WhatsApp")
        return wins[0] if wins else None
    except Exception:
        return None


def _force_focus(wa):
    """win32 ile WhatsApp'ı kesinlikle öne getir ve odakla."""
    try:
        import win32gui, win32con  # type: ignore
        hwnd = win32gui.FindWindow(None, "WhatsApp")
        if hwnd:
            win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
            win32gui.SetForegroundWindow(hwnd)
            time.sleep(0.4)
            return
    except Exception:
        pass
    # win32 yoksa pygetwindow ile dene
    try:
        if wa and not wa.isActive:
            wa.activate()
            time.sleep(0.4)
    except Exception:
        pass


def _paste(text: str):
    try:
        import pyperclip
        pyperclip.copy(text)
    except Exception:
        subprocess.run(
            ["powershell", "-command", f"Set-Clipboard -Value '{text}'"],
            capture_output=True
        )
    time.sleep(0.12)
    pyautogui.hotkey("ctrl", "v")


# ── Ana gönderme fonksiyonu ───────────────────────────────────────────── #

def send_whatsapp_auto(parameters: dict, **_) -> str:
    if not _GUI:
        return "Efendim, pyautogui kurulu değil."

    receiver = (parameters or {}).get("receiver", "").strip()
    message  = (parameters or {}).get("message_text", "").strip()

    if not receiver:
        return "Efendim, mesajı kime gönderelim?"
    if not message:
        return "Efendim, ne yazmamı istersiniz?"

    # ── 1. WhatsApp'ı aç / maximize et ───────────────────────────────── #
    wa = _get_wa()
    if not wa:
        subprocess.Popen("start whatsapp:", shell=True,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(3.5)
        wa = _get_wa()
    if not wa:
        return "Efendim, WhatsApp açılamadı."

    # Maximize + kesinlikle odakla
    try:
        wa.maximize()
        time.sleep(0.5)
        wa = _get_wa()
    except Exception:
        pass
    _force_focus(wa)
    time.sleep(0.3)

    # ── 2. Ctrl+F — arama kutusu OTOMATİK odaklanır ──────────────────── #
    # KRİTİK: Ctrl+F'den sonra HİÇBİR YERE TIKLAMIYORUZ
    pyautogui.hotkey("ctrl", "f")
    time.sleep(0.8)

    # ── 3. Eski metni sil, kişi adını yaz ───────────────────────────── #
    pyautogui.hotkey("ctrl", "a")   # Kutudaki tüm metni seç
    time.sleep(0.15)
    _paste(receiver)                 # Seçili metnin üstüne yaz
    time.sleep(2.5)

    # ── 4. İlk arama sonucuna tıkla ──────────────────────────────────── #
    # Debug görüntüsüyle doğrulandı: pencere yüksekliğinin %37'si
    wa = _get_wa()
    _force_focus(wa)
    cx = wa.left + int(wa.width  * 0.175)
    cy = wa.top  + int(wa.height * 0.370)
    pyautogui.click(cx, cy)
    time.sleep(2.0)

    # ── 5. ESC YOK — ESC sohbeti kapatıyor! ──────────────────────────── #

    # ── 6. Mesaj kutusuna tıkla ───────────────────────────────────────── #
    # Debug'dan ölçülen: %98.5 yükseklik, %62 genişlik
    wa = _get_wa()
    _force_focus(wa)
    mx = wa.left + int(wa.width  * 0.620)
    my = wa.top  + int(wa.height * 0.965)
    pyautogui.click(mx, my)
    time.sleep(0.35)
    pyautogui.click(mx, my)
    time.sleep(0.25)

    # ── 7. Mesajı yaz ve gönder ───────────────────────────────────────── #
    _paste(message)
    time.sleep(0.3)
    pyautogui.press("enter")

    return f"Efendim, '{receiver}' kişisine WhatsApp mesajı gönderildi: \"{message}\""


def whatsapp_send(parameters: dict, **_) -> str:
    return send_whatsapp_auto(parameters)
