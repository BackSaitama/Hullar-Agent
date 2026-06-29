"""
PC Otomasyon Becerileri — pencere yönetimi, bakım, ekran, ağ, sistem ayarları.
20 skill, her biri bağımsız ve hata toleranslı.
"""

import os
import re
import subprocess
import time
import webbrowser
from pathlib import Path

try:
    import pyautogui
    pyautogui.PAUSE = 0.02
    pyautogui.FAILSAFE = False
    _GUI = True
except ImportError:
    _GUI = False


def _ps(cmd: str, capture=True) -> str:
    """PowerShell komutu çalıştır, stdout döndür."""
    r = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", cmd],
        capture_output=capture, text=True, timeout=15,
    )
    return (r.stdout or "").strip()


# ═══════════════════════════════════════════════════════════════════════ #
#  1. Açık pencereleri listele
# ═══════════════════════════════════════════════════════════════════════ #
def list_windows(parameters: dict, **_) -> str:
    titles = _ps(
        "Get-Process | Where-Object {$_.MainWindowTitle} "
        "| Select-Object -ExpandProperty MainWindowTitle"
    )
    if not titles:
        return "Efendim, şu an görünür pencere bulunamadı."
    lines = [f"  • {t}" for t in titles.splitlines() if t.strip()]
    return "Efendim, açık pencereler:\n" + "\n".join(lines[:20])


# ═══════════════════════════════════════════════════════════════════════ #
#  2. Pencereye odaklan (öne getir)
# ═══════════════════════════════════════════════════════════════════════ #
def focus_window(parameters: dict, **_) -> str:
    title = (parameters or {}).get("title", "").strip()
    if not title:
        return "Efendim, hangi pencerenin öne geleceğini belirtir misiniz?"
    # pygetwindow varsa kullan
    try:
        import pygetwindow as gw  # type: ignore
        wins = gw.getWindowsWithTitle(title)
        if wins:
            wins[0].activate()
            return f"Efendim, '{title}' penceresi öne getirildi."
    except Exception:
        pass
    # PowerShell fallback
    _ps(
        f"$p = Get-Process | Where-Object {{$_.MainWindowTitle -like '*{title}*'}} | "
        f"Select-Object -First 1; "
        f"if ($p) {{ [void][System.Runtime.InteropServices.Marshal]::GetExceptionForHR(0); "
        f"$null = (New-Object -ComObject Shell.Application).Windows() }}"
    )
    # AppActivate ile dene
    _ps(f'$wsh=New-Object -ComObject WScript.Shell; $wsh.AppActivate("{title}")')
    return f"Efendim, '{title}' penceresine odaklanıldı."


# ═══════════════════════════════════════════════════════════════════════ #
#  3. Pencereyi kapat
# ═══════════════════════════════════════════════════════════════════════ #
def close_window(parameters: dict, **_) -> str:
    title = (parameters or {}).get("title", "").strip()
    if not title:
        return "Efendim, hangi pencerenin kapatılacağını belirtir misiniz?"
    try:
        import pygetwindow as gw  # type: ignore
        wins = gw.getWindowsWithTitle(title)
        if wins:
            wins[0].close()
            return f"Efendim, '{title}' penceresi kapatıldı."
    except Exception:
        pass
    result = _ps(
        f"Get-Process | Where-Object {{$_.MainWindowTitle -like '*{title}*'}} "
        f"| ForEach-Object {{ $_.CloseMainWindow() }}"
    )
    return f"Efendim, '{title}' penceresi kapatılmaya çalışıldı."


# ═══════════════════════════════════════════════════════════════════════ #
#  4. Pencereyi büyüt (maximize)
# ═══════════════════════════════════════════════════════════════════════ #
def maximize_window(parameters: dict, **_) -> str:
    title = (parameters or {}).get("title", "").strip()
    try:
        import pygetwindow as gw  # type: ignore
        wins = gw.getWindowsWithTitle(title) if title else [gw.getActiveWindow()]
        if wins and wins[0]:
            wins[0].maximize()
            return f"Efendim, pencere büyütüldü."
    except Exception:
        pass
    if _GUI:
        pyautogui.hotkey("win", "up")
        return "Efendim, aktif pencere büyütüldü."
    return "Efendim, pyautogui gerekiyor."


# ═══════════════════════════════════════════════════════════════════════ #
#  5. Pencereyi küçült (minimize)
# ═══════════════════════════════════════════════════════════════════════ #
def minimize_window(parameters: dict, **_) -> str:
    title = (parameters or {}).get("title", "").strip()
    try:
        import pygetwindow as gw  # type: ignore
        wins = gw.getWindowsWithTitle(title) if title else [gw.getActiveWindow()]
        if wins and wins[0]:
            wins[0].minimize()
            return "Efendim, pencere küçültüldü."
    except Exception:
        pass
    if _GUI:
        pyautogui.hotkey("win", "down")
        return "Efendim, aktif pencere küçültüldü."
    return "Efendim, pyautogui gerekiyor."


# ═══════════════════════════════════════════════════════════════════════ #
#  6. Metin yaz (mevcut odakta)
# ═══════════════════════════════════════════════════════════════════════ #
def type_text(parameters: dict, **_) -> str:
    text = (parameters or {}).get("text", "").strip()
    if not text:
        return "Efendim, yazılacak metni belirtir misiniz?"
    if not _GUI:
        return "Efendim, pyautogui gerekiyor."
    # Pano üzerinden yaz — Türkçe karakter güvenli
    try:
        import pyperclip
        pyperclip.copy(text)
    except Exception:
        subprocess.run(
            f'powershell -c "Set-Clipboard -Value \'{text}\'"',
            shell=True, stdout=subprocess.DEVNULL,
        )
    time.sleep(0.1)
    pyautogui.hotkey("ctrl", "v")
    return f"Efendim, metin yazıldı: '{text[:40]}'"


# ═══════════════════════════════════════════════════════════════════════ #
#  7. Klavye kısayolu gönder
# ═══════════════════════════════════════════════════════════════════════ #
def press_hotkey(parameters: dict, **_) -> str:
    keys_raw = (parameters or {}).get("keys", "").strip().lower()
    if not keys_raw:
        return "Efendim, tuş kombinasyonunu belirtir misiniz? (örn: ctrl+c)"
    if not _GUI:
        return "Efendim, pyautogui gerekiyor."
    keys = [k.strip() for k in re.split(r"[+,\s]+", keys_raw) if k.strip()]
    pyautogui.hotkey(*keys)
    return f"Efendim, '{'+'.join(keys)}' tuş kombinasyonu gönderildi."


# ═══════════════════════════════════════════════════════════════════════ #
#  8. Sayfayı kaydır
# ═══════════════════════════════════════════════════════════════════════ #
def scroll_page(parameters: dict, **_) -> str:
    direction = (parameters or {}).get("direction", "down").lower()
    amount    = int((parameters or {}).get("amount", 5))
    if not _GUI:
        return "Efendim, pyautogui gerekiyor."
    clicks = amount if direction in ("down", "aşağı") else -amount
    pyautogui.scroll(clicks)
    return f"Efendim, sayfa {'aşağı' if clicks > 0 else 'yukarı'} kaydırıldı."


# ═══════════════════════════════════════════════════════════════════════ #
#  9. Geçici dosyaları temizle
# ═══════════════════════════════════════════════════════════════════════ #
def clear_temp(parameters: dict, **_) -> str:
    """
    Hem kullanıcı (%TEMP%) hem sistem (%SystemRoot%\\Temp) geçici klasörlerini temizler.
    Kullanımda olan dosyaları atlar, hata vermez.
    """
    user_temp   = os.environ.get("TEMP", os.environ.get("TMP", ""))
    system_temp = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "Temp")

    folders = [p for p in [user_temp, system_temp] if p and os.path.isdir(p)]
    if not folders:
        return "Efendim, TEMP klasörü bulunamadı."

    # PowerShell ile toplu sil — kullanımda olanları sessizce atla
    paths_ps = ", ".join(f'"{p}"' for p in folders)
    script = (
        f'$total = 0; '
        f'$freed = 0; '
        f'foreach ($dir in @({paths_ps})) {{ '
        f'  $items = Get-ChildItem -Path $dir -Recurse -Force -ErrorAction SilentlyContinue; '
        f'  foreach ($item in $items) {{ '
        f'    try {{ '
        f'      $size = if ($item.PSIsContainer) {{ 0 }} else {{ $item.Length }}; '
        f'      Remove-Item -Path $item.FullName -Recurse -Force -ErrorAction Stop; '
        f'      $total++; $freed += $size '
        f'    }} catch {{}} '
        f'  }} '
        f'}}; '
        f'$mb = [math]::Round($freed / 1MB, 1); '
        f'Write-Output "$total|$mb"'
    )
    result = _ps(script).strip()

    if "|" in result:
        count, mb = result.split("|", 1)
        return (
            f"Efendim, geçici dosyalar temizlendi. "
            f"{count} öğe silindi, yaklaşık {mb} MB boşaltıldı."
        )
    return "Efendim, geçici dosyalar temizlendi."


# ═══════════════════════════════════════════════════════════════════════ #
#  10. DNS önbelleğini temizle
# ═══════════════════════════════════════════════════════════════════════ #
def flush_dns(parameters: dict, **_) -> str:
    r = subprocess.run(
        "ipconfig /flushdns", shell=True,
        capture_output=True, text=True, timeout=10,
    )
    if r.returncode == 0:
        return "Efendim, DNS önbelleği temizlendi."
    return f"Efendim, DNS temizlenemedi (yönetici yetkisi gerekebilir)."


# ═══════════════════════════════════════════════════════════════════════ #
#  11. Sistem geri yükleme noktası oluştur
# ═══════════════════════════════════════════════════════════════════════ #
def create_restore_point(parameters: dict, **_) -> str:
    desc = (parameters or {}).get("description", "JARVIS Geri Yükleme Noktası")
    r = _ps(
        f'Checkpoint-Computer -Description "{desc}" '
        f'-RestorePointType "MODIFY_SETTINGS" -ErrorAction SilentlyContinue'
    )
    if "hata" in r.lower() or "error" in r.lower():
        return "Efendim, geri yükleme noktası oluşturulamadı (yönetici yetkisi gerekebilir)."
    return f"Efendim, '{desc}' geri yükleme noktası oluşturuldu."


# ═══════════════════════════════════════════════════════════════════════ #
#  12. Başlangıç programlarını listele
# ═══════════════════════════════════════════════════════════════════════ #
def list_startup_apps(parameters: dict, **_) -> str:
    items = _ps(
        "Get-CimInstance Win32_StartupCommand "
        "| Select-Object Name, Command "
        "| ForEach-Object { $_.Name + ' :: ' + $_.Command }"
    )
    if not items:
        return "Efendim, başlangıç programı listesi alınamadı."
    lines = [f"  • {l}" for l in items.splitlines() if l.strip()]
    return "Efendim, başlangıç programları:\n" + "\n".join(lines[:15])


# ═══════════════════════════════════════════════════════════════════════ #
#  13. Başlangıç klasörünü aç
# ═══════════════════════════════════════════════════════════════════════ #
def open_startup_folder(parameters: dict, **_) -> str:
    startup = Path(os.environ.get("APPDATA", "")) / "Microsoft\\Windows\\Start Menu\\Programs\\Startup"
    if startup.exists():
        os.startfile(str(startup))
        return "Efendim, başlangıç klasörü açıldı."
    subprocess.Popen("shell:startup", shell=True)
    return "Efendim, başlangıç klasörü açıldı."


# ═══════════════════════════════════════════════════════════════════════ #
#  14. Gece modu aç/kapat
# ═══════════════════════════════════════════════════════════════════════ #
def toggle_night_mode(parameters: dict, **_) -> str:
    """
    Gece ışığını (Night Light) aç/kapat/toggle.
    Yöntem 1: Registry Data baytını doğrudan yaz (Windows 10/11).
    Yöntem 2 (fallback): Ayarlar sayfasını aç.
    """
    action = (parameters or {}).get("action", "toggle").lower()

    # Registry yolu (Windows 10/11 için geçerli)
    reg_key = (
        r"HKCU\Software\Microsoft\Windows\CurrentVersion\CloudStore\Store"
        r"\DefaultAccount\Current"
        r"\default$windows.data.bluelightreduction.bluelightreductionstate"
        r"\windows.data.bluelightreduction.bluelightreductionstate"
    )

    def _read_enabled() -> bool | None:
        """Gece ışığının şu anki durumunu oku. None = okunamadı."""
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                reg_key.replace("HKCU\\", ""), 0, winreg.KEY_READ)
            data, _ = winreg.QueryValueEx(key, "Data")
            winreg.CloseKey(key)
            # Byte 24 (0-indexed): 0x01 = açık, 0x00 = kapalı
            if len(data) > 24:
                return data[24] == 0x01
        except Exception:
            pass
        return None

    def _write_state(enable: bool) -> bool:
        """Registry Data'yı değiştir — birden fazla byte offset'i dene."""
        import winreg
        try:
            hive_path = reg_key.replace("HKCU\\", "")
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, hive_path, 0,
                winreg.KEY_READ | winreg.KEY_WRITE,
            )
            data, rtype = winreg.QueryValueEx(key, "Data")
            data = bytearray(data)
            changed = False
            # Windows 10/11'de farklı offset'ler: 18, 23, 24 dene
            for offset in (18, 23, 24):
                if len(data) > offset:
                    # Açık işareti: 0x15 (21) veya 0x01; Kapalı: 0x13 (19) veya 0x00
                    if enable:
                        if data[offset] in (0x13, 0x00, 19, 0):
                            data[offset] = 0x15
                            changed = True
                    else:
                        if data[offset] in (0x15, 0x01, 21, 1):
                            data[offset] = 0x13
                            changed = True
            if changed:
                winreg.SetValueEx(key, "Data", 0, rtype, bytes(data))
            winreg.CloseKey(key)
            return True
        except Exception:
            return False

    def _broadcast_settings():
        """WM_SETTINGCHANGE gönder — explorer yeniden başlatmadan uygula."""
        try:
            import ctypes
            ctypes.windll.user32.SendMessageTimeoutW(
                0xFFFF, 0x001A, 0, "ImmersiveColorSet", 2, 500, None
            )
        except Exception:
            pass

    current = _read_enabled()

    if action in ("aç", "on", "enable", "ac"):
        target = True
    elif action in ("kapat", "off", "disable", "kapa"):
        target = False
    else:
        target = not current if current is not None else True

    success = _write_state(target)
    if success:
        _broadcast_settings()
        state_str = "açıldı" if target else "kapatıldı"
        return f"Efendim, gece ışığı {state_str}."

    # Fallback: Ayarlar sayfasını aç
    subprocess.Popen("start ms-settings:nightlight", shell=True)
    return "Efendim, gece ışığı ayar sayfası açıldı — oradan açıp kapatabilirsiniz."


# ═══════════════════════════════════════════════════════════════════════ #
#  15. Ağ adaptörünü sıfırla
# ═══════════════════════════════════════════════════════════════════════ #
def reset_network(parameters: dict, **_) -> str:
    cmds = [
        "netsh winsock reset",
        "netsh int ip reset",
        "ipconfig /release",
        "ipconfig /flushdns",
        "ipconfig /renew",
    ]
    results = []
    for cmd in cmds:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15)
        results.append(f"✓ {cmd}" if r.returncode == 0 else f"✗ {cmd}")
    return "Efendim, ağ sıfırlandı (yeniden başlatma önerilir):\n" + "\n".join(results)


# ═══════════════════════════════════════════════════════════════════════ #
#  16. Ağ ayarlarını aç
# ═══════════════════════════════════════════════════════════════════════ #
def open_network_settings(parameters: dict, **_) -> str:
    subprocess.Popen("start ms-settings:network", shell=True)
    return "Efendim, ağ ayarları açıldı."


# ═══════════════════════════════════════════════════════════════════════ #
#  17. Kayıtlı WiFi şifrelerini göster
# ═══════════════════════════════════════════════════════════════════════ #
def show_wifi_passwords(parameters: dict, **_) -> str:
    profiles_raw = _ps("netsh wlan show profiles")
    profiles = re.findall(r"All User Profile\s*:\s*(.+)", profiles_raw)
    if not profiles:
        return "Efendim, kayıtlı WiFi profili bulunamadı."
    lines = []
    for p in profiles[:10]:
        p = p.strip()
        detail = _ps(f'netsh wlan show profile name="{p}" key=clear')
        pwd_m = re.search(r"Key Content\s*:\s*(.+)", detail)
        pwd   = pwd_m.group(1).strip() if pwd_m else "(şifre yok)"
        lines.append(f"  📶 {p}: {pwd}")
    return "Efendim, kayıtlı WiFi şifreleri:\n" + "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════ #
#  18. Ekran ayarlarını aç
# ═══════════════════════════════════════════════════════════════════════ #
def open_display_settings(parameters: dict, **_) -> str:
    subprocess.Popen("start ms-settings:display", shell=True)
    return "Efendim, ekran ayarları açıldı."


# ═══════════════════════════════════════════════════════════════════════ #
#  19. Ses ayarlarını aç
# ═══════════════════════════════════════════════════════════════════════ #
def open_sound_settings(parameters: dict, **_) -> str:
    subprocess.Popen("start ms-settings:sound", shell=True)
    return "Efendim, ses ayarları açıldı."


# ═══════════════════════════════════════════════════════════════════════ #
#  20. Windows Update sayfasını aç
# ═══════════════════════════════════════════════════════════════════════ #
def open_windows_update(parameters: dict, **_) -> str:
    subprocess.Popen("start ms-settings:windowsupdate", shell=True)
    return "Efendim, Windows Update açıldı."


# ═══════════════════════════════════════════════════════════════════════ #
#  BONUS: Masaüstü duvar kağıdı değiştir
# ═══════════════════════════════════════════════════════════════════════ #
def set_wallpaper(parameters: dict, **_) -> str:
    path = (parameters or {}).get("path", "").strip()
    if not path or not Path(path).exists():
        return f"Efendim, geçerli bir resim dosyası yolu belirtir misiniz? (örn: C:\\resim.jpg)"
    _ps(
        f"Add-Type -TypeDefinition '"
        f"using System; using System.Runtime.InteropServices; "
        f"public class W {{ [DllImport(\"user32.dll\")] public static extern bool SystemParametersInfo(int a, int b, string c, int d); }}"
        f"'; [W]::SystemParametersInfo(20, 0, '{path}', 3)"
    )
    return f"Efendim, duvar kağıdı değiştirildi: {path}"


# ═══════════════════════════════════════════════════════════════════════ #
#  BONUS 2: Aktif pencerenin başlığını söyle
# ═══════════════════════════════════════════════════════════════════════ #
def active_window_title(parameters: dict, **_) -> str:
    # pygetwindow en hızlı yol
    try:
        import pygetwindow as gw  # type: ignore
        w = gw.getActiveWindow()
        if w:
            return f"Efendim, aktif pencere: '{w.title}'"
    except Exception:
        pass
    # Fallback: çalışan proseslerden ön plandakini bul
    title = _ps(
        "Get-Process | Where-Object {$_.MainWindowTitle -ne ''} "
        "| Sort-Object CPU -Descending | Select-Object -First 1 -ExpandProperty MainWindowTitle"
    )
    if title:
        return f"Efendim, aktif pencere: '{title}'"
    return "Efendim, aktif pencere başlığı alınamadı."
