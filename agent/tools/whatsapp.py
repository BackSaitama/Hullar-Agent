"""
WhatsApp özel araçları — kanıtlanmış klavye akışı (görsel aramaya gerek yok).
Ctrl+F → isim yaz → Down+Enter → sohbet açılır.
"""

import subprocess
import time

try:
    import pyautogui
    pyautogui.PAUSE = 0.05
    pyautogui.FAILSAFE = False
except ImportError:
    pyautogui = None


def _get_wa():
    try:
        import pygetwindow as gw
        wins = gw.getWindowsWithTitle("WhatsApp")
        return wins[0] if wins else None
    except Exception:
        return None


def _focus(wa):
    try:
        import win32gui, win32con
        hwnd = win32gui.FindWindow(None, "WhatsApp")
        if hwnd:
            win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
            win32gui.SetForegroundWindow(hwnd)
            time.sleep(0.4)
            return
    except Exception:
        pass
    try:
        if wa:
            wa.maximize(); time.sleep(0.3); wa.activate(); time.sleep(0.4)
    except Exception:
        pass


def _paste(text):
    try:
        import pyperclip
        pyperclip.copy(text)
    except Exception:
        subprocess.run(["powershell", "-command", f"Set-Clipboard -Value '{text}'"],
                       capture_output=True)
    time.sleep(0.1)
    pyautogui.hotkey("ctrl", "v")


def whatsapp_open_chat(ctx, contact: str) -> str:
    """WhatsApp'ı açar ve belirtilen kişinin sohbetini açar (kanıtlanmış akış)."""
    wa = _get_wa()
    if not wa:
        subprocess.Popen("start whatsapp:", shell=True,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(3.5)
        wa = _get_wa()
    if not wa:
        return "HATA: WhatsApp açılamadı."

    _focus(wa)
    time.sleep(0.3)

    # Ctrl+F → arama kutusu otomatik odaklanır (tıklama YOK)
    pyautogui.hotkey("ctrl", "f")
    time.sleep(0.8)
    pyautogui.hotkey("ctrl", "a")   # eski metni seç
    time.sleep(0.15)
    _paste(contact)                  # üzerine yaz
    time.sleep(2.3)

    # İlk sonuca tıkla (pencere yüksekliğinin %37'si — kanıtlanmış)
    wa = _get_wa()
    cx = wa.left + int(wa.width * 0.175)
    cy = wa.top + int(wa.height * 0.370)
    pyautogui.click(cx, cy)
    time.sleep(1.8)

    return f"'{contact}' sohbeti açıldı."


def read_messages(ctx, count: int = 30) -> str:
    """
    Açık WhatsApp sohbetindeki mesajları OKUR.
    Önce Gemini vision, yoksa OCR (Tesseract) dener.
    """
    if ctx and ctx.vision:
        # Sohbet alanını analiz et (sağ panel)
        result = ctx.vision.analyze(
            "Bu WhatsApp sohbet ekranındaki TÜM mesajları, kim yazmış "
            "ve ne yazmış şeklinde sırayla yaz. Sadece mesaj içeriklerini ver."
        )
        if result and "okunamadı" not in result.lower() and len(result) > 20:
            # Okunan veriyi scratch'e koy → summarize_and_save kullanabilsin
            if hasattr(ctx, "scratch"):
                ctx.scratch["last_read"] = result
            return result
    return ("HATA: Mesajlar okunamadı. Gemini kotası dolu ve Tesseract OCR kurulu değil. "
            "Tesseract kurulması gerekiyor.")


def register(box):
    box.add("whatsapp_open_chat",
            "WhatsApp'ı açar ve bir kişinin sohbetini açar (en güvenilir yol)",
            {"contact": "kişi adı"}, whatsapp_open_chat)
    box.add("read_messages",
            "Açık WhatsApp sohbetindeki mesajları okur",
            {"count": "kaç mesaj (varsayılan 30)"}, read_messages)
