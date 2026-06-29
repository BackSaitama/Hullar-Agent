"""
Hafıza sistemi — kullanıcı alışkanlıkları + geçmiş görevler.
Kalıcı JSON dosyası.
"""

import json
import logging
import time
from pathlib import Path

logger = logging.getLogger(__name__)

MEM_FILE = Path(__file__).parent.parent / "memory" / "agent_memory.json"


class Memory:
    def __init__(self):
        MEM_FILE.parent.mkdir(parents=True, exist_ok=True)
        self._data = self._load()

    def _load(self) -> dict:
        if MEM_FILE.exists():
            try:
                return json.loads(MEM_FILE.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {"facts": {}, "tasks": [], "preferences": {}}

    def _save(self):
        try:
            MEM_FILE.write_text(
                json.dumps(self._data, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
        except Exception as exc:
            logger.warning("Hafıza kaydedilemedi: %s", exc)

    # ── Kalıcı bilgi ──────────────────────────────────────────────────── #
    def remember(self, key: str, value: str):
        self._data["facts"][key] = value
        self._save()

    def recall(self, key: str, default=None):
        return self._data["facts"].get(key, default)

    def set_preference(self, key: str, value):
        self._data["preferences"][key] = value
        self._save()

    def get_preference(self, key: str, default=None):
        return self._data["preferences"].get(key, default)

    # ── Görev geçmişi ─────────────────────────────────────────────────── #
    def log_task(self, goal: str, success: bool, steps: int):
        self._data["tasks"].append({
            "goal": goal,
            "success": success,
            "steps": steps,
            "ts": time.strftime("%Y-%m-%d %H:%M"),
        })
        self._data["tasks"] = self._data["tasks"][-50:]  # son 50
        self._save()

    def recent_tasks(self, n: int = 5) -> list:
        return self._data["tasks"][-n:]

    def context_summary(self) -> str:
        """LLM'e verilecek kısa hafıza özeti."""
        parts = []
        if self._data["facts"]:
            facts = "; ".join(f"{k}={v}" for k, v in list(self._data["facts"].items())[:10])
            parts.append(f"Bilinenler: {facts}")
        if self._data["preferences"]:
            prefs = "; ".join(f"{k}={v}" for k, v in self._data["preferences"].items())
            parts.append(f"Tercihler: {prefs}")
        return "\n".join(parts)
