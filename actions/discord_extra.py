"""
JARVIS Discord Skill'leri.

  9.  discord_durum — Discord'u öne getirir, durum menüsünü hazırlar
 10.  discord_mute  — Mikrofon/kulaklık aç-kapa (Discord varsayılan kısayolları)

Not: Mute (Ctrl+Shift+M) ve Deafen (Ctrl+Shift+D) Discord'un GLOBAL varsayılan
kısayollarıdır ve güvenilir çalışır. Durum (status) değişimi için sabit kısayol
yoktur; o yüzden discord_durum Discord'u öne getirip menüyü açar (yarı otomatik).
"""

import logging
import subprocess
import time

logger = logging.getLogger(__name__)


def _focus_discord() -> bool:
    try:
        import psutil
        for p in psutil.process_iter(["name"]):
            if (p.info["name"] or "").lower() == "discord.exe":
                break
        else:
            subprocess.Popen("cmd /c start discord:", shell=True)
            time.sleep(3)
        # Öne getir
        import pygetwindow as gw
        wins = [w for w in gw.getAllWindows() if "discord" in (w.title or "").lower()]
        if wins:
            try:
                wins[0].activate()
            except Exception:
                wins[0].minimize(); wins[0].restore()
            time.sleep(0.4)
            return True
    except Exception as exc:
        logger.warning("Discord odak hatası: %s", exc)
    return False


def discord_mute(parameters: dict | None = None) -> str:
    """Skill 10 — Mikrofon (mute) veya kulaklık (deafen) aç/kapa."""
    params = parameters or {}
    deafen = params.get("deafen", False)
    if not _focus_discord():
        return "Efendim, Discord penceresini bulamadım."
    try:
        import pyautogui
        combo = ["ctrl", "shift", "d" if deafen else "m"]
        pyautogui.hotkey(*combo)
        return ("🔇 Discord kulaklık (deafen) değiştirildi." if deafen
                else "🎙️ Discord mikrofon (mute) değiştirildi.")
    except Exception as exc:
        return f"Efendim, işlem başarısız: {exc}"


def discord_durum(parameters: dict | None = None) -> str:
    """Skill 9 — Discord'u öne getirir; durum menüsünü kullanıcıya bırakır."""
    durum = (parameters or {}).get("durum", "")
    if not _focus_discord():
        return "Efendim, Discord penceresini bulamadım."
    msg = "Efendim, Discord öne getirildi."
    if durum:
        msg += (f" '{durum}' durumuna geçmek için sol-alttaki profil "
                f"resmine tıklayın (sabit kısayolu yok).")
    return msg


def _extract_discord_mute(msg: str) -> dict:
    low = msg.lower()
    return {"deafen": any(k in low for k in ("kulaklık", "kulaklik", "deafen", "sağır", "sagir"))}


def _extract_discord_durum(msg: str) -> dict:
    low = msg.lower()
    for kw, val in [("meşgul", "Meşgul"), ("mesgul", "Meşgul"),
                    ("rahatsız", "Rahatsız Etme"), ("uzakta", "Boşta"),
                    ("boşta", "Boşta"), ("çevrimiçi", "Çevrimiçi"),
                    ("görünmez", "Görünmez")]:
        if kw in low:
            return {"durum": val}
    return {"durum": ""}
