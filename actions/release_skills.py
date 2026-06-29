"""
HULLAR — yayın öncesi cila skilleri (1-10).

bot_loglari, bot_yeniden_baslat, komut_ara, favoriler, pano_gecmisi,
ekran_yayin (kısa), pil_esik, konum, ne_indirdim.
('Tehlikeli komutta onay' dispatcher içinde ele alınır.)
"""

from __future__ import annotations

import os
import re
import subprocess
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
LOG = DATA / "hullar.log"
FAV = DATA / "favoriler.json"
PANO = DATA / "pano_gecmisi.json"


def _push(text: str):
    try:
        from .notify import push
        push(text)
    except Exception:
        pass


# ── 1) Bot logları ─────────────────────────────────────────────────────── #
def bot_loglari(parameters: dict | None = None) -> str:
    n = int((parameters or {}).get("satir", 20))
    if not LOG.exists():
        return "📜 Henüz log yok (bot yeni başlamış olabilir)."
    try:
        lines = LOG.read_text(encoding="utf-8", errors="ignore").splitlines()
        son = lines[-n:]
        return "📜 Son loglar:\n" + "\n".join(son)[-3500:]
    except Exception as exc:
        return f"Log okunamadı: {exc}"


def _extract_log(msg: str) -> dict:
    m = re.search(r"(\d+)", msg)
    return {"satir": int(m.group(1)) if m else 20}


# ── 2) Botu yeniden başlat ─────────────────────────────────────────────── #
def bot_yeniden_baslat(parameters: dict | None = None) -> str:
    vbs = ROOT / "start_hidden.vbs"
    try:
        if vbs.exists():
            # 4 sn sonra yeni örneği başlat (eski kapanıp mutex'i bıraksın)
            subprocess.Popen(
                f'cmd /c timeout /t 4 >nul & wscript "{vbs}"',
                shell=True,
                creationflags=getattr(subprocess, "DETACHED_PROCESS", 0))
        else:
            subprocess.Popen(
                'cmd /c timeout /t 4 >nul & start "" pythonw -m hullar telegram',
                shell=True, cwd=str(ROOT))
    except Exception as exc:
        return f"Yeniden başlatılamadı: {exc}"

    def _bye():
        time.sleep(1.5)
        os._exit(0)
    threading.Thread(target=_bye, daemon=True).start()
    return "🔄 Yeniden başlıyorum... 5 saniye içinde tekrar buradayım."


# ── 3) Komut ara ───────────────────────────────────────────────────────── #
def komut_ara(parameters: dict | None = None) -> str:
    q = (parameters or {}).get("kelime", "").strip().lower()
    if not q:
        return "Ne arıyorsun? Örn: 'komut ara ekran'"
    try:
        from .yardim import _YARDIM_HAM  # ham metin varsa
        kaynak = _YARDIM_HAM
    except Exception:
        from . import yardim
        kaynak = yardim.yardim(parameters={})
    bulunan = [l.strip("•- ") for l in kaynak.splitlines()
               if q in l.lower() and len(l.strip()) > 3]
    if not bulunan:
        return f"🔎 '{q}' ile ilgili komut bulamadım. /skills ile hepsine bak."
    return f"🔎 '{q}' ile ilgili komutlar:\n" + "\n".join(f"• {b}" for b in bulunan[:15])


def _extract_ara(msg: str) -> dict:
    m = re.search(r"(?:komut ara|ara|skill ara|hangi komut)\s*[:\-]?\s*(.+)", msg, re.I)
    return {"kelime": m.group(1).strip() if m else ""}


# ── 4) Favoriler (kayıt + göster) ──────────────────────────────────────── #
def _fav_yukle() -> list:
    try:
        import json
        return json.loads(FAV.read_text(encoding="utf-8")) if FAV.exists() else []
    except Exception:
        return []


def _fav_kaydet(lst: list):
    try:
        import json
        DATA.mkdir(parents=True, exist_ok=True)
        FAV.write_text(json.dumps(lst, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


def favoriler(parameters: dict | None = None) -> str:
    p = parameters or {}
    lst = _fav_yukle()
    if p.get("ekle"):
        k = p["ekle"].strip()
        if k and k not in lst:
            lst.append(k); _fav_kaydet(lst[-12:])
        return f"⭐ Favorilere eklendi: {k}"
    if p.get("sil"):
        lst = [x for x in lst if x != p["sil"].strip()]
        _fav_kaydet(lst)
        return f"⭐ Silindi: {p['sil']}"
    if not lst:
        return ("⭐ Favori yok. Ekle: 'favori ekle pil durumu'. "
                "Sonra 'favorilerim' ile hızlı erişirsin.")
    return "⭐ Favorilerin:\n" + "\n".join(f"• {x}" for x in lst)


def _extract_fav(msg: str) -> dict:
    m = re.search(r"favori(?:ye)?\s*ekle\s*[:\-]?\s*(.+)", msg, re.I)
    if m:
        return {"ekle": m.group(1).strip()}
    m = re.search(r"favori(?:den)?\s*sil\s*[:\-]?\s*(.+)", msg, re.I)
    if m:
        return {"sil": m.group(1).strip()}
    return {}


# ── 5) Pano geçmişi ────────────────────────────────────────────────────── #
def pano_gecmisi(parameters: dict | None = None) -> str:
    import json
    try:
        hist = json.loads(PANO.read_text(encoding="utf-8")) if PANO.exists() else []
    except Exception:
        hist = []
    # şu anki panoyu da ekle
    try:
        import pyperclip
        cur = pyperclip.paste()
        if cur and (not hist or hist[-1] != cur):
            hist.append(cur); hist = hist[-15:]
            DATA.mkdir(parents=True, exist_ok=True)
            PANO.write_text(json.dumps(hist, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass
    if not hist:
        return "📋 Pano geçmişi boş."
    return "📋 Son kopyalananlar:\n" + "\n".join(
        f"{i+1}. {x[:60]}" for i, x in enumerate(reversed(hist[-10:])))


# ── 6) Ekranı kısa süre yayınla (gözcü kısa) ──────────────────────────── #
def ekran_yayin(parameters: dict | None = None) -> str:
    sn = int((parameters or {}).get("sure", 30))
    sn = max(5, min(sn, 120))
    try:
        from .monitor2 import gozcu  # varsa süreli ekran takibi
        return gozcu(parameters={"sure": sn})
    except Exception:
        pass
    return (f"📺 {sn} sn ekran yayını için 'ekranı izle' kullan "
            f"(canlı ekran zaten menüde).")


def _extract_yayin(msg: str) -> dict:
    m = re.search(r"(\d+)", msg)
    return {"sure": int(m.group(1)) if m else 30}


# ── 7) Pil eşik bildirimi ──────────────────────────────────────────────── #
_PIL = {"on": False}


def pil_esik(parameters: dict | None = None) -> str:
    esik = int((parameters or {}).get("esik", 20))
    if _PIL.get("on"):
        _PIL["on"] = False
        return "🔋 Pil takibi durduruldu."
    _PIL["on"] = True

    def _watch():
        try:
            import psutil
        except Exception:
            return
        uyarildi = False
        while _PIL.get("on"):
            try:
                b = psutil.sensors_battery()
                if b and not b.power_plugged:
                    if b.percent <= esik and not uyarildi:
                        _push(f"🔋 Pil %{int(b.percent)}! Şarja tak.")
                        uyarildi = True
                    elif b.percent > esik + 5:
                        uyarildi = False
            except Exception:
                pass
            time.sleep(60)
    threading.Thread(target=_watch, daemon=True).start()
    return f"🔋 Pil %{esik} altına inince haber vereceğim. Durdurmak için tekrar yaz."


def _extract_pil_esik(msg: str) -> dict:
    m = re.search(r"%?\s*(\d{1,3})", msg)
    return {"esik": int(m.group(1)) if m else 20}


# ── 8) Konum (IP'den yaklaşık) ─────────────────────────────────────────── #
def konum(parameters: dict | None = None) -> str:
    try:
        import requests
        d = requests.get("http://ip-api.com/json/?lang=tr", timeout=10).json()
        if d.get("status") == "success":
            return (f"📍 Yaklaşık konum (IP):\n"
                    f"• {d.get('city')}, {d.get('regionName')}, {d.get('country')}\n"
                    f"• ISP: {d.get('isp')}\n"
                    f"• Konum: {d.get('lat')}, {d.get('lon')}\n"
                    f"🗺️ https://maps.google.com/?q={d.get('lat')},{d.get('lon')}")
        return "Konum alınamadı."
    except Exception as exc:
        return f"Konum hatası: {exc}"


# ── 9) Ne indirdim (son indirilenler) ──────────────────────────────────── #
def ne_indirdim(parameters: dict | None = None) -> str:
    dl = Path(os.path.expanduser("~")) / "Downloads"
    if not dl.exists():
        return "İndirilenler klasörü bulunamadı."
    try:
        dosyalar = sorted(dl.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True)
        dosyalar = [f for f in dosyalar if f.is_file()][:10]
        if not dosyalar:
            return "📥 İndirilenler boş."
        out = ["📥 Son indirilenler:"]
        for f in dosyalar:
            mb = f.stat().st_size / 1_048_576
            out.append(f"• {f.name} ({mb:.1f} MB)")
        out.append("\n💡 Birini telefona almak için: 'dosya gönder <isim>'")
        return "\n".join(out)
    except Exception as exc:
        return f"Hata: {exc}"
