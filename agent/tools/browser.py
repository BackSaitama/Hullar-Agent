"""Web/tarayıcı araçları."""

import time
import urllib.parse
import webbrowser


def open_url(ctx, url: str) -> str:
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    webbrowser.open(url)
    time.sleep(2)
    return f"Açıldı: {url}"


def web_search(ctx, query: str) -> str:
    url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
    webbrowser.open(url)
    time.sleep(2)
    return f"Google arama: {query}"


def youtube(ctx, query: str = "") -> str:
    if query:
        url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}"
    else:
        url = "https://www.youtube.com"
    webbrowser.open(url)
    time.sleep(2)
    return f"YouTube: {query or 'ana sayfa'}"


def read_screen(ctx, question: str = "Ekranda ne var?") -> str:
    """Mevcut ekranı görsel olarak analiz eder (tarayıcı/uygulama içeriği)."""
    result = ctx.vision.analyze(question)
    if result and hasattr(ctx, "scratch"):
        ctx.scratch["last_read"] = result
    return result


def register(box):
    box.add("open_url", "Tarayıcıda bir URL açar",
            {"url": "adres"}, open_url)
    box.add("web_search", "Google'da arama yapar",
            {"query": "arama terimi"}, web_search)
    box.add("youtube", "YouTube açar/arar",
            {"query": "arama (boş=ana sayfa)"}, youtube)
    box.add("read_screen", "Mevcut ekranı görsel analiz eder, ne olduğunu okur",
            {"question": "ne sorulacak"}, read_screen)
