"""HULLAR batch3 — izleme, sistem, oyun, eğlence skilleri."""

from __future__ import annotations

import random
import re
import subprocess
import threading
import time
from pathlib import Path


def _push(text: str):
    try:
        from .notify import push
        push(text)
    except Exception:
        pass


# ── Klasör izle (yeni dosya gelince bildir) ───────────────────────────── #
_FOLDER = {"on": False}


def klasor_izle(parameters: dict | None = None) -> str:
    p = parameters or {}
    if p.get("action") == "stop":
        _FOLDER["on"] = False
        return "📂 Klasör izleme durduruldu."
    yol = (p.get("path") or "").strip().strip('"') or str(Path.home() / "Downloads")
    root = Path(yol)
    if not root.exists():
        return f"Klasör yok: {yol}"
    if _FOLDER.get("on"):
        return "Zaten bir klasör izleniyor."
    _FOLDER["on"] = True

    def _run():
        onceki = set(p.name for p in root.iterdir())
        while _FOLDER.get("on"):
            try:
                simdi = set(p.name for p in root.iterdir())
                yeni = simdi - onceki
                for f in yeni:
                    _push(f"📂 Yeni dosya: {f}  ({root.name})")
                onceki = simdi
            except Exception:
                pass
            time.sleep(5)

    threading.Thread(target=_run, daemon=True).start()
    return f"📂 '{root.name}' izleniyor — yeni dosya gelince haber veririm. Durdur: 'klasör izlemeyi durdur'."


def _extract_klasor(msg: str) -> dict:
    if any(w in msg.lower() for w in ("durdur", "bırak", "iptal")):
        return {"action": "stop"}
    m = re.search(r"([A-Za-z]:\\[^\n]+)", msg)
    return {"path": m.group(1).strip().strip('"') if m else ""}


# ── Kaynak uyarısı (CPU/RAM yüksekse) ─────────────────────────────────── #
_KAYNAK = {"on": False}


def kaynak_uyari(parameters: dict | None = None) -> str:
    p = parameters or {}
    if p.get("action") == "stop":
        _KAYNAK["on"] = False
        return "📈 Kaynak uyarısı durduruldu."
    esik = int(p.get("esik", 90))
    if _KAYNAK.get("on"):
        return "Kaynak uyarısı zaten açık."
    _KAYNAK["on"] = True

    def _run():
        import psutil
        uyarildi = False
        while _KAYNAK.get("on"):
            try:
                cpu = psutil.cpu_percent(interval=1)
                ram = psutil.virtual_memory().percent
                if (cpu >= esik or ram >= esik) and not uyarildi:
                    _push(f"⚠️ Yüksek yük! CPU %{cpu:.0f}, RAM %{ram:.0f}")
                    uyarildi = True
                elif cpu < esik - 15 and ram < esik - 15:
                    uyarildi = False
            except Exception:
                pass
            time.sleep(10)

    threading.Thread(target=_run, daemon=True).start()
    return f"📈 Kaynak uyarısı açık — CPU/RAM %{esik} olunca haber veririm. Durdur: 'kaynak uyarısı durdur'."


def _extract_kaynak(msg: str) -> dict:
    if any(w in msg.lower() for w in ("durdur", "bırak", "iptal")):
        return {"action": "stop"}
    m = re.search(r"%?\s*(\d{2})", msg)
    return {"esik": int(m.group(1)) if m else 90}


# ── Disk dolu uyarısı ─────────────────────────────────────────────────── #
def disk_dolu_uyari(parameters: dict | None = None) -> str:
    try:
        import psutil
        uyari = []
        for part in psutil.disk_partitions():
            try:
                u = psutil.disk_usage(part.mountpoint)
                if u.percent >= 90:
                    uyari.append(f"{part.device} %{u.percent} dolu ({u.free//(1024**3)}GB boş)")
            except Exception:
                continue
        if uyari:
            return "⚠️ Disk doluyor:\n" + "\n".join(uyari)
        return "✅ Diskler rahat (hepsi %90 altında)."
    except Exception as exc:
        return f"Disk kontrol edilemedi: {exc}"


# ── Desen tıklayıcı (sağ-sol değişimli) ───────────────────────────────── #
_DESEN = {"on": False}


def desen_tikla(parameters: dict | None = None) -> str:
    p = parameters or {}
    if p.get("action") == "stop":
        _DESEN["on"] = False
        return "🖱️ Desen tıklayıcı durduruldu."
    interval = float(p.get("interval", 0.5))
    if _DESEN.get("on"):
        return "Zaten çalışıyor. 'desen durdur' de."
    _DESEN["on"] = True

    def _run():
        try:
            import pyautogui as g  # type: ignore
            g.FAILSAFE = True
            while _DESEN.get("on"):
                g.click(button="left")
                time.sleep(interval)
                g.click(button="right")
                time.sleep(interval)
        except Exception:
            pass
        _DESEN["on"] = False

    threading.Thread(target=_run, daemon=True).start()
    return f"🖱️ Sol-sağ değişimli tıklama başladı ({interval}s). Durdur: 'desen durdur' (veya imleç sol-üst köşe)."


def _extract_desen(msg: str) -> dict:
    if any(w in msg.lower() for w in ("durdur", "dur", "kapat", "stop")):
        return {"action": "stop"}
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:saniye|sn)", msg, re.I)
    return {"interval": float(m.group(1).replace(",", ".")) if m else 0.5}


# ── Akıllı anti-AFK (rastgele küçük hareket) ──────────────────────────── #
_AFK2 = {"on": False}


def akilli_afk(parameters: dict | None = None) -> str:
    p = parameters or {}
    if p.get("action") == "stop":
        _AFK2["on"] = False
        return "🚶 Akıllı AFK durduruldu."
    if _AFK2.get("on"):
        return "Zaten açık."
    _AFK2["on"] = True

    def _run():
        try:
            import pyautogui as g  # type: ignore
            while _AFK2.get("on"):
                time.sleep(random.randint(30, 60))
                if not _AFK2.get("on"):
                    break
                dx, dy = random.randint(-40, 40), random.randint(-40, 40)
                g.moveRel(dx, dy, duration=0.3)
                g.moveRel(-dx, -dy, duration=0.3)
                if random.random() < 0.3:
                    g.press("shift")
        except Exception:
            pass

    threading.Thread(target=_run, daemon=True).start()
    return "🚶 Akıllı AFK açık — rastgele küçük hareketlerle aktif kalır. Durdur: 'akıllı afk durdur'."


def _extract_afk2(msg: str) -> dict:
    return {"action": "stop"} if any(w in msg.lower() for w in ("durdur", "kapat", "dur")) else {}


# ── Açık pencere/sekme sayısı ─────────────────────────────────────────── #
def acik_pencere_sayisi(parameters: dict | None = None) -> str:
    try:
        import pygetwindow as gw  # type: ignore
        titles = [t for t in gw.getAllTitles() if t.strip()]
        return f"🪟 {len(titles)} açık pencere var."
    except Exception as exc:
        return f"Sayılamadı: {exc}"


# ── Hangi program internet kullanıyor ─────────────────────────────────── #
def net_kullanan(parameters: dict | None = None) -> str:
    try:
        import psutil
        from collections import Counter
        sayac = Counter()
        for c in psutil.net_connections(kind="inet"):
            if c.status == "ESTABLISHED" and c.pid:
                try:
                    sayac[psutil.Process(c.pid).name()] += 1
                except Exception:
                    pass
        if not sayac:
            return "Aktif internet bağlantısı yok."
        top = sayac.most_common(8)
        return "🌐 İnternet kullananlar:\n" + "\n".join(f"• {n}: {c} bağlantı" for n, c in top)
    except Exception as exc:
        return f"Alınamadı: {exc}"


# ── Hızlı temizlik (temp + çöp + cache) ───────────────────────────────── #
def hizli_temizlik(parameters: dict | None = None) -> str:
    yapilan = []
    try:
        subprocess.run('del /q /s "%TEMP%\\*"', shell=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        yapilan.append("temp")
    except Exception:
        pass
    try:
        subprocess.run('powershell -NoProfile -Command "Clear-RecycleBin -Force -ErrorAction SilentlyContinue"',
                       shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        yapilan.append("çöp kutusu")
    except Exception:
        pass
    try:
        cache = Path.home() / "AppData/Local/Google/Chrome/User Data/Default/Cache"
        if cache.exists():
            subprocess.run(f'del /q /s "{cache}\\*"', shell=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            yapilan.append("chrome cache")
    except Exception:
        pass
    return "🧹 Temizlendi: " + (", ".join(yapilan) if yapilan else "bir şey yok") + "."


# ── Rastgele seç / karar ver ──────────────────────────────────────────── #
def rastgele_sec(parameters: dict | None = None) -> str:
    secenekler = (parameters or {}).get("secenekler", [])
    if not secenekler:
        return "Seçenek ver: 'rastgele seç pizza, burger, döner'"
    return f"🎯 Seçimim: {random.choice(secenekler)}"


def _extract_rastgele(msg: str) -> dict:
    m = re.search(r"(?:seç|karar ver|çek|hangisi)\s*[:\-]?\s*(.+)", msg, re.I)
    raw = m.group(1) if m else ""
    parts = [s.strip() for s in re.split(r"[,/]| ya da | veya | yoksa ", raw) if s.strip()]
    return {"secenekler": parts}
