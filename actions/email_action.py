"""
E-posta gönderme eylemi.
Varsayılan mail istemcini mailto: ile açar.
Composio/Gmail bağlandığında direkt gönderime geçer.
"""

import re
import urllib.parse
import webbrowser


def email_gonder(parameters: dict = None, **_) -> str:
    p       = parameters or {}
    alici   = p.get("alici", "").strip()
    konu    = p.get("konu", "").strip()
    icerik  = p.get("icerik", "").strip()

    if not alici:
        return "Efendim, e-postayı kime göndermemi istediğinizi belirtir misiniz?"

    # Gmail compose URL — mailto: yerine, her zaman çalışır
    base = "https://mail.google.com/mail/?view=cm&fs=1"
    base += f"&to={urllib.parse.quote(alici)}"
    if konu:
        base += f"&su={urllib.parse.quote(konu)}"
    if icerik:
        base += f"&body={urllib.parse.quote(icerik)}"

    webbrowser.open(base)

    msg = f"Efendim, '{alici}' adresine Gmail taslağı açıldı"
    if konu:
        msg += f" (konu: {konu})"
    msg += ". Göndermek için Gönder'e tıklayın."
    return msg


def _extract_email(msg: str) -> dict:
    """
    'ornek@gmail.com'e toplantı daveti maili gönder' gibi
    komutlardan alıcı, konu, içerik çıkarır.
    """
    # E-posta adresini bul
    email_m = re.search(r"[\w.+-]+@[\w-]+\.[a-zA-Z]{2,}", msg)
    alici   = email_m.group(0) if email_m else ""

    # Adresi mesajdan çıkar
    clean = msg
    if alici:
        clean = clean.replace(alici, "")

    # Konu ipuçlarını bul ("konu: X" veya "X maili/e-postası")
    konu = ""
    konu_m = re.search(
        r"\bkonu\b\s*[:\-]?\s*([^\n,;]+?)(?:\s*(?:gönder|at|yaz|mail|e-?posta)|$)",
        clean, re.I
    )
    if konu_m:
        konu = konu_m.group(1).strip()
    else:
        # "toplantı daveti maili" → konu = "toplantı daveti"
        icerik_m = re.search(
            r"([^\n,;]{3,40}?)\s+(?:mail[iı]?|e-?posta[sı]?)\s+(?:gönder|at|yaz)",
            clean, re.I
        )
        if icerik_m:
            konu = icerik_m.group(1).strip()

    # Dolgu kelimeleri temizle
    for kw in ("mail", "e-posta", "eposta", "gönder", "at", "yaz", "konu",
               "efendim", "lütfen", "bir", "'e", "'a", "'ye", "'ya"):
        konu = re.sub(rf"\b{re.escape(kw)}\b", "", konu, flags=re.I).strip()

    return {"alici": alici, "konu": konu, "icerik": ""}
