"""
HULLAR Wake-on-LAN — PC'yi uzaktan AÇMA (gerçek yöntem).

ÖNEMLİ: Kapalı bir PC kendini açamaz. Uzaktan açmanın tek yolu Wake-on-LAN:
aynı ağdaki BAŞKA bir cihaz (telefon/router/açık PC) MAC adresine "sihirli
paket" gönderir. Bu modül:
  • wol_uyandir(mac)  : verilen MAC'li cihazı uyandırır (sihirli paket)
  • wol_bilgi()       : bu PC'nin MAC + IP'sini gösterir (telefona girmen için)
  • wol_etkinlestir() : bu PC'de WoL'u açmaya çalışır + uyku ipuçları
"""

from __future__ import annotations

import re
import socket
import subprocess


# ── Sihirli paket gönder (cihazı uyandır) ─────────────────────────────── #
def wol_uyandir(parameters: dict | None = None) -> str:
    mac = (parameters or {}).get("mac", "").strip()
    if not mac:
        return ("Hangi cihazı uyandırayım? MAC ver: 'uyandır AA:BB:CC:DD:EE:FF'. "
                "Bu PC'nin MAC'i için 'wol bilgi' yaz.")
    temiz = re.sub(r"[^0-9a-fA-F]", "", mac)
    if len(temiz) != 12:
        return "Geçersiz MAC. Örn: AA:BB:CC:DD:EE:FF"
    try:
        data = bytes.fromhex("FF" * 6 + temiz * 16)
        for bcast in ("255.255.255.255", "192.168.1.255", "192.168.0.255"):
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                s.sendto(data, (bcast, 9))
                s.close()
            except Exception:
                continue
        return f"📡 Sihirli paket gönderildi → {mac}. Cihaz WoL açıksa uyanır."
    except Exception as exc:
        return f"Gönderilemedi: {exc}"


def _extract_wol(msg: str) -> dict:
    m = re.search(r"([0-9a-fA-F]{2}([:\-]?)[0-9a-fA-F]{2}(\2[0-9a-fA-F]{2}){4})", msg)
    return {"mac": m.group(1) if m else ""}


# ── Bu PC'nin MAC + IP bilgisi ────────────────────────────────────────── #
def wol_bilgi(parameters: dict | None = None) -> str:
    ip = "?"
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80)); ip = s.getsockname()[0]; s.close()
    except Exception:
        pass
    mac = "bulunamadı"
    # 1) Aktif IP'ye ait adaptörün MAC'ini ipconfig /all'dan bul
    try:
        r = subprocess.run("ipconfig /all", shell=True, capture_output=True,
                           text=True, timeout=15, errors="ignore")
        bloklar = re.split(r"\n(?=\S)", r.stdout or "")
        for blok in bloklar:
            if ip != "?" and ip in blok:
                m = re.search(r"([0-9A-Fa-f]{2}-){5}[0-9A-Fa-f]{2}", blok)
                if m:
                    mac = m.group(0); break
    except Exception:
        pass
    # 2) Yedek: getmac csv ilk satır
    if mac == "bulunamadı":
        try:
            r = subprocess.run("getmac /fo csv /nh", shell=True,
                               capture_output=True, text=True, timeout=15)
            m = re.search(r"([0-9A-Fa-f]{2}-){5}[0-9A-Fa-f]{2}", r.stdout or "")
            if m:
                mac = m.group(0)
        except Exception:
            pass
    return (f"🖥️ Bu PC:\n• MAC: {mac}\n• IP: {ip}\n\n"
            f"Uzaktan açmak için: telefonuna 'Wake on LAN' uygulaması kur, "
            f"bu MAC'i gir. Aynı WiFi'deyken (veya router ayarıyla dışarıdan) "
            f"PC'yi uykudan/kapalıdan uyandırır.")


# ── WoL'u etkinleştir + uyku ipucu ────────────────────────────────────── #
def wol_etkinlestir(parameters: dict | None = None) -> str:
    notlar = []
    try:
        # Ağ kartının PC'yi uyandırmasına izin ver (yönetici gerekebilir)
        subprocess.run(
            'powershell -NoProfile -Command "Get-NetAdapter -Physical | '
            'Where-Object {$_.Status -eq \'Up\'} | '
            'Enable-NetAdapterPowerManagement -ErrorAction SilentlyContinue"',
            shell=True, capture_output=True, timeout=20)
        notlar.append("ağ kartı uyandırma denendi")
    except Exception:
        pass
    return ("⚙️ WoL ayarı denendi. TAM açmak için bir kez şunları yap:\n"
            "1) BIOS → 'Wake on LAN' / 'Power On by PCI-E' → Enabled\n"
            "2) Aygıt Yöneticisi → Ağ Kartı → Güç Yönetimi → "
            "'Bu aygıtın bilgisayarı uyandırmasına izin ver' ✓\n"
            "3) Tam kapatma yerine 'uyut' kullan (uykudan WoL daha güvenilir)\n"
            "Sonra telefon WoL uygulamasıyla açabilirsin. ('wol bilgi' → MAC)")
