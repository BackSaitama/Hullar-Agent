"""
JARVIS Anti-AFK (Skill 7).

Belirli aralıklarla zararsız bir tuş (Scroll Lock aç/kapa) göndererek
oturumun AFK sayılmasını engeller. Arka plan thread'i ile çalışır,
"anti afk kapat" denince durur.

Kapsam: Yalnızca kendi oturumunu canlı tutmak içindir. Oyun/uygulama
hizmet şartlarına aykırı kullanmaktan kaçının.
"""

import logging
import threading
import time

logger = logging.getLogger(__name__)

_thread: threading.Thread | None = None
_stop = threading.Event()
_interval = 60


def _loop():
    try:
        import pyautogui
    except Exception as exc:
        logger.error("anti-afk: pyautogui yok: %s", exc)
        return
    while not _stop.wait(_interval):
        try:
            # Zararsız: Scroll Lock'a iki kez bas (durum değişmez)
            pyautogui.press("scrolllock")
            pyautogui.press("scrolllock")
            logger.debug("anti-afk tik")
        except Exception as exc:
            logger.warning("anti-afk tik hatası: %s", exc)


def anti_afk(parameters: dict | None = None) -> str:
    """parameters: {"action": "ac"|"kapat", "interval": int}"""
    global _thread, _interval
    params = parameters or {}
    action = params.get("action", "toggle")

    aktif = _thread is not None and _thread.is_alive()
    if action == "toggle":
        action = "kapat" if aktif else "ac"

    if action == "kapat":
        if not aktif:
            return "Efendim, anti-afk zaten kapalı."
        _stop.set()
        return "✅ Anti-AFK kapatıldı."

    # aç
    if aktif:
        return f"Efendim, anti-afk zaten açık ({_interval}s)."
    _interval = max(15, int(params.get("interval", 60)))
    _stop.clear()
    _thread = threading.Thread(target=_loop, daemon=True)
    _thread.start()
    return f"🟢 Anti-AFK açıldı (her {_interval}s). Kapatmak için 'anti afk kapat' deyin."


def _extract_afk(msg: str) -> dict:
    import re
    low = msg.lower()
    action = "kapat" if any(k in low for k in ("kapat", "durdur", "stop", "off")) else \
             ("ac" if any(k in low for k in ("aç", "ac", "başlat", "baslat", "on")) else "toggle")
    m = re.search(r"(\d+)\s*(sn|saniye|sec)", low)
    out = {"action": action}
    if m:
        out["interval"] = int(m.group(1))
    return out
