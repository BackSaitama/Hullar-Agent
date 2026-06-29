"""
Ekran kaydı — ekranı belirli süre video (mp4) olarak kaydeder.
Telegram'a video gönderilir; canlı izlemeden farklı olarak akıcı oynar.
"""

from __future__ import annotations

import re
import time
from pathlib import Path

_OUT = Path(__file__).parent.parent / "data"


def record_screen(seconds: int = 8, fps: int = 10, scale: float = 0.6) -> str | None:
    """Ekranı kaydedip mp4 dosya yolunu döndürür."""
    try:
        import cv2          # type: ignore
        import numpy as np  # type: ignore
        import mss          # type: ignore
    except Exception:
        return None

    seconds = max(2, min(seconds, 60))
    _OUT.mkdir(parents=True, exist_ok=True)
    path = str(_OUT / f"kayit_{time.strftime('%Y%m%d_%H%M%S')}.mp4")
    try:
        with mss.mss() as sct:
            mon = sct.monitors[1]
            w = int(mon["width"] * scale) & ~1   # çift sayı (codec)
            h = int(mon["height"] * scale) & ~1
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            out = cv2.VideoWriter(path, fourcc, fps, (w, h))
            end = time.time() + seconds
            frame_dt = 1.0 / fps
            while time.time() < end:
                c0 = time.time()
                img = np.array(sct.grab(mon))               # BGRA
                frame = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
                frame = cv2.resize(frame, (w, h))
                out.write(frame)
                kalan = frame_dt - (time.time() - c0)
                if kalan > 0:
                    time.sleep(kalan)
            out.release()
        return path
    except Exception:
        return None


def ekran_kaydi(parameters: dict | None = None) -> str:
    """CMD/dispatcher action: kaydeder, yolu bildirir (Telegram'da video gönderilir)."""
    sec = int((parameters or {}).get("seconds", 8))
    path = record_screen(sec)
    if path:
        return f"🎥 Ekran kaydı ({sec} sn) hazır: {path}"
    return "Ekran kaydı yapılamadı (cv2/mss gerekli)."


def _extract_kayit(msg: str) -> dict:
    m = re.search(r"(\d+)\s*(?:saniye|sn|s)\b", msg, re.I)
    return {"seconds": int(m.group(1)) if m else 8}
