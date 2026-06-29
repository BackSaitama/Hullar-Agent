"""
Uzun Süreli Kullanıcı Hafızası (#1) — JARVIS Efendisi hakkında bildiklerini saklar.

"şunu hatırla / aklında tut / beni ... olarak tanı" → kalıcı not.
Notlar her sohbette sistem promptuna enjekte edilir (Ollama + Gemini).
"""

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_FILE = Path(__file__).parent.parent / "memory" / "user_facts.json"


class _UserMemory:
    def __init__(self):
        self._facts: list[str] = self._load()

    def _load(self) -> list[str]:
        try:
            data = json.loads(_FILE.read_text(encoding="utf-8"))
            return [str(x) for x in data] if isinstance(data, list) else []
        except Exception:
            return []

    def _save(self):
        try:
            _FILE.parent.mkdir(parents=True, exist_ok=True)
            _FILE.write_text(
                json.dumps(self._facts, ensure_ascii=False, indent=2),
                encoding="utf-8")
        except Exception as exc:
            logger.warning("Hafıza kaydedilemedi: %s", exc)

    def add(self, fact: str) -> bool:
        fact = (fact or "").strip(" .,:;")
        if not fact or fact in self._facts:
            return False
        self._facts.append(fact)
        self._save()
        return True

    def all(self) -> list[str]:
        return list(self._facts)

    def clear(self):
        self._facts = []
        self._save()

    def as_block(self) -> str:
        if not self._facts:
            return ""
        lines = "\n".join(f"- {f}" for f in self._facts[-25:])
        return "Efendin (kullanıcı) hakkında hatırladıkların:\n" + lines


memory = _UserMemory()
