"""
HULLAR — Beyin (orkestratör).

Akış (token-dostu):
  1. ActionDispatcher.dispatch(msg)  → 140+ regex kuralı, AI HARCAMAZ.
     Eşleşirse sonucu döndür. (En ucuz yol — çoğu komut buraya düşer.)
  2. Eşleşme yoksa dispatcher zaten LLM router + self-code teklifini dener.
  3. O da None dönerse → _ask_ai ile sohbet/soru cevabı.
     Sistem promptuna skill indeksi gömülür (model ne yapabildiğini bilir).

Tek genel arayüz:
    from hullar.brain import Hullar
    h = Hullar()
    cevap = h.handle("masaüstündeki dosyaları listele")
"""

from __future__ import annotations

import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# ── jarvis kökünü path'e ekle (actions paketi için) ───────────────────── #
_JARVIS_ROOT = Path(__file__).parent.parent
if str(_JARVIS_ROOT) not in sys.path:
    sys.path.insert(0, str(_JARVIS_ROOT))

# .env yükle
try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv(_JARVIS_ROOT / ".env")
except Exception:
    pass

from actions import ActionDispatcher          # noqa: E402
from actions.ai_skills import _ask_ai          # noqa: E402
from hullar import skills                       # noqa: E402

logger = logging.getLogger("hullar.brain")

_NAME = "Hullar"


def _system_prompt() -> str:
    """Skill-farkında, token-dengeli sistem promptu."""
    now = datetime.now().strftime("%d %B %Y, %A %H:%M")
    index = skills.build_index()
    rules = skills.load_rules()

    return (
        f"Sen {_NAME}'sın — bu Windows bilgisayarını kontrol eden kişisel asistan. "
        f"Tarih: {now}.\n\n"
        f"## EN ÖNEMLİ KURAL: KISA KONUŞ\n"
        f"- Cevapların EN FAZLA 1-2 cümle olsun. Asla uzun paragraf yazma.\n"
        f"- Net ve direkt ol. Gereksiz açıklama, giriş, 'umarım yardımcı olur' yok.\n"
        f"- Bir işi yaptıysan tek cümleyle 'oldu' de; yapamadıysan tek cümleyle nedenini söyle.\n"
        f"- Emin değilsen kısa bir soru sor, uzun uzun varsayım yapma.\n\n"
        f"Bilgisayarı kontrol edebilirsin (uygulama, dosya, sistem, medya, otomasyon). "
        f"Somut komutlar zaten otomatik çalışır; sen kısa sohbet ve karar verirsin. "
        f"'Bilgisayara erişemem' ASLA deme.\n\n"
        f"## Yeteneklerin (özet)\n{index[:1500]}"
    )


class Hullar:
    """Telegram ve CMD arayüzlerinin paylaştığı tek beyin."""

    def __init__(self):
        self._dispatcher = ActionDispatcher()
        self._sys_prompt = _system_prompt()
        logger.info("Hullar hazır — %d skill indekslendi.", skills.count())

    def handle(self, message: str) -> str:
        """Bir kullanıcı mesajını işler, metin cevap döndürür."""
        message = (message or "").strip()
        if not message:
            return "Efendim?"

        # 1) Kural motoru + (gerekirse) router/self-code — AI harcamadan
        try:
            result = self._dispatcher.dispatch(message)
        except Exception as exc:
            logger.error("dispatch hatası: %s", exc)
            result = None

        if result is not None:
            return result

        # 2) Hiçbir araç yok → AI sohbet/soru cevabı
        try:
            return _ask_ai(self._sys_prompt, message)
        except Exception as exc:
            logger.error("AI hatası: %s", exc)
            return f"Efendim, şu an cevap veremedim: {exc}"
