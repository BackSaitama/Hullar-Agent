"""
HULLAR çok dilli destek.

HULLAR_LANG = tr (varsayılan) ise hiçbir şey çevrilmez (hızlı).
Başka dil seçilmişse:
  • gelen mesaj  → Türkçe'ye çevrilir (regex'ler Türkçe çalışsın)
  • giden cevap  → seçilen dile çevrilir
Çeviri seçili AI backend ile yapılır, sonuçlar önbelleğe alınır.
"""

from __future__ import annotations

import os
import re

_DEST_AD = {"tr": "Turkish", "en": "English", "de": "German",
            "es": "Spanish", "fr": "French"}

_cache: dict = {}


def get_lang() -> str:
    return (os.getenv("HULLAR_LANG", "tr") or "tr")[:2].lower()


# AI yanıtı çeviri DEĞİL de hata/uyarı ise (anahtar yok, servis yok) bunları yakala
_BAD_MARKERS = ("🔑", "API anahtarı girilmemiş", "API key", "servisi şu anda",
                "yanıt vermiyor", "AI servisi")


def _backend_usable() -> bool:
    """Seçili backend gerçekten çeviri yapabilir mi? (ollama hep; cloud → anahtar varsa)"""
    try:
        import os
        from .ai_skills import _has_key
        backend = os.getenv("AI_BACKEND", "ollama").lower()
        return backend == "ollama" or _has_key(backend)
    except Exception:
        return False


def _is_bad(out: str, original: str) -> bool:
    """Çeviri başarısız/uyarı mı? (orijinali korumak için)"""
    if not out or not out.strip():
        return True
    return any(m in out for m in _BAD_MARKERS) and out.strip() != original.strip()


def _translate(text: str, hedef_dil: str) -> str:
    if not text or not text.strip():
        return text
    key = (hedef_dil, text)
    if key in _cache:
        return _cache[key]
    # Backend çeviremezse (anahtar yok vb.) ORİJİNALİ koru — asla uyarıyla değiştirme
    if not _backend_usable():
        return text
    try:
        from .ai_skills import _ask_ai
        ad = _DEST_AD.get(hedef_dil, hedef_dil)
        out = (_ask_ai(
            f"You are a translator. Translate the user's text to {ad}. "
            "Keep emojis, numbers, URLs and formatting. Output ONLY the translation.",
            text) or "").strip()
        if _is_bad(out, text):      # hata/uyarı geldiyse orijinali döndür
            return text
        if len(_cache) < 500:
            _cache[key] = out
        return out
    except Exception:
        return text


def to_turkish(msg: str) -> str:
    """Kullanıcı mesajını komut eşleşmesi için Türkçe'ye çevirir (gerekirse)."""
    if get_lang() == "tr":
        return msg
    return _translate(msg, "tr")


def from_turkish(reply: str) -> str:
    """Bot cevabını kullanıcının diline çevirir (gerekirse)."""
    lang = get_lang()
    if lang == "tr":
        return reply
    return _translate(reply, lang)


def from_turkish_list(items: list) -> list:
    """Birden çok kısa metni (buton etiketleri) TEK AI çağrısıyla çevirir + önbellekler."""
    lang = get_lang()
    items = list(items)
    if lang == "tr" or not items or not _backend_usable():
        return items
    out = {}
    todo = []
    for t in items:
        if (lang, t) in _cache:
            out[t] = _cache[(lang, t)]
        elif t not in todo:
            todo.append(t)
    if todo:
        numbered = "\n".join(f"{i+1}. {t}" for i, t in enumerate(todo))
        try:
            ad = _DEST_AD.get(lang, lang)
            res = _ai(f"Translate each numbered line to {ad}. These are SHORT UI button "
                      "labels — keep them short (1-3 words). Keep the SAME numbering and "
                      "line count. Keep emojis where they are. NO markdown, NO asterisks, "
                      "no quotes. Output only the numbered lines.",
                      numbered)
            if any(m in res for m in _BAD_MARKERS):   # uyarı/hata → orijinali koru
                raise ValueError("çeviri yapılamadı")
            parsed = {}
            for l in res.splitlines():
                m = re.match(r"\s*(\d+)[.)]\s*(.+)", l.strip())
                if m:
                    lbl = re.sub(r"[*_`\"]", "", m.group(2)).strip()
                    parsed[int(m.group(1)) - 1] = lbl
            if len(parsed) == len(todo):
                for i, t in enumerate(todo):
                    tr = parsed.get(i, t)
                    out[t] = tr
                    if len(_cache) < 500:
                        _cache[(lang, t)] = tr
            else:
                raise ValueError("satır sayısı uyuşmadı")
        except Exception:
            for t in todo:
                out[t] = _translate(t, lang)
    return [out.get(t, t) for t in items]


def _ai(system: str, user: str) -> str:
    from .ai_skills import _ask_ai
    return _ask_ai(system, user) or user
