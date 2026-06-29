"""
HULLAR Vision Ajanı — ekranı GERÇEKTEN görür (Gemini vision) ve buna göre davranır.

  • gor_ekran(istek) : ekranın fotosunu vision modeline gönderir, ne olduğunu anlatır
  • gor_yap(istek)   : ekrana bakar, ne yapılacağına karar verir ve UYGULAR
                       (TIKLA:<yazı> → OCR ile bulup tıklar, YAZ/TUS/BEKLE)

Oyun (Minecraft/Roblox) ve normal uygulamalarda çalışır — kör makro değil,
ekranı görüp anlayarak hareket eder.
"""

from __future__ import annotations

import base64
import io
import os
import re
import threading
import time


def _push(text: str):
    try:
        from .notify import push
        push(text)
    except Exception:
        pass


def _screen_jpeg_b64(scale: float = 0.66, quality: int = 70) -> tuple[str, int, int] | None:
    """Ekranı JPEG base64 döndürür + (gerçek_genişlik, gerçek_yükseklik)."""
    try:
        import mss          # type: ignore
        from PIL import Image  # type: ignore
        with mss.mss() as sct:
            mon = sct.monitors[1]
            shot = sct.grab(mon)
            img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
        W, H = img.width, img.height
        small = img.resize((int(W * scale), int(H * scale)))
        buf = io.BytesIO()
        small.save(buf, format="JPEG", quality=quality)
        return base64.b64encode(buf.getvalue()).decode(), W, H
    except Exception:
        return None


def _vision_describe(b64: str, prompt: str = "Describe everything on this screen "
                     "in detail: apps, windows, buttons, visible text, game elements.") -> str:
    """Ekranı GÖRÜR. Önce yerel Ollama moondream (bedava), sonra OpenRouter vision."""
    # 1) Yerel moondream — bedava, offline
    try:
        import requests  # type: ignore
        base = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        vm = os.getenv("VISION_MODEL", "moondream")
        r = requests.post(f"{base}/api/generate",
                          json={"model": vm, "prompt": prompt,
                                "images": [b64], "stream": False}, timeout=120)
        resp = (r.json().get("response") or "").strip()
        if resp:
            return resp
    except Exception:
        pass
    # 2) OpenRouter vision (kredi varsa)
    try:
        import requests  # type: ignore
        key = os.getenv("OPENROUTER_API_KEY", "")
        if key:
            model = os.getenv("OPENROUTER_VISION_MODEL", "google/gemini-3.5-flash")
            r = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={"Authorization": f"Bearer {key}",
                         "Content-Type": "application/json"},
                json={"model": model, "temperature": 0.3, "messages": [
                    {"role": "user", "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url",
                         "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}]}]},
                timeout=60)
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"].strip()
    except Exception:
        pass
    return ""


# ── Ekranı gör ve anlat ───────────────────────────────────────────────── #
def gor_ekran(parameters: dict | None = None) -> str:
    istek = (parameters or {}).get("istek", "").strip() or "Ekranda ne var?"
    cap = _screen_jpeg_b64()
    if not cap:
        return "Ekran yakalanamadı."
    b64, _, _ = cap
    desc = _vision_describe(b64)
    if not desc:
        return "Ekranı göremedim (vision modeli yanıt vermedi)."
    # İngilizce açıklamayı Türkçe, isteğe göre cevaba çevir
    try:
        from .ai_skills import _ask_ai
        return "👁️ " + _ask_ai(
            "Bir ekran görüntüsünün açıklaması verilecek. Kullanıcının sorusuna "
            "bu açıklamaya dayanarak Türkçe, KISA cevap ver.",
            f"Ekran açıklaması: {desc}\n\nSoru: {istek}")
    except Exception:
        return "👁️ " + desc[:600]


def _extract_gor(msg: str) -> dict:
    t = re.sub(r"\b(ekrana?\s*bak|ekranı? gör|gör|bak|gemini gibi|görsel)\b",
               " ", msg, flags=re.I)
    return {"istek": re.sub(r"\s+", " ", t).strip(" :-?") or "Ekranda ne var?"}


# ── Ekrana bakıp YAP (vision → eylem) ─────────────────────────────────── #
_ACTION_SYS = (
    "Sen ekranı gören bir Windows/oyun otomasyon ajanısın. Ekran görüntüsüne bak. "
    "Kullanıcının isteğini yerine getirmek için yapılacak ADIMLARI üret. "
    "SADECE adımları yaz, her satıra bir adım, şu komutlardan:\n"
    "TIKLA:<ekranda görünen yazı/öğe>   (o yazıyı bulup tıklarım)\n"
    "YAZ:<metin>\n"
    "TUS:<tuş veya kombin, örn enter / w / ctrl+s>\n"
    "BEKLE:<saniye>\n"
    "CEVAP:<kullanıcıya kısa bilgi>\n"
    "En fazla 6 adım. Tıklanacak şey ekranda net bir YAZI ise TIKLA kullan. "
    "Emin değilsen CEVAP ile durumu açıkla. Başka hiçbir şey yazma."
)


def gor_yap(parameters: dict | None = None) -> str:
    istek = (parameters or {}).get("istek", "").strip()
    if not istek:
        return "Ne yapayım? Örn: 'ekrana bakıp Oyna'ya bas'"
    cap = _screen_jpeg_b64()
    if not cap:
        return "Ekran yakalanamadı."
    b64, _, _ = cap
    # 1) Ekranı GÖR (moondream) → tıklanabilir öğeleri/yazıları öğren
    desc = _vision_describe(
        b64, "List all visible buttons, menu items, and text labels on this screen. "
             "Also describe what app/game it is.")
    if not desc:
        return "Ekranı göremedim (vision yanıt vermedi)."
    # 2) Açıklama + istek → adım planı (metin LLM)
    try:
        from .ai_skills import _ask_ai
        plan = _ask_ai(_ACTION_SYS,
                       f"EKRANDA GÖRÜNENLER: {desc}\n\nKULLANICI İSTEĞİ: {istek}")
    except Exception as exc:
        return f"Plan üretilemedi: {exc}"

    adimlar = [l.strip() for l in plan.splitlines() if l.strip()]
    if not adimlar:
        return "Ne yapacağımı çıkaramadım."

    def _run():
        try:
            import pyautogui as g  # type: ignore
            from .smart_click import find_text_on_screen
        except Exception:
            return
        yapilan = []
        for a in adimlar:
            try:
                if a.upper().startswith("TIKLA:"):
                    hedef = a.split(":", 1)[1].strip()
                    pos = find_text_on_screen(hedef)
                    if pos:
                        g.click(*pos); yapilan.append(f"tıkla:{hedef[:15]}")
                    else:
                        yapilan.append(f"bulunamadı:{hedef[:15]}")
                elif a.upper().startswith("YAZ:"):
                    metin = a.split(":", 1)[1].strip()
                    try:
                        import pyperclip; pyperclip.copy(metin)
                        g.hotkey("ctrl", "v")
                    except Exception:
                        g.write(metin, interval=0.02)
                    yapilan.append("yaz")
                elif a.upper().startswith("TUS:"):
                    keys = re.split(r"[+\s]+", a.split(":", 1)[1].strip())
                    g.hotkey(*keys); yapilan.append("tuş")
                elif a.upper().startswith("BEKLE:"):
                    sn = re.search(r"\d+", a)
                    time.sleep(min(int(sn.group()) if sn else 1, 10))
                elif a.upper().startswith("CEVAP:"):
                    _push("👁️ " + a.split(":", 1)[1].strip())
                time.sleep(0.4)
            except Exception:
                continue
        _push("👁️ Yapıldı: " + (", ".join(yapilan) if yapilan else "—"))

    threading.Thread(target=_run, daemon=True).start()
    return "👁️ Ekrana baktım, planı uyguluyorum:\n" + "\n".join(adimlar[:6])


def _extract_gor_yap(msg: str) -> dict:
    t = re.sub(r"\b(ekrana?\s*bak(ıp|arak)?|ekranı? gör(üp)?|gör(üp)?\s*yap|"
               r"gemini gibi|bakıp)\b", " ", msg, flags=re.I)
    return {"istek": re.sub(r"\s+", " ", t).strip(" :-")}


# ── Vision ile OYNA (döngü: gör → karar → uygula → tekrar) ────────────── #
_OYNA = {"on": False}

_OYNA_SYS = (
    "Sen ekranı gören bir oyun ajanısın. Ekran açıklaması + hedef verilecek. "
    "Hedefe doğru SADECE BİR sonraki adımı ver, şu formatta:\n"
    "TUS:<tuş>  | TIKLA:<görünen yazı>  | BEKLE:<sn>  | BITTI\n"
    "Örn: ana menüdeyse TIKLA:Play; oyundaysa TUS:w. Tek satır, başka şey yazma."
)


def gor_oyna(parameters: dict | None = None) -> str:
    p = parameters or {}
    if p.get("action") == "stop":
        _OYNA["on"] = False
        return "🎮 Vision oyun durduruldu."
    hedef = (p.get("hedef") or "").strip()
    if not hedef:
        return "Hedef ver. Örn: 'oyunu oyna: ana menüden oyuna gir'"
    if _OYNA.get("on"):
        return "Zaten oynuyorum. 'oyunu durdur' de."
    _OYNA["on"] = True
    adim = int(p.get("adim", 8))

    def _run():
        try:
            import pyautogui as g  # type: ignore
            from .smart_click import find_text_on_screen
            from .ai_skills import _ask_ai
        except Exception:
            _OYNA["on"] = False
            return
        for i in range(min(adim, 20)):
            if not _OYNA.get("on"):
                break
            cap = _screen_jpeg_b64(scale=0.6, quality=55)
            if not cap:
                break
            desc = _vision_describe(cap[0],
                                    "Briefly: what is shown? menu/game? what buttons/state?")
            try:
                karar = _ask_ai(_OYNA_SYS,
                                f"EKRAN: {desc}\nHEDEF: {hedef}\nSıradaki tek adım?").strip()
            except Exception:
                break
            k = karar.splitlines()[0].strip()
            up = k.upper()
            try:
                if up.startswith("BITTI"):
                    _push("🎮 Hedefe ulaşıldı."); break
                if up.startswith("TIKLA:"):
                    pos = find_text_on_screen(k.split(":", 1)[1].strip())
                    if pos:
                        g.click(*pos)
                elif up.startswith("TUS:"):
                    keys = re.split(r"[+\s]+", k.split(":", 1)[1].strip())
                    g.hotkey(*keys)
                elif up.startswith("BEKLE:"):
                    s = re.search(r"\d+", k); time.sleep(min(int(s.group()) if s else 1, 8))
            except Exception:
                pass
            time.sleep(1.5)
        _OYNA["on"] = False
        _push("🎮 Vision oyun bitti.")

    threading.Thread(target=_run, daemon=True).start()
    return (f"🎮 Ekrana bakarak oynuyorum (hedef: {hedef}). Her adımda görüp "
            f"karar veriyorum. Durdur: 'oyunu durdur'. (Yerel vision yavaş olabilir.)")


def _extract_oyna(msg: str) -> dict:
    if any(w in msg.lower() for w in ("durdur", "dur", "bırak", "kapat")):
        return {"action": "stop"}
    m = re.search(r"(?:oyunu? oyna|oyna|vision oyna)\s*[:\-]?\s*(.+)", msg, re.I)
    return {"hedef": m.group(1).strip() if m else "oyunu ilerlet"}
