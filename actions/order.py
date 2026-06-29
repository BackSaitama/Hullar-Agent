"""
Sipariş yardımcısı — GÜVENLİ.

Ne YAPAR:
  • Ürünü seçtiğin sitede arar ve sayfasını açar
  • "sepeti aç" deyince ödeme/sepet sayfasını açar

Ne YAPMAZ (bilinçli — para güvenliği):
  • Otomatik "Satın Al / Öde" butonuna BASMAZ
  • Kart/ödeme bilgisi GİRMEZ
  → Son ödeme onayını her zaman SEN yaparsın.
"""

from __future__ import annotations

import logging
import re
import threading
import time
import urllib.parse
import webbrowser

logger = logging.getLogger("hullar.order")

# Site → (arama url şablonu, sepet url)
# Not: {q} içeren siteler doğrudan arama yapar. Yemek siteleri konum/JS bazlı
# olduğu için düz arama linki YOK → ana sayfayı açarız ({q} yok).
_SITES = {
    "trendyol":    ("https://www.trendyol.com/sr?q={q}",      "https://www.trendyol.com/sepet"),
    "hepsiburada": ("https://www.hepsiburada.com/ara?q={q}",  "https://www.hepsiburada.com/ara?q="),
    "amazon":      ("https://www.amazon.com.tr/s?k={q}",      "https://www.amazon.com.tr/gp/cart/view.html"),
    "n11":         ("https://www.n11.com/arama?q={q}",        "https://www.n11.com/sepetim"),
    # Yemek siparişi — Yemeksepeti'nde DOĞRUDAN arama URL'si çalışıyor
    "yemeksepeti": ("https://www.yemeksepeti.com/?expedition=delivery&vertical=restaurants&query={q}",
                    "https://www.yemeksepeti.com/"),
    "getir":       ("https://getir.com/",                     "https://getir.com/"),
    "trendyolyemek":("https://tgoyemek.com/",                 "https://tgoyemek.com/"),
}
_DEFAULT = "trendyol"

# Yemek siteleri için farklı mesaj
_FOOD = {"yemeksepeti", "getir", "trendyolyemek"}


def _pick_site(text: str) -> str:
    low = text.lower()
    # Site adı doğrudan geçiyorsa
    for s in _SITES:
        if s in low:
            return s
    # "yemek/yemeksepeti/getir" çağrışımları
    if "yemek" in low:
        return "yemeksepeti"
    if "getir" in low:
        return "getir"
    return _DEFAULT


# ── Otomatik akış (yemek): aç → ara → tıkla (en iyi çaba, OCR) ────────── #
def _notify(text: str) -> None:
    try:
        from .notify import push
        push(text)
    except Exception:
        pass
    logger.info("oto-sipariş: %s", text)


def _type_text(text: str) -> None:
    """Türkçe-güvenli yazma (pano + ctrl+v)."""
    try:
        import pyperclip  # type: ignore
        pyperclip.copy(text)
    except Exception:
        import subprocess
        subprocess.run(f'powershell -c "Set-Clipboard -Value \'{text}\'"',
                       shell=True, stdout=subprocess.DEVNULL)
    time.sleep(0.2)
    try:
        import pyautogui  # type: ignore
        pyautogui.hotkey("ctrl", "v")
    except Exception:
        pass


def _advance_checkout() -> None:
    """OCR ile sepete doğru ilerler: 'Sepete Ekle' → 'Sepetim/Sepete Git'.
    Son 'Sipariş Ver / Öde' tuşuna BASMAZ — o kullanıcıda kalır."""
    try:
        import pyautogui  # type: ignore
        from .smart_click import find_text_on_screen
    except Exception:
        return
    # 1) Sepete ekle
    for kw in ("sepete ekle", "ekle", "add to"):
        p = find_text_on_screen(kw)
        if p:
            pyautogui.click(*p)
            time.sleep(2.5)
            break
    # 2) Sepete git / Sepetim
    for kw in ("sepete git", "sepetim", "sepeti onayla", "devam"):
        p = find_text_on_screen(kw)
        if p:
            pyautogui.click(*p)
            time.sleep(2.5)
            break
    # Not: 'Sipariş Ver / Öde' burada bilinçli olarak TIKLANMAZ.


def _auto_food_flow(urun: str, url_searched: bool = False) -> None:
    """Sayfa açıldıktan sonra restoranı/sonucu OCR ile bulup tıklar.
    url_searched=True (Yemeksepeti): sayfa zaten sonuçla gelir → restorana tıkla.
    False (Getir vb.): arama kutusunu bul → yaz → Enter → restorana tıkla."""
    try:
        import pyautogui  # type: ignore
        from .smart_click import find_text_on_screen
    except Exception:
        _notify("Otomatik akış için pyautogui/OCR gerekli.")
        return

    first = (urun.split() or [urun])[0]
    time.sleep(7)  # sayfa yüklensin

    # A) URL zaten arama yaptıysa → doğrudan restorana tıklamayı dene
    if url_searched:
        rpos = find_text_on_screen(first)
        if rpos:
            pyautogui.click(*rpos)
            time.sleep(4)
            _advance_checkout()   # Sepete Ekle → Sepetim → ödeme adımları
            _notify(f"🍔 '{first}' açıldı ve sepete doğru ilerledim. "
                    f"Adres/kart kayıtlıysa son 'Sipariş Ver' sende.")
            return
        _notify(f"🔎 '{urun}' arandı ama '{first}' sonucunu tıklayamadım "
                f"(giriş/adres gerekebilir). Sonuçlardan elle seç.")
        return

    # B) Ana sayfa açıldı → arama kutusunu bul, yaz, Enter
    pos = None
    for kw in ("restoran", "mutfak", "ara", "search", "yemek ara"):
        pos = find_text_on_screen(kw)
        if pos:
            break
    if not pos:
        _notify("🔎 Arama kutusunu bulamadım — giriş/adres ekranında olabilirsin. "
                "Bir kez giriş yap + adres seç, sonra tekrar dene.")
        return
    pyautogui.click(*pos)
    time.sleep(0.6)
    _type_text(urun)
    time.sleep(0.4)
    pyautogui.press("enter")
    time.sleep(4.5)
    rpos = find_text_on_screen(first)
    if rpos:
        pyautogui.click(*rpos)
        _notify(f"🍔 '{first}' açıldı. Menüyü seç, sepete ekle. Son tuşa SEN bas.")
    else:
        _notify(f"🔎 '{urun}' arandı. Sonuçlardan restoranı seç, sepete ekle.")


def order(parameters: dict | None = None) -> str:
    p = parameters or {}
    urun = (p.get("urun") or "").strip()
    site = p.get("site") or _DEFAULT
    if not urun:
        return "Efendim, ne sipariş edeyim? (örn: 'kablosuz mouse sipariş et')"

    search_url, _ = _SITES.get(site, _SITES[_DEFAULT])
    first = (urun.split() or [urun])[0]
    # Yemeksepeti restoran adıyla arar → ilk kelime; mağazalar tam ürün adı
    query = first if site == "yemeksepeti" else urun
    url = search_url.format(q=urllib.parse.quote(query))
    try:
        webbrowser.open(url)
    except Exception as exc:
        return f"Sayfa açılamadı: {exc}"
    if site in _FOOD:
        # Yemeksepeti URL'si doğrudan arama yapar → restorana tıklamayı dene
        url_searched = "{q}" in search_url
        threading.Thread(target=_auto_food_flow, args=(urun, url_searched),
                         daemon=True).start()
        return (f"🍔 {site} açıldı, '{urun}' için otomatik ilerliyorum "
                f"(restoranı bulup giriyorum)...\n"
                f"Adres + kart hesabında KAYITLI ise tek yapman gereken son "
                f"'Sipariş Ver' tuşuna basmak. (Kart numarasını ben giremem — "
                f"o yüzden kartın kayıtlı olmalı.)\n"
                f"Takılırsam: 'ekranda Sepete Ekle'ye tıkla', sonra 'sepeti aç'.")
    return (f"🛒 '{urun}' için {site} araması açıldı.\n"
            f"Ürünü seç ve sepete ekle. Hazır olunca 'sepeti aç' de — "
            f"ödeme sayfasına götüreyim. Son ödemeyi SEN onaylarsın "
            f"(ben kart bilgisi girmem / 'Öde' tuşuna basmam).")


_HOMEPAGES = {
    "trendyol": "https://www.trendyol.com/",
    "hepsiburada": "https://www.hepsiburada.com/",
    "amazon": "https://www.amazon.com.tr/",
    "n11": "https://www.n11.com/",
    "yemeksepeti": "https://www.yemeksepeti.com/",
    "getir": "https://getir.com/",
    "trendyolyemek": "https://tgoyemek.com/",
}


def open_site(parameters: dict | None = None) -> str:
    """Bir alışveriş/yemek sitesinin ana sayfasını açar (ürün aramadan)."""
    site = (parameters or {}).get("site") or _DEFAULT
    url = _HOMEPAGES.get(site, _HOMEPAGES[_DEFAULT])
    try:
        webbrowser.open(url)
    except Exception as exc:
        return f"Açılamadı: {exc}"
    return f"🌐 {site} açıldı."


def _extract_site(msg: str) -> dict:
    return {"site": _pick_site(msg)}


def open_cart(parameters: dict | None = None) -> str:
    p = parameters or {}
    site = p.get("site") or _DEFAULT
    _, cart_url = _SITES.get(site, _SITES[_DEFAULT])
    try:
        webbrowser.open(cart_url)
    except Exception as exc:
        return f"Sepet açılamadı: {exc}"
    return (f"💳 {site} sepet/ödeme sayfası açıldı. Siparişi gözden geçir ve "
            f"ödemeyi sen tamamla. Güvenlik için son onayı ben yapmıyorum.")


# ── Extractor'lar ─────────────────────────────────────────────────────── #
def _extract_order(msg: str) -> dict:
    site = _pick_site(msg)
    # Ürün adını ayıkla: site adları (ekleriyle) + fiiller + dolgu kelimeleri
    urun = re.sub(
        r"\b(trendyolyemek|yemeksepeti|hepsiburada|trendyol|amazon|getir|n11)"
        r"(?:'?(?:nden|ndan|dan|den|tan|ten|da|de|a|e))?\b",
        "", msg, flags=re.I)
    urun = re.sub(
        r"\b(sipariş(?:\s*et)?|siparis(?:\s*et)?|satın\s*al|satin\s*al|ısmarla|"
        r"ismarla|söyle|soyle|yemek|al)\b",
        "", urun, flags=re.I)
    urun = re.sub(r"\s+", " ", urun).strip(" .,;:'\"-")
    return {"urun": urun, "site": site}


def _extract_cart(msg: str) -> dict:
    return {"site": _pick_site(msg)}
