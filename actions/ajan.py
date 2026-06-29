"""
HULLAR Ajan — jarvis-agent'ın Ollama'ya uyarlanmış hali.

Karmaşık/çok adımlı görevleri (proje oluştur, dosyalar yaz, kur+çalıştır)
Ollama tool-calling ile kendi kendine yapar. Groq yerine YEREL Ollama
(qwen2.5-coder, tool destekli) kullanır — bedava, offline.

  "ajan: masaüstünde hesap makinesi html projesi yap"
  → adım adım klasör açar, dosyaları yazar, çalıştırır, raporlar.
"""

from __future__ import annotations

import json
import logging
import os
import threading

import requests  # type: ignore

from . import agent_tools

logger = logging.getLogger("hullar.ajan")

_DESKTOP = os.path.join(os.path.expanduser("~"), "Desktop")

_SYS = f"""Sen HULLAR'ın görev ajanısın — Windows'ta çok adımlı işleri araçlarla yaparsın.
Kurallar:
1. Eldeki araçları (write_file, create_directory, run_command, list_directory...) sırayla kullan.
2. Masaüstü için {_DESKTOP} yolunu kullan.
3. Bir proje bittiğinde klasörü 'run_command' ile 'explorer.exe <yol>' açarak göster.
4. Araç çıktısını özetleyerek kullanıcıya bildir.
5. İş tamamen bitince cevabın sonuna '[GÖREV TAMAMLANDI]' yaz.
Kısa konuş, gereksiz açıklama yapma."""


def _push(text: str):
    try:
        from .notify import push
        push(text)
    except Exception:
        pass


def _ollama_chat(messages: list) -> dict:
    base = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    model = os.getenv("AJAN_MODEL", os.getenv("OLLAMA_CODER_MODEL", "qwen2.5-coder:7b"))
    r = requests.post(f"{base}/api/chat", json={
        "model": model,
        "messages": messages,
        "tools": agent_tools.TOOL_DECLARATIONS,
        "stream": False,
        "options": {"temperature": 0.2},
    }, timeout=180)
    r.raise_for_status()
    return r.json().get("message", {})


def _parse_text_tools(content: str) -> list:
    """Model tool çağrısını metin/JSON olarak döndürdüyse ayıkla."""
    import re
    calls = []
    # <tool_call>{...}</tool_call> veya düz {"name":..,"arguments":..}
    bloklar = re.findall(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", content, re.S)
    if not bloklar:
        bloklar = re.findall(r'\{[^{}]*"name"\s*:\s*"[^"]+"[^{}]*"arguments"\s*:\s*\{[^{}]*\}[^{}]*\}',
                             content, re.S)
    for b in bloklar:
        try:
            obj = json.loads(b)
            calls.append({"function": {"name": obj.get("name"),
                                       "arguments": obj.get("arguments", {})}})
        except Exception:
            continue
    return calls


def _exec_tool(name: str, args) -> str:
    fn = agent_tools.TOOL_MAP.get(name)
    if not fn:
        return f"Bilinmeyen araç: {name}"
    try:
        return str(fn(**(args if isinstance(args, dict) else {})))[:2000]
    except Exception as exc:
        return f"Araç hatası: {exc}"


def _loop(gorev: str):
    messages = [{"role": "system", "content": _SYS},
                {"role": "user", "content": gorev}]
    son = ""
    for tur in range(12):
        try:
            msg = _ollama_chat(messages)
        except Exception as exc:
            _push(f"🤖 Ajan hatası: {exc}")
            return
        tool_calls = msg.get("tool_calls") or []
        content = (msg.get("content") or "").strip()
        if not tool_calls and content:        # metin içinde tool çağrısı varsa ayıkla
            tool_calls = _parse_text_tools(content)
        messages.append({"role": "assistant", "content": content,
                         "tool_calls": tool_calls})
        if tool_calls:
            for tc in tool_calls:
                fn = tc.get("function", {})
                ad = fn.get("name", "")
                args = fn.get("arguments", {})
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except Exception:
                        args = {}
                sonuc = _exec_tool(ad, args)
                logger.info("ajan araç: %s", ad)
                messages.append({"role": "tool", "content": sonuc})
            continue
        son = content
        if content:
            break
    _push("🤖 Ajan bitti:\n" + (son.replace("[GÖREV TAMAMLANDI]", "").strip()[:1500]
                                or "tamamlandı"))


def ajan(parameters: dict | None = None) -> str:
    gorev = (parameters or {}).get("istek", "").strip()
    if not gorev:
        return "Ne yapayım? Örn: 'ajan: masaüstünde not defteri html sitesi yap'"
    threading.Thread(target=_loop, args=(gorev,), daemon=True).start()
    return (f"🤖 Ajan görevi aldı: '{gorev}'. Adım adım yapıp Telegram'dan "
            f"rapor edeceğim (1-2 dk sürebilir).")


def _extract_ajan(msg: str) -> dict:
    import re
    m = re.search(r"\bajan\b\s*[:\-]?\s*(.+)", msg, re.I | re.S)
    return {"istek": m.group(1).strip() if m else ""}
