"""
JARVIS Proaktif Bildirim — PC'den SANA (Telegram push).

İş bitti, onay gerekiyor, uyarı var → Telegram'dan haber verir.
Token/chat_id'yi ortam değişkeninden veya data/telegram.json'dan okur.

Diğer modüllerden:
    from .notify import push
    push("İndirme tamamlandı ✅")
"""

import json
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

_CONFIG = Path(__file__).parent.parent / "data" / "telegram.json"


def _creds() -> tuple[str, str]:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat  = os.getenv("TELEGRAM_CHAT_ID", "")
    if (not token or not chat) and _CONFIG.exists():
        try:
            cfg = json.loads(_CONFIG.read_text(encoding="utf-8"))
            token = token or cfg.get("bot_token", "")
            chat  = chat  or str(cfg.get("chat_id", ""))
        except Exception as exc:
            logger.warning("telegram.json okunamadı: %s", exc)
    return token, chat


def push(text: str) -> bool:
    """Telegram'a mesaj gönderir. Başarılıysa True."""
    token, chat = _creds()
    if not token or not chat:
        logger.info("notify: token/chat_id yok, atlandı: %s", text[:50])
        return False
    try:
        import requests
        r = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat, "text": text},
            timeout=10,
        )
        return r.ok
    except Exception as exc:
        logger.warning("notify push hatası: %s", exc)
        return False


def bildirim_gonder(parameters: dict | None = None) -> str:
    """Dispatcher action: 'bana bildir: ...'"""
    text = (parameters or {}).get("text", "").strip()
    if not text:
        return "Efendim, ne bildireyim?"
    ok = push(text)
    return "📨 Telegram'a gönderildi." if ok else \
           "Efendim, Telegram bilgileri ayarlı değil (data/telegram.json)."


def _extract_notify(msg: str) -> dict:
    import re
    m = re.search(r"(?:bildir|haber ver|push)[:\s]+(.+)", msg, re.I)
    return {"text": m.group(1).strip() if m else ""}


# ── Akşam özeti (fikir: günü özetle + Telegram push) ──────────────────── #
def gunluk_ozet(parameters: dict | None = None) -> str:
    """O gün uzaktan gelen komutları + sistem durumunu özetleyip push eder.
    scheduler ile her akşam çalıştırılabilir."""
    lines = ["📊 Günlük Özet"]
    # Uzaktan komut sayısı
    try:
        from .remote_security import _LOG
        if _LOG.exists():
            from datetime import date
            today = date.today().strftime("%Y-%m-%d")
            cnt = sum(1 for l in _LOG.read_text(encoding="utf-8").splitlines()
                      if l.startswith(today))
            lines.append(f"• Uzaktan komut: {cnt}")
    except Exception:
        pass
    # Sistem durumu
    try:
        import psutil
        lines.append(f"• CPU: %{psutil.cpu_percent(interval=0.5):.0f}  "
                     f"RAM: %{psutil.virtual_memory().percent:.0f}")
        bat = psutil.sensors_battery()
        if bat:
            lines.append(f"• Pil: %{bat.percent:.0f}")
    except Exception:
        pass
    summary = "\n".join(lines)
    push(summary)
    return summary
