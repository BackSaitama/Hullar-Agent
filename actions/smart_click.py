"""
Akıllı tıklama (OCR) — ekrandaki YAZIYA bakarak tıklar.

"ekranda Popeyes'e tıkla"  → ekranı okur, 'Popeyes' yazısını bulur, ortasına tıklar.
Koordinat bilmene gerek yok. Tesseract OCR kullanır (offline).

Vision-LLM'den daha güvenilir: butonların/menülerin ÜZERİNDEKİ metni okur.
"""

from __future__ import annotations

import re
from pathlib import Path

# Tesseract binary yolu (kurulu konum)
_TESS_CANDIDATES = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    str(Path.home() / "AppData" / "Local" / "Programs" / "Tesseract-OCR" / "tesseract.exe"),
]


def _ensure_tesseract() -> bool:
    try:
        import pytesseract  # type: ignore
    except Exception:
        return False
    for c in _TESS_CANDIDATES:
        if Path(c).exists():
            pytesseract.pytesseract.tesseract_cmd = c
            return True
    # PATH'te olabilir
    return True


def _grab_screen():
    """Tüm ekranı PIL Image olarak alır."""
    try:
        import mss  # type: ignore
        from PIL import Image  # type: ignore
        with mss.mss() as sct:
            mon = sct.monitors[1]
            shot = sct.grab(mon)
            img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
            return img, mon["left"], mon["top"]
    except Exception:
        try:
            import pyautogui  # type: ignore
            return pyautogui.screenshot(), 0, 0
        except Exception:
            return None, 0, 0


def find_text_on_screen(target: str) -> tuple[int, int] | None:
    """Hedef metni ekranda bulur, merkez koordinatını (x, y) döndürür."""
    if not _ensure_tesseract():
        return None
    img, ox, oy = _grab_screen()
    if img is None:
        return None
    try:
        import pytesseract  # type: ignore
        from pytesseract import Output  # type: ignore
        # Türkçe + İngilizce dene, yoksa varsayılan
        try:
            data = pytesseract.image_to_data(img, lang="tur+eng", output_type=Output.DICT)
        except Exception:
            data = pytesseract.image_to_data(img, output_type=Output.DICT)
    except Exception:
        return None

    target_l = target.lower().strip()
    words = data.get("text", [])
    n = len(words)

    # 1) Tek kelime tam/kısmi eşleşme
    best = None
    for i in range(n):
        w = (words[i] or "").strip().lower()
        if not w:
            continue
        try:
            conf = float(data["conf"][i])
        except Exception:
            conf = 0
        if conf < 40:
            continue
        # Çift yönlü kısmi eşleşme: "popeyes" ↔ "popeyese" (ekli) ikisi de tutar
        if target_l == w or (len(target_l) >= 3 and (target_l in w or w in target_l)):
            cx = data["left"][i] + data["width"][i] // 2 + ox
            cy = data["top"][i] + data["height"][i] // 2 + oy
            return (cx, cy)

    # 2) Çok kelimeli hedef → ardışık kelimeleri birleştirip ara
    parts = target_l.split()
    if len(parts) > 1:
        joined = []
        for i in range(n):
            w = (words[i] or "").strip().lower()
            joined.append((w, i))
        text_seq = [w for w, _ in joined]
        for i in range(n - len(parts) + 1):
            window = text_seq[i:i + len(parts)]
            if all(parts[k] in window[k] for k in range(len(parts)) if window[k]):
                idx = i
                cx = data["left"][idx] + data["width"][idx] // 2 + ox
                cy = data["top"][idx] + data["height"][idx] // 2 + oy
                return (cx, cy)
    return best


def smart_click(parameters: dict | None = None) -> str:
    p = parameters or {}
    target = (p.get("target") or "").strip()
    if not target:
        return "Efendim, neye tıklayayım? (örn: 'ekranda Giriş Yap'a tıkla')"
    pos = find_text_on_screen(target)
    if not pos:
        return (f"'{target}' yazısını ekranda bulamadım. "
                f"Görünür ve net yazılı olduğundan emin ol, ya da koordinatla "
                f"tıkla ('500 300'e tıkla').")
    try:
        import pyautogui  # type: ignore
        pyautogui.click(pos[0], pos[1])
        return f"🎯 '{target}' bulundu ({pos[0]},{pos[1]}) ve tıklandı."
    except Exception as exc:
        return f"Tıklama hatası: {exc}"


def _extract_smart_click(msg: str) -> dict:
    """'ekranda Popeyes'e tıkla', 'Giriş Yap butonuna bas' → target çıkarır."""
    t = msg
    # Çevresel kelimeleri temizle
    t = re.sub(r"\b(ekranda|ekrandaki|şu|su|olan|yazısına|yazına|butonuna|"
               r"buton|tuşuna|linkine|yazan|metnine)\b", " ", t, flags=re.I)
    t = re.sub(r"\b(tıkla|tikla|bas|bastır|seç|sec|aç|git)\b", " ", t, flags=re.I)
    # Sondaki ekleri at: "Popeyes'e" → "Popeyes"
    t = re.sub(r"'(?:y?[ae]|n[ae]|den|dan)\b", " ", t)
    target = re.sub(r"\s+", " ", t).strip(" .,;:'\"-")
    return {"target": target}
