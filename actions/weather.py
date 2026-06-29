"""Hava durumu — Google'da şehir araması açar."""

import webbrowser
from urllib.parse import quote_plus


def weather_action(parameters: dict, **_) -> str:
    p    = parameters or {}
    city = p.get("city", p.get("sehir", p.get("şehir", ""))).strip()
    when = p.get("time", p.get("zaman", "bugün")).strip() or "bugün"

    if not city:
        return "Efendim, hangi şehrin hava durumunu görmek istersiniz?"

    query = f"{city} hava durumu {when}"
    webbrowser.open(f"https://www.google.com/search?q={quote_plus(query)}")
    return f"Efendim, {city} için {when} hava durumu açıldı."
