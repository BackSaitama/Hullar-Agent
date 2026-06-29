"""Sistem bilgisi: CPU, RAM, disk, pil, IP, çalışan uygulamalar, işlem sonlandır."""

import platform
import socket
import subprocess
from pathlib import Path


def _ps(cmd: str) -> str:
    r = subprocess.run(
        ["powershell", "-NoProfile", "-Command", cmd],
        capture_output=True, text=True, timeout=10,
    )
    return r.stdout.strip()


def battery_status(parameters: dict, **_) -> str:
    try:
        import psutil  # type: ignore
        b = psutil.sensors_battery()
        if b is None:
            return "Efendim, pil bilgisi alınamadı (AC ile çalışıyor olabilir)."
        status = "Şarj oluyor" if b.power_plugged else "Pil ile çalışıyor"
        return f"Efendim, pil durumu: %{b.percent:.0f} — {status}."
    except ImportError:
        out = _ps("(Get-WmiObject Win32_Battery).EstimatedChargeRemaining")
        return f"Efendim, pil seviyesi: %{out}" if out else "Efendim, pil bilgisi alınamadı."


def cpu_ram_usage(parameters: dict, **_) -> str:
    try:
        import psutil  # type: ignore
        cpu  = psutil.cpu_percent(interval=1)
        ram  = psutil.virtual_memory()
        return (
            f"Efendim, CPU: %{cpu:.1f}  |  "
            f"RAM: {ram.used / 1024**3:.1f} GB / {ram.total / 1024**3:.1f} GB  (%{ram.percent:.1f})"
        )
    except ImportError:
        cpu = _ps("(Get-WmiObject Win32_Processor).LoadPercentage")
        return f"Efendim, CPU kullanımı: %{cpu}"


def disk_usage(parameters: dict, **_) -> str:
    try:
        import psutil  # type: ignore
        lines = []
        for p in psutil.disk_partitions():
            try:
                u = psutil.disk_usage(p.mountpoint)
                lines.append(
                    f"{p.device}  {u.used/1024**3:.1f}/{u.total/1024**3:.1f} GB  (%{u.percent})"
                )
            except Exception:
                pass
        return "Efendim, disk kullanımı:\n" + "\n".join(lines) if lines else "Disk bilgisi alınamadı."
    except ImportError:
        out = _ps("Get-PSDrive -PSProvider FileSystem | Select-Object Name,Used,Free | Format-Table | Out-String")
        return f"Efendim, disk bilgisi:\n{out}"


def system_info(parameters: dict, **_) -> str:
    node    = platform.node()
    sys_    = platform.system()
    release = platform.release()
    machine = platform.machine()
    proc    = platform.processor()
    try:
        import psutil  # type: ignore
        ram = f"{psutil.virtual_memory().total / 1024**3:.1f} GB"
    except ImportError:
        ram = "bilinmiyor"
    return (
        f"Efendim, sistem bilgisi:\n"
        f"  Bilgisayar: {node}\n"
        f"  OS: {sys_} {release} ({machine})\n"
        f"  İşlemci: {proc}\n"
        f"  RAM: {ram}"
    )


def ip_info(parameters: dict, **_) -> str:
    local_ip = socket.gethostbyname(socket.gethostname())
    try:
        import urllib.request, json
        data = json.loads(urllib.request.urlopen("https://ipinfo.io/json", timeout=5).read())
        pub_ip = data.get("ip", "?")
        city   = data.get("city", "?")
        return f"Efendim, yerel IP: {local_ip}  |  Genel IP: {pub_ip}  |  Konum: {city}"
    except Exception:
        return f"Efendim, yerel IP adresiniz: {local_ip}"


def running_apps(parameters: dict, **_) -> str:
    try:
        import psutil  # type: ignore
        apps = sorted({p.name() for p in psutil.process_iter(["name"]) if p.info["name"]})
        top  = apps[:20]
        return "Efendim, çalışan uygulamalar (ilk 20):\n" + ", ".join(top)
    except ImportError:
        out = _ps("Get-Process | Select-Object -First 20 Name | ForEach-Object {$_.Name}")
        return f"Efendim, çalışan uygulamalar:\n{out}"


def kill_process(parameters: dict, **_) -> str:
    name = (parameters or {}).get("name", "").strip()
    if not name:
        return "Efendim, hangi uygulamayı kapatmamı istediğinizi belirtir misiniz?"
    try:
        import psutil  # type: ignore
        killed = 0
        for p in psutil.process_iter(["name"]):
            if name.lower() in p.info["name"].lower():
                p.kill()
                killed += 1
        return f"Efendim, {killed} adet '{name}' işlemi sonlandırıldı." if killed else f"'{name}' adlı işlem bulunamadı."
    except ImportError:
        subprocess.run(f"taskkill /f /im {name}", shell=True)
        return f"Efendim, '{name}' kapatılmaya çalışıldı."


def wifi_info(parameters: dict, **_) -> str:
    out = _ps("netsh wlan show interfaces | Select-String 'SSID|Signal|State'")
    return f"Efendim, Wi-Fi bilgisi:\n{out}" if out.strip() else "Efendim, Wi-Fi bilgisi alınamadı."
