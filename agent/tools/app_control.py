"""Uygulama + pencere kontrol araçları."""

import subprocess
import time


def open_app(ctx, name: str) -> str:
    """Uygulama açar (mevcut open_app action'ını kullanır)."""
    try:
        from actions.open_app import open_app as _open
        return _open(parameters={"app_name": name})
    except Exception:
        subprocess.Popen(name, shell=True)
        time.sleep(1.5)
        return f"'{name}' başlatıldı."


def focus_window(ctx, title: str) -> str:
    """Pencereyi öne getirir."""
    try:
        import pygetwindow as gw
        wins = gw.getWindowsWithTitle(title)
        if wins:
            w = wins[0]
            try:
                w.maximize()
            except Exception:
                pass
            w.activate()
            time.sleep(0.5)
            return f"'{title}' öne getirildi."
        return f"HATA: '{title}' penceresi yok."
    except Exception as exc:
        return f"HATA: {exc}"


def list_windows(ctx) -> str:
    """Açık pencereleri listeler."""
    try:
        import pygetwindow as gw
        titles = [t for t in gw.getAllTitles() if t.strip()]
        return "Açık pencereler: " + " | ".join(titles[:25])
    except Exception as exc:
        return f"HATA: {exc}"


def wait(ctx, seconds: float = 1.0) -> str:
    time.sleep(min(float(seconds), 10))
    return f"{seconds}sn beklendi."


def register(box):
    box.add("open_app", "Bir uygulama/program açar (whatsapp, chrome, discord, notepad...)",
            {"name": "uygulama adı"}, open_app)
    box.add("focus_window", "Açık bir pencereyi öne getirir ve büyütür",
            {"title": "pencere başlığı"}, focus_window)
    box.add("list_windows", "Açık tüm pencereleri listeler", {}, list_windows)
    box.add("wait", "Belirtilen saniye bekler (yükleme için)",
            {"seconds": "saniye"}, wait)
