"""
HULLAR Özel Komutlar — kullanıcı kendi komutlarını/sahnelerini tanımlar.

  "komut yarat film modu: ışıkları kapat; ses 30 yap; netflix aç"
  → sonra "film modu" deyince hepsi sırayla çalışır (SAHNE = çoklu eylem).

  "komut yarat selam: ekrana yaz merhaba"
  "komutlarım"          → tanımlıları listele
  "komut sil film modu" → siler

Kayıt: data/ozel_komutlar.json {tetikleyici: "eylem1; eylem2"}
"""

from __future__ import annotations

import json
import re
from pathlib import Path

_DB = Path(__file__).parent.parent / "data" / "ozel_komutlar.json"


def load_custom() -> dict:
    if _DB.exists():
        try:
            return json.loads(_DB.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save(d: dict):
    _DB.parent.mkdir(exist_ok=True)
    _DB.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")


def komut_yarat(parameters: dict | None = None) -> str:
    p = parameters or {}
    ad = (p.get("ad") or "").strip().lower()
    eylem = (p.get("eylem") or "").strip()
    if not ad or not eylem:
        return ("Kullanım: 'komut yarat film modu: ışıkları kapat; ses 30 yap; netflix aç' "
                "(eylemleri ; ile ayır — sahne gibi sırayla çalışır)")
    d = load_custom()
    d[ad] = eylem
    _save(d)
    adimlar = [a.strip() for a in eylem.split(";") if a.strip()]
    return f"✨ '{ad}' komutu kaydedildi ({len(adimlar)} adım). Artık '{ad}' de, hepsi çalışır."


def _extract_yarat(msg: str) -> dict:
    m = re.search(r"komut\s*(?:yarat|ekle|oluştur|tanımla)\s+(.+?)\s*[:\-]\s*(.+)",
                  msg, re.I | re.S)
    return {"ad": m.group(1), "eylem": m.group(2)} if m else {}


def komut_sil(parameters: dict | None = None) -> str:
    ad = (parameters or {}).get("ad", "").strip().lower()
    d = load_custom()
    if ad in d:
        del d[ad]; _save(d)
        return f"🗑️ '{ad}' silindi."
    return f"'{ad}' adlı özel komut yok."


def _extract_sil(msg: str) -> dict:
    m = re.search(r"komut\s*(?:sil|kaldır)\s+(.+)", msg, re.I)
    return {"ad": m.group(1).strip() if m else ""}


def komut_liste(parameters: dict | None = None) -> str:
    d = load_custom()
    if not d:
        return "Henüz özel komut yok. 'komut yarat <ad>: <eylemler>' ile ekle."
    lines = ["✨ Özel komutların:"]
    for ad, eyl in d.items():
        lines.append(f"• {ad} → {eyl[:60]}")
    return "\n".join(lines)


def match_custom(msg: str) -> str | None:
    """Mesaj bir özel komutla eşleşiyorsa o komutun EYLEM dizisini döndürür."""
    low = msg.lower().strip()
    # Yönetim komutlarını ('komut sil/yarat ...') ASLA tetikleme
    if re.match(r"\s*komut\s*(yarat|ekle|oluştur|tanımla|sil|kaldır)\b", low):
        return None
    d = load_custom()
    if not d:
        return None
    if low in d:                       # tam eşleşme
        return d[low]
    # 'X yap' / 'X çalıştır' / 'X başlat' gibi sarmalar
    for ad, eyl in d.items():
        if re.search(rf"\b{re.escape(ad)}\b", low):
            return eyl
    return None
