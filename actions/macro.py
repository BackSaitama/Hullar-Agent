"""
Makro — klavye + fare hareketlerini kaydet ve tekrar oynat (pynput).

Kaydet:  "makro kaydet <isim>"  → ESC'ye basana kadar kaydeder (max 120 sn)
Oynat:   "makro oynat <isim>"
Liste:   "makrolar"

Kayıtlar: data/macros/<isim>.json
Kullanıcı kaydederken bilgisayarın başında olur (eylemleri kendisi yapar).
"""

from __future__ import annotations

import json
import re
import threading
import time
from pathlib import Path

_DIR = Path(__file__).parent.parent / "data" / "macros"
_MAX_SECONDS = 120

_rec: dict = {"active": False}


def _safe_name(name: str) -> str:
    name = re.sub(r"[^\w\-]+", "_", (name or "makro").strip().lower())
    return name or "makro"


# ── Kayıt ─────────────────────────────────────────────────────────────── #
def record_macro(name: str, duration: float | None = None) -> str:
    if _rec.get("active"):
        return "Zaten kayıt yapılıyor. Bitirmek için ESC'ye bas."
    try:
        from pynput import keyboard, mouse  # type: ignore
    except Exception:
        return "Makro için pynput gerekli (kurulu değil)."

    _DIR.mkdir(parents=True, exist_ok=True)
    events: list[dict] = []
    start = time.time()
    _rec["active"] = True
    stop_flag = {"stop": False}

    def _ts() -> float:
        return round(time.time() - start, 4)

    # Dinleyiciler
    def on_key_press(key):
        events.append({"t": _ts(), "type": "key_press", "key": _key_str(key)})
        if key == keyboard.Key.esc:
            stop_flag["stop"] = True
            return False  # klavye dinleyicisini durdur

    def on_key_release(key):
        events.append({"t": _ts(), "type": "key_release", "key": _key_str(key)})

    def on_click(x, y, button, pressed):
        events.append({"t": _ts(), "type": "click", "x": x, "y": y,
                       "button": str(button), "pressed": pressed})

    def _key_str(key):
        try:
            return key.char if hasattr(key, "char") and key.char else str(key)
        except Exception:
            return str(key)

    kl = keyboard.Listener(on_press=on_key_press, on_release=on_key_release)
    ml = mouse.Listener(on_click=on_click)
    kl.start()
    ml.start()

    limit = min(duration or _MAX_SECONDS, _MAX_SECONDS)
    while not stop_flag["stop"] and (time.time() - start) < limit:
        time.sleep(0.05)

    stop_flag["stop"] = True
    try:
        kl.stop()
        ml.stop()
    except Exception:
        pass
    _rec["active"] = False

    # ESC tuşunu kayıttan çıkar (tekrar oynatınca kaydı bozmasın)
    events = [e for e in events if not (e.get("key") == "Key.esc")]
    path = _DIR / f"{_safe_name(name)}.json"
    path.write_text(json.dumps(events, ensure_ascii=False), encoding="utf-8")
    return (f"💾 Makro '{_safe_name(name)}' kaydedildi ({len(events)} eylem). "
            f"Oynatmak için: makro oynat {_safe_name(name)}")


def record_macro_bg(name: str, duration: float | None = None) -> str:
    """Kaydı arka planda başlatır (CLI/Telegram bloklanmasın)."""
    if _rec.get("active"):
        return "Zaten kayıt yapılıyor."
    threading.Thread(target=record_macro, args=(name, duration), daemon=True).start()
    return (f"⏺️ '{_safe_name(name)}' makrosu kaydediliyor. Şimdi yap, bitince "
            f"ESC'ye bas (en fazla {_MAX_SECONDS}s).")


# ── Oynat ─────────────────────────────────────────────────────────────── #
def play_macro(name: str) -> str:
    path = _DIR / f"{_safe_name(name)}.json"
    if not path.exists():
        return f"'{_safe_name(name)}' adlı makro yok. 'makrolar' ile listele."
    try:
        from pynput import keyboard, mouse  # type: ignore
    except Exception:
        return "Makro için pynput gerekli (kurulu değil)."

    events = json.loads(path.read_text(encoding="utf-8"))
    kc = keyboard.Controller()
    mc = mouse.Controller()

    def _resolve_key(s: str):
        if s and s.startswith("Key."):
            return getattr(keyboard.Key, s.split(".", 1)[1], None)
        return s

    def _resolve_button(s: str):
        return getattr(mouse.Button, s.split(".", 1)[1], mouse.Button.left) \
            if s.startswith("Button.") else mouse.Button.left

    def _run():
        prev = 0.0
        for e in events:
            delay = max(0.0, e.get("t", 0) - prev)
            time.sleep(min(delay, 5))  # 5sn üstü bekleme kırp
            prev = e.get("t", 0)
            try:
                if e["type"] == "key_press":
                    k = _resolve_key(e["key"])
                    if k is not None:
                        kc.press(k)
                elif e["type"] == "key_release":
                    k = _resolve_key(e["key"])
                    if k is not None:
                        kc.release(k)
                elif e["type"] == "click":
                    mc.position = (e["x"], e["y"])
                    btn = _resolve_button(e["button"])
                    if e["pressed"]:
                        mc.press(btn)
                    else:
                        mc.release(btn)
            except Exception:
                continue

    threading.Thread(target=_run, daemon=True).start()
    return f"▶️ '{_safe_name(name)}' makrosu oynatılıyor ({len(events)} eylem)."


def list_macros() -> str:
    if not _DIR.exists():
        return "Henüz kayıtlı makro yok."
    items = sorted(p.stem for p in _DIR.glob("*.json"))
    if not items:
        return "Henüz kayıtlı makro yok."
    return "🎬 Makrolar:\n" + "\n".join(f"• {n}" for n in items)


# ── Dispatcher action'ları ────────────────────────────────────────────── #
def macro_record(parameters: dict | None = None) -> str:
    p = parameters or {}
    return record_macro_bg(p.get("name", "makro"), p.get("duration"))


def macro_play(parameters: dict | None = None) -> str:
    return play_macro((parameters or {}).get("name", "makro"))


def macro_list(parameters: dict | None = None) -> str:
    return list_macros()


def _extract_macro(msg: str) -> dict:
    m = re.search(r"makro(?:yu)?\s+(?:kaydet|oynat|çalıştır|calistir)\s+([\w\-]+)", msg, re.I)
    name = m.group(1) if m else "makro"
    d = re.search(r"(\d+)\s*(?:saniye|sn)", msg, re.I)
    out = {"name": name}
    if d:
        out["duration"] = int(d.group(1))
    return out
