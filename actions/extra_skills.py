"""
HULLAR ek skiller — temiz, bağımsız yetenekler.

  • konus(text)          : metni sesli oku (Windows SAPI — ek kurulum yok)
  • ekran_kapat()        : monitörü kapat (hareket edince açılır)
  • kripto_fiyat(coin)   : anlık kripto fiyatı (CoinGecko API)
  • en_cok_kaynak()      : en çok RAM/CPU kullanan uygulamalar
  • pano_temizle()       : panoyu temizle
  • bos_disk()           : disk boş alan özeti
"""

from __future__ import annotations

import ctypes
import re
import subprocess


# ── Sesli konuşma (Windows SAPI, ek kurulum gerektirmez) ──────────────── #
def konus(parameters: dict | None = None) -> str:
    text = (parameters or {}).get("text", "").strip()
    if not text:
        return "Efendim, ne söyleyeyim?"
    safe = text.replace("'", "''")
    ps = (f"Add-Type -AssemblyName System.Speech; "
          f"$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
          f"$s.Speak('{safe}')")
    try:
        subprocess.Popen(["powershell", "-NoProfile", "-Command", ps],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return f"🔊 Söylüyorum: {text[:60]}"
    except Exception as exc:
        return f"Sesli okuma hatası: {exc}"


def _extract_konus(msg: str) -> dict:
    m = re.search(r"(?:konuş|sesli\s*(?:söyle|oku)|seslen|söyle)\s*[:\-]?\s*(.+)",
                  msg, re.I)
    return {"text": m.group(1).strip() if m else ""}


# ── Monitörü kapat (fare/klavye ile geri açılır) ──────────────────────── #
def ekran_kapat(parameters: dict | None = None) -> str:
    try:
        # WM_SYSCOMMAND=0x0112, SC_MONITORPOWER=0xF170, 2=kapat
        ctypes.windll.user32.SendMessageW(0xFFFF, 0x0112, 0xF170, 2)
        return "🖥️ Monitör kapatıldı (fareyi oynat/tuşa bas → açılır)."
    except Exception as exc:
        return f"Monitör kapatılamadı: {exc}"


# ── Anlık kripto fiyatı (CoinGecko) ───────────────────────────────────── #
_COIN_MAP = {
    "bitcoin": "bitcoin", "btc": "bitcoin",
    "ethereum": "ethereum", "eth": "ethereum",
    "bnb": "binancecoin", "binance": "binancecoin",
    "solana": "solana", "sol": "solana",
    "cardano": "cardano", "ada": "cardano",
    "dogecoin": "dogecoin", "doge": "dogecoin",
    "ripple": "ripple", "xrp": "ripple",
    "avalanche": "avalanche-2", "avax": "avalanche-2",
    "shiba": "shiba-inu", "shib": "shiba-inu",
}


def kripto_fiyat(parameters: dict | None = None) -> str:
    coin = (parameters or {}).get("coin", "bitcoin").lower().strip()
    cid = _COIN_MAP.get(coin, coin)
    try:
        import requests
        r = requests.get(
            "https://api.coingecko.com/api/v3/simple/price",
            params={"ids": cid, "vs_currencies": "usd,try"},
            timeout=12,
        ).json()
        if cid not in r:
            return f"'{coin}' bulunamadı. Örn: bitcoin, eth, solana, doge."
        usd = r[cid].get("usd", "?")
        try_ = r[cid].get("try", "?")
        return f"💰 {coin.upper()}: ${usd:,} | ₺{try_:,}"
    except Exception as exc:
        return f"Kripto fiyatı alınamadı: {exc}"


def _extract_kripto(msg: str) -> dict:
    low = msg.lower()
    for k in _COIN_MAP:
        if re.search(rf"\b{k}\b", low):
            return {"coin": k}
    return {"coin": "bitcoin"}


# ── En çok kaynak kullanan uygulamalar ────────────────────────────────── #
def en_cok_kaynak(parameters: dict | None = None) -> str:
    try:
        import psutil
        procs = []
        for p in psutil.process_iter(["name", "memory_info"]):
            try:
                mb = p.info["memory_info"].rss / (1024 * 1024)
                procs.append((p.info["name"] or "?", mb))
            except Exception:
                continue
        procs.sort(key=lambda x: x[1], reverse=True)
        top = procs[:7]
        lines = ["📊 En çok RAM kullananlar:"]
        for name, mb in top:
            lines.append(f"• {name}: {mb:.0f} MB")
        return "\n".join(lines)
    except Exception as exc:
        return f"Kaynak bilgisi alınamadı: {exc}"


# ── Pano temizle ──────────────────────────────────────────────────────── #
def pano_temizle(parameters: dict | None = None) -> str:
    try:
        subprocess.run("echo off | clip", shell=True)
        return "📋 Pano temizlendi."
    except Exception as exc:
        return f"Pano temizlenemedi: {exc}"


# ── Boş disk özeti ────────────────────────────────────────────────────── #
# ── Uyku engelle / serbest bırak (uzaktayken PC açık kalsın) ──────────── #
_ES_CONTINUOUS = 0x80000000
_ES_SYSTEM_REQUIRED = 0x00000001
_ES_DISPLAY_REQUIRED = 0x00000002


def uyanik_kal(parameters: dict | None = None) -> str:
    try:
        ctypes.windll.kernel32.SetThreadExecutionState(
            _ES_CONTINUOUS | _ES_SYSTEM_REQUIRED | _ES_DISPLAY_REQUIRED)
        return ("☕ Bilgisayar uyumayacak (uzaktan erişim açık kalsın). "
                "Kapatmak için 'uykuyu serbest bırak'.")
    except Exception as exc:
        return f"Uyku engellenemedi: {exc}"


def uyku_serbest(parameters: dict | None = None) -> str:
    try:
        ctypes.windll.kernel32.SetThreadExecutionState(_ES_CONTINUOUS)
        return "😴 Uyku ayarı normale döndü (PC artık uyuyabilir)."
    except Exception as exc:
        return f"Ayar değiştirilemedi: {exc}"


# ── PC ekranında BÜYÜK bildirim göster (sesli/sessiz) ─────────────────── #
def pc_bildirim(parameters: dict | None = None) -> str:
    from pathlib import Path
    import sys as _sys
    p = parameters or {}
    text = (p.get("text") or "").strip() or "HULLAR bildirimi"
    sesli = bool(p.get("sesli", False))

    base = Path(__file__).parent.parent
    msg_file = base / "data" / "overlay_msg.txt"
    try:
        msg_file.parent.mkdir(parents=True, exist_ok=True)
        msg_file.write_text(text, encoding="utf-8")
        # Pencereli (konsolsuz) python ile ayrı süreçte aç
        pyw = str(base / "venv" / "Scripts" / "pythonw.exe")
        if not Path(pyw).exists():
            pyw = _sys.executable
        overlay = str(base / "actions" / "overlay.py")
        subprocess.Popen([pyw, overlay, "sesli" if sesli else "sessiz"],
                         cwd=str(base))
        return f"📺 Ekrana {'sesli' if sesli else 'sessiz'} büyük bildirim gönderildi: {text[:50]}"
    except Exception as exc:
        return f"Bildirim gösterilemedi: {exc}"


def _extract_bildirim(msg: str) -> dict:
    low = msg.lower()
    sesli = any(w in low for w in ("sesli", "sesle", "ötür"))
    # Önce sesli/sessiz kelimelerini çıkar ki 'ekrana sesli yaz: X' bozulmasın
    clean = re.sub(r"\b(sesli|sessiz|sesle)\b", " ", msg, flags=re.I)
    m = re.search(
        r"(?:pc\s*bildirim|ekrana?\s*(?:mesaj|yaz|bildir)\w*|ekranda göster|"
        r"masaüstüne yaz|bildirim göster|duyur)\s*[:\-]?\s*(.+)",
        clean, re.I)
    text = re.sub(r"\s+", " ", (m.group(1).strip() if m else "")).strip(" :-")
    return {"text": text, "sesli": sesli}


# ── Uyarı sesi çal (PC'yi bul / dikkat çek) ───────────────────────────── #
def uyari_cal(parameters: dict | None = None) -> str:
    try:
        import winsound
        import threading

        def _beep():
            for _ in range(6):
                winsound.Beep(1000, 350)
                winsound.Beep(1500, 350)
        threading.Thread(target=_beep, daemon=True).start()
        return "🔔 Bilgisayar yüksek sesle ötüyor (bulmak için)."
    except Exception as exc:
        return f"Ses çalınamadı: {exc}"


# ── Tüm tarayıcıları kapat (panik / gizlilik) ─────────────────────────── #
def tarayicilari_kapat(parameters: dict | None = None) -> str:
    browsers = ["chrome.exe", "msedge.exe", "firefox.exe", "opera.exe", "brave.exe"]
    kapatilan = []
    for b in browsers:
        try:
            r = subprocess.run(f"taskkill /f /im {b}", shell=True,
                               capture_output=True, text=True)
            if "SUCCESS" in (r.stdout or ""):
                kapatilan.append(b.replace(".exe", ""))
        except Exception:
            continue
    if kapatilan:
        return "🧹 Kapatıldı: " + ", ".join(kapatilan)
    return "Açık tarayıcı bulunamadı."


def bos_disk(parameters: dict | None = None) -> str:
    try:
        import psutil
        lines = ["💾 Disk boş alan:"]
        for part in psutil.disk_partitions():
            try:
                u = psutil.disk_usage(part.mountpoint)
                lines.append(f"• {part.device} {u.free // (1024**3)}GB boş / "
                             f"{u.total // (1024**3)}GB (%{u.percent} dolu)")
            except Exception:
                continue
        return "\n".join(lines)
    except Exception as exc:
        return f"Disk bilgisi alınamadı: {exc}"
