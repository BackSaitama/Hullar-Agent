"""
Sosyal medya araçları — tamamen bedava, API key gerektirmez.
Ajan uygulamayı/siteyi açar, ekranı görüp (OCR/vision) klavye-fare ile sürer.
Discord ve Steam için opsiyonel bedava API (key varsa) daha güvenilir çalışır.
"""

import os
import subprocess
import time
import webbrowser


def _open_wait(url_or_app: str, is_app: bool = False, wait: float = 3.0):
    if is_app:
        subprocess.Popen(f"start {url_or_app}", shell=True,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        webbrowser.open(url_or_app)
    time.sleep(wait)


# ── INSTAGRAM (tarayıcı — bedava, API yok) ───────────────────────────── #
def instagram_open(ctx, section: str = "") -> str:
    """
    Instagram açar. section: '' (ana sayfa), 'dm'/'mesaj', 'profil', 'kesfet'.
    Açtıktan sonra ajan read_screen + click_element ile gezinir.
    """
    routes = {
        "dm": "https://www.instagram.com/direct/inbox/",
        "mesaj": "https://www.instagram.com/direct/inbox/",
        "kesfet": "https://www.instagram.com/explore/",
        "keşfet": "https://www.instagram.com/explore/",
        "profil": "https://www.instagram.com/accounts/edit/",
    }
    url = routes.get(section.lower().strip(), "https://www.instagram.com/")
    _open_wait(url, wait=4.0)
    return f"Instagram açıldı ({section or 'ana sayfa'}). Devam etmek için read_screen ile ekranı incele."


# ── DISCORD ──────────────────────────────────────────────────────────── #
def discord_open(ctx, target: str = "") -> str:
    """Discord uygulamasını açar (yoksa web)."""
    try:
        subprocess.Popen("start discord:", shell=True,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(3.5)
        return "Discord açıldı. read_screen ile incele, click_element/type_text ile sür."
    except Exception:
        _open_wait("https://discord.com/app", wait=4.0)
        return "Discord web açıldı."


def discord_webhook_send(ctx, message: str, webhook_url: str = "") -> str:
    """
    Discord kanalına webhook ile mesaj gönderir (en güvenilir bedava yol).
    webhook_url verilmezse .env'deki DISCORD_WEBHOOK kullanılır.
    """
    url = webhook_url or os.getenv("DISCORD_WEBHOOK", "")
    if not url:
        return ("HATA: Discord webhook URL yok. Discord'da kanal ayarları → "
                "Entegrasyonlar → Webhook oluştur, URL'yi .env'e DISCORD_WEBHOOK olarak ekle.")
    try:
        import requests
        r = requests.post(url, json={"content": message}, timeout=10)
        if r.status_code in (200, 204):
            return f"Discord'a gönderildi: {message[:50]}"
        return f"HATA: Discord {r.status_code}"
    except Exception as exc:
        return f"HATA: {exc}"


# ── GMAIL (tarayıcı — bedava) ────────────────────────────────────────── #
def gmail_open(ctx, action: str = "inbox", to: str = "", subject: str = "", body: str = "") -> str:
    """
    Gmail açar. action: 'inbox' (gelen kutusu) veya 'compose' (yeni mail).
    compose için to/subject/body verilebilir.
    """
    import urllib.parse
    if action.lower() in ("compose", "yaz", "gonder", "gönder", "yeni"):
        url = "https://mail.google.com/mail/?view=cm&fs=1"
        if to:      url += f"&to={urllib.parse.quote(to)}"
        if subject: url += f"&su={urllib.parse.quote(subject)}"
        if body:    url += f"&body={urllib.parse.quote(body)}"
        _open_wait(url, wait=3.5)
        return f"Gmail yeni mesaj açıldı{f' ({to})' if to else ''}."
    _open_wait("https://mail.google.com/mail/u/0/#inbox", wait=4.0)
    return "Gmail gelen kutusu açıldı. read_screen ile mailleri oku."


# ── STEAM ────────────────────────────────────────────────────────────── #
def steam_open(ctx, section: str = "") -> str:
    """Steam açar. section: '' (ana), 'kutuphane'/'library', 'arkadaslar'/'friends', 'magaza'/'store'."""
    routes = {
        "kutuphane": "steam://open/games",
        "kütüphane": "steam://open/games",
        "library":   "steam://open/games",
        "arkadaslar":"steam://open/friends",
        "arkadaşlar":"steam://open/friends",
        "friends":   "steam://open/friends",
        "magaza":    "steam://open/store",
        "mağaza":    "steam://open/store",
        "store":     "steam://open/store",
        "indirilenler": "steam://open/downloads",
        "downloads": "steam://open/downloads",
    }
    uri = routes.get(section.lower().strip(), "steam://open/main")
    _open_wait(uri, is_app=True, wait=3.0)
    return f"Steam açıldı ({section or 'ana'})."


def steam_player_info(ctx, query: str = "") -> str:
    """
    Steam Web API ile oyuncu/oyun bilgisi (bedava key gerekir).
    .env'de STEAM_API_KEY + STEAM_ID olmalı.
    """
    key = os.getenv("STEAM_API_KEY", "")
    sid = os.getenv("STEAM_ID", "")
    if not key or not sid:
        return ("HATA: Steam API key yok. steamcommunity.com/dev/apikey'den BEDAVA key al, "
                ".env'e STEAM_API_KEY ve STEAM_ID ekle.")
    try:
        import requests
        # Sahip olunan oyunlar
        url = ("https://api.steampowered.com/IPlayerService/GetOwnedGames/v1/"
               f"?key={key}&steamid={sid}&include_appinfo=1&format=json")
        r = requests.get(url, timeout=10).json()
        games = r.get("response", {}).get("games", [])
        games.sort(key=lambda g: g.get("playtime_forever", 0), reverse=True)
        top = games[:10]
        lines = [f"  • {g['name']} ({g['playtime_forever']//60}saat)" for g in top]
        return f"Steam kütüphanen ({len(games)} oyun), en çok oynananlar:\n" + "\n".join(lines)
    except Exception as exc:
        return f"HATA: {exc}"


def register(box):
    box.add("instagram_open", "Instagram açar (ana/dm/keşfet/profil), sonra read_screen ile gezin",
            {"section": "bölüm: dm, keşfet, profil veya boş"}, instagram_open)
    box.add("discord_open", "Discord uygulamasını açar",
            {"target": "opsiyonel"}, discord_open)
    box.add("discord_webhook_send", "Discord kanalına webhook ile mesaj gönderir (en güvenilir)",
            {"message": "mesaj", "webhook_url": "opsiyonel, .env'den alır"}, discord_webhook_send)
    box.add("gmail_open", "Gmail açar (inbox/compose). compose için to/subject/body ver",
            {"action": "inbox veya compose", "to": "alıcı", "subject": "konu", "body": "içerik"}, gmail_open)
    box.add("steam_open", "Steam açar (ana/kütüphane/arkadaşlar/mağaza)",
            {"section": "bölüm veya boş"}, steam_open)
    box.add("steam_player_info", "Steam kütüphane/oynama istatistiklerini gösterir (API key gerekir)",
            {"query": "opsiyonel"}, steam_player_info)
