"""
JARVIS Oyun & Mod Skill'leri.

  1. oyun_hazirlik  — Oyun öncesi: yüksek performans + RAM boşalt + dikkat dağıtanları kapat
  5. steam_guncelle — Steam indirme/güncelleme ekranını aç
 50. mod_degistir   — Bağlam değiştirici: "oyun moduna geç" / "iş moduna geç"
"""

import logging
import os
import subprocess
import webbrowser

logger = logging.getLogger(__name__)

# Oyun modunda kapatılacak dikkat dağıtıcılar (yalnızca varsa kapatılır)
_DISTRACTORS = ["chrome", "msedge", "firefox", "OneDrive", "Spotify"]
# İş modunda açılacak uygulamalar
_WORK_APPS   = ["Code", "notepad"]


def _run(cmd: str) -> None:
    subprocess.run(cmd, shell=True, capture_output=True)


def _empty_working_set() -> int:
    """Boştaki working-set'i serbest bırak; etkilenen süreç sayısı döner."""
    try:
        import ctypes
        import psutil
        psapi = ctypes.WinDLL("psapi.dll")
        n = 0
        for p in psutil.process_iter(["pid"]):
            try:
                h = ctypes.windll.kernel32.OpenProcess(0x1F0FFF, False, p.info["pid"])
                if h:
                    psapi.EmptyWorkingSet(h)
                    ctypes.windll.kernel32.CloseHandle(h)
                    n += 1
            except Exception:
                continue
        return n
    except Exception as exc:
        logger.warning("RAM boşaltma atlandı: %s", exc)
        return 0


def _close_apps(names: list[str]) -> list[str]:
    closed = []
    try:
        import psutil
        for p in psutil.process_iter(["name"]):
            base = (p.info["name"] or "").rsplit(".", 1)[0].lower()
            if base in [n.lower() for n in names]:
                try:
                    p.terminate()
                    closed.append(p.info["name"])
                except Exception:
                    pass
    except Exception as exc:
        logger.warning("Uygulama kapatma atlandı: %s", exc)
    return closed


def oyun_hazirlik(parameters: dict | None = None) -> str:
    """Skill 1 — Oyun öncesi hazırlık ritüeli."""
    _run("powercfg /setactive SCHEME_MIN")          # Yüksek performans
    freed  = _empty_working_set()
    closed = _close_apps(_DISTRACTORS)
    parts = ["⚡ Yüksek performans açık"]
    if freed:
        parts.append(f"🧹 {freed} süreçte RAM boşaltıldı")
    if closed:
        parts.append(f"❌ Kapatıldı: {', '.join(set(closed))}")
    return "🎮 Oyun moduna hazır.\n" + "\n".join(parts)


def steam_guncelle(parameters: dict | None = None) -> str:
    """Skill 5 — Steam indirme/güncelleme ekranını aç."""
    try:
        webbrowser.open("steam://open/downloads")
        return "Efendim, Steam indirme/güncelleme ekranı açıldı."
    except Exception as exc:
        return f"Efendim, Steam açılamadı: {exc}"


def mod_degistir(parameters: dict | None = None) -> str:
    """Skill 50 — Bağlam değiştirici."""
    mod = (parameters or {}).get("mod", "oyun")
    if mod == "oyun":
        return oyun_hazirlik()
    # İş modu
    _run("powercfg /setactive SCHEME_BALANCED")
    closed = _close_apps(["steam", "EpicGamesLauncher", "RobloxPlayerBeta", "Discord"])
    opened = []
    for app in _WORK_APPS:
        try:
            subprocess.Popen(app, shell=True)
            opened.append(app)
        except Exception:
            pass
    msg = ["💼 İş moduna geçildi.", "🔋 Dengeli güç planı"]
    if closed:
        msg.append(f"❌ Kapatıldı: {', '.join(set(closed))}")
    if opened:
        msg.append(f"✅ Açıldı: {', '.join(opened)}")
    return "\n".join(msg)


# ── Parametre çıkarıcılar ─────────────────────────────────────────────── #
def _extract_mod(msg: str) -> dict:
    low = msg.lower()
    if any(k in low for k in ("iş mod", "is mod", "çalışma mod", "calisma mod", "work mode")):
        return {"mod": "is"}
    return {"mod": "oyun"}
