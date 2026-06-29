"""
JARVIS Uzaktan Kontrol — Güvenlik & Görev Kuyruğu.

Üç parça:
  1. Yetki kilidi   — yalnızca izinli chat_id komut verebilir (is_authorized)
  2. Komut logu     — uzaktan gelen her komut zaman damgalı kaydedilir (log_command)
  3. Görev kuyruğu  — dışarıdayken iş biriktir, sonra sırayla çalıştır
                      (gorev_ekle / gorevler / gorev_calistir)

Telegram listener'ında kullanım (öneri):
    from actions.remote_security import is_authorized, log_command
    if not is_authorized(update.chat_id):
        return "⛔ Yetkisiz."
    log_command(text, source="telegram", chat_id=update.chat_id)
"""

import json
import logging
import os
import re
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

_DATA = Path(__file__).parent.parent / "data"
_LOG = _DATA / "remote_commands.log"
_TASKS = _DATA / "task_queue.json"


# ── 1. Yetki kilidi ───────────────────────────────────────────────────── #
def _allowed_ids() -> set[str]:
    raw = os.getenv("TELEGRAM_ALLOWED_IDS", "")
    ids = {x.strip() for x in raw.split(",") if x.strip()}
    cfg = _DATA / "telegram.json"
    if cfg.exists():
        try:
            data = json.loads(cfg.read_text(encoding="utf-8"))
            if data.get("chat_id"):
                ids.add(str(data["chat_id"]))
            for x in data.get("allowed_ids", []):
                ids.add(str(x))
        except Exception:
            pass
    return ids


def is_authorized(chat_id) -> bool:
    """İzin listesi boşsa (kurulmamışsa) güvenli tarafta: True döner ama uyarır."""
    allowed = _allowed_ids()
    if not allowed:
        logger.warning("Yetki listesi boş — herkes komut verebilir! data/telegram.json ayarlayın.")
        return True
    return str(chat_id) in allowed


# ── Tehlikeli komut PIN'i (fikir) ─────────────────────────────────────── #
_DANGER = re.compile(
    r"\b(bilgisayarı kapat|shutdown|yeniden başlat|restart|format|"
    r"diski temizle|fabrika ayarları|tüm.*sil|hepsini sil)\b", re.I)


def _pin() -> str:
    pin = os.getenv("JARVIS_PIN", "")
    if not pin:
        cfg = _DATA / "telegram.json"
        if cfg.exists():
            try:
                pin = str(json.loads(cfg.read_text(encoding="utf-8")).get("pin", ""))
            except Exception:
                pass
    return pin


def tehlikeli_mi(text: str) -> bool:
    """Komut PIN gerektiren tehlikeli bir komut mu?"""
    return bool(_DANGER.search(text or ""))


def pin_dogru(girilen: str) -> bool:
    """Telegram listener'ı tehlikeli komuttan önce bunu çağırır.
    PIN ayarlı değilse True (eski davranış)."""
    pin = _pin()
    return True if not pin else str(girilen).strip() == pin


# ── 2. Komut logu ─────────────────────────────────────────────────────── #
def log_command(text: str, source: str = "telegram", chat_id="") -> None:
    try:
        _DATA.mkdir(exist_ok=True)
        line = f"{datetime.now():%Y-%m-%d %H:%M:%S}\t{source}\t{chat_id}\t{text}\n"
        with _LOG.open("a", encoding="utf-8") as f:
            f.write(line)
    except Exception as exc:
        logger.warning("Komut logu yazılamadı: %s", exc)


def komut_gecmisi(parameters: dict | None = None) -> str:
    """Son uzaktan komutları göster."""
    n = int((parameters or {}).get("n", 10))
    if not _LOG.exists():
        return "Efendim, uzaktan komut geçmişi boş."
    lines = _LOG.read_text(encoding="utf-8").strip().splitlines()[-n:]
    out = [f"• {l.split(chr(9))[0]} — {l.split(chr(9))[-1]}" for l in lines]
    return "🗒️ Son komutlar:\n" + "\n".join(out)


# ── 3. Görev kuyruğu ──────────────────────────────────────────────────── #
def _load_tasks() -> list[dict]:
    if _TASKS.exists():
        try:
            return json.loads(_TASKS.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


def _save_tasks(tasks: list[dict]) -> None:
    _DATA.mkdir(exist_ok=True)
    _TASKS.write_text(json.dumps(tasks, ensure_ascii=False, indent=2), encoding="utf-8")


def gorev_ekle(parameters: dict | None = None) -> str:
    """Dışarıdayken bir prompt/görevi kuyruğa ekle."""
    text = (parameters or {}).get("text", "").strip()
    if not text:
        return "Efendim, hangi görevi ekleyeyim?"
    tasks = _load_tasks()
    tasks.append({"text": text, "added": datetime.now().strftime("%H:%M")})
    _save_tasks(tasks)
    return f"➕ Görev eklendi (#{len(tasks)}): {text}"


def gorevler(parameters: dict | None = None) -> str:
    tasks = _load_tasks()
    if not tasks:
        return "Efendim, bekleyen görev yok."
    return "📋 Görev kuyruğu:\n" + "\n".join(
        f"#{i+1} — {t['text']} ({t.get('added','')})" for i, t in enumerate(tasks))


def gorev_calistir(parameters: dict | None = None) -> str:
    """
    Kuyruğun ilk görevini dispatcher+AI'a verip sonucu döndürür.
    AI/dispatcher döngüsünü kırmamak için lazy import.
    """
    tasks = _load_tasks()
    if not tasks:
        return "Efendim, çalıştırılacak görev yok."
    task = tasks.pop(0)
    _save_tasks(tasks)
    text = task["text"]
    try:
        from .dispatcher import ActionDispatcher
        result = ActionDispatcher().dispatch(text)
        if result is None:
            result = "(AI'a yönlendirildi — yanıt ana akıştan gelecek)"
    except Exception as exc:
        result = f"hata: {exc}"
    return f"▶️ Görev çalıştı: {text}\n→ {result}\n({len(tasks)} görev kaldı)"


# ── Parametre çıkarıcılar ─────────────────────────────────────────────── #
def _extract_task(msg: str) -> dict:
    import re
    m = re.search(r"(?:görev ekle|gorev ekle|kuyruğa ekle|sonra yap)[:\s]+(.+)", msg, re.I)
    return {"text": m.group(1).strip() if m else ""}
