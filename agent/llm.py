"""
Agent LLM katmanı — metin + görsel (vision) destekli.
Gemini birincil, Ollama yedek. JSON çıktı için optimize.
"""

import json
import logging
import os
import re

logger = logging.getLogger(__name__)


class AgentLLM:
    def __init__(self):
        self._backend = os.getenv("AI_BACKEND", "ollama").strip().lower()
        self._gemini = None
        # SADECE backend gemini ise Gemini'yi başlat (ollama'da 429 spam'i önle)
        if self._backend == "gemini":
            self._init_gemini()

    def _init_gemini(self):
        try:
            import google.generativeai as genai  # type: ignore
            api_key = os.getenv("GEMINI_API_KEY", "")
            if api_key and not api_key.startswith("YOUR_"):
                genai.configure(api_key=api_key)
                self._gemini = genai.GenerativeModel(
                    os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
                )
        except Exception as exc:
            logger.warning("Gemini başlatılamadı: %s", exc)

    # ── Genel sorgu (metin) ───────────────────────────────────────────── #
    def ask(self, prompt: str, system: str = "") -> str:
        full = f"{system}\n\n{prompt}" if system else prompt
        # Backend ollama → direkt Ollama (Gemini denenmez)
        if self._backend == "ollama":
            return self._ask_ollama(full)
        if self._gemini:
            try:
                return self._gemini.generate_content(full).text.strip()
            except Exception as exc:
                logger.warning("Gemini ask hata, Ollama'ya geçiliyor: %s", str(exc)[:80])
        return self._ask_ollama(full)

    # ── Görsel + metin ─────────────────────────────────────────────────── #
    def ask_vision(self, prompt: str, image_path: str, system: str = "") -> str:
        full = f"{system}\n\n{prompt}" if system else prompt
        if self._backend == "ollama":
            return self._ask_ollama_vision(full, image_path)
        if self._gemini:
            try:
                from PIL import Image  # type: ignore
                img = Image.open(image_path)
                return self._gemini.generate_content([full, img]).text.strip()
            except Exception as exc:
                logger.warning("Gemini vision hata: %s", str(exc)[:80])
        return self._ask_ollama_vision(full, image_path)

    # ── JSON çıktı al ─────────────────────────────────────────────────── #
    def ask_json(self, prompt: str, system: str = "", image_path: str | None = None) -> dict:
        raw = (self.ask_vision(prompt, image_path, system)
               if image_path else self.ask(prompt, system))
        return self._extract_json(raw)

    # ── Yardımcılar ───────────────────────────────────────────────────── #
    def _ask_ollama(self, prompt: str) -> str:
        try:
            import requests
            base = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
            model = os.getenv("OLLAMA_MODEL", "llama3")
            r = requests.post(f"{base}/api/generate",
                              json={"model": model, "prompt": prompt, "stream": False},
                              timeout=90)
            return r.json().get("response", "").strip()
        except Exception as exc:
            logger.error("Ollama hata: %s", exc)
            return ""

    def _ask_ollama_vision(self, prompt: str, image_path: str) -> str:
        try:
            import base64, requests
            base = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
            model = (os.getenv("OLLAMA_VISION_MODEL")
                     or os.getenv("VISION_MODEL", "moondream"))
            with open(image_path, "rb") as f:
                img_b64 = base64.b64encode(f.read()).decode()
            r = requests.post(f"{base}/api/generate",
                              json={"model": model, "prompt": prompt,
                                    "images": [img_b64], "stream": False},
                              timeout=120)
            return r.json().get("response", "").strip()
        except Exception as exc:
            logger.warning("Ollama vision yok: %s", exc)
            return ""

    @staticmethod
    def _extract_json(text: str) -> dict:
        """Metinden ilk geçerli JSON objesini çıkar (balanced braces)."""
        if not text:
            return {}
        # ```json bloğu
        m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(1))
            except json.JSONDecodeError:
                pass
        # Balanced brace tarama
        for i, ch in enumerate(text):
            if ch == "{":
                depth, in_str, esc = 0, False, False
                for j in range(i, len(text)):
                    c = text[j]
                    if esc:
                        esc = False; continue
                    if c == "\\" and in_str:
                        esc = True; continue
                    if c == '"':
                        in_str = not in_str; continue
                    if in_str:
                        continue
                    if c == "{":
                        depth += 1
                    elif c == "}":
                        depth -= 1
                        if depth == 0:
                            try:
                                return json.loads(text[i:j+1])
                            except json.JSONDecodeError:
                                break
                break
        return {}
