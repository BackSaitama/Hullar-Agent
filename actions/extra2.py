"""
HULLAR ek skiller — üretkenlik, sistem, geliştirici, AI, iletişim.
"""

from __future__ import annotations

import json
import re
import subprocess
import threading
import time
from collections import Counter
from pathlib import Path


def _push(text: str):
    try:
        from .notify import push
        push(text)
    except Exception:
        pass


# ── Odak engelleyici (dikkat dağıtanları kapat) ───────────────────────── #
_ODAK = {"on": False}
_DAGITAN = ["chrome.exe", "msedge.exe", "discord.exe", "steam.exe",
            "RobloxPlayerBeta.exe", "Spotify.exe", "Instagram.exe"]


def odak_engelle(parameters: dict | None = None) -> str:
    p = parameters or {}
    if p.get("action") == "stop":
        _ODAK["on"] = False
        return "🎯 Odak modu kapatıldı."
    dk = int(p.get("dakika", 30))
    if _ODAK.get("on"):
        return "Odak modu zaten açık."
    _ODAK["on"] = True

    def _run():
        import psutil
        t0 = time.time()
        while _ODAK.get("on") and (time.time() - t0) < dk * 60:
            for pr in psutil.process_iter(["name"]):
                nm = (pr.info["name"] or "")
                if nm in _DAGITAN:
                    try:
                        pr.kill()
                    except Exception:
                        pass
            time.sleep(5)
        _ODAK["on"] = False
        _push("🎯 Odak modu bitti.")

    threading.Thread(target=_run, daemon=True).start()
    return f"🎯 Odak modu açık ({dk} dk) — dikkat dağıtan uygulamalar kapalı tutulur. Durdur: 'odak modu durdur'."


def _extract_odak(msg: str) -> dict:
    low = msg.lower()
    if any(w in low for w in ("durdur", "kapat", "bitir", "bırak")):
        return {"action": "stop"}
    m = re.search(r"(\d+)\s*(dakika|dk|saat)", low)
    dk = 30
    if m:
        dk = int(m.group(1)) * (60 if "saat" in m.group(2) else 1)
    return {"dakika": dk}


# ── Kronometre ────────────────────────────────────────────────────────── #
_KRONO = {"start": None}


def kronometre(parameters: dict | None = None) -> str:
    low = (parameters or {}).get("action", "")
    if low == "stop" or low == "durdur":
        if not _KRONO["start"]:
            return "Kronometre çalışmıyor."
        gecen = int(time.time() - _KRONO["start"])
        _KRONO["start"] = None
        dk, sn = divmod(gecen, 60)
        return f"⏱️ Süre: {dk} dk {sn} sn."
    _KRONO["start"] = time.time()
    return "⏱️ Kronometre başladı. Durdurmak için 'kronometre durdur'."


def _extract_krono(msg: str) -> dict:
    if any(w in msg.lower() for w in ("durdur", "dur", "stop", "bitir")):
        return {"action": "stop"}
    return {"action": "start"}


# ── Uygulama kullanım istatistiği ─────────────────────────────────────── #
_ISTAT = {"on": False, "data": Counter()}


def uygulama_istatistik(parameters: dict | None = None) -> str:
    p = parameters or {}
    act = p.get("action", "")
    if act == "stop":
        _ISTAT["on"] = False
        return "📊 Takip durduruldu."
    if act == "report":
        d = _ISTAT["data"]
        if not d:
            return "Henüz veri yok. Önce 'uygulama takibi başlat' de."
        top = d.most_common(8)
        lines = ["📊 Uygulama süreleri:"]
        for app, sec in top:
            dk = sec // 60
            lines.append(f"• {app}: {dk} dk" if dk else f"• {app}: {sec} sn")
        return "\n".join(lines)
    # başlat
    if _ISTAT.get("on"):
        return "Takip zaten açık. Görmek için 'uygulama istatistiği göster'."
    _ISTAT["on"] = True

    def _run():
        try:
            import pygetwindow as gw  # type: ignore
        except Exception:
            return
        while _ISTAT.get("on"):
            try:
                w = gw.getActiveWindow()
                if w and w.title:
                    ad = w.title.split(" - ")[-1][:30]
                    _ISTAT["data"][ad] += 5
            except Exception:
                pass
            time.sleep(5)

    threading.Thread(target=_run, daemon=True).start()
    return "📊 Uygulama takibi başladı. Görmek için 'uygulama istatistiği göster'."


def _extract_istat(msg: str) -> dict:
    low = msg.lower()
    if any(w in low for w in ("göster", "raporla", "ne kadar")):
        return {"action": "report"}
    if any(w in low for w in ("durdur", "kapat", "bitir")):
        return {"action": "stop"}
    return {"action": "start"}


# ── Pencere şeffaflığı ────────────────────────────────────────────────── #
def pencere_seffaf(parameters: dict | None = None) -> str:
    yuzde = int((parameters or {}).get("yuzde", 80))
    try:
        import ctypes
        u = ctypes.windll.user32
        hwnd = u.GetForegroundWindow()
        GWL_EXSTYLE = -20
        WS_EX_LAYERED = 0x80000
        LWA_ALPHA = 0x2
        u.SetWindowLongW(hwnd, GWL_EXSTYLE,
                         u.GetWindowLongW(hwnd, GWL_EXSTYLE) | WS_EX_LAYERED)
        alpha = int(max(20, min(100, yuzde)) * 255 / 100)
        u.SetLayeredWindowAttributes(hwnd, 0, alpha, LWA_ALPHA)
        return f"🪟 Aktif pencere %{yuzde} opaklığa ayarlandı."
    except Exception as exc:
        return f"Şeffaflık ayarlanamadı: {exc}"


def _extract_seffaf(msg: str) -> dict:
    m = re.search(r"(\d{1,3})", msg)
    return {"yuzde": int(m.group(1)) if m else 80}


# ── Sürücü / güncelleme kontrolü ──────────────────────────────────────── #
def surucu_guncelle(parameters: dict | None = None) -> str:
    try:
        r = subprocess.run("winget upgrade", shell=True, capture_output=True,
                           text=True, timeout=60)
        out = (r.stdout or "").strip()
        satir = [l for l in out.splitlines() if l.strip()]
        n = max(0, len(satir) - 2)
        if n <= 0:
            return "✅ Güncel — bekleyen güncelleme yok."
        return f"🔄 {n} güncelleme var:\n" + "\n".join(satir[-min(n, 8):])
    except Exception:
        subprocess.Popen("start ms-settings:windowsupdate", shell=True)
        return "🔄 Windows Update açıldı."


# ── Disk sağlığı (SMART) ──────────────────────────────────────────────── #
def disk_saglik(parameters: dict | None = None) -> str:
    try:
        r = subprocess.run(
            'powershell -NoProfile -Command "Get-PhysicalDisk | '
            'Select-Object FriendlyName,HealthStatus,@{n=\'GB\';e={[int]($_.Size/1GB)}} | Format-Table -HideTableHeaders"',
            shell=True, capture_output=True, text=True, timeout=30)
        out = (r.stdout or "").strip()
        if out:
            return "💽 Disk sağlığı:\n" + out
    except Exception:
        pass
    try:
        r = subprocess.run("wmic diskdrive get model,status", shell=True,
                           capture_output=True, text=True, timeout=20)
        return "💽 Disk:\n" + (r.stdout or "").strip()
    except Exception as exc:
        return f"Disk bilgisi alınamadı: {exc}"


# ── JSON güzelleştir ──────────────────────────────────────────────────── #
def json_guzel(parameters: dict | None = None) -> str:
    raw = (parameters or {}).get("text", "").strip()
    if not raw:
        return "Kullanım: 'json güzelleştir {\"a\":1}'"
    try:
        obj = json.loads(raw)
        return "```\n" + json.dumps(obj, ensure_ascii=False, indent=2) + "\n```"
    except Exception as exc:
        return f"Geçersiz JSON: {exc}"


def _extract_json(msg: str) -> dict:
    m = re.search(r"(\{.*\}|\[.*\])", msg, re.S)
    return {"text": m.group(1) if m else ""}


# ── Kısa link ─────────────────────────────────────────────────────────── #
def kisa_link(parameters: dict | None = None) -> str:
    url = (parameters or {}).get("url", "").strip()
    if not url:
        return "Kullanım: 'kısalt https://uzun-link...'"
    if not url.startswith("http"):
        url = "https://" + url
    try:
        import requests
        r = requests.get("https://is.gd/create.php",
                         params={"format": "simple", "url": url}, timeout=12)
        if r.ok and r.text.startswith("http"):
            return f"🔗 {r.text.strip()}"
        return "Kısaltılamadı."
    except Exception as exc:
        return f"Hata: {exc}"


def _extract_kisa(msg: str) -> dict:
    m = re.search(r"(https?://\S+|[\w\-]+\.[a-z]{2,}/\S*)", msg, re.I)
    return {"url": m.group(1) if m else ""}


# ── WiFi QR (online API ile) ──────────────────────────────────────────── #
def wifi_qr(parameters: dict | None = None) -> str:
    p = parameters or {}
    ssid = (p.get("ssid") or "").strip()
    sifre = (p.get("sifre") or "").strip()
    if not ssid:
        return "Kullanım: 'wifi qr <ağ adı> <şifre>'"
    import urllib.parse
    payload = f"WIFI:S:{ssid};T:WPA;P:{sifre};;"
    url = "https://api.qrserver.com/v1/create-qr-code/?size=400x400&data=" + \
          urllib.parse.quote(payload)
    return (f"📶 '{ssid}' WiFi QR kodu (telefonla okut, otomatik bağlanır):\n{url}")


def _extract_wifi_qr(msg: str) -> dict:
    m = re.search(r"wifi\s*qr\s+(\S+)\s+(\S+)", msg, re.I)
    if m:
        return {"ssid": m.group(1), "sifre": m.group(2)}
    return {}


# ── Web sayfası özetle (AI) ───────────────────────────────────────────── #
def web_ozet(parameters: dict | None = None) -> str:
    url = (parameters or {}).get("url", "").strip()
    if not url:
        return "Kullanım: 'şu sayfayı özetle <link>'"
    if not url.startswith("http"):
        url = "https://" + url
    try:
        import requests
        html = requests.get(url, timeout=15,
                            headers={"User-Agent": "Mozilla/5.0"}).text
        metin = re.sub(r"<script.*?</script>|<style.*?</style>", " ", html, flags=re.S)
        metin = re.sub(r"<[^>]+>", " ", metin)
        metin = re.sub(r"\s+", " ", metin).strip()[:3000]
        from .ai_skills import _ask_ai
        return "📄 " + _ask_ai(
            "Bu web sayfasını Türkçe, 3-4 maddede kısaca özetle.", metin)
    except Exception as exc:
        return f"Özetlenemedi: {exc}"


def _extract_web_ozet(msg: str) -> dict:
    m = re.search(r"(https?://\S+|[\w\-]+\.[a-z]{2,}/\S*)", msg, re.I)
    return {"url": m.group(1) if m else ""}


# ── E-posta taslağı (AI) ──────────────────────────────────────────────── #
def email_taslak(parameters: dict | None = None) -> str:
    konu = (parameters or {}).get("konu", "").strip()
    if not konu:
        return "Ne hakkında e-posta? Örn: 'email taslağı yaz izin talebi'"
    try:
        from .ai_skills import _ask_ai
        return "✉️ " + _ask_ai(
            "Profesyonel, kısa bir Türkçe e-posta taslağı yaz (konu + gövde).", konu)
    except Exception as exc:
        return f"Yazılamadı: {exc}"


def _extract_email_taslak(msg: str) -> dict:
    k = re.sub(r"\b(email|e-?posta|mail|taslağı|taslak|yaz|hazırla|oluştur)\b",
               "", msg, flags=re.I)
    return {"konu": re.sub(r"\s+", " ", k).strip(" :-")}


# ── Sesli dikte (mikrofon → yazı → aktif pencere) ─────────────────────── #
def sesli_dikte(parameters: dict | None = None) -> str:
    sure = int((parameters or {}).get("sure", 6))
    try:
        import sounddevice as sd  # type: ignore
        import numpy as np        # type: ignore
        import speech_recognition as sr  # type: ignore
        fs = 16000
        _push(f"🎙️ {sure} sn dinliyorum, konuş...")
        rec = sd.rec(int(sure * fs), samplerate=fs, channels=1, dtype="int16")
        sd.wait()
        r = sr.Recognizer()
        audio = sr.AudioData(rec.tobytes(), fs, 2)
        try:
            metin = r.recognize_google(audio, language="tr-TR")
        except Exception:
            return "Anlayamadım, tekrar dene."
        # aktif pencereye yaz
        try:
            import pyperclip, pyautogui  # type: ignore
            pyperclip.copy(metin)
            time.sleep(0.1)
            pyautogui.hotkey("ctrl", "v")
        except Exception:
            pass
        return f"🎙️ Yazıldı: {metin}"
    except Exception as exc:
        return f"Dikte hatası: {exc}"


def _extract_dikte(msg: str) -> dict:
    m = re.search(r"(\d+)\s*(?:saniye|sn)", msg, re.I)
    return {"sure": int(m.group(1)) if m else 6}


# ── Zamanlı mesaj (saatte WhatsApp) ───────────────────────────────────── #
def zamanli_mesaj(parameters: dict | None = None) -> str:
    p = parameters or {}
    kisi = (p.get("kisi") or "").strip()
    mesaj = (p.get("mesaj") or "").strip()
    saat = (p.get("saat") or "").strip()
    if not (kisi and mesaj and saat):
        return "Kullanım: 'saat 15:30'da Ahmet'e WhatsApp at: geliyorum'"

    def _run():
        from datetime import datetime
        hh, mm = (saat.split(":") + ["0"])[:2]
        while True:
            now = datetime.now()
            if now.hour == int(hh) and now.minute == int(mm):
                try:
                    from .whatsapp_auto import whatsapp_send
                    whatsapp_send(parameters={"receiver": kisi, "message_text": mesaj})
                    _push(f"📨 {kisi}'e zamanlı mesaj gönderildi.")
                except Exception:
                    pass
                break
            time.sleep(25)

    threading.Thread(target=_run, daemon=True).start()
    return f"⏰ {saat}'te {kisi}'e WhatsApp gönderilecek: '{mesaj}'"


def _extract_zamanli_mesaj(msg: str) -> dict:
    saat = re.search(r"(\d{1,2}[:.]\d{2})", msg)
    kisi = re.search(r"([A-ZÇĞİÖŞÜ][\wçğışöü]+)'?[ae]\b", msg)
    mesaj = re.search(r"(?:at|gönder|yaz|söyle)[:\s]+(.+)$", msg, re.I)
    return {"saat": saat.group(1).replace(".", ":") if saat else "",
            "kisi": kisi.group(1) if kisi else "",
            "mesaj": mesaj.group(1).strip() if mesaj else ""}


# ── Discord'a mesaj (aktif Discord penceresine) ───────────────────────── #
def discord_mesaj(parameters: dict | None = None) -> str:
    mesaj = (parameters or {}).get("mesaj", "").strip()
    if not mesaj:
        return "Ne yazayım? Örn: 'discorda yaz: selam'"
    try:
        import pygetwindow as gw  # type: ignore
        import pyautogui          # type: ignore
        wins = [w for w in gw.getWindowsWithTitle("Discord") if w.title]
        if not wins:
            return "Discord penceresi bulunamadı (açık olmalı)."
        wins[0].activate()
        time.sleep(0.6)
        try:
            import pyperclip
            pyperclip.copy(mesaj)
            pyautogui.hotkey("ctrl", "v")
        except Exception:
            pyautogui.write(mesaj)
        time.sleep(0.2)
        pyautogui.press("enter")
        return f"💬 Discord'a gönderildi: {mesaj[:40]}"
    except Exception as exc:
        return f"Gönderilemedi: {exc}"


def _extract_discord_mesaj(msg: str) -> dict:
    m = re.search(r"discord'?[ae]?\s*(?:yaz|mesaj|gönder)?\s*[:\-]\s*(.+)", msg, re.I)
    return {"mesaj": m.group(1).strip() if m else ""}
