"""Mesajlaşma — WhatsApp, Telegram, Discord, Instagram, Messenger."""

import subprocess
import time
import webbrowser
from urllib.parse import quote

try:
    import pyautogui  # type: ignore
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE    = 0.06
    _GUI = True
except ImportError:
    _GUI = False

try:
    import pyperclip  # type: ignore
    _CLIP = True
except ImportError:
    _CLIP = False


def _paste(text: str):
    if _CLIP:
        pyperclip.copy(text)
        time.sleep(0.15)
        pyautogui.hotkey("ctrl", "v")
    else:
        pyautogui.write(text, interval=0.03)


def _open_app(name: str) -> bool:
    try:
        pyautogui.press("win")
        time.sleep(0.6)
        _paste(name)
        time.sleep(0.7)
        pyautogui.press("enter")
        time.sleep(3.0)
        return True
    except Exception:
        return False


def _search_contact(query: str):
    pyautogui.hotkey("ctrl", "f")
    time.sleep(0.5)
    pyautogui.hotkey("ctrl", "a")
    _paste(query)
    time.sleep(1.0)


def _desktop_send(app: str, receiver: str, message: str) -> str:
    if not _GUI:
        return "Efendim, pyautogui kurulu değil. pip install pyautogui gerekiyor."
    if not _open_app(app):
        return f"Efendim, {app} açılamadı."
    _search_contact(receiver)
    pyautogui.press("enter")
    time.sleep(0.8)
    _paste(message)
    time.sleep(0.2)
    pyautogui.press("enter")
    return f"Efendim, {receiver}'e {app} üzerinden mesaj gönderildi."


def _whatsapp(receiver: str, message: str) -> str:
    # Önce masaüstü uygulamasını dene, yoksa web
    if _GUI:
        return _desktop_send("WhatsApp", receiver, message)
    url = f"https://web.whatsapp.com/send?phone={quote(receiver)}&text={quote(message)}"
    webbrowser.open(url)
    return f"Efendim, WhatsApp web arayüzü açıldı."


def _telegram(receiver: str, message: str) -> str:
    return _desktop_send("Telegram", receiver, message)


def _discord(receiver: str, message: str) -> str:
    return _desktop_send("Discord", receiver, message)


def _instagram(receiver: str, message: str) -> str:
    if not _GUI:
        return "Efendim, pyautogui gerekiyor."
    webbrowser.open("https://www.instagram.com/direct/new/")
    time.sleep(4.0)
    _paste(receiver)
    time.sleep(1.5)
    pyautogui.press("down")
    time.sleep(0.3)
    pyautogui.press("enter")
    time.sleep(0.4)
    for _ in range(4):
        pyautogui.press("tab")
        time.sleep(0.15)
    pyautogui.press("enter")
    time.sleep(2.0)
    _paste(message)
    time.sleep(0.2)
    pyautogui.press("enter")
    return f"Efendim, {receiver}'e Instagram üzerinden mesaj gönderildi."


def _messenger(receiver: str, message: str) -> str:
    if not _GUI:
        return "Efendim, pyautogui gerekiyor."
    webbrowser.open("https://www.messenger.com/")
    time.sleep(4.0)
    pyautogui.hotkey("ctrl", "f")
    time.sleep(0.5)
    _paste(receiver)
    time.sleep(0.5)
    pyautogui.press("down")
    time.sleep(0.3)
    pyautogui.press("enter")
    time.sleep(1.0)
    _paste(message)
    time.sleep(0.2)
    pyautogui.press("enter")
    return f"Efendim, {receiver}'e Messenger üzerinden mesaj gönderildi."


_PLATFORMS = {
    frozenset({"whatsapp", "wp", "wapp", "wassap"}): _whatsapp,
    frozenset({"telegram", "tg"}):                   _telegram,
    frozenset({"discord"}):                           _discord,
    frozenset({"instagram", "ig", "insta"}):          _instagram,
    frozenset({"messenger", "facebook", "fb"}):       _messenger,
}


def send_message(parameters: dict, **_) -> str:
    p        = parameters or {}
    receiver = p.get("receiver", "").strip()
    message  = p.get("message_text", p.get("mesaj", "")).strip()
    platform = p.get("platform", "whatsapp").lower().strip()

    if not receiver:
        return "Efendim, mesajı kime göndereceğimi belirtir misiniz?"
    if not message:
        return "Efendim, mesaj içeriğini belirtir misiniz?"

    for keywords, handler in _PLATFORMS.items():
        if any(k in platform for k in keywords):
            return handler(receiver, message)

    # Bilinmeyen platform → masaüstü aç
    return _desktop_send(platform.title(), receiver, message)
