"""Hızlı araçlar: QR kod, pano, birim çevirme, renk kodu, metin temizle."""

import os
import re
import subprocess
import webbrowser
from pathlib import Path


def qr_generate(parameters: dict, **_) -> str:
    text = (parameters or {}).get("text", parameters.get("metin", "")).strip()
    if not text:
        return "Efendim, QR koda çevrilecek metni belirtir misiniz?"
    try:
        import qrcode  # type: ignore
        from datetime import datetime
        img      = qrcode.make(text)
        out_path = Path.home() / "Desktop" / f"qr_{datetime.now().strftime('%H%M%S')}.png"
        img.save(str(out_path))
        os.startfile(str(out_path))
        return f"Efendim, QR kod oluşturuldu: {out_path}"
    except ImportError:
        url = f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={text}"
        webbrowser.open(url)
        return "Efendim, QR kod tarayıcıda açıldı."


def clipboard_read(parameters: dict, **_) -> str:
    try:
        import pyperclip  # type: ignore
        text = pyperclip.paste()
        return f"Efendim, panodaki metin:\n{text[:500]}" if text else "Efendim, pano boş."
    except Exception:
        out = subprocess.run(
            'powershell -c "Get-Clipboard"',
            shell=True, capture_output=True, text=True,
        ).stdout.strip()
        return f"Efendim, panodaki metin: {out}" if out else "Efendim, pano boş."


def clipboard_write(parameters: dict, **_) -> str:
    text = (parameters or {}).get("text", parameters.get("metin", "")).strip()
    if not text:
        return "Efendim, panoya kopyalanacak metni belirtir misiniz?"
    try:
        import pyperclip  # type: ignore
        pyperclip.copy(text)
    except Exception:
        subprocess.run(
            f'powershell -c "Set-Clipboard -Value \'{text}\'"',
            shell=True, stdout=subprocess.DEVNULL,
        )
    return "Efendim, metin panoya kopyalandı."


def unit_convert(parameters: dict, **_) -> str:
    value  = float((parameters or {}).get("value", 0))
    from_u = (parameters or {}).get("from", "").lower().strip()
    to_u   = (parameters or {}).get("to", "").lower().strip()

    conversions = {
        ("km",  "mil"):   lambda v: v * 0.621371,
        ("mil", "km"):    lambda v: v * 1.60934,
        ("kg",  "pound"): lambda v: v * 2.20462,
        ("pound","kg"):   lambda v: v * 0.453592,
        ("m",   "ft"):    lambda v: v * 3.28084,
        ("ft",  "m"):     lambda v: v * 0.3048,
        ("c",   "f"):     lambda v: v * 9/5 + 32,
        ("f",   "c"):     lambda v: (v - 32) * 5/9,
        ("l",   "galon"): lambda v: v * 0.264172,
        ("galon","l"):    lambda v: v * 3.78541,
        ("cm",  "inch"):  lambda v: v * 0.393701,
        ("inch","cm"):    lambda v: v * 2.54,
        ("gb",  "mb"):    lambda v: v * 1024,
        ("mb",  "gb"):    lambda v: v / 1024,
    }

    key = (from_u, to_u)
    if key in conversions:
        result = conversions[key](value)
        return f"Efendim, {value} {from_u} = {result:.4f} {to_u}"

    # Google'da açılacak
    url = f"https://www.google.com/search?q={value}+{from_u}+to+{to_u}"
    webbrowser.open(url)
    return f"Efendim, {value} {from_u} → {to_u} dönüşümü Google'da açıldı."


def color_info(parameters: dict, **_) -> str:
    color = (parameters or {}).get("color", parameters.get("renk", "")).strip()
    if not color:
        return "Efendim, renk adı veya HEX kodu belirtir misiniz?"
    url = f"https://www.google.com/search?q={color}+color+hex+rgb"
    webbrowser.open(url)
    return f"Efendim, '{color}' renk bilgisi açıldı."


def ascii_art(parameters: dict, **_) -> str:
    text = (parameters or {}).get("text", "JARVIS").strip()[:20]
    try:
        import pyfiglet  # type: ignore
        art = pyfiglet.figlet_format(text, font="slant")
        return art
    except ImportError:
        return f"  ★ {text} ★"


def text_reverse(parameters: dict, **_) -> str:
    text = (parameters or {}).get("text", "").strip()
    return f"Efendim: {text[::-1]}" if text else "Efendim, metin belirtir misiniz?"


def text_upper(parameters: dict, **_) -> str:
    text = (parameters or {}).get("text", "").strip()
    return text.upper() if text else "Efendim, metin belirtir misiniz?"


def text_lower(parameters: dict, **_) -> str:
    text = (parameters or {}).get("text", "").strip()
    return text.lower() if text else "Efendim, metin belirtir misiniz?"


def encoding_base64(parameters: dict, **_) -> str:
    import base64
    text   = (parameters or {}).get("text", "").strip()
    decode = (parameters or {}).get("decode", False)
    if not text:
        return "Efendim, metni belirtir misiniz?"
    if decode:
        result = base64.b64decode(text).decode("utf-8", errors="replace")
        return f"Efendim, çözülen metin: {result}"
    result = base64.b64encode(text.encode()).decode()
    return f"Efendim, Base64: {result}"


def hash_text(parameters: dict, **_) -> str:
    import hashlib
    text      = (parameters or {}).get("text", "").strip()
    algorithm = (parameters or {}).get("algorithm", "sha256").lower()
    if not text:
        return "Efendim, hash'lenecek metni belirtir misiniz?"
    h = hashlib.new(algorithm, text.encode(), usedforsecurity=False)
    return f"Efendim, {algorithm.upper()}: {h.hexdigest()}"
