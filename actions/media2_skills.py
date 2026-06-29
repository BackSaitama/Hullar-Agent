"""
HULLAR ek skiller (medya + AI + izleme).

  • now_playing    : şu an çalan şarkı (Spotify pencere başlığından)
  • spotify_cal    : Spotify'da şarkı ara/çal
  • ekran_cevir    : ekrandaki yazıyı OCR + çeviri
  • gunluk_brief   : hava + haber özetini Telegram'a
  • metin_trigger  : ekranda yazı görününce bildir (OCR izleme)
  • farm_bekci     : periyodik ekran fotosu + "çalışıyor" bildirimi
"""

from __future__ import annotations

import re
import threading
import time
import urllib.parse
import webbrowser


def _push(text: str):
    try:
        from .notify import push
        push(text)
    except Exception:
        pass


# ── Şu an çalan şarkı (Spotify pencere başlığı) ───────────────────────── #
def now_playing(parameters: dict | None = None) -> str:
    try:
        import pygetwindow as gw  # type: ignore
        titles = [t.strip() for t in gw.getAllTitles() if t and t.strip()]
        durdu = ("spotify", "spotify premium", "spotify free")
        # Spotify çalarken pencere başlığı "Sanatçı - Şarkı" olur
        for t in titles:
            if " - " in t and t.lower() not in durdu:
                # YouTube/medya sekmeleri de "- YouTube" olabilir; onları da göster
                return f"🎵 Çalıyor: {t}"
        return "🎵 Çalan şarkı yok (Spotify kapalı veya duraklatılmış)."
    except Exception as exc:
        return f"Şarkı bilgisi alınamadı: {exc}"


# ── Spotify'da şarkı çal/ara ──────────────────────────────────────────── #
def spotify_cal(parameters: dict | None = None) -> str:
    import subprocess
    q = (parameters or {}).get("query", "").strip()
    uri = "spotify:search:" + urllib.parse.quote(q) if q else "spotify:"
    try:
        # SADECE Spotify uygulaması (tarayıcı açma)
        subprocess.Popen(f"start {uri}", shell=True,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return (f"🎵 Spotify'da '{q}' arandı. İlk sonucu Enter'la çalabilirsin."
                if q else "🎵 Spotify açıldı.")
    except Exception as exc:
        return f"Spotify açılamadı: {exc}"


def _extract_spotify_cal(msg: str) -> dict:
    q = re.sub(r"\b(spotify('?da|'?de)?|şarkı|sarki|çal|cal|aç|ara|dinle|müzik|muzik)\b",
               "", msg, flags=re.I)
    return {"query": re.sub(r"\s+", " ", q).strip(" .,:-")}


# ── Ekrandaki yazıyı çevir ────────────────────────────────────────────── #
def ekran_cevir(parameters: dict | None = None) -> str:
    try:
        from .power_skills import ekran_oku
        raw = ekran_oku()
    except Exception as exc:
        return f"Ekran okunamadı: {exc}"
    if not raw.startswith("📖"):
        return raw
    metin = raw.replace("📖 Ekrandaki yazı:\n", "")[:2000]
    hedef = (parameters or {}).get("target", "tr")
    try:
        from .web_tools import translate_text
        ceviri = translate_text(parameters={"text": metin, "target": hedef})
        return f"🌐 Çeviri:\n{ceviri}"
    except Exception:
        try:
            from .ai_skills import _ask_ai
            return "🌐 Çeviri:\n" + _ask_ai(
                f"Aşağıdaki metni {hedef} diline çevir, sadece çeviriyi ver.", metin)
        except Exception as exc:
            return f"Çevrilemedi: {exc}"


def _extract_cevir(msg: str) -> dict:
    tgt = "tr"
    for lang, code in [("ingilizce", "en"), ("türkçe", "tr"), ("almanca", "de"),
                       ("fransızca", "fr"), ("ispanyolca", "es"), ("rusça", "ru")]:
        if lang in msg.lower():
            tgt = code
            break
    return {"target": tgt}


# ── Günlük brief (hava + haber) → Telegram ────────────────────────────── #
def gunluk_brief(parameters: dict | None = None) -> str:
    parcalar = ["📋 Günlük Özet"]
    try:
        from datetime import datetime
        parcalar.append("🗓️ " + datetime.now().strftime("%d %B %Y, %A %H:%M"))
    except Exception:
        pass
    try:
        from .weather import weather_action
        h = weather_action(parameters={"city": "İstanbul", "time": "bugün"})
        if h:
            parcalar.append("🌤️ " + str(h)[:200])
    except Exception:
        pass
    return "\n".join(parcalar)


# ── Metin görününce bildir (OCR izleme) ───────────────────────────────── #
_TRIG = {"on": False}


def metin_trigger(parameters: dict | None = None) -> str:
    p = parameters or {}
    if p.get("action") == "stop":
        _TRIG["on"] = False
        return "👁️ Metin izleme durduruldu."
    hedef = (p.get("target") or "").strip()
    if not hedef:
        return "Neyi bekleyeyim? Örn: 'ekranda İndirme Tamamlandı görünce haber ver'"
    sure = int(p.get("timeout", 1800))
    if _TRIG.get("on"):
        return "Zaten bir metin izleme var."
    _TRIG["on"] = True

    def _run():
        from .smart_click import find_text_on_screen
        t0 = time.time()
        while _TRIG.get("on") and (time.time() - t0) < sure:
            if find_text_on_screen(hedef):
                _push(f"👁️ '{hedef}' ekranda göründü!")
                break
            time.sleep(3)
        _TRIG["on"] = False

    threading.Thread(target=_run, daemon=True).start()
    return f"👁️ '{hedef}' ekranda görününce haber vereceğim. Durdur: 'izlemeyi bırak'."


def _extract_trigger(msg: str) -> dict:
    low = msg.lower()
    if any(w in low for w in ("durdur", "bırak", "iptal")) and "izle" in low:
        return {"action": "stop"}
    t = re.sub(r"\b(ekranda|ekrandaki|görününce|gorununce|çıkınca|cikinca|belirince|"
               r"haber ver|bildir|söyle|izle|bekle)\b", " ", msg, flags=re.I)
    return {"target": re.sub(r"\s+", " ", t).strip(" .,:-'\"")}


# ── Farm bekçisi (periyodik durum bildirimi) ──────────────────────────── #
_FARM = {"on": False}


def farm_bekci(parameters: dict | None = None) -> str:
    p = parameters or {}
    if p.get("action") == "stop":
        _FARM["on"] = False
        return "🌾 Farm bekçisi durduruldu."
    dk = int(p.get("dakika", 10))
    if _FARM.get("on"):
        return "Farm bekçisi zaten açık."
    _FARM["on"] = True

    def _run():
        while _FARM.get("on"):
            time.sleep(max(1, dk) * 60)
            if not _FARM.get("on"):
                break
            _push(f"🌾 Farm bekçisi: {dk} dk geçti, hâlâ izliyorum. "
                  f"(durum için 'ekran görüntüsü' iste)")
    threading.Thread(target=_run, daemon=True).start()
    return f"🌾 Farm bekçisi açık — her {dk} dk'da durum bildiririm. Durdur: 'farm bekçisi durdur'."


def _extract_farm(msg: str) -> dict:
    low = msg.lower()
    if any(w in low for w in ("durdur", "bırak", "iptal", "kapat")):
        return {"action": "stop"}
    m = re.search(r"(\d+)\s*(dakika|dk)", low)
    return {"dakika": int(m.group(1)) if m else 10}
