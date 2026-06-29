"""
Composio Tool Entegrasyonu
Ollama'ya 250+ servis entegrasyonu sağlar (GitHub, Gmail, Calendar, Slack, vb.)
Ollama'nın OpenAI uyumlu /v1 endpoint'ini kullanır.
"""

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

_toolset = None   # Singleton


def _get_toolset():
    global _toolset
    if _toolset is None:
        try:
            from composio_openai import ComposioToolSet  # type: ignore
            api_key = os.getenv("COMPOSIO_API_KEY", "")
            if not api_key:
                return None
            _toolset = ComposioToolSet(api_key=api_key)
            logger.info("Composio toolset hazır.")
        except Exception as exc:
            logger.warning("Composio başlatılamadı: %s", exc)
            return None
    return _toolset


def get_composio_tools(apps: list[str] | None = None) -> list[dict]:
    """
    Composio'dan tool tanımlarını OpenAI formatında döndürür.
    apps: ["GITHUB", "GMAIL", "GOOGLECALENDAR", ...]
    Boş bırakılırsa bağlı tüm app'lerin araçları döner.
    """
    toolset = _get_toolset()
    if not toolset:
        return []
    try:
        if apps:
            from composio_openai import App  # type: ignore
            app_enums = [getattr(App, a.upper(), None) for a in apps]
            app_enums = [a for a in app_enums if a]
            tools = toolset.get_tools(apps=app_enums)
        else:
            tools = toolset.get_tools()
        logger.info("Composio: %d tool yüklendi.", len(tools))
        return tools
    except Exception as exc:
        logger.warning("Composio tool listesi alınamadı: %s", exc)
        return []


def handle_composio_tool_call(tool_name: str, tool_input: dict) -> str:
    """
    LLM'in çağırdığı Composio tool'unu çalıştırır ve sonucu döndürür.
    """
    toolset = _get_toolset()
    if not toolset:
        return "Composio bağlantısı yok."
    try:
        from composio import action as composio_action  # type: ignore
        result = toolset.execute_action(
            action=tool_name,
            params=tool_input,
        )
        logger.info("Composio tool çalıştı: %s → %s", tool_name, str(result)[:80])
        # Sonucu string'e dönüştür
        if isinstance(result, dict):
            data = result.get("data") or result.get("response") or result
            return str(data)
        return str(result)
    except Exception as exc:
        logger.error("Composio tool hatası [%s]: %s", tool_name, exc)
        return f"Araç çalıştırılırken hata: {exc}"


def is_composio_tool(tool_name: str) -> bool:
    """Bu tool adı Composio'ya mı ait?"""
    toolset = _get_toolset()
    if not toolset:
        return False
    try:
        tools = toolset.get_tools()
        tool_names = {t.get("function", {}).get("name", "") for t in tools}
        return tool_name in tool_names
    except Exception:
        return False
