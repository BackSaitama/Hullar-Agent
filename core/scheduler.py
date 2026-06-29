"""
Görev Zamanlayıcı — 'her sabah 9'da hava durumu' gibi zamanlanmış komutlar.
QTimer ile dakikada bir kontrol eder, vakti gelen komutu brain'e gönderir.
"""

import json
import logging
import re
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import QTimer

logger = logging.getLogger(__name__)

SCHED_FILE = Path(__file__).parent.parent / "memory" / "schedules.json"


class Scheduler:
    def __init__(self, on_fire):
        """on_fire(command:str) → komutu çalıştıran callback (genelde pet._send_to_ai)."""
        self._on_fire = on_fire
        self._items = self._load()
        self._timer = QTimer()
        self._timer.timeout.connect(self._check)
        self._timer.start(60_000)   # her dakika
        logger.info("Zamanlayıcı aktif (%d görev)", len(self._items))

    def _load(self) -> list:
        if SCHED_FILE.exists():
            try:
                return json.loads(SCHED_FILE.read_text(encoding="utf-8"))
            except Exception:
                pass
        return []

    def _save(self):
        SCHED_FILE.parent.mkdir(parents=True, exist_ok=True)
        SCHED_FILE.write_text(json.dumps(self._items, ensure_ascii=False, indent=2),
                              encoding="utf-8")

    def add(self, time_str: str, command: str) -> str:
        self._items.append({"time": time_str, "command": command, "last": ""})
        self._save()
        return f"Efendim, her gün {time_str}'da şu görev planlandı: \"{command}\""

    def list_items(self) -> str:
        if not self._items:
            return "Efendim, planlanmış görev yok."
        return "Planlı görevler:\n" + "\n".join(
            f"  • {it['time']} → {it['command']}" for it in self._items)

    def clear(self) -> str:
        n = len(self._items)
        self._items = []
        self._save()
        return f"Efendim, {n} planlı görev silindi."

    def _check(self):
        now = datetime.now()
        hhmm = now.strftime("%H:%M")
        today = now.strftime("%Y-%m-%d")
        for it in self._items:
            if it["time"] == hhmm and it.get("last") != today:
                it["last"] = today
                self._save()
                logger.info("Zamanlanmış görev tetiklendi: %s", it["command"])
                try:
                    self._on_fire(it["command"])
                except Exception as exc:
                    logger.error("Zamanlı görev hatası: %s", exc)


# ── Dispatcher yardımcıları ──────────────────────────────────────────── #
_SCHEDULER: Scheduler | None = None


def set_scheduler(s: Scheduler):
    global _SCHEDULER
    _SCHEDULER = s


def schedule_action(parameters: dict = None, **_) -> str:
    if not _SCHEDULER:
        return "Zamanlayıcı hazır değil."
    p = parameters or {}
    if p.get("liste"):
        return _SCHEDULER.list_items()
    if p.get("temizle"):
        return _SCHEDULER.clear()
    t, cmd = p.get("time"), p.get("command")
    if t and cmd:
        return _SCHEDULER.add(t, cmd)
    return "Efendim, saat ve görev belirtin. Örn: 'her sabah 9'da hava durumu söyle'"


def _extract_schedule(msg: str) -> dict:
    ml = msg.lower()
    if "listele" in ml or "göster" in ml or "goster" in ml or "neler var" in ml:
        return {"liste": True}
    if "iptal" in ml or "temizle" in ml or ("sil" in ml and "görev" in ml):
        return {"temizle": True}

    # Saat çıkar
    m = re.search(r"(\d{1,2})[:.](\d{2})", msg)
    if m:
        t = f"{int(m.group(1)):02d}:{m.group(2)}"
    else:
        m2 = re.search(r"saat\s*(\d{1,2})", ml)
        if m2:
            t = f"{int(m2.group(1)):02d}:00"
        elif "sabah" in ml:
            t = "09:00"
        elif "öğle" in ml or "ogle" in ml:
            t = "12:00"
        elif "akşam" in ml or "aksam" in ml:
            t = "19:00"
        else:
            t = "09:00"

    # Komut: zaman ifadelerini temizle
    cmd = re.sub(r"\b(her\s*(gün|sabah|akşam|öğle)|saat|\d{1,2}[:.]\d{2}|"
                 r"\d{1,2}('?da|'?de|'?te)?|sabah|akşam|öğle|de|da|"
                 r"zamanla|planla|hatırlat|olduğunda)\b", "", msg, flags=re.I)
    cmd = cmd.strip(" ,.:'-")
    return {"time": t, "command": cmd or "hava durumu"}
