"""Salad — GPU kazanç platformu kontrolü."""

import os
import subprocess
import webbrowser

_SALAD_PATHS = [
    r"C:\Program Files\Salad\Salad.exe",
    os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Salad", "Salad.exe"),
    os.path.join(os.environ.get("LOCALAPPDATA", ""), "Salad Technologies", "Salad", "Salad.exe"),
    r"C:\Program Files\Salad Technologies\Salad\Salad.exe",
]


def _find_salad() -> str | None:
    for p in _SALAD_PATHS:
        if os.path.exists(p):
            return p
    # Masaüstünde kısayol ara
    desktop = os.path.join(os.environ.get("USERPROFILE", ""), "Desktop")
    if os.path.exists(desktop):
        for f in os.listdir(desktop):
            if "salad" in f.lower() and f.endswith((".lnk", ".exe")):
                return os.path.join(desktop, f)
    return None


def salad_ac(parameters: dict = None, **_) -> str:
    path = _find_salad()
    if path:
        try:
            if path.endswith(".lnk"):
                subprocess.Popen(["start", "", path], shell=True)
            else:
                subprocess.Popen([path])
            return "Efendim, Salad başlatıldı. GPU ile kazanç başlıyor."
        except Exception as exc:
            return f"Salad başlatılamadı: {exc}"
    # Bulunamazsa web'den indir
    webbrowser.open("https://salad.com")
    return "Efendim, Salad kurulu görünmüyor. İndirme sayfası açıldı."


def salad_kapat(parameters: dict = None, **_) -> str:
    try:
        result = subprocess.run(
            ["taskkill", "/f", "/im", "Salad.exe"],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            return "Efendim, Salad durduruldu."
        return "Efendim, Salad zaten çalışmıyor veya kapatılamadı."
    except Exception as exc:
        return f"Salad kapatılamadı: {exc}"
