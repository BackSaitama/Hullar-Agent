"""
HULLAR görüntü skilleri (cv2).

  • qr_oku       : ekrandaki QR kodu çözer (link/metin döndürür)
  • yuz_algila   : webcam'de yüz var mı kontrol eder (kaç kişi)
"""

from __future__ import annotations


def _grab_rgb():
    import numpy as np  # type: ignore
    import mss          # type: ignore
    with mss.mss() as sct:
        mon = sct.monitors[1]
        img = np.array(sct.grab(mon))[:, :, :3]   # BGRA→BGR
    return img


# ── QR oku (ekrandan) ─────────────────────────────────────────────────── #
def qr_oku(parameters: dict | None = None) -> str:
    try:
        import cv2  # type: ignore
        img = _grab_rgb()
        det = cv2.QRCodeDetector()
        data, pts, _ = det.detectAndDecode(img)
        if data:
            return f"🔳 QR çözüldü:\n{data}"
        # Çoklu QR dene
        ok, datas, _, _ = det.detectAndDecodeMulti(img)
        if ok and datas:
            return "🔳 QR(lar):\n" + "\n".join(d for d in datas if d)
        return "Ekranda QR kod bulamadım. QR net görünür olsun."
    except Exception as exc:
        return f"QR okunamadı: {exc}"


# ── Yüz algıla (webcam) ───────────────────────────────────────────────── #
def yuz_algila(parameters: dict | None = None) -> str:
    try:
        import cv2  # type: ignore
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if not cap.isOpened():
            cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            return "Kameraya erişemedim."
        for _ in range(5):
            cap.read()
        ok, frame = cap.read()
        cap.release()
        if not ok or frame is None:
            return "Kameradan görüntü alınamadı."
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        casc = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
        faces = casc.detectMultiScale(gray, 1.1, 5)
        n = len(faces)
        if n == 0:
            return "👤 Kamerada yüz görünmüyor (kimse yok)."
        return f"👤 Kamerada {n} yüz algılandı."
    except Exception as exc:
        return f"Yüz algılanamadı: {exc}"
