"""Ses seviyesi — Windows ctypes VK_VOLUME tuşları ile güvenilir kontrol."""

import ctypes
import time


# Windows sanal tuş kodları
VK_VOLUME_MUTE = 0xAD
VK_VOLUME_DOWN = 0xAE
VK_VOLUME_UP   = 0xAF
KEYEVENTF_KEYUP = 0x0002


def _press_vk(vk: int, times: int = 1):
    """Sanal tuşa bas ve bırak — sistem genelinde çalışır."""
    for _ in range(times):
        ctypes.windll.user32.keybd_event(vk, 0, 0, 0)
        ctypes.windll.user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)
        time.sleep(0.02)


def _endpoint_volume():
    """pycaw IAudioEndpointVolume arayüzünü döndürür (yeni + eski API uyumlu)."""
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume  # type: ignore
    devices = AudioUtilities.GetSpeakers()
    # Yeni pycaw (2.x): AudioDevice.EndpointVolume hazır verir
    ev = getattr(devices, "EndpointVolume", None)
    if ev is not None:
        return ev
    # Eski pycaw: COM aktivasyonu gerekir
    from comtypes import CLSCTX_ALL  # type: ignore
    interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
    return interface.QueryInterface(IAudioEndpointVolume)


def _set_volume_pycaw(level_pct: int) -> bool:
    """pycaw kuruluysa belirli bir seviyeye direkt ayarla."""
    try:
        vol = _endpoint_volume()
        vol.SetMasterVolumeLevelScalar(max(0.0, min(1.0, level_pct / 100)), None)
        return True
    except Exception:
        return False


def _get_volume_pycaw() -> int | None:
    try:
        vol = _endpoint_volume()
        return int(vol.GetMasterVolumeLevelScalar() * 100)
    except Exception:
        return None


def volume_control(parameters: dict, **_) -> str:
    p      = parameters or {}
    action = p.get("action", "").lower().strip()
    value  = p.get("value", 10)

    try:
        value = int(value)
    except (ValueError, TypeError):
        value = 10

    # ── Artır ── #
    if action in ("artır", "arttir", "artir", "up", "yukari", "yükselt", "yukselt"):
        steps = max(1, value // 2)
        current = _get_volume_pycaw()
        if current is not None and _set_volume_pycaw(min(100, current + value)):
            return f"Efendim, ses %{min(100, current + value)} yapıldı."
        _press_vk(VK_VOLUME_UP, steps)
        return f"Efendim, ses artırıldı."

    # ── Azalt ── #
    if action in ("azalt", "düşür", "dusur", "down", "asagi", "aşağı", "kıs", "kis"):
        steps = max(1, value // 2)
        current = _get_volume_pycaw()
        if current is not None and _set_volume_pycaw(max(0, current - value)):
            return f"Efendim, ses %{max(0, current - value)} yapıldı."
        _press_vk(VK_VOLUME_DOWN, steps)
        return f"Efendim, ses azaltıldı."

    # ── Kapat / Mute ── #
    if action in ("kapat", "kapa", "mute", "sessize al", "sustur", "kes"):
        _press_vk(VK_VOLUME_MUTE)
        return "Efendim, ses kapatıldı (mute)."

    # ── Aç / Unmute ── #
    if action in ("ac", "aç", "unmute", "geri aç", "geri ac"):
        _press_vk(VK_VOLUME_MUTE)   # Mute toggle
        return "Efendim, ses açıldı."

    # ── Belirli seviye ── #
    if action in ("ayarla", "set", "yap", "seviye") or str(value).isdigit():
        if _set_volume_pycaw(value):
            return f"Efendim, ses %{value} yapıldı."
        # pycaw yoksa yaklaşık basışla ayarla
        current = 50  # Tahmin
        diff = value - current
        if diff > 0:
            _press_vk(VK_VOLUME_UP, abs(diff) // 2)
        else:
            _press_vk(VK_VOLUME_DOWN, abs(diff) // 2)
        return f"Efendim, ses yaklaşık %{value} yapıldı."

    return f"Efendim, '{action}' ses komutu tanınmadı."
