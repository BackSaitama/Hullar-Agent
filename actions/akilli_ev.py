"""
HULLAR Akıllı Ev — webhook ile akıllı cihaz kontrolü.

Çalışma mantığı (cihazdan bağımsız): her komut bir URL'e (webhook) tetikler.
IFTTT Webhooks, Home Assistant, Tuya/Smart Life otomasyonu, akıllı priz vb.
hepsi webhook kabul eder. Kullanıcı bir kez tanımlar:

  "akıllı ev ekle ışık aç: https://maker.ifttt.com/trigger/isik_ac/with/key/XXX"

Sonra: "ışığı aç" / "ışığı kapat" / "müziği aç" → o webhook'u tetikler.
Kayıt: data/akilli_ev.json
"""

from __future__ import annotations

import json
import re
from pathlib import Path

_DB = Path(__file__).parent.parent / "data" / "akilli_ev.json"


def _load() -> dict:
    if _DB.exists():
        try:
            return json.loads(_DB.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save(d: dict):
    _DB.parent.mkdir(exist_ok=True)
    _DB.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")


def akilli_ev_ekle(parameters: dict | None = None) -> str:
    p = parameters or {}
    ad = (p.get("ad") or "").strip().lower()
    url = (p.get("url") or "").strip()
    if not ad or not url.startswith("http"):
        return ("Kullanım: 'akıllı ev ekle ışık aç: https://webhook-adresin' "
                "(IFTTT/Home Assistant/akıllı priz webhook'u)")
    d = _load()
    d[ad] = url
    _save(d)
    return f"🏠 '{ad}' eklendi. Artık '{ad}' diyince çalışır."


def _extract_ev_ekle(msg: str) -> dict:
    m = re.search(r"akıllı ev ekle\s+(.+?)\s*[:\-]\s*(https?://\S+)", msg, re.I)
    return {"ad": m.group(1), "url": m.group(2)} if m else {}


def akilli_ev(parameters: dict | None = None) -> str:
    istek = (parameters or {}).get("istek", "").strip().lower()
    d = _load()
    if not d:
        return ("🏠 Henüz akıllı cihaz tanımlı değil. Ekle:\n"
                "'akıllı ev ekle ışık aç: <webhook url>'\n"
                "(IFTTT Webhooks ya da Home Assistant webhook'u kullanabilirsin.)")
    # en iyi eşleşmeyi bul (kelime örtüşmesi)
    kelimeler = set(re.findall(r"\w+", istek))
    en_iyi, skor = None, 0
    for ad, url in d.items():
        ortak = len(kelimeler & set(re.findall(r"\w+", ad)))
        if ortak > skor:
            en_iyi, skor = (ad, url), ortak
    if not en_iyi or skor == 0:
        return "🏠 Tanımlılar: " + ", ".join(d.keys()) + ". Bunlardan birini söyle."
    ad, url = en_iyi
    try:
        import requests
        requests.get(url, timeout=10)
        return f"🏠 '{ad}' tetiklendi."
    except Exception as exc:
        return f"Tetiklenemedi: {exc}"


def akilli_ev_liste(parameters: dict | None = None) -> str:
    d = _load()
    if not d:
        return "Tanımlı akıllı cihaz yok."
    return "🏠 Akıllı cihazlar:\n" + "\n".join(f"• {k}" for k in d)


def _extract_ev(msg: str) -> dict:
    return {"istek": msg}
