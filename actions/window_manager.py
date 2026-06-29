"""Pencere yönetimi ve ekran kontrolü."""

import subprocess
import time

try:
    import pyautogui  # type: ignore
    _GUI = True
except ImportError:
    _GUI = False


def minimize_all(parameters: dict, **_) -> str:
    subprocess.run(
        'powershell -c "$s=New-Object -ComObject Shell.Application; $s.MinimizeAll()"',
        shell=True, stdout=subprocess.DEVNULL,
    )
    return "Efendim, tüm pencereler küçültüldü."


def restore_all(parameters: dict, **_) -> str:
    subprocess.run(
        'powershell -c "$s=New-Object -ComObject Shell.Application; $s.UndoMinimizeALL()"',
        shell=True, stdout=subprocess.DEVNULL,
    )
    return "Efendim, pencereler geri yüklendi."


def virtual_desktop_new(parameters: dict, **_) -> str:
    if _GUI:
        import pyautogui
        pyautogui.hotkey("win", "ctrl", "d")
        return "Efendim, yeni sanal masaüstü oluşturuldu."
    return "Efendim, pyautogui gerekiyor."


def task_view(parameters: dict, **_) -> str:
    if _GUI:
        import pyautogui
        pyautogui.hotkey("win", "tab")
        return "Efendim, görev görünümü açıldı."
    subprocess.run("start ms-taskview:", shell=True)
    return "Efendim, görev görünümü açıldı."


def take_screenshot_region(parameters: dict, **_) -> str:
    """Ekranın belirli bir bölgesini yakala (snipping tool)."""
    subprocess.Popen("SnippingTool.exe /clip", shell=True)
    return "Efendim, ekran alıntısı aracı açıldı."


def open_task_manager(parameters: dict, **_) -> str:
    subprocess.Popen("taskmgr.exe", shell=True)
    return "Efendim, Görev Yöneticisi açıldı."


def open_control_panel(parameters: dict, **_) -> str:
    subprocess.Popen("control.exe", shell=True)
    return "Efendim, Denetim Masası açıldı."


def open_device_manager(parameters: dict, **_) -> str:
    subprocess.Popen("devmgmt.msc", shell=True)
    return "Efendim, Aygıt Yöneticisi açıldı."


def open_disk_manager(parameters: dict, **_) -> str:
    subprocess.Popen("diskmgmt.msc", shell=True)
    return "Efendim, Disk Yönetimi açıldı."


def open_registry(parameters: dict, **_) -> str:
    subprocess.Popen("regedit.exe", shell=True)
    return "Efendim, Kayıt Defteri Düzenleyicisi açıldı."


def run_command(parameters: dict, **_) -> str:
    cmd = (parameters or {}).get("command", "").strip()
    if not cmd:
        return "Efendim, çalıştırılacak komutu belirtir misiniz?"
    # Tehlikeli komutları engelle
    blocked = ["rm -rf", "del /f", "format", "rd /s", "shutdown /f"]
    if any(b in cmd.lower() for b in blocked):
        return "Efendim, bu komut güvenlik nedeniyle engellendi."
    result = subprocess.run(
        cmd, shell=True, capture_output=True, text=True, timeout=15,
    )
    output = (result.stdout or result.stderr or "").strip()
    return f"Efendim, komut çalıştırıldı:\n{output[:500]}" if output else "Efendim, komut tamamlandı."


def ping_host(parameters: dict, **_) -> str:
    host = (parameters or {}).get("host", "google.com").strip()
    result = subprocess.run(
        f"ping -n 4 {host}", shell=True, capture_output=True, text=True, timeout=15,
    )
    lines = [l for l in result.stdout.splitlines() if l.strip()]
    summary = "\n".join(lines[-3:])
    return f"Efendim, ping sonucu ({host}):\n{summary}"


def check_internet(parameters: dict, **_) -> str:
    result = subprocess.run(
        "ping -n 1 8.8.8.8", shell=True, capture_output=True, text=True, timeout=8,
    )
    if result.returncode == 0:
        return "Efendim, internet bağlantısı aktif."
    return "Efendim, internet bağlantısı yok veya zayıf."
