"""
Fare kontrolü — imleci taşı, tıkla, çift tıkla, sağ tıkla, sürükle (pyautogui).

Komutlar:
  "500 300'e tıkla"            → o koordinata sol tık
  "fareyi 800 400'e götür"     → imleci taşı (tıklamadan)
  "çift tıkla"                 → bulunduğu yerde çift tık
  "sağ tıkla"                  → sağ tık
  "fare nerede"                → imlecin koordinatı
  "300 200'den 600 500'e sürükle"
"""

from __future__ import annotations

import re

try:
    import pyautogui  # type: ignore
    pyautogui.FAILSAFE = True   # imleç sol-üst köşe → acil dur
    pyautogui.PAUSE = 0.02
    _GUI = True
except Exception:
    _GUI = False


def _coords(msg: str):
    """Mesajdaki ilk iki sayıyı (x, y) olarak döndürür."""
    nums = re.findall(r"-?\d+", msg)
    if len(nums) >= 2:
        return int(nums[0]), int(nums[1])
    return None


def mouse_click(parameters: dict | None = None) -> str:
    if not _GUI:
        return "Efendim, pyautogui gerekiyor."
    p = parameters or {}
    x, y = p.get("x"), p.get("y")
    button = p.get("button", "left")
    clicks = int(p.get("clicks", 1))
    try:
        if x is not None and y is not None:
            pyautogui.click(x=int(x), y=int(y), clicks=clicks, button=button)
            yer = f"({x},{y})"
        else:
            pyautogui.click(clicks=clicks, button=button)
            yer = "bulunduğu yer"
        tip = {"left": "sol", "right": "sağ", "middle": "orta"}.get(button, button)
        kez = "çift " if clicks == 2 else ""
        return f"🖱️ {yer} {tip} {kez}tıklandı."
    except Exception as exc:
        return f"Tıklama hatası: {exc}"


def mouse_move(parameters: dict | None = None) -> str:
    if not _GUI:
        return "Efendim, pyautogui gerekiyor."
    p = parameters or {}
    x, y = p.get("x"), p.get("y")
    if x is None or y is None:
        return "Efendim, nereye? (örn: 'fareyi 800 400'e götür')"
    try:
        pyautogui.moveTo(int(x), int(y), duration=0.2)
        return f"🖱️ İmleç ({x},{y}) konumuna taşındı."
    except Exception as exc:
        return f"Taşıma hatası: {exc}"


def mouse_drag(parameters: dict | None = None) -> str:
    if not _GUI:
        return "Efendim, pyautogui gerekiyor."
    p = parameters or {}
    x1, y1, x2, y2 = p.get("x1"), p.get("y1"), p.get("x2"), p.get("y2")
    if None in (x1, y1, x2, y2):
        return "Efendim, 'X1 Y1'den X2 Y2'ye sürükle' şeklinde söyle."
    try:
        pyautogui.moveTo(int(x1), int(y1))
        pyautogui.dragTo(int(x2), int(y2), duration=0.4, button="left")
        return f"🖱️ ({x1},{y1}) → ({x2},{y2}) sürüklendi."
    except Exception as exc:
        return f"Sürükleme hatası: {exc}"


def mouse_position(parameters: dict | None = None) -> str:
    if not _GUI:
        return "Efendim, pyautogui gerekiyor."
    x, y = pyautogui.position()
    return f"🖱️ İmleç şu an: ({x}, {y})"


# ── Extractor'lar ─────────────────────────────────────────────────────── #
def _extract_click(msg: str) -> dict:
    low = msg.lower()
    button = "right" if ("sağ" in low or "sag" in low) else \
             ("middle" if "orta" in low else "left")
    clicks = 2 if ("çift" in low or "cift" in low or "double" in low) else 1
    out = {"button": button, "clicks": clicks}
    c = _coords(msg)
    if c:
        out["x"], out["y"] = c
    return out


def _extract_move(msg: str) -> dict:
    c = _coords(msg)
    return {"x": c[0], "y": c[1]} if c else {}


def _extract_drag(msg: str) -> dict:
    nums = re.findall(r"-?\d+", msg)
    if len(nums) >= 4:
        return {"x1": int(nums[0]), "y1": int(nums[1]),
                "x2": int(nums[2]), "y2": int(nums[3])}
    return {}
