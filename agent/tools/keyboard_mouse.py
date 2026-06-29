"""Klavye + fare araçları."""

import time

try:
    import pyautogui
    pyautogui.PAUSE = 0.05
    pyautogui.FAILSAFE = False
except ImportError:
    pyautogui = None


def _paste(text: str):
    try:
        import pyperclip
        pyperclip.copy(text)
    except Exception:
        import subprocess
        subprocess.run(["powershell", "-command", f"Set-Clipboard -Value '{text}'"],
                       capture_output=True)
    time.sleep(0.1)
    pyautogui.hotkey("ctrl", "v")


def click_xy(ctx, x: int, y: int) -> str:
    pyautogui.click(int(x), int(y))
    time.sleep(0.3)
    return f"({x},{y}) tıklandı."


def click_element(ctx, element: str) -> str:
    """Ekranda bir elementi (buton, kutu) bulup tıklar."""
    pos = ctx.vision.locate(element)
    if not pos:
        return f"HATA: '{element}' ekranda bulunamadı."
    pyautogui.click(*pos)
    time.sleep(0.4)
    return f"'{element}' tıklandı {pos}."


def type_text(ctx, text: str) -> str:
    """Aktif alana metin yazar (Türkçe destekli)."""
    _paste(text)
    time.sleep(0.2)
    return f"Yazıldı: {text[:40]}"


def press_key(ctx, key: str) -> str:
    """Tek tuş veya kombinasyon: enter, esc, ctrl+a, win+d ..."""
    keys = [k.strip() for k in key.replace("+", " ").split()]
    if len(keys) > 1:
        pyautogui.hotkey(*keys)
    else:
        pyautogui.press(keys[0])
    time.sleep(0.2)
    return f"Tuş: {key}"


def scroll(ctx, direction: str = "down", amount: int = 5) -> str:
    clicks = -amount if direction.lower() in ("down", "aşağı") else amount
    pyautogui.scroll(clicks * 100)
    time.sleep(0.3)
    return f"Kaydırıldı: {direction} x{amount}"


def register(box):
    box.add("click_element", "Ekranda bir UI elementini (buton/kutu/link) bulup tıklar",
            {"element": "tıklanacak şeyin açıklaması, örn 'Gönder butonu'"}, click_element)
    box.add("click_xy", "Belirli piksel koordinatına tıklar",
            {"x": "x piksel", "y": "y piksel"}, click_xy)
    box.add("type_text", "Aktif alana metin yazar",
            {"text": "yazılacak metin"}, type_text)
    box.add("press_key", "Tuş/kombinasyon basar (enter, esc, ctrl+a, win+d)",
            {"key": "tuş adı"}, press_key)
    box.add("scroll", "Sayfayı kaydırır",
            {"direction": "down/up", "amount": "miktar"}, scroll)
