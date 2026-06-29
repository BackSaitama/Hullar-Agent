"""Web araçları: çeviri, harita, wiki, haber, döviz, kelime tanımı, kısalt URL."""

import urllib.parse
import webbrowser


def translate_text(parameters: dict, **_) -> str:
    text   = (parameters or {}).get("text", "").strip()
    target = (parameters or {}).get("target", "tr").strip()
    source = (parameters or {}).get("source", "auto").strip()
    if not text:
        return "Efendim, çevrilecek metni belirtir misiniz?"
    url = f"https://translate.google.com/?sl={source}&tl={target}&text={urllib.parse.quote(text)}&op=translate"
    webbrowser.open(url)
    return f"Efendim, Google Çeviri açıldı."


def maps_open(parameters: dict, **_) -> str:
    location = (parameters or {}).get("location", parameters.get("konum", "")).strip()
    if not location:
        return "Efendim, nereyi aramak istediğinizi belirtir misiniz?"
    url = f"https://www.google.com/maps/search/{urllib.parse.quote(location)}"
    webbrowser.open(url)
    return f"Efendim, '{location}' Google Harita'da açıldı."


def wikipedia_search(parameters: dict, **_) -> str:
    """Wikipedia REST API ile özet çek; bulunamazsa tarayıcıda aç."""
    import urllib.request
    import json

    query = (parameters or {}).get("query", parameters.get("sorgu", "")).strip()
    lang  = (parameters or {}).get("lang", "tr")
    if not query:
        return "Efendim, Wikipedia'da ne aramak istersiniz?"

    def _fetch_summary(q: str, lg: str) -> str | None:
        """Wikipedia REST summary API — özet metni döner ya da None."""
        try:
            encoded = urllib.parse.quote(q.replace(" ", "_"))
            api_url = f"https://{lg}.wikipedia.org/api/rest_v1/page/summary/{encoded}"
            req = urllib.request.Request(api_url, headers={"User-Agent": "JARVIS/1.0"})
            with urllib.request.urlopen(req, timeout=6) as resp:
                data = json.loads(resp.read())
                return data.get("extract", "")
        except Exception:
            return None

    def _search_and_fetch(q: str, lg: str) -> str | None:
        """Arama API ile en iyi sonucu bul, özetini döner."""
        try:
            search_url = (
                f"https://{lg}.wikipedia.org/w/api.php"
                f"?action=query&list=search&srsearch={urllib.parse.quote(q)}"
                f"&utf8=1&format=json&srlimit=1"
            )
            req = urllib.request.Request(search_url, headers={"User-Agent": "JARVIS/1.0"})
            with urllib.request.urlopen(req, timeout=6) as resp:
                data = json.loads(resp.read())
                results = data.get("query", {}).get("search", [])
                if results:
                    title = results[0]["title"]
                    return _fetch_summary(title, lg)
        except Exception:
            return None
        return None

    # Önce Türkçe dene
    summary = _fetch_summary(query, "tr") or _search_and_fetch(query, "tr")

    # Türkçe bulunamazsa İngilizce'yi Türkçe'ye çevirerek sun
    if not summary:
        en_summary = _fetch_summary(query, "en") or _search_and_fetch(query, "en")
        if en_summary:
            summary = en_summary
            lang = "en"

    if summary:
        # Çok uzunsa kırp
        text = summary[:600].rstrip()
        if len(summary) > 600:
            text += "..."
        src = "tr.wikipedia.org" if lang == "tr" else "en.wikipedia.org"
        return f"Efendim, Wikipedia ({src}):\n\n{text}"

    # Hiçbir şey bulunamazsa tarayıcıya düş
    url = f"https://tr.wikipedia.org/wiki/Special:Search?search={urllib.parse.quote(query)}"
    webbrowser.open(url)
    return f"Efendim, '{query}' için Wikipedia'da sonuç bulunamadı. Tarayıcıda açıldı."


def news_open(parameters: dict, **_) -> str:
    topic = (parameters or {}).get("topic", parameters.get("konu", "")).strip()
    if topic:
        url = f"https://news.google.com/search?q={urllib.parse.quote(topic)}&hl=tr"
    else:
        url = "https://news.google.com/?hl=tr"
    webbrowser.open(url)
    return f"Efendim, {'`' + topic + '` haberler' if topic else 'haberler'} açıldı."


def currency_info(parameters: dict, **_) -> str:
    amount = (parameters or {}).get("amount", "1")
    source = (parameters or {}).get("from", "USD").upper()
    target = (parameters or {}).get("to",   "TRY").upper()
    query  = f"{amount} {source} to {target}"
    url    = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
    webbrowser.open(url)
    return f"Efendim, {query} döviz çevirisi açıldı."


def define_word(parameters: dict, **_) -> str:
    word = (parameters or {}).get("word", parameters.get("kelime", "")).strip()
    if not word:
        return "Efendim, tanımını öğrenmek istediğiniz kelimeyi belirtir misiniz?"
    url = f"https://sozluk.gov.tr/?q={urllib.parse.quote(word)}"
    webbrowser.open(url)
    return f"Efendim, '{word}' TDK sözlüğünde açıldı."


def open_url(parameters: dict, **_) -> str:
    url = (parameters or {}).get("url", parameters.get("adres", "")).strip()
    if not url:
        return "Efendim, açılacak adresi belirtir misiniz?"
    if not url.startswith("http"):
        url = "https://" + url
    webbrowser.open(url)
    return f"Efendim, {url} açıldı."


def image_search(parameters: dict, **_) -> str:
    query = (parameters or {}).get("query", parameters.get("sorgu", "")).strip()
    if not query:
        return "Efendim, ne aramak istediğinizi belirtir misiniz?"
    url = f"https://www.google.com/search?tbm=isch&q={urllib.parse.quote(query)}"
    webbrowser.open(url)
    return f"Efendim, '{query}' için Google Görseller açıldı."


def flight_search(parameters: dict, **_) -> str:
    origin = (parameters or {}).get("from", parameters.get("nereden", "")).strip()
    dest   = (parameters or {}).get("to",   parameters.get("nereye", "")).strip()
    date   = (parameters or {}).get("date", "").strip()
    if not origin or not dest:
        return "Efendim, kalkış ve varış noktalarını belirtir misiniz?"
    q = f"uçuş {origin} {dest} {date}".strip()
    url = f"https://www.google.com/travel/flights?q={urllib.parse.quote(q)}"
    webbrowser.open(url)
    return f"Efendim, {origin} → {dest} uçuş araması açıldı."


def shopping_search(parameters: dict, **_) -> str:
    query = (parameters or {}).get("query", parameters.get("urun", "")).strip()
    if not query:
        return "Efendim, aranacak ürünü belirtir misiniz?"
    url = f"https://www.trendyol.com/sr?q={urllib.parse.quote(query)}"
    webbrowser.open(url)
    return f"Efendim, '{query}' için Trendyol araması açıldı."
