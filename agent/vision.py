"""
Vision katmanı — screenshot + OCR + UI element algılama.
Gemini vision ile görsel karar; pytesseract ile metin/koordinat.
"""

import logging
import os
import tempfile
import time
from pathlib import Path

logger = logging.getLogger(__name__)


def _setup_tesseract():
    """Tesseract binary'sini bul + Türkçe dil paketini (yerel tessdata) tanıt."""
    try:
        import pytesseract
    except ImportError:
        return
    candidates = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Tesseract-OCR", "tesseract.exe"),
    ]
    for p in candidates:
        if os.path.exists(p):
            pytesseract.pytesseract.tesseract_cmd = p
            break
    # Yerel tessdata (tur+eng) klasörünü TESSDATA_PREFIX olarak ayarla
    local_td = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "tessdata")
    if os.path.exists(os.path.join(local_td, "tur.traineddata")):
        os.environ["TESSDATA_PREFIX"] = local_td


_setup_tesseract()


def _ocr_lang() -> str:
    """Kurulu dillere göre en iyi OCR dilini seç (tur+eng > eng)."""
    try:
        import pytesseract
        langs = pytesseract.get_languages()
        if "tur" in langs and "eng" in langs:
            return "tur+eng"
        if "tur" in langs:
            return "tur"
        return "eng"
    except Exception:
        return "eng"


_OCR_LANG = _ocr_lang()


class Vision:
    def __init__(self, llm=None):
        self._llm = llm

    # ── Ekran görüntüsü al ────────────────────────────────────────────── #
    def screenshot(self, region=None) -> str:
        """Ekranı kaydeder, dosya yolu döndürür."""
        path = Path(tempfile.gettempdir()) / f"jarvis_screen_{int(time.time()*1000)}.png"
        try:
            import pyautogui
            img = pyautogui.screenshot(region=region)
            img.save(str(path))
            return str(path)
        except Exception:
            from PIL import ImageGrab
            img = ImageGrab.grab(bbox=region)
            img.save(str(path))
            return str(path)

    # ── Gemini ile ekranı anla ────────────────────────────────────────── #
    def analyze(self, question: str) -> str:
        """Ekranı al, LLM'e sor. Vision yoksa OCR metnine düşer."""
        if self._llm:
            shot = self.screenshot()
            ans = self._llm.ask_vision(question, shot)
            self._cleanup(shot)
            if ans and ans.strip():
                return ans
        # Vision çalışmadı → OCR ile ekrandaki metni döndür
        text = self.read_text()
        if text:
            return f"[Ekrandaki metin]\n{text[:2000]}"
        return "Ekran okunamadı."

    # ── Element konumu bul (Gemini koordinat) ─────────────────────────── #
    def locate(self, element_desc: str) -> tuple[int, int] | None:
        """
        'Gönder butonu', 'arama kutusu' gibi bir elementin
        ekran koordinatını (x, y) döndürür.
        """
        if not self._llm:
            return self._locate_ocr(element_desc)

        import pyautogui
        w, h = pyautogui.size()
        shot = self.screenshot()
        prompt = (
            f"Bu {w}x{h} ekran görüntüsünde '{element_desc}' nerede? "
            f"SADECE merkez koordinatını JSON ver: {{\"x\": <piksel>, \"y\": <piksel>}}. "
            f"Bulamazsan {{\"x\": -1, \"y\": -1}}."
        )
        data = self._llm.ask_json(prompt, image_path=shot)
        self._cleanup(shot)
        x, y = data.get("x", -1), data.get("y", -1)
        if x >= 0 and y >= 0:
            return (int(x), int(y))
        return self._locate_ocr(element_desc)

    # ── OCR ile metin konumu (yedek) ──────────────────────────────────── #
    def _locate_ocr(self, text: str) -> tuple[int, int] | None:
        try:
            import pytesseract, pyautogui
            from pytesseract import Output
            img = pyautogui.screenshot()
            data = pytesseract.image_to_data(img, lang=_OCR_LANG, output_type=Output.DICT)
            tl = text.lower()
            for i, word in enumerate(data["text"]):
                if word and tl in word.lower() and int(data["conf"][i]) > 30:
                    x = data["left"][i] + data["width"][i] // 2
                    y = data["top"][i] + data["height"][i] // 2
                    return (x, y)
        except Exception as exc:
            logger.debug("OCR locate hata: %s", exc)
        return None

    # ── Ekrandaki tüm metni oku ───────────────────────────────────────── #
    def read_text(self, region=None) -> str:
        try:
            import pytesseract, pyautogui
            img = pyautogui.screenshot(region=region)
            return pytesseract.image_to_string(img, lang=_OCR_LANG).strip()
        except Exception as exc:
            logger.debug("OCR read hata: %s", exc)
            return ""

    @staticmethod
    def _cleanup(path: str):
        try:
            Path(path).unlink(missing_ok=True)
        except Exception:
            pass
