"""
JARVIS Onay Kuyruğu — uzaktan (Telegram) onay sistemi.

Amaç: Sen dışarıdayken Hermes riskli/geri alınamaz bir işi DOĞRUDAN yapmaz;
önce kuyruğa koyar ve sana sorar. Sen Telegram'dan "onayla" / "iptal" dersin.

Akış:
    Kullanıcı: "Ahmet'e whatsapp at: geç kalacağım"
        → ilgili skill request_approval(...) ile kuyruğa ekler
        → JARVIS: "⏳ Onay bekliyor (#1): Ahmet'e WhatsApp... 'onayla' de."
    Kullanıcı: "onayla"
        → kuyruktaki iş çalışır, sonucu döner.

Diğer skill'lerden kullanım:
    from .approval import request_approval
    return request_approval(
        desc="Ahmet'e WhatsApp: 'geç kalacağım'",
        action=lambda: whatsapp_send(parameters={...}),
    )

Dispatcher'a eklenecek kurallar dosyanın en altındadır.
"""

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Callable

logger = logging.getLogger(__name__)

# ── Ayarlar ───────────────────────────────────────────────────────────── #
_MAX_QUEUE   = 20          # kuyrukta en fazla bekleyen iş
_EXPIRE_SEC  = 1800        # 30 dk sonra otomatik düşer (eski onaylar tehlikeli)


@dataclass
class _Pending:
    id: int
    desc: str
    action: Callable[[], str]
    created: float = field(default_factory=time.time)

    @property
    def expired(self) -> bool:
        return (time.time() - self.created) > _EXPIRE_SEC

    @property
    def age_str(self) -> str:
        m = int((time.time() - self.created) // 60)
        return "az önce" if m == 0 else f"{m} dk önce"


# ── Global kuyruk (thread-safe) ───────────────────────────────────────── #
_QUEUE: list[_Pending] = []
_LOCK = threading.Lock()
_COUNTER = 0


def _purge_expired() -> None:
    """Süresi dolmuş onayları sessizce at."""
    global _QUEUE
    _QUEUE = [p for p in _QUEUE if not p.expired]


# ══════════════════════════════════════════════════════════════════════════ #
#  Diğer skill'lerin çağırdığı giriş noktası                                #
# ══════════════════════════════════════════════════════════════════════════ #
def request_approval(desc: str, action: Callable[[], str]) -> str:
    """
    Bir işi onay kuyruğuna ekler ve kullanıcıya soru metni döndürür.
    `action`: onaylanınca çağrılacak, string döndüren parametresiz fonksiyon.
    """
    global _COUNTER
    with _LOCK:
        _purge_expired()
        if len(_QUEUE) >= _MAX_QUEUE:
            return "Efendim, onay kuyruğu dolu. Önce bekleyenleri onaylayın/iptal edin."
        _COUNTER += 1
        item = _Pending(id=_COUNTER, desc=desc, action=action)
        _QUEUE.append(item)
        bekleyen = len(_QUEUE)

    extra = f" ({bekleyen} iş bekliyor)" if bekleyen > 1 else ""
    logger.info("Onay kuyruğa eklendi #%s: %s", item.id, desc)
    return (f"⏳ Onay bekliyor (#{item.id}): {desc}\n"
            f"Onaylamak için 'onayla', iptal için 'iptal' deyin.{extra}")


# ══════════════════════════════════════════════════════════════════════════ #
#  Dispatcher action'ları                                                    #
# ══════════════════════════════════════════════════════════════════════════ #
def bekleyenler(parameters: dict | None = None) -> str:
    """Onay bekleyen işleri listeler."""
    with _LOCK:
        _purge_expired()
        if not _QUEUE:
            return "Efendim, onay bekleyen iş yok."
        lines = [f"#{p.id} — {p.desc} ({p.age_str})" for p in _QUEUE]
    return "⏳ Onay bekleyenler:\n" + "\n".join(lines)


def onayla(parameters: dict | None = None) -> str:
    """
    Belirtilen (veya en eski) işi onaylar ve çalıştırır.
    parameters: {"id": int | None, "all": bool}
    """
    params = parameters or {}
    with _LOCK:
        _purge_expired()
        if not _QUEUE:
            return "Efendim, onaylanacak iş yok."

        if params.get("all"):
            items = _QUEUE[:]
            _QUEUE.clear()
        elif params.get("id"):
            items = [p for p in _QUEUE if p.id == params["id"]]
            if not items:
                return f"Efendim, #{params['id']} numaralı bekleyen iş bulamadım."
            _QUEUE.remove(items[0])
        else:
            items = [_QUEUE.pop(0)]   # en eski

    results = []
    for item in items:
        try:
            logger.info("Onaylandı #%s: %s", item.id, item.desc)
            results.append(f"✅ #{item.id}: " + (item.action() or "tamamlandı"))
        except Exception as exc:
            logger.error("Onaylı iş hatası #%s: %s", item.id, exc)
            results.append(f"❌ #{item.id} hata: {exc}")
    return "\n".join(results)


def iptal(parameters: dict | None = None) -> str:
    """
    Belirtilen (veya en eski) işi iptal eder.
    parameters: {"id": int | None, "all": bool}
    """
    params = parameters or {}
    with _LOCK:
        _purge_expired()
        if not _QUEUE:
            return "Efendim, iptal edilecek iş yok."

        if params.get("all"):
            n = len(_QUEUE)
            _QUEUE.clear()
            return f"🗑️ {n} bekleyen iş iptal edildi."
        if params.get("id"):
            before = len(_QUEUE)
            _QUEUE[:] = [p for p in _QUEUE if p.id != params["id"]]
            if len(_QUEUE) == before:
                return f"Efendim, #{params['id']} numaralı iş bulunamadı."
            return f"🗑️ #{params['id']} iptal edildi."
        item = _QUEUE.pop(0)
    return f"🗑️ #{item.id} iptal edildi: {item.desc}"


# ── Parametre çıkarıcılar (dispatcher için) ───────────────────────────── #
def _extract_approve(msg: str) -> dict:
    import re
    if re.search(r"\b(hepsini|tümünü|hepsi|tumunu)\b", msg, re.I):
        return {"all": True}
    m = re.search(r"#?(\d+)", msg)
    return {"id": int(m.group(1))} if m else {}


# ── Dispatcher'a EKLENECEK kurallar (referans) ────────────────────────── #
# from .approval import bekleyenler, onayla, iptal, _extract_approve
#
#     ([r"\b(onay bekleyen|bekleyen işler|onay kuyruğu|ne bekliyor|pending)\b"],
#      bekleyenler, lambda _: {}),
#
#     ([r"\b(onayla|onaylıyorum|kabul|tamam yap|evet yap|approve|onay ver)\b"],
#      onayla, _extract_approve),
#
#     ([r"\b(iptal|vazgeç|reddet|yapma|cancel|hayır iptal)\b"],
#      iptal, _extract_approve),
