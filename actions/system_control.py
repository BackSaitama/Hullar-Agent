"""Sistem kontrolü: ekran görüntüsü, kilit, kapatma, yeniden başlatma, uyku."""

import os
import subprocess
import time
from datetime import datetime
from pathlib import Path


def screenshot(parameters: dict, **_) -> str:
    dest = parameters.get("path", "").strip()
    if not dest:
        ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
        dest = str(Path.home() / "Desktop" / f"ekran_{ts}.png")
    try:
        import PIL.ImageGrab as ImageGrab  # type: ignore
        img = ImageGrab.grab()
        img.save(dest)
        return f"Efendim, ekran görüntüsü kaydedildi: {dest}"
    except ImportError:
        pass
    try:
        subprocess.run(
            f'powershell -c "Add-Type -AssemblyName System.Windows.Forms; '
            f'[System.Windows.Forms.Screen]::PrimaryScreen | Out-Null; '
            f'$bmp = New-Object System.Drawing.Bitmap([System.Windows.Forms.Screen]::PrimaryScreen.Bounds.Width,'
            f'[System.Windows.Forms.Screen]::PrimaryScreen.Bounds.Height); '
            f'$g = [System.Drawing.Graphics]::FromImage($bmp); '
            f'$g.CopyFromScreen(0,0,0,0,$bmp.Size); '
            f'$bmp.Save(\\"{dest}\\")"',
            shell=True, check=True,
        )
        return f"Efendim, ekran görüntüsü kaydedildi: {dest}"
    except Exception as e:
        return f"Ekran görüntüsü alınamadı: {e}"


def lock_screen(parameters: dict, **_) -> str:
    subprocess.run("rundll32.exe user32.dll,LockWorkStation", shell=True)
    return "Efendim, ekran kilitlendi."


def shutdown(parameters: dict, **_) -> str:
    delay = int(parameters.get("delay", 0))
    subprocess.run(f"shutdown /s /t {delay}", shell=True)
    msg = f"Efendim, bilgisayar {delay} saniye içinde kapatılacak." if delay else "Efendim, bilgisayar kapatılıyor."
    return msg


def restart(parameters: dict, **_) -> str:
    delay = int(parameters.get("delay", 0))
    subprocess.run(f"shutdown /r /t {delay}", shell=True)
    return f"Efendim, bilgisayar yeniden başlatılıyor."


def sleep_mode(parameters: dict, **_) -> str:
    subprocess.run("rundll32.exe powrprof.dll,SetSuspendState 0,1,0", shell=True)
    return "Efendim, bilgisayar uyku moduna alındı."


def cancel_shutdown(parameters: dict, **_) -> str:
    subprocess.run("shutdown /a", shell=True)
    return "Efendim, zamanlanmış kapatma iptal edildi."


def empty_recycle_bin(parameters: dict, **_) -> str:
    try:
        import winshell  # type: ignore
        winshell.recycle_bin().empty(confirm=False, show_progress=False, sound=False)
        return "Efendim, geri dönüşüm kutusu boşaltıldı."
    except ImportError:
        subprocess.run(
            'powershell -c "Clear-RecycleBin -Force -ErrorAction SilentlyContinue"',
            shell=True,
        )
        return "Efendim, geri dönüşüm kutusu boşaltıldı."


def show_desktop(parameters: dict, **_) -> str:
    subprocess.run(
        'powershell -c "$shell=New-Object -ComObject Shell.Application; $shell.MinimizeAll()"',
        shell=True,
    )
    return "Efendim, tüm pencereler simge durumuna küçültüldü."
