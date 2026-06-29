"""
JARVIS Spotify Mood (Skill 16).

Ruh haline / aktiviteye göre uygun Spotify çalma listesini açar.
Spotify URI/derin link kullanır — güvenilir, ekran otomasyonu gerekmez.
"""

import logging
import webbrowser

logger = logging.getLogger(__name__)

# mood anahtarı → (etiket, Spotify arama sorgusu)
_MOODS = {
    "calisma":  ("Çalışma / Odak", "focus"),
    "oyun":     ("Oyun / Gaming",  "gaming"),
    "uyku":     ("Uyku / Sakin",   "sleep"),
    "spor":     ("Spor / Workout",  "workout"),
    "mutlu":    ("Mutlu / Enerji",  "happy"),
    "sakin":    ("Sakin / Lofi",    "lofi chill"),
    "parti":    ("Parti",           "party"),
    "yol":      ("Yolculuk",        "road trip"),
}


def spotify_mood(parameters: dict | None = None) -> str:
    """parameters: {"mood": "calisma"|...}"""
    mood = (parameters or {}).get("mood", "calisma")
    label, query = _MOODS.get(mood, _MOODS["calisma"])
    try:
        # Spotify uygulamasında arama aç (uygulama yoksa web'e düşer)
        webbrowser.open(f"spotify:search:{query.replace(' ', '%20')}")
        return f"🎵 Spotify '{label}' müzikleri açıldı. Üstteki çalma listesinden birini seçin."
    except Exception as exc:
        return f"Efendim, Spotify açılamadı: {exc}"


def _extract_mood(msg: str) -> dict:
    low = msg.lower()
    table = [
        (("çalış", "calis", "odak", "focus", "ders"), "calisma"),
        (("oyun", "gaming", "game"),                   "oyun"),
        (("uyku", "uyu", "sleep", "gece"),             "uyku"),
        (("spor", "workout", "antren", "koşu", "kosu"),"spor"),
        (("mutlu", "enerji", "happy", "neşe"),         "mutlu"),
        (("sakin", "lofi", "chill", "rahat"),          "sakin"),
        (("parti", "party", "dans"),                   "parti"),
        (("yol", "araba", "sürüş", "surus", "road"),   "yol"),
    ]
    for keys, mood in table:
        if any(k in low for k in keys):
            return {"mood": mood}
    return {"mood": "calisma"}
