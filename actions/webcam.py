"""Webcam — kameradan tek kare fotoğraf çeker (cv2)."""

from __future__ import annotations

import time
from pathlib import Path


def capture_photo() -> str | None:
    """Varsayılan kameradan bir foto çeker, kaydedip dosya yolunu döndürür.
    Kamera yoksa/erişilemezse None."""
    try:
        import cv2  # type: ignore
    except Exception:
        return None

    cap = None
    try:
        # Windows'ta DSHOW backend daha hızlı/güvenilir açılır
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if not cap.isOpened():
            cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            return None

        # Kamera ışık dengesi için birkaç kare ısınma
        for _ in range(5):
            cap.read()
            time.sleep(0.05)

        ok, frame = cap.read()
        if not ok or frame is None:
            return None

        ts = time.strftime("%Y%m%d_%H%M%S")
        dest = Path.home() / "Desktop" / "hullar" / "data"
        dest.mkdir(parents=True, exist_ok=True)
        path = str(dest / f"webcam_{ts}.jpg")
        cv2.imwrite(path, frame)
        return path
    except Exception:
        return None
    finally:
        if cap is not None:
            cap.release()


def webcam_action(parameters: dict | None = None) -> str:
    """Dispatcher/CLI action: foto çeker, yolu metin olarak bildirir."""
    path = capture_photo()
    if path:
        return f"📷 Webcam fotoğrafı çekildi: {path}"
    return "Efendim, kameraya erişemedim (bağlı değil veya kullanımda olabilir)."
