"""Medya kontrolü: duraklat/oynat, sonraki/önceki, Spotify, ses ayarı."""

import subprocess
import time
import webbrowser

try:
    import pyautogui  # type: ignore
    pyautogui.PAUSE = 0.05
    _GUI = True
except ImportError:
    _GUI = False


def _media_key(key: str):
    if _GUI:
        pyautogui.press(key)
    else:
        # PowerShell WScript ile gönder
        key_map = {
            "playpause":        0xB3,
            "nexttrack":        0xB0,
            "prevtrack":        0xB1,
            "stop":             0xB2,
        }
        code = key_map.get(key)
        if code:
            subprocess.run(
                f'powershell -c "$wsh = New-Object -ComObject WScript.Shell; $wsh.SendKeys([char]{code})"',
                shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )


def media_play_pause(parameters: dict, **_) -> str:
    _media_key("playpause")
    return "Efendim, medya oynatma/duraklat."


def media_next(parameters: dict, **_) -> str:
    _media_key("nexttrack")
    return "Efendim, sonraki parçaya geçildi."


def media_prev(parameters: dict, **_) -> str:
    _media_key("prevtrack")
    return "Efendim, önceki parçaya geçildi."


def media_stop(parameters: dict, **_) -> str:
    _media_key("stop")
    return "Efendim, medya durduruldu."


def spotify_open(parameters: dict, **_) -> str:
    query = (parameters or {}).get("query", "").strip()
    # SADECE Spotify uygulaması (spotify: protokolü) — tarayıcı/web AÇMA
    if query:
        import urllib.parse
        uri = "spotify:search:" + urllib.parse.quote(query)
    else:
        uri = "spotify:"
    subprocess.Popen(f"start {uri}", shell=True,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return f"Efendim, Spotify {'`' + query + '` araması ile ' if query else ''}açıldı."


def open_radio(parameters: dict, **_) -> str:
    station = (parameters or {}).get("station", "").strip()
    stations = {
        "trt fm": "https://www.trtdinle.com/radyo/trt-fm",
        "kral fm": "https://www.kralfm.com.tr/",
        "power fm": "https://www.powertürk.com.tr/",
        "radyo d": "https://www.radyod.com/",
        "joy fm": "https://www.joytürk.com.tr/",
        "number one": "https://www.numberone.com.tr/",
    }
    key = station.lower()
    url = stations.get(key, f"https://www.google.com/search?q={station}+radyo+dinle")
    webbrowser.open(url)
    return f"Efendim, {station or 'radyo'} açıldı."


def open_podcast(parameters: dict, **_) -> str:
    query = (parameters or {}).get("query", "").strip()
    import urllib.parse
    url = f"https://open.spotify.com/search/{urllib.parse.quote(query + ' podcast')}" if query else "https://open.spotify.com/genre/podcasts-page"
    webbrowser.open(url)
    return f"Efendim, {'`' + query + '` ' if query else ''}podcast araması açıldı."
