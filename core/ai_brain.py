"""
AI Beyin — dispatcher önce, AI sonra.

Akış:
  1. ActionDispatcher kural tablosuna bak
  2. Kural eşleştiyse → action'ı çalıştır, AI'a gitme
  3. Eşleşmediyse → Gemini veya Ollama'ya sor
"""

import logging
import os
from typing import Callable

from .tools import ToolRegistry

logger = logging.getLogger(__name__)


class AIBrain:

    def __init__(self, on_tool_called: Callable[[str, str], None] | None = None):
        self._on_tool_called = on_tool_called
        self.tool_registry   = ToolRegistry()
        self._backend        = self._load_backend()

        # Dispatcher'ı geç import et (circular import önlemek için)
        from actions import ActionDispatcher
        self._dispatcher = ActionDispatcher()

    def _load_backend(self):
        name = os.getenv("AI_BACKEND", "gemini").strip().lower()
        logger.info("AI arka ucu yükleniyor: %s", name)
        if name == "gemini":
            from .gemini_backend import GeminiBackend
            return GeminiBackend(self.tool_registry)
        elif name == "ollama":
            from .ollama_backend import OllamaBackend
            return OllamaBackend(self.tool_registry)
        else:
            raise ValueError(f"Bilinmeyen AI_BACKEND: '{name}'. 'gemini' veya 'ollama' kullanın.")

    def chat(self, message: str) -> str:
        # ── 1. Kural tabanlı dispatcher ────────────────────────────────── #
        result = self._dispatcher.dispatch(message)
        if result is not None:
            logger.info("Dispatcher yanıtladı (AI atlandı)")
            return result

        # ── 2. AI arka ucu ─────────────────────────────────────────────── #
        logger.info("Dispatcher eşleşmedi → AI'a iletiliyor")
        return self._backend.chat(message)

    @property
    def backend_name(self) -> str:
        return os.getenv("AI_BACKEND", "gemini").strip().lower()
