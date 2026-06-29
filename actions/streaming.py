"""Streaming & sosyal medya platformları."""

import re
import webbrowser
from urllib.parse import quote_plus


def netflix_ac(parameters: dict = None, **_) -> str:
    webbrowser.open("https://www.netflix.com")
    return "Efendim, Netflix açıldı."


def twitch_ac(parameters: dict = None, **_) -> str:
    p = parameters or {}
    kanal = p.get("kanal", "").strip()
    if kanal:
        webbrowser.open(f"https://www.twitch.tv/{quote_plus(kanal)}")
        return f"Efendim, Twitch'te '{kanal}' kanalı açıldı."
    webbrowser.open("https://www.twitch.tv")
    return "Efendim, Twitch açıldı."


def tiktok_ac(parameters: dict = None, **_) -> str:
    webbrowser.open("https://www.tiktok.com")
    return "Efendim, TikTok açıldı."


def twitter_ac(parameters: dict = None, **_) -> str:
    webbrowser.open("https://www.x.com")
    return "Efendim, Twitter/X açıldı."


def instagram_ac(parameters: dict = None, **_) -> str:
    webbrowser.open("https://www.instagram.com")
    return "Efendim, Instagram açıldı."


def _extract_twitch(msg: str) -> dict:
    q = re.sub(r"\b(twitch|yayın|izle|aç|baslat|başlat|kanal|git|gir|open|ac)\b", "", msg, flags=re.I).strip()
    return {"kanal": q}
