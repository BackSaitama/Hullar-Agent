"""
HULLAR güç-kullanıcı skilleri (yeni).

  • panik_modu       : ekranı kilitle + tarayıcıları kapat + sustur (tek komut)
  • ekran_oku        : ekrandaki TÜM yazıyı OCR ile okur (metin döndürür)
  • ekran_ozetle     : ekrandaki metni AI ile özetler
  • guc_plani        : performans / tasarruf / dengeli güç planı
  • zamanli_kapat    : "1 saat sonra kapat", "30 dk sonra kapat"
  • sabah_rutini     : günlük uygulamaları aç
  • pil_uyari        : arka planda pili izle, %20 altına düşünce Telegram'dan uyar
"""

from __future__ import annotations

import re
import subprocess
import threading
import time


# ── Panik modu ────────────────────────────────────────────────────────── #
def panik_modu(parameters: dict | None = None) -> str:
    yapilan = []
    try:
        from .extra_skills import tarayicilari_kapat
        tarayicilari_kapat()
        yapilan.append("tarayıcılar kapatıldı")
    except Exception:
        pass
    try:
        from .volume_control import volume_control
        volume_control({"action": "kapat"})
        yapilan.append("ses kapatıldı")
    except Exception:
        pass
    try:
        subprocess.run("rundll32.exe user32.dll,LockWorkStation", shell=True)
        yapilan.append("ekran kilitlendi")
    except Exception:
        pass
    return "🚨 Panik modu: " + ", ".join(yapilan) + "."


# ── Ekrandaki yazıyı oku (OCR) ────────────────────────────────────────── #
def ekran_oku(parameters: dict | None = None) -> str:
    try:
        from .smart_click import _grab_screen, _ensure_tesseract
        if not _ensure_tesseract():
            return "OCR (tesseract) bulunamadı."
        img, _, _ = _grab_screen()
        if img is None:
            return "Ekran yakalanamadı."
        import pytesseract  # type: ignore
        try:
            txt = pytesseract.image_to_string(img, lang="tur+eng")
        except Exception:
            txt = pytesseract.image_to_string(img)
        txt = re.sub(r"\n{3,}", "\n\n", txt).strip()
        if not txt:
            return "Ekranda okunabilir yazı bulamadım."
        return "📖 Ekrandaki yazı:\n" + txt[:3500]
    except Exception as exc:
        return f"Ekran okunamadı: {exc}"


# ── Ekranı AI ile özetle ──────────────────────────────────────────────── #
def ekran_ozetle(parameters: dict | None = None) -> str:
    raw = ekran_oku()
    if not raw.startswith("📖"):
        return raw
    metin = raw.replace("📖 Ekrandaki yazı:\n", "")
    try:
        from .ai_skills import _ask_ai
        ozet = _ask_ai(
            "Sen bir asistansın. Verilen ekran metnini Türkçe, kısa (2-3 cümle) özetle.",
            f"Ekrandaki metin:\n{metin[:3000]}",
        )
        return f"🧠 Ekran özeti:\n{ozet}"
    except Exception as exc:
        return f"Özetlenemedi: {exc}"


# ── Güç planı ─────────────────────────────────────────────────────────── #
_GUC = {
    "performans": "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c",  # Yüksek performans
    "tasarruf":   "a1841308-3541-4fab-bc81-f71556f20b4a",  # Güç tasarrufu
    "dengeli":    "381b4222-f694-41f0-9685-ff5bb260df2e",  # Dengeli
}


def guc_plani(parameters: dict | None = None) -> str:
    mod = (parameters or {}).get("mod", "dengeli")
    guid = _GUC.get(mod, _GUC["dengeli"])
    try:
        subprocess.run(f"powercfg /setactive {guid}", shell=True,
                       capture_output=True)
        return f"⚡ Güç planı: {mod}."
    except Exception as exc:
        return f"Güç planı değiştirilemedi: {exc}"


def _extract_guc(msg: str) -> dict:
    low = msg.lower()
    if "performans" in low or "yüksek" in low or "hızlı" in low:
        return {"mod": "performans"}
    if "tasarruf" in low or "pil" in low or "düşük" in low:
        return {"mod": "tasarruf"}
    return {"mod": "dengeli"}


# ── Zamanlı kapatma ───────────────────────────────────────────────────── #
def zamanli_kapat(parameters: dict | None = None) -> str:
    sec = int((parameters or {}).get("seconds", 0))
    if sec <= 0:
        return "Ne zaman kapatayım? (örn: '1 saat sonra kapat')"
    try:
        subprocess.run(f"shutdown /s /t {sec}", shell=True)
        dk = sec // 60
        return (f"⏲️ Bilgisayar {dk} dakika sonra kapanacak. "
                f"İptal: 'kapatmayı iptal et'.")
    except Exception as exc:
        return f"Zamanlanamadı: {exc}"


def _extract_zamanli(msg: str) -> dict:
    low = msg.lower()
    total = 0
    h = re.search(r"(\d+)\s*saat", low)
    m = re.search(r"(\d+)\s*(dakika|dk)", low)
    if h:
        total += int(h.group(1)) * 3600
    if m:
        total += int(m.group(1)) * 60
    if total == 0:
        n = re.search(r"(\d+)", low)
        if n:
            total = int(n.group(1)) * 60  # sayı varsa dakika say
    return {"seconds": total}


# ── Sabah rutini (günlük uygulamaları aç) ─────────────────────────────── #
_RUTIN_APPS = ["start chrome.exe", "start spotify:"]


def sabah_rutini(parameters: dict | None = None) -> str:
    acilan = []
    for cmd in _RUTIN_APPS:
        try:
            subprocess.Popen(cmd, shell=True)
            acilan.append(cmd.split()[-1])
        except Exception:
            continue
    return "🌅 Sabah rutini: " + (", ".join(acilan) + " açıldı." if acilan
                                   else "uygulama açılamadı.")


# ── Pil uyarısı (arka planda izle) ────────────────────────────────────── #
_PIL = {"on": False}


def pil_uyari(parameters: dict | None = None) -> str:
    if _PIL.get("on"):
        return "🔋 Pil uyarısı zaten açık."
    esik = int((parameters or {}).get("esik", 20))
    _PIL["on"] = True

    def _watch():
        from .notify import push
        uyarildi = False
        while _PIL.get("on"):
            try:
                import psutil
                b = psutil.sensors_battery()
                if b is not None:
                    if not b.power_plugged and b.percent <= esik and not uyarildi:
                        push(f"🪫 Pil %{int(b.percent)}! Şarja tak.")
                        uyarildi = True
                    if b.power_plugged:
                        uyarildi = False
            except Exception:
                pass
            time.sleep(60)

    threading.Thread(target=_watch, daemon=True).start()
    return f"🔋 Pil uyarısı açık — %{esik} altına düşünce Telegram'dan haber veririm."


def pil_uyari_kapat(parameters: dict | None = None) -> str:
    _PIL["on"] = False
    return "🔋 Pil uyarısı kapatıldı."


# ── Zamanlı sesli uyarı (overlay + ses + Telegram) ────────────────────── #
def zamanli_uyari(parameters: dict | None = None) -> str:
    p = parameters or {}
    sec = int(p.get("seconds", 0))
    text = (p.get("text") or "Hatırlatma!").strip() or "Hatırlatma!"
    if sec <= 0:
        return "Ne zaman uyarayım? (örn: '10 dk sonra uyar: çay hazır')"

    def _fire():
        time.sleep(sec)
        try:
            from .extra_skills import pc_bildirim
            pc_bildirim({"text": text, "sesli": True})
        except Exception:
            pass
        try:
            from .notify import push
            push(f"⏰ {text}")
        except Exception:
            pass

    threading.Thread(target=_fire, daemon=True).start()
    dk = sec // 60
    ne = f"{dk} dk" if dk else f"{sec} sn"
    return f"⏰ {ne} sonra büyük+sesli uyaracağım: {text}"


def _extract_uyari(msg: str) -> dict:
    low = msg.lower()
    total = 0
    h = re.search(r"(\d+)\s*saat", low)
    m = re.search(r"(\d+)\s*(dakika|dk)", low)
    s = re.search(r"(\d+)\s*(saniye|sn)", low)
    if h:
        total += int(h.group(1)) * 3600
    if m:
        total += int(m.group(1)) * 60
    if s:
        total += int(s.group(1))
    if total == 0:
        n = re.search(r"(\d+)", low)
        if n:
            total = int(n.group(1)) * 60
    # Mesajı ayıkla: "... uyar: MESAJ" veya "... sonra MESAJ"
    mt = re.search(r"(?:uyar|hatırlat|alarm)\s*[:\-]?\s*(.+)", msg, re.I)
    text = mt.group(1).strip() if mt else ""
    if not text:
        mt2 = re.search(r"sonra\s+(.+)", msg, re.I)
        text = mt2.group(1).strip() if mt2 else "Hatırlatma!"
    text = re.sub(r"\b(uyar|beni|bana)\b", "", text, flags=re.I).strip(" :-")
    return {"seconds": total, "text": text or "Hatırlatma!"}
