"""Ekran okuma/analiz — 'ekranımda ne var' komutu.
Gemini vision varsa görsel analiz, yoksa OCR metni."""

import re


def screen_read(parameters: dict = None, **_) -> str:
    soru = (parameters or {}).get("soru", "").strip() or \
        "Bu ekranda ne var? Kısaca Türkçe özetle, önemli öğeleri söyle."
    try:
        from agent.vision import Vision
        from agent.llm import AgentLLM
        v = Vision(AgentLLM())
        result = v.analyze(soru)
        if result and result.strip():
            return f"Efendim, ekranınızda şunu görüyorum:\n{result[:1500]}"
    except Exception as exc:
        return f"Ekran okunamadı: {exc}"
    return "Efendim, ekranı okuyamadım."


def _extract_screen(msg: str) -> dict:
    q = re.sub(r"\b(ekran[ıi]?m?d?a?|ne var|ne görüyorsun|oku|göster|"
              r"analiz et|incele|bak)\b", "", msg, flags=re.I).strip(" ?.,")
    return {"soru": q}
