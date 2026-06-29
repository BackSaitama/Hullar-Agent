"""Pano AI — kopyalanan metni özetle / çevir / açıkla."""

import re


def _get_clipboard() -> str:
    try:
        import pyperclip
        return pyperclip.paste()
    except Exception:
        try:
            import subprocess
            return subprocess.run(["powershell", "-command", "Get-Clipboard"],
                                  capture_output=True, text=True, timeout=5).stdout.strip()
        except Exception:
            return ""


def clipboard_ai(parameters: dict = None, **_) -> str:
    p = parameters or {}
    islem = p.get("islem", "özetle")
    text = _get_clipboard()
    if not text or len(text.strip()) < 3:
        return "Efendim, panoda işlenecek metin yok. Önce bir şey kopyalayın."

    yonerge = {
        "özetle":  "Bu metni kısaca Türkçe özetle.",
        "çevir":   "Bu metni Türkçeye çevir (zaten Türkçeyse İngilizceye).",
        "açıkla":  "Bu metni basit Türkçe ile açıkla.",
    }.get(islem, "Bu metni kısaca Türkçe özetle.")

    try:
        from agent.llm import AgentLLM
        result = AgentLLM().ask(f"{yonerge}\n\n---\n{text[:4000]}")
        return f"Efendim ({islem}):\n{result[:1500]}" if result else "Yanıt alınamadı."
    except Exception as exc:
        return f"Pano işlenemedi: {exc}"


def _extract_clip_ai(msg: str) -> dict:
    ml = msg.lower()
    if "çevir" in ml or "cevir" in ml:
        return {"islem": "çevir"}
    if "açıkla" in ml or "acikla" in ml:
        return {"islem": "açıkla"}
    return {"islem": "özetle"}
