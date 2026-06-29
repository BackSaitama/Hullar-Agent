"""HULLAR mega1 — güçlü/akıllı skiller."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


def _push(text: str):
    try:
        from .notify import push
        push(text)
    except Exception:
        pass


# ── Uzaktan terminal (her CMD komutunu çalıştır) ──────────────────────── #
def uzak_terminal(parameters: dict | None = None) -> str:
    cmd = (parameters or {}).get("cmd", "").strip()
    if not cmd:
        return "Ne çalıştırayım? Örn: 'çalıştır: ipconfig'"
    # basit güvenlik: format/diskpart gibi yıkıcıları engelle
    if re.search(r"\b(format|diskpart|del /f /s /q c:|rmdir /s c:)\b", cmd, re.I):
        return "⛔ Bu komut tehlikeli, çalıştırmadım."
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                           timeout=60, errors="ignore")
        out = (r.stdout or "").strip() or (r.stderr or "").strip() or "(çıktı yok)"
        return f"💻 Çıktı:\n{out[:3500]}"
    except subprocess.TimeoutExpired:
        return "⏱️ Komut 60 sn'de bitmedi (arka planda sürebilir)."
    except Exception as exc:
        return f"Hata: {exc}"


def _extract_terminal(msg: str) -> dict:
    m = re.search(r"(?:çalıştır|calistir|terminal|cmd|komut çalıştır)\s*[:\-]?\s*(.+)",
                  msg, re.I)
    return {"cmd": m.group(1).strip() if m else ""}


# ── Kod çalıştır (Python REPL) ────────────────────────────────────────── #
def kod_calistir(parameters: dict | None = None) -> str:
    kod = (parameters or {}).get("kod", "").strip()
    if not kod:
        return "Çalıştırılacak Python kodunu ver. Örn: 'python çalıştır: print(2**10)'"
    try:
        tmp = Path(__file__).parent / "generated" / "repl_tmp.py"
        tmp.parent.mkdir(exist_ok=True)
        tmp.write_text(kod, encoding="utf-8")
        r = subprocess.run([sys.executable, str(tmp)], capture_output=True,
                           text=True, timeout=30, errors="ignore")
        out = (r.stdout or "").strip()
        err = (r.stderr or "").strip()
        sonuc = out or "(çıktı yok)"
        if err:
            sonuc += f"\n⚠️ {err[-500:]}"
        return f"🐍 Sonuç:\n{sonuc[:3000]}"
    except subprocess.TimeoutExpired:
        return "⏱️ Kod 30 sn'de bitmedi."
    except Exception as exc:
        return f"Hata: {exc}"


def _extract_kod_calistir(msg: str) -> dict:
    m = re.search(r"(?:python|kod)\s*(?:çalıştır|calistir|run)\s*[:\-]?\s*(.+)",
                  msg, re.I | re.S)
    return {"kod": m.group(1).strip() if m else ""}


# ── Soru/ödev çöz (ekrandaki soruyu AI çözer) ─────────────────────────── #
def soru_coz(parameters: dict | None = None) -> str:
    try:
        from .power_skills import ekran_oku
        raw = ekran_oku()
    except Exception as exc:
        return f"Ekran okunamadı: {exc}"
    if not raw.startswith("📖"):
        return raw
    metin = raw.replace("📖 Ekrandaki yazı:\n", "")[:2500]
    try:
        from .ai_skills import _ask_ai
        return "✏️ " + _ask_ai(
            "Ekranda bir soru var. Soruyu çöz, Türkçe KISA ve net cevap + "
            "gerekiyorsa tek satır açıklama ver.", metin)
    except Exception as exc:
        return f"Çözülemedi: {exc}"


# ── Web'de araştır (ara + AI özet) ────────────────────────────────────── #
def arastir(parameters: dict | None = None) -> str:
    konu = (parameters or {}).get("konu", "").strip()
    if not konu:
        return "Ne araştırayım? Örn: 'araştır: kuantum bilgisayar'"
    metin = ""
    try:
        import requests, urllib.parse
        # DuckDuck Go instant answer + html snippet
        u = "https://duckduckgo.com/html/?q=" + urllib.parse.quote(konu)
        html = requests.get(u, timeout=12, headers={"User-Agent": "Mozilla/5.0"}).text
        snips = re.findall(r'result__snippet[^>]*>(.*?)</a>', html, re.S)[:5]
        metin = " ".join(re.sub(r"<[^>]+>", "", s) for s in snips)[:2500]
    except Exception:
        pass
    try:
        from .ai_skills import _ask_ai
        soru = f"Konu: {konu}\n\nWeb özetleri:\n{metin}" if metin else konu
        return "🔎 " + _ask_ai(
            "Kullanıcının sorusunu/konusunu Türkçe, kısa (3-4 cümle) ve doğru yanıtla. "
            "Web özetleri verildiyse onları kullan.", soru)
    except Exception as exc:
        return f"Araştırılamadı: {exc}"


def _extract_arastir(msg: str) -> dict:
    m = re.search(r"(?:araştır|arastir|araştırıp.*söyle|araştır bul)\s*[:\-]?\s*(.+)",
                  msg, re.I)
    return {"konu": m.group(1).strip() if m else re.sub(r"\baraştır\w*\b", "", msg, flags=re.I).strip()}


# ── Döviz / altın (anlık) ─────────────────────────────────────────────── #
def doviz_altin(parameters: dict | None = None) -> str:
    try:
        import requests
        r = requests.get("https://finans.truncgil.com/today.json", timeout=12).json()
        def al(k):
            v = r.get(k, {})
            return v.get("Satış") or v.get("Alış") or "?"
        usd = al("USD"); eur = al("EUR"); gbp = al("GBP")
        gram = al("gram-altin") or al("GRA")
        ceyrek = al("ceyrek-altin")
        return (f"💱 Güncel:\n• Dolar: {usd} ₺\n• Euro: {eur} ₺\n• Sterlin: {gbp} ₺\n"
                f"• Gram Altın: {gram} ₺\n• Çeyrek Altın: {ceyrek} ₺")
    except Exception as exc:
        return f"Kur alınamadı: {exc}"


# ── Tam sağlık raporu ─────────────────────────────────────────────────── #
def tam_saglik(parameters: dict | None = None) -> str:
    lines = ["🩺 Sistem Raporu"]
    try:
        import psutil
        lines.append(f"• CPU: %{psutil.cpu_percent(interval=0.5)}")
        vm = psutil.virtual_memory()
        lines.append(f"• RAM: %{vm.percent} ({vm.used//(1024**3)}/{vm.total//(1024**3)} GB)")
        b = psutil.sensors_battery()
        if b:
            lines.append(f"• Pil: %{int(b.percent)} {'(şarjda)' if b.power_plugged else ''}")
        for part in psutil.disk_partitions():
            try:
                u = psutil.disk_usage(part.mountpoint)
                lines.append(f"• {part.device} %{u.percent} dolu ({u.free//(1024**3)}GB boş)")
            except Exception:
                pass
        net = len([c for c in psutil.net_connections() if c.status == "ESTABLISHED"])
        lines.append(f"• Aktif bağlantı: {net}")
        lines.append(f"• Açık işlem: {len(psutil.pids())}")
    except Exception as exc:
        lines.append(f"(hata: {exc})")
    return "\n".join(lines)


# ── Gizlilik modu (temp + çöp + pano temizle) ─────────────────────────── #
def gizlilik_modu(parameters: dict | None = None) -> str:
    yapilan = []
    try:
        subprocess.run('del /q /s "%TEMP%\\*"', shell=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        yapilan.append("temp")
    except Exception:
        pass
    try:
        subprocess.run("echo off | clip", shell=True)
        yapilan.append("pano")
    except Exception:
        pass
    try:
        subprocess.run('powershell -NoProfile -Command "Clear-RecycleBin -Force -ErrorAction SilentlyContinue"',
                       shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        yapilan.append("çöp kutusu")
    except Exception:
        pass
    return "🕶️ Gizlilik: " + ", ".join(yapilan) + " temizlendi."


# ── Akıllı pano (kopyalananı tanı) ────────────────────────────────────── #
def akilli_pano(parameters: dict | None = None) -> str:
    try:
        import pyperclip
        içerik = pyperclip.paste().strip()
    except Exception:
        return "Pano okunamadı."
    if not içerik:
        return "Pano boş."
    if re.match(r"^https?://", içerik):
        try:
            import webbrowser; webbrowser.open(içerik)
            return f"🔗 Link açıldı: {içerik[:50]}"
        except Exception:
            return f"Link: {içerik}"
    if re.match(r"^[\d\s\+\-\(\)]{7,}$", içerik):
        return f"📞 Telefon numarası: {içerik}"
    if re.search(r"\b(def |import |function|<\w+>|console\.|print\()", içerik):
        return f"💻 Kod tespit edildi ({len(içerik)} karakter). 'python çalıştır:' ile çalıştırabilirim."
    return f"📋 Metin ({len(içerik)} karakter): {içerik[:200]}"


# ── Otomatik cevap öner (gelen mesaja taslak) ─────────────────────────── #
def otomatik_cevap(parameters: dict | None = None) -> str:
    gelen = (parameters or {}).get("mesaj", "").strip()
    if not gelen:
        return "Hangi mesaja cevap önereyim? 'cevap öner: <gelen mesaj>'"
    try:
        from .ai_skills import _ask_ai
        return "💬 Önerilen cevap:\n" + _ask_ai(
            "Sana gelen bir mesaj verilecek. Kibar, kısa, doğal bir Türkçe yanıt "
            "taslağı yaz (sadece yanıt metni).", gelen)
    except Exception as exc:
        return f"Öneremedim: {exc}"


def _extract_cevap(msg: str) -> dict:
    m = re.search(r"(?:cevap öner|yanıt öner|ne cevap)\s*[:\-]?\s*(.+)", msg, re.I)
    return {"mesaj": m.group(1).strip() if m else ""}


# ── Hızlı ayar menüsü (Win+A action center) ───────────────────────────── #
def hizli_ayar(parameters: dict | None = None) -> str:
    try:
        import pyautogui
        pyautogui.hotkey("win", "a")
        return "⚙️ Hızlı ayarlar açıldı (WiFi/Bluetooth/parlaklık)."
    except Exception as exc:
        return f"Açılamadı: {exc}"
