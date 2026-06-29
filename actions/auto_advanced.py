"""
HULLAR gelişmiş otomasyon skilleri (mouse / klavye / makro).

  • tus_tut          : bir tuşu N saniye basılı tut ("W'ye 5 sn bas")
  • tus_spam         : bir tuşa N kez bas ("Space'e 50 kez bas")
  • bekle_tikla      : ekranda yazı görününce otomatik tıkla (OCR, bekler)
  • renge_tikla      : ekranda belirli renkteki ilk noktaya tıkla
  • snippet_yaz/kaydet : hazır metin kaydet ve yaz ("imza yaz", "iban yaz")
  • coklu_makro      : "tıkla 500 300; yaz merhaba; enter" dizisini çalıştır
  • pencere_diz      : pencereyi sol/sağ yarıya yapıştır / tam ekran (Win+ok)
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path

_SNIP = Path(__file__).parent.parent / "data" / "snippets.json"


def _gui():
    import pyautogui  # type: ignore
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.02
    return pyautogui


def _type(text: str):
    """Türkçe-güvenli yazma (pano + ctrl+v)."""
    try:
        import pyperclip  # type: ignore
        pyperclip.copy(text)
    except Exception:
        import subprocess
        subprocess.run(f'powershell -c "Set-Clipboard -Value \'{text}\'"',
                       shell=True, stdout=subprocess.DEVNULL)
    time.sleep(0.15)
    _gui().hotkey("ctrl", "v")


# ── Tuşu basılı tut ───────────────────────────────────────────────────── #
def tus_tut(parameters: dict | None = None) -> str:
    p = parameters or {}
    key = (p.get("key") or "").lower().strip()
    sec = float(p.get("seconds", 3))
    if not key:
        return "Hangi tuşu basılı tutayım? (örn: \"W'ye 5 sn bas\")"
    sec = max(0.1, min(sec, 60))
    try:
        g = _gui()
        g.keyDown(key)
        time.sleep(sec)
        g.keyUp(key)
        return f"⌨️ '{key}' tuşu {sec:g} sn basılı tutuldu."
    except Exception as exc:
        return f"Tuş hatası: {exc}"


def _extract_tus_tut(msg: str) -> dict:
    low = msg.lower()
    sec = float(m.group(1)) if (m := re.search(r"(\d+(?:[.,]\d+)?)\s*(?:saniye|sn|s)\b", low)) else 3
    k = re.search(r"\b([a-z0-9])\s*(?:'?[ye]?\s*)?(?:tuşunu?|harfini?)?\s*(?:bas|tut)", low)
    if not k:
        k = re.search(r"\b([a-z0-9])\b", low)
    return {"key": k.group(1) if k else "", "seconds": sec}


# ── MC: Köprü kur (sneak + geri + sağ tık) ────────────────────────────── #
_BRIDGE = {"on": False}


def koprusu(parameters: dict | None = None) -> str:
    p = parameters or {}
    if p.get("action") == "stop":
        _BRIDGE["on"] = False
        return "🌉 Köprü durduruldu."
    sec = float(p.get("seconds", 20))
    sec = max(2, min(sec, 600))
    if _BRIDGE.get("on"):
        return "Zaten köprü kuruyorum. 'köprüyü durdur' de."
    _BRIDGE["on"] = True

    def _run():
        g = _gui()
        try:
            g.keyDown("shift")   # sneak (düşmeden)
            g.keyDown("s")       # geri yürü
            t0 = time.time()
            while _BRIDGE.get("on") and (time.time() - t0) < sec:
                g.click(button="right")   # blok koy
                time.sleep(0.28)
        finally:
            try:
                g.keyUp("s"); g.keyUp("shift")
            except Exception:
                pass
            _BRIDGE["on"] = False
            try:
                from .notify import push
                push("🌉 Köprü kurma bitti.")
            except Exception:
                pass

    import threading
    threading.Thread(target=_run, daemon=True).start()
    return (f"🌉 {sec:g} sn köprü kuruyorum (sneak + geri + blok). "
            f"Aşağı bak, elinde blok olsun. Durdur: 'köprüyü durdur'.")


def _extract_koprusu(msg: str) -> dict:
    low = msg.lower()
    if any(w in low for w in ("durdur", "dur", "bırak", "stop")):
        return {"action": "stop"}
    m = re.search(r"(\d+)\s*(saniye|sn|dakika|dk)", low)
    sec = 20
    if m:
        sec = int(m.group(1)) * (60 if "d" in m.group(2) else 1)
    return {"seconds": sec}


# ── MC: Envanteri at (hotbar eşyalarını düşür) ────────────────────────── #
def envanter_at(parameters: dict | None = None) -> str:
    try:
        g = _gui()
        for slot in "123456789":
            g.press(slot)               # slotu seç
            time.sleep(0.1)
            g.hotkey("ctrl", "q")       # tüm yığını düşür
            time.sleep(0.15)
        return "🗑️ Hotbar'daki eşyalar atıldı (oyun önde olmalıydı)."
    except Exception as exc:
        return f"Atılamadı: {exc}"


# ── Minecraft chat/komut: T'ye bas → yaz → Enter ──────────────────────── #
def mc_komut(parameters: dict | None = None) -> str:
    cmd = (parameters or {}).get("komut", "").strip()
    if not cmd:
        return "Ne yazayım? (örn: 'mc komut /gamemode creative')"
    try:
        g = _gui()
        g.press("t")          # MC sohbeti aç
        time.sleep(0.35)
        _type(cmd)            # komutu/mesajı yaz (pano + ctrl+v)
        time.sleep(0.15)
        g.press("enter")      # gönder
        return f"⌨️ Minecraft'a gönderildi: {cmd}"
    except Exception as exc:
        return f"MC komut hatası: {exc}"


def _extract_mc_komut(msg: str) -> dict:
    m = (re.search(r"(?:mc|minecraft)\s*(?:komut|chat|yaz|mesaj|chate)\s*[:\-]?\s*(.+)", msg, re.I)
         or re.search(r"\bt'?ye\s*bas(?:ıp)?\s*(?:yaz)?\s*[:\-]?\s*(.+)", msg, re.I)
         or re.search(r"\bsohbete?\s*yaz\s*[:\-]?\s*(.+)", msg, re.I))
    return {"komut": m.group(1).strip() if m else ""}


# ── Fare tuşunu basılı tut (Minecraft: blok kır / koy) ────────────────── #
_HOLD = {"on": False}


def blok_kir(parameters: dict | None = None) -> str:
    """Sol/sağ fare tuşunu N saniye basılı tutar.
    'kır' → sol (madencilik/vurma), 'koy/yerleştir' → sağ (blok koyma)."""
    p = parameters or {}
    if p.get("action") == "stop":
        _HOLD["on"] = False
        return "🛑 Bırakıldı."
    sec = float(p.get("seconds", 10))
    button = p.get("button", "left")
    sec = max(0.5, min(sec, 1800))   # en çok 30 dk
    if _HOLD.get("on"):
        return "Zaten basılı tutuyorum. Durdurmak için 'kırmayı durdur'."

    def _hold():
        g = _gui()
        _HOLD["on"] = True
        try:
            g.mouseDown(button=button)
            t0 = time.time()
            while _HOLD.get("on") and (time.time() - t0) < sec:
                time.sleep(0.1)
        finally:
            try:
                g.mouseUp(button=button)
            except Exception:
                pass
            tamam = (time.time() - t0) >= sec
            _HOLD["on"] = False
            try:
                from .notify import push
                push("✅ Blok kırma bitti (süre doldu)." if tamam
                     else "🛑 Blok kırma durduruldu.")
            except Exception:
                pass

    import threading
    threading.Thread(target=_hold, daemon=True).start()
    ne = "sol (kır/vur)" if button == "left" else "sağ (koy/kullan)"
    dk = sec / 60
    sure = f"{dk:g} dk" if sec >= 60 else f"{sec:g} sn"
    return (f"⛏️ {sure} boyunca {ne} tuşu basılı tutuluyor. "
            f"Erken durdur: 'kırmayı durdur' (oyun penceresi önde olmalı).")


def _extract_blok_kir(parameters_msg: str) -> dict:
    low = parameters_msg.lower()
    if any(w in low for w in ("durdur", "bırak", "birak", "dur", "stop")):
        return {"action": "stop"}
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
        total = int(n.group(1)) if n else 10
    button = "right" if any(w in low for w in ("koy", "yerleştir", "yerlestir", "sağ tık", "kullan")) else "left"
    return {"seconds": total, "button": button}


# ── Tuş spam ──────────────────────────────────────────────────────────── #
def tus_spam(parameters: dict | None = None) -> str:
    p = parameters or {}
    key = (p.get("key") or "").lower().strip()
    n = int(p.get("count", 10))
    if not key:
        return "Hangi tuşa basayım? (örn: \"Space'e 50 kez bas\")"
    n = max(1, min(n, 1000))
    try:
        _gui().press(key, presses=n, interval=0.03)
        return f"⌨️ '{key}' tuşuna {n} kez basıldı."
    except Exception as exc:
        return f"Tuş hatası: {exc}"


_KEY_WORDS = {"space": "space", "boşluk": "space", "bosluk": "space",
              "enter": "enter", "tab": "tab", "esc": "esc", "escape": "esc",
              "yukarı": "up", "aşağı": "down", "sol": "left", "sağ": "right"}


def _extract_tus_spam(msg: str) -> dict:
    low = msg.lower()
    n = int(m.group(1)) if (m := re.search(r"(\d+)\s*(?:kez|defa|kere)", low)) else 10
    key = ""
    for w, k in _KEY_WORDS.items():
        if w in low:
            key = k
            break
    if not key:
        kk = re.search(r"\b([a-z0-9])\s*(?:'?[ye])?\s*(?:tuşuna|harfine)?\s*\d*\s*(?:kez|defa)?\s*bas", low)
        key = kk.group(1) if kk else ""
    return {"key": key, "count": n}


# ── Bekle ve tıkla (OCR) ──────────────────────────────────────────────── #
def bekle_tikla(parameters: dict | None = None) -> str:
    p = parameters or {}
    target = (p.get("target") or "").strip()
    timeout = int(p.get("timeout", 30))
    if not target:
        return "Neyi bekleyip tıklayayım? (örn: 'ekranda Kabul Et çıkınca tıkla')"
    try:
        from .smart_click import find_text_on_screen
        g = _gui()
        t0 = time.time()
        while time.time() - t0 < timeout:
            pos = find_text_on_screen(target)
            if pos:
                g.click(*pos)
                return f"🎯 '{target}' belirdi ({pos[0]},{pos[1]}) ve tıklandı."
            time.sleep(1.2)
        return f"⏱️ '{target}' {timeout} sn içinde görünmedi."
    except Exception as exc:
        return f"Bekle-tıkla hatası: {exc}"


def _extract_bekle_tikla(msg: str) -> dict:
    t = re.sub(r"\b(ekranda|ekrandaki|şu|çıkınca|cikinca|görününce|gorununce|belirince|"
               r"olunca|bekle|tıkla|tikla|bas|seç)\b", " ", msg, flags=re.I)
    t = re.sub(r"'(?:y?[ae]|n[ae])\b", " ", t)
    to = int(m.group(1)) if (m := re.search(r"(\d+)\s*(?:saniye|sn)", msg, re.I)) else 30
    t = re.sub(r"\b\d+\s*(?:saniye|sn|s)\b", " ", t).strip(" .,;:'\"-")
    return {"target": re.sub(r"\s+", " ", t).strip(), "timeout": to}


# ── Renge tıkla ───────────────────────────────────────────────────────── #
_COLORS = {
    "kırmızı": (220, 30, 30), "kirmizi": (220, 30, 30), "red": (220, 30, 30),
    "yeşil": (30, 180, 30), "yesil": (30, 180, 30), "green": (30, 180, 30),
    "mavi": (30, 80, 220), "blue": (30, 80, 220),
    "sarı": (235, 220, 30), "sari": (235, 220, 30), "yellow": (235, 220, 30),
    "turuncu": (240, 140, 20), "orange": (240, 140, 20),
    "beyaz": (245, 245, 245), "white": (245, 245, 245),
    "siyah": (15, 15, 15), "black": (15, 15, 15),
    "mor": (150, 40, 200), "pembe": (240, 90, 180), "pink": (240, 90, 180),
}


def renge_tikla(parameters: dict | None = None) -> str:
    p = parameters or {}
    rgb = p.get("rgb")
    name = p.get("name", "renk")
    if not rgb:
        return "Hangi renge tıklayayım? (örn: 'yeşile tıkla')"
    try:
        import numpy as np  # type: ignore
        import mss          # type: ignore
        g = _gui()
        with mss.mss() as sct:
            mon = sct.monitors[1]
            img = np.array(sct.grab(mon))[:, :, :3][:, :, ::-1]  # RGB
        target = np.array(rgb)
        dist = np.sqrt(((img.astype(int) - target) ** 2).sum(axis=2))
        ys, xs = np.where(dist < 40)   # tolerans
        if len(xs) == 0:
            return f"'{name}' rengi ekranda bulunamadı."
        # En yoğun kümenin ortası yerine ilk eşleşmenin medyanı
        cx = int(np.median(xs)) + mon["left"]
        cy = int(np.median(ys)) + mon["top"]
        g.click(cx, cy)
        return f"🎯 '{name}' rengine tıklandı ({cx},{cy})."
    except Exception as exc:
        return f"Renge tıklama hatası: {exc}"


def _extract_renge_tikla(msg: str) -> dict:
    low = msg.lower()
    for w, rgb in _COLORS.items():
        if w in low:
            return {"rgb": rgb, "name": w}
    return {}


# ── Snippet (hazır metin) ─────────────────────────────────────────────── #
def _load_snip() -> dict:
    if _SNIP.exists():
        try:
            return json.loads(_SNIP.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save_snip(d: dict):
    _SNIP.parent.mkdir(parents=True, exist_ok=True)
    _SNIP.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")


def snippet_kaydet(parameters: dict | None = None) -> str:
    p = parameters or {}
    ad = (p.get("ad") or "").strip().lower()
    metin = (p.get("metin") or "").strip()
    if not ad or not metin:
        return "Kullanım: 'snippet kaydet imza: Saygılarımla, [adın]'"
    d = _load_snip()
    d[ad] = metin
    _save_snip(d)
    return f"💾 Snippet '{ad}' kaydedildi. Yazmak için: '{ad} yaz'"


def snippet_yaz(parameters: dict | None = None) -> str:
    ad = (parameters or {}).get("ad", "").strip().lower()
    d = _load_snip()
    if ad not in d:
        liste = ", ".join(d.keys()) or "(boş)"
        return f"'{ad}' snippet'i yok. Kayıtlılar: {liste}"
    try:
        _type(d[ad])
        return f"⌨️ '{ad}' yazıldı."
    except Exception as exc:
        return f"Yazma hatası: {exc}"


def snippet_liste(parameters: dict | None = None) -> str:
    d = _load_snip()
    if not d:
        return "Kayıtlı snippet yok. Ekle: 'snippet kaydet imza: ...'"
    return "📋 Snippet'ler:\n" + "\n".join(f"• {k}" for k in d)


def _extract_snip_kaydet(msg: str) -> dict:
    m = re.search(r"snippet\s*(?:kaydet|ekle)\s+([\w\-]+)\s*[:\-]\s*(.+)", msg, re.I)
    return {"ad": m.group(1), "metin": m.group(2)} if m else {}


def _extract_snip_yaz(msg: str) -> dict:
    m = re.search(r"\b([\w\-]+)\s+(?:snippet\s+)?yaz\b", msg, re.I) or \
        re.search(r"snippet\s+yaz\s+([\w\-]+)", msg, re.I)
    return {"ad": m.group(1)} if m else {}


# ── Pencere diz (snap) ────────────────────────────────────────────────── #
def pencere_diz(parameters: dict | None = None) -> str:
    yon = (parameters or {}).get("yon", "sol")
    g = _gui()
    try:
        if yon == "sol":
            g.hotkey("win", "left")
        elif yon == "sağ":
            g.hotkey("win", "right")
        elif yon == "tam":
            g.hotkey("win", "up")
        elif yon == "küçült":
            g.hotkey("win", "down")
        return f"🪟 Pencere {yon}a yerleştirildi."
    except Exception as exc:
        return f"Pencere dizilemedi: {exc}"


def _extract_pencere_diz(msg: str) -> dict:
    low = msg.lower()
    if "sağ" in low or "sag" in low:
        return {"yon": "sağ"}
    if "tam" in low or "büyüt" in low or "maximize" in low:
        return {"yon": "tam"}
    if "küçült" in low or "kucult" in low or "minimize" in low:
        return {"yon": "küçült"}
    return {"yon": "sol"}


# ── Çoklu makro (doğal dil) ───────────────────────────────────────────── #
def coklu_makro(parameters: dict | None = None) -> str:
    p = parameters or {}
    steps_raw = p.get("steps", "")
    tekrar = int(p.get("tekrar", 1))
    if not steps_raw:
        return ("Örnek (telefondan, koordinatsız):\n"
                "makro 5 kez: tıkla Giriş Yap; yaz selam; enter")
    g = _gui()
    done = []
    tekrar = max(1, min(tekrar, 500))
    for _ in range(tekrar):
      for raw in re.split(r"[;\n]+", steps_raw):
        s = raw.strip()
        if not s:
            continue
        low = s.lower()
        try:
            if m := re.match(r"(?:çift\s*tıkla|cift tikla)\s+(\d+)\s+(\d+)", low):
                g.click(int(m.group(1)), int(m.group(2)), clicks=2); done.append("çift tık")
            elif m := re.match(r"(?:sağ\s*tık|sag tik)\s+(\d+)\s+(\d+)", low):
                g.click(int(m.group(1)), int(m.group(2)), button="right"); done.append("sağ tık")
            elif m := re.match(r"(?:tıkla|tikla|click)\s+(\d+)\s+(\d+)", low):
                g.click(int(m.group(1)), int(m.group(2))); done.append("tıkla")
            elif m := re.match(r"(?:tıkla|tikla|bas|click)\s+(.+)", s, re.I):
                # Koordinat değil → ekrandaki YAZIYA tıkla (telefon dostu)
                from .smart_click import find_text_on_screen
                pos = find_text_on_screen(m.group(1).strip())
                if pos:
                    g.click(*pos); done.append(f"tıkla:{m.group(1).strip()[:15]}")
                else:
                    done.append(f"bulunamadı:{m.group(1).strip()[:15]}")
            elif m := re.match(r"(?:yaz|type)\s+(.+)", s, re.I):
                _type(m.group(1).strip()); done.append("yaz")
            elif m := re.match(r"(?:bekle|wait)\s+(\d+(?:[.,]\d+)?)", low):
                time.sleep(min(float(m.group(1).replace(",", ".")), 30)); done.append("bekle")
            elif m := re.match(r"(?:tuş|tus|hotkey)\s+(.+)", low):
                keys = re.split(r"[+\s]+", m.group(1).strip())
                g.hotkey(*keys); done.append("tuş")
            elif low in ("enter", "tab", "esc", "escape", "space", "boşluk"):
                g.press({"boşluk": "space", "escape": "esc"}.get(low, low)); done.append(low)
            elif m := re.match(r"(?:kaydır|scroll)\s+(yukarı|aşağı|up|down)", low):
                amt = 500 if m.group(1) in ("aşağı", "down") else -500
                g.scroll(-amt); done.append("kaydır")
            time.sleep(0.25)
        except Exception:
            continue
    return f"🤖 Makro çalıştı ({len(done)} adım: {', '.join(done)})."


def _extract_coklu_makro(msg: str) -> dict:
    tekrar = 1
    tk = re.search(r"(\d+)\s*(?:kez|defa|kere)", msg, re.I)
    if tk:
        tekrar = int(tk.group(1))
    m = re.search(r"makro\b[^:]*[:\-]\s*(.+)", msg, re.I | re.S)
    if not m:
        return {}
    return {"steps": m.group(1).strip(), "tekrar": tekrar}
