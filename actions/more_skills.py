"""
HULLAR ek skiller (toplu).

  • bu_ne            : ekrandaki içeriği OCR + AI ile yorumlar ("bu ne?")
  • zamanli_tekrar   : "her 5 dk şunu yap" — komutu periyodik çalıştırır
  • watchdog         : "chrome kapanırsa aç" — süreç ölünce yeniden başlatır
  • ram_temizle      : çalışan süreçlerin working set'ini boşaltır (RAM optimize)
  • ses_cihazi       : ses çıkış cihazı seçici / ayarları açar
"""

from __future__ import annotations

import logging
import re
import subprocess
import threading
import time

logger = logging.getLogger("hullar.more")


def _push(text: str):
    try:
        from .notify import push
        push(text)
    except Exception:
        pass


# ── AI: ekranda ne var, bu ne? ────────────────────────────────────────── #
def bu_ne(parameters: dict | None = None) -> str:
    try:
        from .power_skills import ekran_oku
        raw = ekran_oku()
    except Exception as exc:
        return f"Ekran okunamadı: {exc}"
    if not raw.startswith("📖"):
        return raw
    metin = raw.replace("📖 Ekrandaki yazı:\n", "")
    try:
        from .ai_skills import _ask_ai
        cevap = _ask_ai(
            "Sen bir asistansın. Kullanıcı ekranında ne olduğunu merak ediyor. "
            "Verilen ekran metnine bakarak ne olduğunu Türkçe, kısa ve net açıkla "
            "(hangi uygulama/site, ne yapılıyor).",
            f"Ekran metni:\n{metin[:3000]}",
        )
        return f"🔎 Ekranda: {cevap}"
    except Exception as exc:
        return f"Yorumlanamadı: {exc}"


# ── Zamanlı tekrar: her N dk bir komut ────────────────────────────────── #
_REPEAT = {"on": False}


def zamanli_tekrar(parameters: dict | None = None) -> str:
    p = parameters or {}
    if p.get("action") == "stop":
        _REPEAT["on"] = False
        return "🔁 Zamanlı tekrar durduruldu."
    komut = (p.get("komut") or "").strip()
    interval = int(p.get("interval", 300))
    if not komut:
        return "Örnek: 'her 5 dakika ekran görüntüsü al'"
    if _REPEAT.get("on"):
        return "Zaten bir zamanlı tekrar çalışıyor. 'tekrarı durdur' de."
    interval = max(10, min(interval, 86400))
    _REPEAT["on"] = True

    def _run():
        from actions import ActionDispatcher
        d = ActionDispatcher()
        while _REPEAT.get("on"):
            time.sleep(interval)
            if not _REPEAT.get("on"):
                break
            try:
                r = d.dispatch(komut)
                if r:
                    _push(f"🔁 {r[:300]}")
            except Exception as exc:
                logger.warning("zamanli_tekrar hatası: %s", exc)

    threading.Thread(target=_run, daemon=True).start()
    dk = interval // 60
    return f"🔁 Her {dk if dk else interval} {'dk' if dk else 'sn'}'de bir: '{komut}'. Durdur: 'tekrarı durdur'."


def _extract_tekrar(msg: str) -> dict:
    low = msg.lower()
    if any(w in low for w in ("durdur", "iptal", "kapat")) and "tekrar" in low:
        return {"action": "stop"}
    interval = 300
    h = re.search(r"(\d+)\s*saat", low)
    m = re.search(r"(\d+)\s*(dakika|dk)", low)
    s = re.search(r"(\d+)\s*(saniye|sn)", low)
    if h:
        interval = int(h.group(1)) * 3600
    elif m:
        interval = int(m.group(1)) * 60
    elif s:
        interval = int(s.group(1))
    # komutu ayıkla: "her N dk/saat <komut>"
    komut = re.sub(r"\bher\b|\b\d+\s*(saat|dakika|dk|saniye|sn)\b|\bbir\b|\bde\b",
                   " ", msg, flags=re.I)
    komut = re.sub(r"\s+", " ", komut).strip(" .,:-")
    return {"komut": komut, "interval": interval}


# ── Watchdog: uygulama kapanırsa yeniden aç ───────────────────────────── #
_WATCH = {"on": False}


def watchdog(parameters: dict | None = None) -> str:
    p = parameters or {}
    if p.get("action") == "stop":
        _WATCH["on"] = False
        return "🐕 Watchdog durduruldu."
    app = (p.get("app") or "").strip().lower()
    if not app:
        return "Hangi uygulama? Örn: 'chrome kapanırsa aç'"
    exe = app if app.endswith(".exe") else app + ".exe"
    if _WATCH.get("on"):
        return "Zaten bir watchdog çalışıyor. 'watchdog durdur' de."
    _WATCH["on"] = True

    def _run():
        import psutil
        while _WATCH.get("on"):
            try:
                alive = any(exe in (pr.info["name"] or "").lower()
                            for pr in psutil.process_iter(["name"]))
                if not alive:
                    subprocess.Popen(f"start {app}", shell=True)
                    _push(f"🐕 {app} kapanmıştı, yeniden açtım.")
                    time.sleep(15)
            except Exception:
                pass
            time.sleep(8)

    threading.Thread(target=_run, daemon=True).start()
    return f"🐕 Watchdog açık — '{app}' kapanırsa otomatik açacağım. Durdur: 'watchdog durdur'."


def _extract_watchdog(msg: str) -> dict:
    low = msg.lower()
    if any(w in low for w in ("durdur", "iptal", "kapat")) and "watchdog" in low:
        return {"action": "stop"}
    m = re.search(r"\b([\w\.]+)\s*(?:kapan[ıi]rsa|kapanırsa|giderse|çökerse)", low)
    if not m:
        m = re.search(r"watchdog\s+([\w\.]+)", low)
    return {"app": m.group(1) if m else ""}


# ── RAM temizle (working set boşalt) ──────────────────────────────────── #
def ram_temizle(parameters: dict | None = None) -> str:
    try:
        import ctypes
        import psutil
        before = psutil.virtual_memory().available
        psapi = ctypes.WinDLL("psapi")
        kernel32 = ctypes.WinDLL("kernel32")
        PROCESS_SET_QUOTA = 0x0100
        PROCESS_QUERY_INFORMATION = 0x0400
        n = 0
        for pr in psutil.process_iter(["pid"]):
            try:
                h = kernel32.OpenProcess(PROCESS_SET_QUOTA | PROCESS_QUERY_INFORMATION,
                                         False, pr.info["pid"])
                if h:
                    if psapi.EmptyWorkingSet(h):
                        n += 1
                    kernel32.CloseHandle(h)
            except Exception:
                continue
        after = psutil.virtual_memory().available
        freed = max(0, (after - before)) // (1024 * 1024)
        pct = psutil.virtual_memory().percent
        return f"🧹 RAM temizlendi ({n} işlem). ~{freed} MB boşaldı. Doluluk: %{pct}."
    except Exception as exc:
        return f"RAM temizlenemedi: {exc}"


# ── Ses çıkış cihazı (seçici aç) ──────────────────────────────────────── #
def ses_cihazi(parameters: dict | None = None) -> str:
    try:
        # Modern ses çıkış seçiciyi/ayarları aç (nircmd olmadan en güvenli yol)
        subprocess.Popen("start ms-settings:sound", shell=True)
        return ("🔈 Ses ayarları açıldı — çıkış cihazını (kulaklık/hoparlör) "
                "oradan seçebilirsin.")
    except Exception as exc:
        return f"Ses ayarları açılamadı: {exc}"
