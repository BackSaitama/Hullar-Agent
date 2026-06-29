"""
JARVIS Uygulama Süre Limiti (Skill 47).

Bir uygulamayı izler; belirli süre çalıştıktan sonra uyarır (ve istenirse kapatır).
Arka plan thread'i ile çalışır. notify.py varsa Telegram'dan da haber verir.

Örnek: "discord'a 30 dakika limit koy"
"""

import logging
import threading
import time

logger = logging.getLogger(__name__)

_timers: dict[str, threading.Thread] = {}
_stops: dict[str, threading.Event] = {}


def _watch(proc_name: str, minutes: int, kapat: bool):
    stop = _stops[proc_name]
    deadline = time.time() + minutes * 60
    try:
        import psutil
    except Exception as exc:
        logger.error("app_limit psutil yok: %s", exc)
        return

    def _running() -> bool:
        return any((p.info["name"] or "").lower().startswith(proc_name.lower())
                   for p in psutil.process_iter(["name"]))

    # Süre dolana kadar bekle (uygulama kapanırsa sayaç da biter)
    while time.time() < deadline:
        if stop.wait(10):
            return
        if not _running():
            logger.info("app_limit: %s zaten kapandı, izleme bitti.", proc_name)
            _timers.pop(proc_name, None)
            return

    # Süre doldu
    msg = f"⏰ '{proc_name}' için {minutes} dk süre doldu."
    try:
        from .notify import push
        push(msg + (" Uygulama kapatılıyor." if kapat else ""))
    except Exception:
        pass
    if kapat:
        try:
            for p in psutil.process_iter(["name"]):
                if (p.info["name"] or "").lower().startswith(proc_name.lower()):
                    p.terminate()
        except Exception as exc:
            logger.warning("app_limit kapatma hatası: %s", exc)
    logger.info(msg)
    _timers.pop(proc_name, None)


def uygulama_limit(parameters: dict | None = None) -> str:
    """parameters: {"app": str, "minutes": int, "kapat": bool}"""
    params = parameters or {}
    app = (params.get("app") or "").strip()
    if not app:
        return "Efendim, hangi uygulamaya limit koyayım?"
    minutes = int(params.get("minutes", 30))
    kapat = bool(params.get("kapat", False))

    key = app.lower()
    if key in _timers and _timers[key].is_alive():
        _stops[key].set()   # eskiyi durdur, yenisini kur

    _stops[key] = threading.Event()
    t = threading.Thread(target=_watch, args=(app, minutes, kapat), daemon=True)
    _timers[key] = t
    t.start()
    son = " (süre sonunda kapatılacak)" if kapat else ""
    return f"⏳ '{app}' için {minutes} dakika limit kuruldu{son}."


def _extract_limit(msg: str) -> dict:
    import re
    low = msg.lower()
    m_min = re.search(r"(\d+)\s*(dk|dakika|saat|min)", low)
    minutes = int(m_min.group(1)) if m_min else 30
    if m_min and ("saat" in m_min.group(2)):
        minutes *= 60
    # uygulama adı: bilinen adları yakala
    app = ""
    for known in ("discord", "chrome", "steam", "youtube", "spotify", "roblox",
                  "instagram", "tiktok", "valorant", "telegram", "edge", "firefox"):
        if known in low:
            app = known
            break
    if not app:
        m = re.search(r"([a-zçğıöşü]+)'?(?:a|e|ya|ye)\s+\d+\s*(?:dk|dakika|saat)", low)
        if m:
            app = m.group(1)
    kapat = any(k in low for k in ("kapat", "kapansın", "engelle"))
    return {"app": app, "minutes": minutes, "kapat": kapat}
