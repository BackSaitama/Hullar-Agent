"""
HULLAR izleme/uyarı skilleri — arka planda izler, Telegram'dan haber verir.

  • site_izle    : bir site çökerse bildir
  • net_izle     : internet kesilince/gelince bildir
  • yagmur_uyari : bugün yağmur varsa bildir (wttr.in)
  • fiyat_takip  : bir ürün sayfasında fiyat hedefin altına düşünce bildir (best-effort)
"""

from __future__ import annotations

import re
import threading
import time


def _push(text: str):
    try:
        from .notify import push
        push(text)
    except Exception:
        pass


# ── Site izle (çökerse bildir) ────────────────────────────────────────── #
_SITE = {"on": False}


def site_izle(parameters: dict | None = None) -> str:
    p = parameters or {}
    if p.get("action") == "stop":
        _SITE["on"] = False
        return "🌐 Site izleme durduruldu."
    url = (p.get("url") or "").strip()
    if not url:
        return "Hangi siteyi izleyeyim? Örn: 'siteyi izle example.com'"
    if not url.startswith("http"):
        url = "https://" + url
    if _SITE.get("on"):
        return "Zaten bir site izleniyor."
    _SITE["on"] = True

    def _run():
        import requests
        cokmustu = False
        while _SITE.get("on"):
            try:
                r = requests.get(url, timeout=10)
                if r.status_code >= 500 and not cokmustu:
                    cokmustu = True
                    _push(f"🔴 {url} çöktü (HTTP {r.status_code}).")
                elif r.ok and cokmustu:
                    cokmustu = False
                    _push(f"🟢 {url} geri geldi.")
            except Exception:
                if not cokmustu:
                    cokmustu = True
                    _push(f"🔴 {url} erişilemiyor!")
            time.sleep(60)

    threading.Thread(target=_run, daemon=True).start()
    return f"🌐 {url} izleniyor — çökerse haber veririm. Durdur: 'site izlemeyi durdur'."


def _extract_site_izle(msg: str) -> dict:
    if any(w in msg.lower() for w in ("durdur", "bırak", "iptal")):
        return {"action": "stop"}
    m = re.search(r"(https?://\S+|[\w\-]+\.[a-z]{2,}\S*)", msg, re.I)
    return {"url": m.group(1) if m else ""}


# ── İnternet izle ─────────────────────────────────────────────────────── #
_NET = {"on": False}


def net_izle(parameters: dict | None = None) -> str:
    p = parameters or {}
    if p.get("action") == "stop":
        _NET["on"] = False
        return "📡 İnternet izleme durduruldu."
    if _NET.get("on"):
        return "İnternet zaten izleniyor."
    _NET["on"] = True

    def _run():
        import socket
        kesik = False
        kesik_t = 0
        while _NET.get("on"):
            try:
                socket.create_connection(("8.8.8.8", 53), timeout=4).close()
                if kesik:
                    kesik = False
                    sure = int(time.time() - kesik_t)
                    _push(f"🟢 İnternet geri geldi ({sure} sn kesikti).")
            except Exception:
                if not kesik:
                    kesik = True
                    kesik_t = time.time()
                    _push("🔴 İnternet kesildi!")
            time.sleep(15)

    threading.Thread(target=_run, daemon=True).start()
    return "📡 İnternet izleniyor — kesilince/gelince haber veririm. Durdur: 'internet izlemeyi durdur'."


def _extract_net_izle(msg: str) -> dict:
    if any(w in msg.lower() for w in ("durdur", "bırak", "iptal")):
        return {"action": "stop"}
    return {}


# ── Yağmur uyarısı ────────────────────────────────────────────────────── #
def yagmur_uyari(parameters: dict | None = None) -> str:
    sehir = (parameters or {}).get("sehir", "Istanbul")
    try:
        import requests
        r = requests.get(f"https://wttr.in/{sehir}?format=j1", timeout=12).json()
        bugun = r["weather"][0]["hourly"]
        yagmurlu = [h for h in bugun if int(h.get("chanceofrain", 0)) >= 50]
        if yagmurlu:
            saatler = ", ".join(f"%{h['chanceofrain']}" for h in yagmurlu[:4])
            return f"🌧️ {sehir}: Bugün yağmur ihtimali yüksek ({saatler}). Şemsiye al!"
        return f"☀️ {sehir}: Bugün yağmur beklenmiyor."
    except Exception as exc:
        return f"Hava durumu alınamadı: {exc}"


def _extract_yagmur(msg: str) -> dict:
    m = re.search(r"\b([A-ZÇĞİÖŞÜ][a-zçğışöü]+)\b.*\b(yağmur|hava)", msg)
    return {"sehir": m.group(1) if m else "Istanbul"}


# ── Fiyat takip (best-effort) ─────────────────────────────────────────── #
_FIYAT = {"on": False}


def fiyat_takip(parameters: dict | None = None) -> str:
    p = parameters or {}
    if p.get("action") == "stop":
        _FIYAT["on"] = False
        return "🏷️ Fiyat takibi durduruldu."
    url = (p.get("url") or "").strip()
    hedef = int(p.get("hedef", 0))
    if not url or not hedef:
        return ("Kullanım: 'fiyat takip <link> <hedef TL>' — "
                "örn: fiyat takip trendyol.com/... 500")
    if not url.startswith("http"):
        url = "https://" + url
    if _FIYAT.get("on"):
        return "Zaten bir fiyat takibi var."
    _FIYAT["on"] = True

    def _run():
        import requests
        while _FIYAT.get("on"):
            try:
                html = requests.get(url, timeout=12,
                                    headers={"User-Agent": "Mozilla/5.0"}).text
                # TL fiyatlarını yakala (1.234,56 TL gibi)
                fiyatlar = re.findall(r"(\d{1,3}(?:[.\s]\d{3})*(?:,\d{2})?)\s*(?:TL|₺)", html)
                nums = []
                for f in fiyatlar:
                    try:
                        nums.append(float(f.replace(".", "").replace(" ", "").replace(",", ".")))
                    except Exception:
                        pass
                if nums:
                    en_dusuk = min(n for n in nums if n > 1)
                    if en_dusuk <= hedef:
                        _push(f"🏷️ Fiyat düştü! {en_dusuk:.0f} TL ≤ {hedef} TL\n{url}")
                        break
            except Exception:
                pass
            time.sleep(1800)   # 30 dk'da bir
        _FIYAT["on"] = False

    threading.Thread(target=_run, daemon=True).start()
    return f"🏷️ Fiyat takibi açık — {hedef} TL altına düşünce haber veririm (30 dk'da bir bakar)."


def _extract_fiyat(msg: str) -> dict:
    if any(w in msg.lower() for w in ("durdur", "bırak", "iptal")):
        return {"action": "stop"}
    url = re.search(r"(https?://\S+|[\w\-]+\.[a-z]{2,}/\S*)", msg, re.I)
    hedef = re.search(r"(\d{2,7})\s*(?:tl|₺|lira)?\s*$", msg.strip(), re.I)
    if not hedef:
        hedef = re.search(r"(\d{2,7})", msg)
    return {"url": url.group(1) if url else "",
            "hedef": int(hedef.group(1)) if hedef else 0}
