"""
Otomatik tıklayıcı (autoclicker) — belirli aralıkla fare tıklaması.

Arka planda çalışır, "durdur" denince durur. Tek oyunculu/idle oyunlar
ve tekrarlı işler için. (Online rekabetçi oyunlarda kullanımı hile sayılır.)
"""

from __future__ import annotations

import re
import threading
import time

_state: dict = {"running": False, "thread": None}


def _loop(interval: float, button: str, count: int):
    try:
        import pyautogui  # type: ignore
        pyautogui.FAILSAFE = True  # imleci sol-üst köşeye götür → acil durdur
        n = 0
        while _state["running"]:
            pyautogui.click(button=button)
            n += 1
            if count and n >= count:
                break
            time.sleep(interval)
    except Exception:
        pass
    finally:
        _state["running"] = False


def start_clicker(interval: float = 1.0, button: str = "left", count: int = 0) -> str:
    if _state["running"]:
        return "Otomatik tıklayıcı zaten çalışıyor. Durdurmak için 'tıklamayı durdur'."
    interval = max(0.01, float(interval))
    _state["running"] = True
    t = threading.Thread(target=_loop, args=(interval, button, count), daemon=True)
    _state["thread"] = t
    t.start()
    hedef = f"{count} kez" if count else "sürekli"
    return (f"🖱️ Otomatik tıklayıcı başladı ({interval}s aralık, {button}, {hedef}). "
            f"Durdurmak için 'tıklamayı durdur' de veya imleci ekranın sol-üst "
            f"köşesine götür.")


def stop_clicker() -> str:
    if not _state["running"]:
        return "Otomatik tıklayıcı zaten kapalı."
    _state["running"] = False
    return "🛑 Otomatik tıklayıcı durduruldu."


# ── Dispatcher action + extractor ─────────────────────────────────────── #
def auto_clicker(parameters: dict | None = None) -> str:
    p = parameters or {}
    if p.get("action") == "stop":
        return stop_clicker()
    return start_clicker(
        interval=p.get("interval", 1.0),
        button=p.get("button", "left"),
        count=p.get("count", 0),
    )


def _extract_clicker(msg: str) -> dict:
    low = msg.lower()
    if any(w in low for w in ("durdur", "dur", "kapat", "stop", "bitir")):
        return {"action": "stop"}

    # Aralık: "0.5 saniyede", "saniyede 5 kez", "her 2 saniye"
    interval = 1.0
    m_int = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:saniye|sn|s)\b", low)
    if m_int:
        interval = float(m_int.group(1).replace(",", "."))
    m_hz = re.search(r"saniyede\s*(\d+)", low)
    if m_hz:
        hz = int(m_hz.group(1))
        interval = 1.0 / max(1, hz)

    # Toplam adet: "100 kez", "50 defa tıkla"
    count = 0
    m_cnt = re.search(r"(\d+)\s*(?:kez|defa|kere|adet)\b", low)
    if m_cnt:
        count = int(m_cnt.group(1))

    button = "right" if ("sağ" in low or "sag" in low or "right" in low) else "left"
    return {"action": "start", "interval": interval, "button": button, "count": count}
