"""Web araması — önce tarayıcıda aç, isteğe bağlı Gemini/DDG özet."""

import webbrowser
from urllib.parse import quote_plus


def web_search(parameters: dict, **_) -> str:
    p     = parameters or {}
    query = p.get("query", p.get("sorgu", "")).strip()
    mode  = p.get("mode", "open").lower()   # "open" | "summary"

    if not query:
        return "Efendim, ne aramamı istersiniz?"

    if query.startswith("http://") or query.startswith("https://"):
        webbrowser.open(query)
        return f"Efendim, {query} adresi açıldı."

    url = f"https://www.google.com/search?q={quote_plus(query)}"
    webbrowser.open(url)
    return f"Efendim, '{query}' için Google araması açıldı."
