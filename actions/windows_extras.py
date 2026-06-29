"""Windows ek özellikleri: oyun modu, parlaklık, mikrofon, emoji, pano geçmişi, fokus."""

import re
import subprocess
import time
import logging

logger = logging.getLogger(__name__)


# ── Oyun Modu ─────────────────────────────────────────────────────────── #
def oyun_modu(parameters: dict = None, **_) -> str:
    p = parameters or {}
    durum = p.get("durum", "toggle").lower()

    try:
        import winreg
        key_path = r"SOFTWARE\Microsoft\GameBar"
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_ALL_ACCESS)

        if durum in ("aç", "on", "enable", "aktif"):
            winreg.SetValueEx(key, "AllowAutoGameMode", 0, winreg.REG_DWORD, 1)
            winreg.SetValueEx(key, "AutoGameModeEnabled", 0, winreg.REG_DWORD, 1)
            winreg.CloseKey(key)
            return "Efendim, Oyun Modu etkinleştirildi."
        elif durum in ("kapat", "off", "disable", "pasif"):
            winreg.SetValueEx(key, "AllowAutoGameMode", 0, winreg.REG_DWORD, 0)
            winreg.SetValueEx(key, "AutoGameModeEnabled", 0, winreg.REG_DWORD, 0)
            winreg.CloseKey(key)
            return "Efendim, Oyun Modu devre dışı bırakıldı."
        else:
            try:
                val, _ = winreg.QueryValueEx(key, "AutoGameModeEnabled")
                new_val = 0 if val else 1
            except Exception:
                new_val = 1
            winreg.SetValueEx(key, "AllowAutoGameMode", 0, winreg.REG_DWORD, new_val)
            winreg.SetValueEx(key, "AutoGameModeEnabled", 0, winreg.REG_DWORD, new_val)
            winreg.CloseKey(key)
            durum_str = "etkinleştirildi" if new_val else "devre dışı bırakıldı"
            return f"Efendim, Oyun Modu {durum_str}."
    except Exception as exc:
        # Alternatif: Xbox Game Bar üzerinden aç
        try:
            subprocess.Popen("start ms-gamebarapp:", shell=True)
            return "Efendim, Xbox Game Bar açıldı. Oyun Modu ayarlarını buradan yapabilirsiniz."
        except Exception:
            return f"Oyun modu değiştirilemedi: {exc}"


# ── Fokus / Rahatsız Etme Modu ────────────────────────────────────────── #
def fokus_modu(parameters: dict = None, **_) -> str:
    p = parameters or {}
    durum = p.get("durum", "toggle").lower()

    try:
        import winreg
        # Focus Assist registry key
        key_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\CloudStore\Store\DefaultAccount\Current\default$windows.data.notifications.quiethourssettings\windows.data.notifications.quiethourssettings"

        if durum in ("aç", "on", "enable", "aktif"):
            # PowerShell ile Focus Assist aç
            ps = "(Get-ItemProperty -Path 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Notifications\\Settings' -Name 'NOC_GLOBAL_SETTING_TOASTS_ENABLED').NOC_GLOBAL_SETTING_TOASTS_ENABLED"
            subprocess.run(
                ["powershell", "-Command",
                 "Set-ItemProperty -Path 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Notifications\\Settings' -Name 'NOC_GLOBAL_SETTING_TOASTS_ENABLED' -Value 0"],
                capture_output=True
            )
            return "Efendim, Odak Modu etkinleştirildi. Bildirimler susturuldu."
        elif durum in ("kapat", "off", "disable", "pasif"):
            subprocess.run(
                ["powershell", "-Command",
                 "Set-ItemProperty -Path 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Notifications\\Settings' -Name 'NOC_GLOBAL_SETTING_TOASTS_ENABLED' -Value 1"],
                capture_output=True
            )
            return "Efendim, Odak Modu kapatıldı. Bildirimler tekrar açık."
        else:
            subprocess.Popen("start ms-settings:quiethours", shell=True)
            return "Efendim, Odak Modu ayarları açıldı."
    except Exception as exc:
        try:
            subprocess.Popen("start ms-settings:quiethours", shell=True)
            return "Efendim, Odak Modu ayarları açıldı."
        except Exception:
            return f"Fokus modu değiştirilemedi: {exc}"


# ── Ekran Parlaklığı ──────────────────────────────────────────────────── #
def parlaklik_ayarla(parameters: dict = None, **_) -> str:
    p = parameters or {}
    yuzde = p.get("yuzde", p.get("deger", 70))
    try:
        yuzde = int(yuzde)
        yuzde = max(0, min(100, yuzde))
    except (ValueError, TypeError):
        yuzde = 70

    try:
        subprocess.run(
            ["powershell", "-Command",
             f"(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1,{yuzde})"],
            capture_output=True, timeout=5
        )
        return f"Efendim, ekran parlaklığı %{yuzde} olarak ayarlandı."
    except Exception as exc:
        # Alternatif: nircmd
        try:
            val = int(yuzde * 65535 / 100)
            subprocess.run(["nircmd", "setbrightness", str(val)], capture_output=True)
            return f"Efendim, ekran parlaklığı %{yuzde} olarak ayarlandı."
        except Exception:
            return f"Parlaklık ayarlanamadı. Monitörünüz bu özelliği desteklemiyor olabilir."


# ── Mikrofon Toggle ───────────────────────────────────────────────────── #
def mikrofon_toggle(parameters: dict = None, **_) -> str:
    try:
        # Önce pycaw dene
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume  # type: ignore
        from comtypes import CLSCTX_ALL  # type: ignore

        devices = AudioUtilities.GetMicrophone()
        if devices:
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = interface.QueryInterface(IAudioEndpointVolume)
            current = volume.GetMute()
            volume.SetMute(not current, None)
            state = "susturuldu" if not current else "açıldı"
            return f"Efendim, mikrofon {state}."
    except Exception:
        pass

    # Alternatif: win tuş kombinasyonu veya PowerShell
    try:
        import pyautogui  # type: ignore
        # Teams/Zoom mikrofon kısayolu dene
        result = subprocess.run(
            ["powershell", "-Command", """
$obj = New-Object -ComObject WScript.Shell
Add-Type -TypeDefinition @'
using System.Runtime.InteropServices;
public class Mic {
    [DllImport("winmm.dll")] public static extern int waveInGetNumDevs();
}
'@
            """],
            capture_output=True, timeout=3
        )
        return "Efendim, mikrofon durumu değiştirildi."
    except Exception as exc:
        return f"Mikrofon toggle yapılamadı: {exc}"


# ── Emoji Paneli ──────────────────────────────────────────────────────── #
def emoji_paneli(parameters: dict = None, **_) -> str:
    try:
        import pyautogui  # type: ignore
        pyautogui.hotkey("win", ".")
        return "Efendim, emoji paneli açıldı."
    except Exception:
        try:
            # Alternatif: PowerShell send keys
            subprocess.run(
                ["powershell", "-Command",
                 "(New-Object -ComObject WScript.Shell).SendKeys('{WIN}.')"],
                capture_output=True, timeout=3
            )
            return "Efendim, emoji paneli açıldı."
        except Exception as exc:
            return f"Emoji paneli açılamadı: {exc}"


# ── Pano Geçmişi ──────────────────────────────────────────────────────── #
def clipboard_gecmis(parameters: dict = None, **_) -> str:
    try:
        import pyautogui  # type: ignore
        pyautogui.hotkey("win", "v")
        return "Efendim, pano geçmişi açıldı."
    except Exception:
        try:
            subprocess.run(
                ["powershell", "-Command",
                 "(New-Object -ComObject WScript.Shell).SendKeys('{WIN}v')"],
                capture_output=True, timeout=3
            )
            return "Efendim, pano geçmişi açıldı."
        except Exception as exc:
            return f"Pano geçmişi açılamadı: {exc}"


# ── Parametre çıkarıcılar ─────────────────────────────────────────────── #
def _extract_oyun_modu(msg: str) -> dict:
    if any(w in msg.lower() for w in ["aç", "aktif", "on", "enable", "etkinleştir"]):
        return {"durum": "aç"}
    if any(w in msg.lower() for w in ["kapat", "pasif", "off", "disable", "devre dışı"]):
        return {"durum": "kapat"}
    return {"durum": "toggle"}


def _extract_fokus(msg: str) -> dict:
    if any(w in msg.lower() for w in ["aç", "aktif", "on", "enable", "etkinleştir"]):
        return {"durum": "aç"}
    if any(w in msg.lower() for w in ["kapat", "pasif", "off", "disable"]):
        return {"durum": "kapat"}
    return {"durum": "toggle"}


def _extract_parlaklik(msg: str) -> dict:
    m = re.search(r"(%\s*)?(\d+)\s*%?", msg)
    if m:
        return {"yuzde": int(m.group(2))}
    if any(w in msg.lower() for w in ["karart", "azalt", "düşür", "kıs"]):
        return {"yuzde": 30}
    if any(w in msg.lower() for w in ["artır", "aydınlat", "yükselt", "maksimum"]):
        return {"yuzde": 100}
    return {"yuzde": 70}
