"""
Minecraft OneBlock yardımcı botu.

Ekranın üst-ortasındaki blok adı tooltip'ini (ör. "Grass Block") OCR ile okur:
  • Sandık (chest) → sağ tık ile açar, içindekileri almaya çalışır, sonra kırar
  • Normal blok → blok türüne göre hotbar'dan doğru aleti seçer ve kırar

HOTBAR DÜZENİ (senin ayarlaman gerek):
  Slot 1 = Kazma (taş/cevher)   Slot 2 = Kürek (toprak/kum)   Slot 3 = Balta (odun)

UYARI: OneBlock genelde SUNUCUDA oynanır; sunucularda bot kullanmak çoğu
yerde yasaktır ve BAN sebebidir. Tek-oyunculu/kendi dünyanda sorun yok.
"""

from __future__ import annotations

import re
import threading
import time

_STATE = {"on": False}


def _push(text: str):
    try:
        from .notify import push
        push(text)
    except Exception:
        pass

# blok adı anahtar kelimesi → hotbar slot numarası (tuş)
# Sıra önemli: önce kürek (toprak/kum), sonra BALTA (odun) — çünkü "stairs/slab"
# hem taşta hem odunda var; odun türü kelimesi (oak/log...) varsa baltaya gitsin.
_TOOL_MAP = [
    # ── Kürek (slot 2): toprak/kum/kar ───────────────────────────────── #
    (["dirt", "grass", "sand", "gravel", "clay", "soul sand", "soul soil",
      "mud", "snow", "podzol", "mycelium", "coarse", "rooted", "farmland",
      "dirt path", "concrete powder", "toprak", "kum", "çim", "cim", "çamur",
      "kar", "çakıl", "cakil"], "2"),
    # ── Balta (slot 3): tüm ağaç/odun türleri + odun eşyaları ────────── #
    (["log", "wood", "plank", "oak", "birch", "spruce", "jungle", "acacia",
      "dark oak", "mangrove", "cherry", "bamboo", "crimson", "warped",
      "stem", "hyphae", "stripped", "fence", "door", "trapdoor", "sign",
      "barrel", "bookshelf", "crafting table", "ladder", "chest", "campfire",
      "mushroom", "melon", "pumpkin", "beehive", "lectern", "loom", "cartography",
      "odun", "kütük", "kutuk", "tahta", "ağaç", "agac", "kapı", "mantar",
      "bal kabağı", "kavun", "raf"], "3"),
    # ── Kazma (slot 1): taş/cevher/metal/mineral (en geniş, en sonda) ── #
    (["stone", "cobble", "ore", "deepslate", "andesite", "diorite", "granite",
      "obsidian", "netherrack", "blackstone", "tuff", "calcite", "basalt",
      "brick", "terracotta", "prismarine", "quartz", "sandstone", "amethyst",
      "copper", "iron", "gold", "coal", "diamond", "emerald", "redstone",
      "lapis", "netherite", "ancient debris", "furnace", "anvil", "smooth",
      "polished", "purpur", "magma", "end stone", "glazed", "concrete",
      "taş", "tas", "cevher", "kaya", "demir", "altın", "altin", "kömür",
      "komur", "elmas", "fırın", "firin"], "1"),
]


def _block_name() -> str:
    """Ekranın üst-ortasındaki blok adı tooltip'ini OCR ile okur."""
    try:
        import mss          # type: ignore
        import pytesseract  # type: ignore
        from PIL import Image  # type: ignore
        from .smart_click import _ensure_tesseract
        _ensure_tesseract()
        with mss.mss() as sct:
            mon = sct.monitors[1]
            w, h = mon["width"], mon["height"]
            region = {"left": mon["left"] + int(w * 0.28), "top": mon["top"],
                      "width": int(w * 0.44), "height": int(h * 0.11)}
            shot = sct.grab(region)
            img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
        # Küçük tooltip yazısını OCR için netleştir: gri + kontrast + 3x büyüt
        from PIL import ImageOps  # type: ignore
        img = ImageOps.autocontrast(img.convert("L")).resize(
            (img.width * 3, img.height * 3))
        try:
            txt = pytesseract.image_to_string(img, lang="eng", config="--psm 6")
        except Exception:
            txt = pytesseract.image_to_string(img)
        return txt.lower().strip()
    except Exception:
        return ""


def _tool_slot(name: str) -> str | None:
    for kws, slot in _TOOL_MAP:
        if any(k in name for k in kws):
            return slot
    return None


# Menü/duraklatma KESİN işaretleri (yanlış pozitif olmasın diye spesifik)
_MENU_WORDS = ("back to game", "oyuna dön", "oyuna don", "save and quit",
               "save and", "game menu", "crafting", "envanter")


def _menu_acik() -> bool:
    """Ekranın ortasında menü/duraklatma yazısı var mı? (Esc, envanter vb.)"""
    try:
        import mss          # type: ignore
        import pytesseract  # type: ignore
        from PIL import Image, ImageOps  # type: ignore
        from .smart_click import _ensure_tesseract
        _ensure_tesseract()
        with mss.mss() as sct:
            mon = sct.monitors[1]
            w, h = mon["width"], mon["height"]
            # Esc menüsünün "Back to Game" butonu üst-orta bölgede olur
            region = {"left": mon["left"] + int(w * 0.33), "top": mon["top"] + int(h * 0.28),
                      "width": int(w * 0.34), "height": int(h * 0.30)}
            shot = sct.grab(region)
            img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
        img = ImageOps.autocontrast(img.convert("L"))
        try:
            txt = pytesseract.image_to_string(img, lang="eng").lower()
        except Exception:
            txt = pytesseract.image_to_string(img).lower()
        return any(k in txt for k in _MENU_WORDS)
    except Exception:
        return False


def _loot_chest(g):
    """Açık sandıktan eşyaları almaya çalışır (shift+tık taraması — best-effort)."""
    try:
        sw, sh = g.size()
        cx, cy = sw // 2, sh // 2
        # GUI scale ~3 varsayımı: tek sandık 9 sütun x 3 sıra, slot ~53px
        slot = int(sh * 0.049) or 50
        x0 = cx - slot * 4
        y0 = cy - int(slot * 1.7)
        g.keyDown("shift")
        for r in range(3):
            for c in range(9):
                g.click(x0 + c * slot, y0 + r * slot)
                time.sleep(0.03)
        g.keyUp("shift")
    except Exception:
        try:
            g.keyUp("shift")
        except Exception:
            pass


def _loop(seconds: float):
    try:
        import pyautogui as g  # type: ignore
        g.PAUSE = 0.01
    except Exception:
        _STATE["on"] = False
        return
    _STATE["on"] = True
    t0 = time.time()
    last_menu = 0.0
    last_tool = 0.0
    son_slot = None
    holding = False
    paused = False
    try:
        g.mouseDown()          # SÜREKLİ kırmaya başla (OneBlock blok yeniler)
        holding = True
        while _STATE.get("on") and (time.time() - t0) < seconds:
            now = time.time()

            # 1) Menü/Esc kontrolü — seyrek (her 2 sn), sağlam algılama
            if now - last_menu >= 2.0:
                last_menu = now
                if _menu_acik():
                    if holding:
                        g.mouseUp(); holding = False
                    if not paused:
                        paused = True
                        _push("⏸️ OneBlock duraklatıldı (menü/Esc açık).")
                    time.sleep(0.3)
                    continue
                if paused:
                    paused = False
                    _push("▶️ OneBlock devam ediyor.")
                    g.mouseDown(); holding = True

            if paused:
                time.sleep(0.3)
                continue
            if not holding:
                g.mouseDown(); holding = True

            # 2) Alet seçimi / sandık — seyrek (her 2.5 sn), kırma kesilmez
            if now - last_tool >= 2.5:
                last_tool = now
                name = _block_name()
                is_chest = any(k in name for k in
                               ("chest", "sandık", "sandik", "shulker", "barrel"))
                if is_chest:
                    g.mouseUp(); holding = False
                    g.click(button="right")    # sandığı aç
                    time.sleep(0.7)
                    _loot_chest(g)
                    time.sleep(0.2)
                    g.press("esc")
                    time.sleep(0.3)
                    g.press("3")               # balta
                    son_slot = "3"
                    g.mouseDown(); holding = True
                elif name:
                    slot = _tool_slot(name)
                    if slot and slot != son_slot:
                        g.press(slot)
                        son_slot = slot

            time.sleep(0.2)   # kırma sürerken nefes
    except Exception:
        pass
    finally:
        if holding:
            try:
                g.mouseUp()
            except Exception:
                pass
        # Bitiş sebebi: süre dolduysa "tamamlandı", erken bittiyse "durduruldu"
        sure_doldu = (time.time() - t0) >= seconds
        _STATE["on"] = False
        if sure_doldu:
            _push("✅ OneBlock botu bitti (süre doldu).")
        else:
            _push("🛑 OneBlock botu durduruldu.")


def oneblock(parameters: dict | None = None) -> str:
    p = parameters or {}
    if p.get("action") == "stop":
        _STATE["on"] = False
        return "🛑 OneBlock botu durduruldu."
    if _STATE.get("on"):
        return "OneBlock botu zaten çalışıyor. Durdurmak için 'oneblock durdur'."
    sec = float(p.get("seconds", 300))
    sec = max(5, min(sec, 3600))
    threading.Thread(target=_loop, args=(sec,), daemon=True).start()
    dk = sec / 60
    return (f"⛏️ OneBlock botu açık (~{dk:g} dk). Blok adına göre alet seçip kırar, "
            f"sandık görünce açıp almaya çalışır.\n"
            f"⚠️ Oyun penceresi ÖNDE olmalı. Hotbar: 1=kazma 2=kürek 3=balta.\n"
            f"Durdur: 'oneblock durdur'.")


# ── MC: Otomatik balık tut (zamanlı) ──────────────────────────────────── #
_FISH = {"on": False}


def balik_tut(parameters: dict | None = None) -> str:
    p = parameters or {}
    if p.get("action") == "stop":
        _FISH["on"] = False
        return "🎣 Balık botu durduruldu."
    sec = float(p.get("seconds", 300))
    sec = max(20, min(sec, 7200))
    if _FISH.get("on"):
        return "Balık botu zaten çalışıyor. 'balık durdur' de."
    _FISH["on"] = True

    def _run():
        try:
            import pyautogui as g  # type: ignore
        except Exception:
            _FISH["on"] = False
            return
        t0 = time.time()
        n = 0
        while _FISH.get("on") and (time.time() - t0) < sec:
            g.click(button="right")           # oltayı at
            # ısırık genelde 10-25 sn; ortalama bekle sonra çek
            bekle = 22
            slept = 0
            while _FISH.get("on") and slept < bekle:
                time.sleep(0.5); slept += 0.5
            if not _FISH.get("on"):
                break
            g.click(button="right")           # çek
            n += 1
            time.sleep(1.5)                   # tekrar atmadan önce
        _FISH["on"] = False
        _push(f"🎣 Balık botu bitti (~{n} kez çekildi).")

    threading.Thread(target=_run, daemon=True).start()
    dk = sec / 60
    return (f"🎣 Balık botu açık (~{dk:g} dk). Oltayı atıp ~22 sn'de bir çeker.\n"
            f"⚠️ Elinde olta olmalı, oyun önde olmalı. Durdur: 'balık durdur'.")


def _extract_balik(msg: str) -> dict:
    low = msg.lower()
    if any(w in low for w in ("durdur", "dur", "kapat", "bırak", "stop")):
        return {"action": "stop"}
    total = 0
    h = re.search(r"(\d+)\s*saat", low)
    m = re.search(r"(\d+)\s*(dakika|dk)", low)
    if h:
        total += int(h.group(1)) * 3600
    if m:
        total += int(m.group(1)) * 60
    return {"seconds": total or 300}


# ── MC: Auto-eat (zamanlı yeme) ───────────────────────────────────────── #
_EAT = {"on": False}


def auto_eat(parameters: dict | None = None) -> str:
    p = parameters or {}
    if p.get("action") == "stop":
        _EAT["on"] = False
        return "🍖 Auto-eat durduruldu."
    sec = float(p.get("seconds", 600))
    sec = max(30, min(sec, 7200))
    aralik = int(p.get("aralik", 40))   # kaç sn'de bir yesin
    if _EAT.get("on"):
        return "Auto-eat zaten açık. 'yemeyi durdur' de."
    _EAT["on"] = True

    def _run():
        try:
            import pyautogui as g  # type: ignore
        except Exception:
            _EAT["on"] = False
            return
        t0 = time.time()
        while _EAT.get("on") and (time.time() - t0) < sec:
            slept = 0
            while _EAT.get("on") and slept < aralik:
                time.sleep(0.5); slept += 0.5
            if not _EAT.get("on"):
                break
            g.mouseDown(button="right")   # yemeği tut (yemek için)
            time.sleep(2.6)
            g.mouseUp(button="right")
        _EAT["on"] = False
        _push("🍖 Auto-eat bitti.")

    threading.Thread(target=_run, daemon=True).start()
    return (f"🍖 Auto-eat açık — her {aralik} sn'de bir yemek yer.\n"
            f"⚠️ Elinde YEMEK olmalı. Durdur: 'yemeyi durdur'.")


def _extract_eat(msg: str) -> dict:
    low = msg.lower()
    if any(w in low for w in ("durdur", "dur", "kapat", "bırak", "stop")):
        return {"action": "stop"}
    a = re.search(r"(\d+)\s*(saniye|sn)", low)
    return {"aralik": int(a.group(1)) if a else 40}


def _extract_oneblock(msg: str) -> dict:
    low = msg.lower()
    if any(w in low for w in ("durdur", "dur", "kapat", "bırak", "birak", "stop")):
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
    return {"seconds": total or 300}
