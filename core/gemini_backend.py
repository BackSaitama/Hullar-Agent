"""
Gemini API arka ucu.
Function calling (tool use) destekli Gemini entegrasyonu.
"""

import logging
import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .tools import ToolRegistry

from .prompt import JARVIS_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


class GeminiBackend:
    def __init__(self, tool_registry: "ToolRegistry"):
        try:
            import google.generativeai as genai  # type: ignore
        except ImportError:
            raise ImportError("google-generativeai kütüphanesi kurulu değil. `pip install google-generativeai` çalıştırın.")

        api_key = os.getenv("GEMINI_API_KEY", "")
        if not api_key or api_key == "YOUR_GEMINI_API_KEY_HERE":
            raise ValueError("GEMINI_API_KEY .env dosyasında tanımlı değil veya varsayılan değer.")

        genai.configure(api_key=api_key)
        model_name = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

        # Araçları Gemini'nin beklediği formata dönüştür
        gemini_tools = self._build_gemini_tools(tool_registry)

        self._model = genai.GenerativeModel(
            model_name=model_name,
            system_instruction=JARVIS_SYSTEM_PROMPT,
            tools=gemini_tools if gemini_tools else None,
        )
        self._tool_registry = tool_registry
        self._chat = self._model.start_chat(history=[])
        logger.info("Gemini backend hazır: %s", model_name)

    def _build_gemini_tools(self, registry: "ToolRegistry") -> list:
        import google.generativeai as genai  # type: ignore

        declarations = []
        for schema in registry.get_schemas():
            props = {}
            required = schema.get("parameters", {}).get("required", [])
            for pname, pdef in schema.get("parameters", {}).get("properties", {}).items():
                ptype = pdef.get("type", "string")
                type_map = {
                    "string": genai.protos.Type.STRING,
                    "integer": genai.protos.Type.INTEGER,
                    "number": genai.protos.Type.NUMBER,
                    "boolean": genai.protos.Type.BOOLEAN,
                }
                props[pname] = genai.protos.Schema(
                    type=type_map.get(ptype, genai.protos.Type.STRING),
                    description=pdef.get("description", ""),
                )

            declarations.append(
                genai.protos.FunctionDeclaration(
                    name=schema["name"],
                    description=schema.get("description", ""),
                    parameters=genai.protos.Schema(
                        type=genai.protos.Type.OBJECT,
                        properties=props,
                        required=required,
                    ),
                )
            )

        return [genai.protos.Tool(function_declarations=declarations)] if declarations else []

    def chat(self, user_message: str) -> str:
        import time
        import google.generativeai as genai  # type: ignore

        # Kota aşımında otomatik bekle ve tekrar dene (max 2 deneme)
        for attempt in range(2):
            try:
                return self._do_chat(user_message)
            except Exception as exc:
                msg = str(exc)
                wait = self._parse_retry_delay(msg)
                if wait and attempt == 0:
                    logger.warning("Kota aşıldı, %s saniye bekleniyor...", wait)
                    time.sleep(min(wait, 35))
                    continue
                return self._friendly_error(msg)
        return "Efendim, kota sınırına ulaşıldı. Lütfen birkaç dakika bekleyip tekrar deneyin."

    def _do_chat(self, user_message: str) -> str:
        import google.generativeai as genai  # type: ignore

        # Dinamik bağlam (hafıza #1 / bağlam #7 / dil #8) mesaja eklenir —
        # Gemini system_instruction'ı başlangıçta sabit olduğu için buradan beslenir.
        try:
            from .prompt import dynamic_context
            dc = dynamic_context()
            msg = (f"[BAĞLAM]\n{dc}\n[/BAĞLAM]\n\n{user_message}") if dc else user_message
        except Exception:
            msg = user_message

        response = self._chat.send_message(msg)

        for _ in range(5):
            tool_calls = [
                part.function_call
                for candidate in response.candidates
                for part in candidate.content.parts
                if part.function_call.name
            ]
            if not tool_calls:
                break

            function_responses = []
            for fc in tool_calls:
                logger.info("Araç çağrısı: %s(%s)", fc.name, dict(fc.args))
                result = self._tool_registry.call(fc.name, **dict(fc.args))
                function_responses.append(
                    genai.protos.Part(
                        function_response=genai.protos.FunctionResponse(
                            name=fc.name,
                            response={"result": result},
                        )
                    )
                )
            response = self._chat.send_message(
                genai.protos.Content(parts=function_responses, role="user")
            )

        return response.text.strip()

    @staticmethod
    def _parse_retry_delay(error_msg: str) -> float | None:
        """Hata mesajındaki 'Please retry in X.Xs' süresini çıkar."""
        import re
        m = re.search(r"retry in\s+([\d.]+)s", error_msg, re.IGNORECASE)
        if m:
            return float(m.group(1))
        return None

    @staticmethod
    def _friendly_error(msg: str) -> str:
        msg_l = msg.lower()
        if "429" in msg or "quota" in msg_l:
            return (
                "Efendim, ücretsiz kota sınırına ulaşıldı. "
                "Gemini dakikada 15 istek izin veriyor. "
                "Lütfen bir dakika bekleyip tekrar deneyin."
            )
        if "404" in msg:
            return "Efendim, seçilen Gemini modeli bulunamadı. .env dosyasındaki GEMINI_MODEL değerini kontrol edin."
        if "401" in msg or "api key" in msg_l:
            return "Efendim, Gemini API anahtarı geçersiz. .env dosyasındaki GEMINI_API_KEY değerini kontrol edin."
        logger.error("Gemini hata: %s", msg)
        return "Efendim, bir hata oluştu. Lütfen tekrar deneyin."
