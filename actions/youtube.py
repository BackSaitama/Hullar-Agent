"""YouTube — video oynat veya arama yap."""

import re
import subprocess
import webbrowser
from urllib.parse import quote_plus

try:
    import requests  # type: ignore
    _REQ = True
except ImportError:
    _REQ = False

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "tr-TR,tr;q=0.9",
}
_VIDEO_FILTER = "EgIQAQ%3D%3D"


def _first_video_url(query: str) -> str | None:
    if not _REQ:
        return None
    try:
        url  = f"https://www.youtube.com/results?search_query={quote_plus(query)}&sp={_VIDEO_FILTER}"
        html = requests.get(url, headers=_HEADERS, timeout=10).text
        ids  = re.findall(r'"videoId":"([A-Za-z0-9_-]{11})"', html)
        seen: set[str] = set()
        for vid in ids:
            if vid in seen:
                continue
            seen.add(vid)
            if f"/shorts/{vid}" in html:
                continue
            return f"https://www.youtube.com/watch?v={vid}"
    except Exception:
        pass
    return None


def _play_first(query: str) -> str | None:
    """İlk videoyu AÇ ve OYNAT. Önce pywhatkit (en güvenilir), sonra kazıma."""
    # 1) pywhatkit.playonyt — ilk videoyu bulup tarayıcıda otomatik oynatır
    try:
        import pywhatkit  # type: ignore
        pywhatkit.playonyt(query)
        return f"Efendim, YouTube'da '{query}' açılıp oynatılıyor."
    except Exception:
        pass
    # 2) HTML kazıma ile ilk video bağlantısı
    url = _first_video_url(query)
    if url:
        webbrowser.open(url)
        return f"Efendim, '{query}' videosu açıldı."
    return None


def youtube(parameters: dict, **_) -> str:
    p      = parameters or {}
    action = p.get("action", "play").lower()
    query  = p.get("query", p.get("sorgu", "")).strip()

    if not query:
        webbrowser.open("https://www.youtube.com")
        return "Efendim, YouTube açıldı."

    if action == "play":
        msg = _play_first(query)
        if msg:
            return msg
        # Son çare: arama sayfası
        fallback = f"https://www.youtube.com/results?search_query={quote_plus(query)}&sp={_VIDEO_FILTER}"
        webbrowser.open(fallback)
        return f"Efendim, YouTube'da '{query}' araması açıldı."

    # Arama modu (açıkça arama istenmişse)
    webbrowser.open(f"https://www.youtube.com/results?search_query={quote_plus(query)}")
    return f"Efendim, YouTube'da '{query}' araması açıldı."
