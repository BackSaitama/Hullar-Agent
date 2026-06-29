"""
HULLAR — Telegram botu (long-polling, harici bot kütüphanesi gerektirmez).

Özellikler:
  • Doğal dil komutları → dispatcher beyni (140+ komut) + AI yedek
  • Buton menüsü (inline keyboard) — yazmadan tıklayarak kontrol
  • Ekran görüntüsü / webcam fotoğrafı → Telegram'a foto olarak gelir
  • Dosya transferi:
      - PC → telefon:  "/dosya C:\\yol\\dosya.txt"
      - telefon → PC:  bota dosya/foto gönder → data/indirilen/ klasörüne iner
  • Güvenlik: sadece izinli chat_id'ler (ilk yazana kilitlenir)

Kimlik bilgileri (öncelik): ortam değişkenleri (TELEGRAM_BOT_TOKEN,
TELEGRAM_CHAT_ID) veya data/telegram.json
  {"bot_token": "...", "chat_id": 123, "allowed": [123,456]}

Çalıştır:  python -m hullar telegram
"""

from __future__ import annotations

import json
import logging
import re
import time
from pathlib import Path

import requests  # type: ignore

from hullar.brain import Hullar

logger = logging.getLogger("hullar.telegram")

_JARVIS_ROOT = Path(__file__).parent.parent
_CONFIG = _JARVIS_ROOT / "data" / "telegram.json"
_DOWNLOAD_DIR = _JARVIS_ROOT / "data" / "indirilen"

_API = "https://api.telegram.org/bot{token}/{method}"

# Canlı izleme + gözcü durumu
_LIVE: dict = {"on": False}
_GUARD: dict = {"on": False}


def _find_file(name: str) -> str | None:
    """Masaüstü/İndirilenler/Belgeler altında ada uyan ilk dosyayı bulur."""
    name = name.strip().strip('"').lower()
    roots = [Path.home() / "Desktop", Path.home() / "Downloads",
             Path.home() / "Documents"]
    for root in roots:
        if not root.exists():
            continue
        for p in root.rglob("*"):
            try:
                if p.is_file() and name in p.name.lower():
                    return str(p)
            except Exception:
                continue
    return None


def _active_window_jpeg(quality: int = 70) -> bytes | None:
    """Öndeki pencerenin görüntüsünü JPEG bytes olarak alır."""
    try:
        import io
        import pygetwindow as gw  # type: ignore
        import mss  # type: ignore
        from PIL import Image  # type: ignore
        win = gw.getActiveWindow()
        if not win:
            return None
        left, top, w, h = win.left, win.top, win.width, win.height
        if w <= 0 or h <= 0:
            return None
        with mss.mss() as sct:
            shot = sct.grab({"left": left, "top": top, "width": w, "height": h})
            img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality)
        return buf.getvalue()
    except Exception as exc:
        logger.warning("aktif pencere görüntü hatası: %s", exc)
        return None

# Foto olarak gönderilecek komutlar
_SCREENSHOT_KW = re.compile(r"\b(ekran görüntüsü|ekran goruntusu|screenshot|ekran at|ekran al)\b", re.I)
_WEBCAM_KW = re.compile(r"\b(webcam|kamera|selfie|foto çek|foto cek|fotoğraf çek)\b", re.I)


# ── Kimlik ────────────────────────────────────────────────────────────── #
def _load_creds() -> tuple[str, set[str]]:
    import os
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat = os.getenv("TELEGRAM_CHAT_ID", "")
    allowed: set[str] = set()
    if chat:
        allowed.add(str(chat))
    if _CONFIG.exists():
        try:
            cfg = json.loads(_CONFIG.read_text(encoding="utf-8"))
            token = token or cfg.get("bot_token", "")
            if cfg.get("chat_id"):
                allowed.add(str(cfg["chat_id"]))
            for c in cfg.get("allowed", []):
                allowed.add(str(c))
        except Exception as exc:
            logger.warning("telegram.json okunamadı: %s", exc)
    return token, allowed


# ── Telegram API yardımcıları ─────────────────────────────────────────── #
def _tr_out(text: str) -> str:
    """Çıkışı kullanıcının diline çevirir (HULLAR_LANG=tr ise no-op)."""
    try:
        from actions.i18n import from_turkish
        return from_turkish(text)
    except Exception:
        return text


def _tr_kb(keyboard: dict | None) -> dict | None:
    """Buton etiketlerini kullanıcının diline çevirir (tr ise no-op)."""
    if not keyboard:
        return keyboard
    try:
        from actions.i18n import get_lang, from_turkish_list
        if get_lang() == "tr":
            return keyboard
        rows = keyboard.get("inline_keyboard") or keyboard.get("keyboard")
        if not rows:
            return keyboard
        btns = [b for row in rows for b in row if isinstance(b, dict) and "text" in b]
        if btns:
            yeni = from_turkish_list([b["text"] for b in btns])
            for b, t in zip(btns, yeni):
                b["text"] = t
    except Exception:
        pass
    return keyboard


def _send(token: str, chat_id: str, text: str, keyboard: dict | None = None) -> None:
    text = _tr_out(text)
    keyboard = _tr_kb(keyboard)
    for i in range(0, len(text) or 1, 4000):
        chunk = text[i:i + 4000] or "(boş)"
        payload = {"chat_id": chat_id, "text": chunk}
        if keyboard and i == 0:
            payload["reply_markup"] = json.dumps(keyboard)
        try:
            requests.post(_API.format(token=token, method="sendMessage"),
                          json=payload, timeout=15)
        except Exception as exc:
            logger.warning("sendMessage hatası: %s", exc)


def _send_photo(token: str, chat_id: str, path: str, caption: str = "") -> bool:
    try:
        with open(path, "rb") as f:
            r = requests.post(
                _API.format(token=token, method="sendPhoto"),
                data={"chat_id": chat_id, "caption": caption},
                files={"photo": f}, timeout=60,
            )
        return r.ok
    except Exception as exc:
        logger.warning("sendPhoto hatası: %s", exc)
        return False


def _screen_jpeg(quality: int = 55, scale: float = 1.0) -> bytes | None:
    """Ekranı DİSKE YAZMADAN JPEG bytes olarak yakalar (hızlı, depolama dolmaz)."""
    try:
        import io
        import mss  # type: ignore
        from PIL import Image  # type: ignore
        with mss.mss() as sct:
            mon = sct.monitors[1]
            shot = sct.grab(mon)
            img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
        if scale != 1.0:
            img = img.resize((int(img.width * scale), int(img.height * scale)))
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality)
        return buf.getvalue()
    except Exception as exc:
        logger.warning("ekran yakalama hatası: %s", exc)
        return None


def _send_photo_bytes(token: str, chat_id: str, data: bytes, caption: str = "") -> int | None:
    """JPEG bytes'ı foto olarak gönderir, mesaj id döndürür (canlı izleme için)."""
    try:
        r = requests.post(
            _API.format(token=token, method="sendPhoto"),
            data={"chat_id": chat_id, "caption": caption},
            files={"photo": ("screen.jpg", data, "image/jpeg")}, timeout=30,
        ).json()
        return r.get("result", {}).get("message_id")
    except Exception as exc:
        logger.warning("sendPhoto(bytes) hatası: %s", exc)
        return None


def _edit_photo_bytes(token: str, chat_id: str, message_id: int, data: bytes) -> bool:
    """Var olan foto mesajını YENİ kareyle değiştirir (editMessageMedia)."""
    try:
        media = json.dumps({"type": "photo", "media": "attach://screen"})
        r = requests.post(
            _API.format(token=token, method="editMessageMedia"),
            data={"chat_id": chat_id, "message_id": message_id, "media": media},
            files={"screen": ("screen.jpg", data, "image/jpeg")}, timeout=30,
        )
        return r.ok
    except Exception as exc:
        logger.warning("editMessageMedia hatası: %s", exc)
        return False


def _edit_text(token: str, chat_id: str, message_id: int, text: str,
               keyboard: dict | None = None) -> bool:
    """Var olan mesajın metnini+butonlarını değiştirir (menü için)."""
    text = _tr_out(text)
    keyboard = _tr_kb(keyboard)
    payload = {"chat_id": chat_id, "message_id": message_id, "text": text}
    if keyboard:
        payload["reply_markup"] = json.dumps(keyboard)
    try:
        r = requests.post(_API.format(token=token, method="editMessageText"),
                          json=payload, timeout=15)
        return r.ok
    except Exception as exc:
        logger.warning("editMessageText hatası: %s", exc)
        return False


def _send_document(token: str, chat_id: str, path: str, caption: str = "") -> bool:
    try:
        with open(path, "rb") as f:
            r = requests.post(
                _API.format(token=token, method="sendDocument"),
                data={"chat_id": chat_id, "caption": caption},
                files={"document": f}, timeout=120,
            )
        return r.ok
    except Exception as exc:
        logger.warning("sendDocument hatası: %s", exc)
        return False


def _voice_to_text(token: str, file_id: str) -> str | None:
    """Telegram sesli mesajını indirir → wav'a çevirir → Google STT ile metne."""
    try:
        import subprocess
        import speech_recognition as sr  # type: ignore
        info = requests.get(_API.format(token=token, method="getFile"),
                            params={"file_id": file_id}, timeout=15).json()
        fpath = info.get("result", {}).get("file_path", "")
        if not fpath:
            return None
        url = f"https://api.telegram.org/file/bot{token}/{fpath}"
        ogg = _DOWNLOAD_DIR / "ses.ogg"
        wav = _DOWNLOAD_DIR / "ses.wav"
        _DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
        ogg.write_bytes(requests.get(url, timeout=60).content)
        # ffmpeg ile wav'a çevir (16kHz mono)
        subprocess.run(["ffmpeg", "-y", "-i", str(ogg), "-ar", "16000", "-ac", "1",
                        str(wav)], capture_output=True)
        r = sr.Recognizer()
        with sr.AudioFile(str(wav)) as src:
            audio = r.record(src)
        try:
            return r.recognize_google(audio, language="tr-TR")
        except Exception:
            return r.recognize_google(audio)   # dil tespiti yedeği
    except Exception as exc:
        logger.warning("ses çözme hatası: %s", exc)
        return None


def _tts_ogg(text: str) -> str | None:
    """Metni sese çevirir (Windows SAPI → wav → ogg). Telegram sesli mesaj için."""
    try:
        import subprocess
        _DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
        wav = _DOWNLOAD_DIR / "tts.wav"
        ogg = _DOWNLOAD_DIR / "tts.ogg"
        safe = text.replace("'", "''")[:400]
        ps = (f"Add-Type -AssemblyName System.Speech; "
              f"$s=New-Object System.Speech.Synthesis.SpeechSynthesizer; "
              f"$s.SetOutputToWaveFile('{wav}'); $s.Speak('{safe}'); $s.Dispose()")
        subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                       capture_output=True, timeout=60)
        subprocess.run(["ffmpeg", "-y", "-i", str(wav), "-c:a", "libopus",
                        str(ogg)], capture_output=True, timeout=60)
        return str(ogg) if ogg.exists() else None
    except Exception as exc:
        logger.warning("tts hatası: %s", exc)
        return None


def _send_voice(token: str, chat_id: str, path: str) -> bool:
    try:
        with open(path, "rb") as f:
            r = requests.post(_API.format(token=token, method="sendVoice"),
                              data={"chat_id": chat_id},
                              files={"voice": f}, timeout=60)
        return r.ok
    except Exception as exc:
        logger.warning("sendVoice hatası: %s", exc)
        return False


def _send_video(token: str, chat_id: str, path: str, caption: str = "") -> bool:
    try:
        with open(path, "rb") as f:
            r = requests.post(
                _API.format(token=token, method="sendVideo"),
                data={"chat_id": chat_id, "caption": caption},
                files={"video": f}, timeout=120,
            )
        return r.ok
    except Exception as exc:
        logger.warning("sendVideo hatası: %s", exc)
        return False


def _download_incoming(token: str, file_id: str, suggested_name: str = "") -> str | None:
    """Telegram'dan gelen dosyayı data/indirilen/ klasörüne indirir."""
    try:
        info = requests.get(_API.format(token=token, method="getFile"),
                            params={"file_id": file_id}, timeout=15).json()
        fpath = info.get("result", {}).get("file_path", "")
        if not fpath:
            return None
        url = f"https://api.telegram.org/file/bot{token}/{fpath}"
        data = requests.get(url, timeout=120).content
        _DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
        name = suggested_name or Path(fpath).name or f"dosya_{int(time.time())}"
        dest = _DOWNLOAD_DIR / name
        dest.write_bytes(data)
        return str(dest)
    except Exception as exc:
        logger.warning("dosya indirme hatası: %s", exc)
        return None


# ── Kategorili buton menüsü ───────────────────────────────────────────── #
# Her kategori: (başlık emoji+ad, [(buton etiketi, çalıştırılacak komut), ...])
# Komut metni doğrudan dispatcher'a gider.
_CATEGORIES: dict[str, tuple[str, list[tuple[str, str]]]] = {
    "ekran": ("🖥️ Ekran", [
        ("📷 Ekran görüntüsü", "ekran görüntüsü"),
        ("📡 Canlı izle", "ekranı izle 180"),
        ("🎥 Ekran kaydı 8sn", "ekranı kaydet 8"),
        ("🤳 Webcam", "webcam"),
        ("🖥️ Masaüstünü göster", "masaüstünü göster"),
        ("⬛ Monitörü kapat", "monitörü kapat"),
        ("🌙 Gece modu", "gece modu"),
    ]),
    "sistem": ("💻 Sistem", [
        ("ℹ️ Sistem bilgisi", "sistem bilgisi"),
        ("📊 CPU/RAM", "cpu ram kaç"),
        ("🔋 Pil", "pil durumu"),
        ("🆓 Boş disk", "boş disk alanı"),
        ("📈 En çok RAM", "en çok ram kullananlar"),
        ("📋 Çalışan uygulamalar", "çalışan uygulamalar"),
        ("📂 Son dosyalar", "son dosyalar"),
        ("🧹 Temp temizle", "geçici dosyaları temizle"),
    ]),
    "guc": ("🔌 Güç", [
        ("🔒 Kilitle", "ekranı kilitle"),
        ("😴 Uyku", "uyku moduna al"),
        ("☕ Uyumasın", "uyanık kal"),
        ("🌅 Uyuyabilir", "uykuyu serbest bırak"),
        ("🔁 Yeniden başlat", "bilgisayarı yeniden başlat"),
        ("⛔ Kapat", "bilgisayarı kapat"),
    ]),
    "ses": ("🔊 Ses & Medya", [
        ("🔉 Ses %0", "sesi 0 yap"),
        ("🔈 Ses %30", "sesi 30 yap"),
        ("🔊 Ses %60", "sesi 60 yap"),
        ("📢 Ses %100", "sesi 100 yap"),
        ("🔇 Sustur", "ses kapat"),
        ("⏯️ Oynat/Duraklat", "medya duraklat"),
        ("⏭️ Sonraki", "sonraki şarkı"),
    ]),
    "internet": ("🌐 İnternet", [
        ("⚡ Hız testi", "hız testi"),
        ("🌍 IP bilgisi", "ip adresim"),
        ("📶 WiFi bilgisi", "wifi bilgisi nasıl"),
        ("✅ Bağlantı kontrol", "internet bağlantısı var mı"),
        ("🧼 DNS temizle", "dns temizle"),
    ]),
    "oto": ("🎮 Otomasyon", [
        ("🎮 Oyun moduna geç", "oyun moduna geç"),
        ("🖱️ Oto-tıkla", "saniyede 5 kez tıkla"),
        ("🛑 Tıklamayı durdur", "otomatik tıklamayı durdur"),
        ("⌨️ Space'e 50 bas", "space'e 50 kez bas"),
        ("⛏️ Blok kır 30sn", "30 saniye boyunca blok kır"),
        ("🛑 Kırmayı durdur", "kırmayı durdur"),
        ("🟫 OneBlock bot 10dk", "oneblock 10 dakika"),
        ("🛑 OneBlock durdur", "oneblock durdur"),
        ("☀️ MC: gündüz yap", "mc komut /time set day"),
        ("🎨 MC: yaratıcı mod", "mc komut /gamemode creative"),
        ("🎬 Makrolar", "makrolar"),
        ("🚫 Anti-AFK", "anti afk"),
        ("🪟 Pencere sola", "pencereyi sola yapıştır"),
        ("🪟 Pencere sağa", "pencereyi sağa yapıştır"),
    ]),
    "uygulama": ("🍿 Uygulamalar", [
        ("▶️ YouTube", "youtube aç"),
        ("🎵 Spotify", "spotify aç"),
        ("🎬 Netflix", "netflix aç"),
        ("🎮 Steam", "steam aç"),
        ("💬 Discord", "discord aç"),
        ("🌐 Chrome", "chrome aç"),
    ]),
    "siparis": ("🛒 Sipariş", [
        ("🛒 Trendyol", "trendyol aç"),
        ("🍔 Yemeksepeti", "yemeksepeti aç"),
        ("🛵 Getir", "getir aç"),
        ("💳 Sepeti aç", "sepeti aç"),
    ]),
    "acil": ("🚨 Acil / Bildirim", [
        ("🚨 Panik modu", "panik modu"),
        ("📺 Ekrana mesaj (sessiz)", "ekrana yaz: HULLAR seni arıyor"),
        ("🔊 Ekrana mesaj (sesli)", "ekrana sesli yaz: HULLAR seni arıyor"),
        ("🧹 Tarayıcıları kapat", "tarayıcıları kapat"),
        ("👁️ Gözcü (5dk)", "gözcü 5"),
    ]),
    "akilli": ("🧠 Akıllı", [
        ("📖 Ekrandaki yazıyı oku", "ekrandaki yazıyı oku"),
        ("🧠 Ekranı özetle", "ekranı özetle"),
        ("🔎 Bu ne?", "bu ne"),
        ("🌐 Ekranı çevir", "ekrandaki yazıyı çevir"),
        ("🔳 QR oku", "qr oku"),
        ("👤 Yüz algıla", "yüz algıla"),
        ("🎵 Ne çalıyor?", "ne çalıyor"),
        ("🪟 Aktif pencere", "aktif pencere"),
        ("📤 Son indirileni gönder", "son indirilen gönder"),
        ("🔋 Pil uyarısı aç", "pil uyarısı"),
    ]),
    "guc2": ("⚡ Güç Planı", [
        ("🚀 Performans", "performans moduna geç"),
        ("🔋 Tasarruf", "tasarruf moduna geç"),
        ("⚖️ Dengeli", "güç planı dengeli"),
        ("⏲️ 1 saat sonra kapat", "1 saat sonra kapat"),
        ("⏰ 10 dk sonra uyar", "10 dk sonra uyar: mola zamanı"),
        ("🌅 Sabah rutini", "sabah rutini"),
    ]),
    "arac": ("🧰 Araçlar", [
        ("🕐 Saat/Tarih", "saat kaç"),
        ("🔑 Şifre üret", "şifre üret"),
        ("₿ Bitcoin", "bitcoin kaç"),
        ("🧹 Pano temizle", "panoyu temizle"),
        ("📝 Notlarım", "notlarımı göster"),
        ("🗣️ Sesli söyle (yaz)", "sesli söyle merhaba"),
    ]),
}


_MENU_INTRO = (
    "🤖 HULLAR — bilgisayarını telefondan yönet\n"
    "━━━━━━━━━━━━━━━━━━\n"
    "✍️ EN HIZLI: direkt yaz →\n"
    "   pil · youtube aç · sesi 50 yap · ekran görüntüsü · durum\n"
    "🎙️ Sesli mesaj at → otomatik çalışır\n"
    "📋 /skills → tüm komutlar (örnekli)\n"
    "━━━━━━━━━━━━━━━━━━\n"
    "Aradığını bilmiyorsan 👇 kategori seç:"
)


def _main_menu() -> dict:
    """Ana menü: kategoriler."""
    def b(text, data):
        return {"text": text, "callback_data": data}
    rows, row = [], []
    for key, (title, _) in _CATEGORIES.items():
        row.append(b(title, f"c:{key}"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    return {"inline_keyboard": rows}


def _category_menu(key: str) -> dict | None:
    """Bir kategorinin komut butonları + geri."""
    cat = _CATEGORIES.get(key)
    if not cat:
        return None
    def b(text, data):
        return {"text": text, "callback_data": data}
    _, items = cat
    rows, row = [], []
    for i, (label, _) in enumerate(items):
        row.append(b(label, f"x:{key}:{i}"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([b("⬅️ Ana menü", "home")])
    return {"inline_keyboard": rows}


# ── Bir metin komutunu işle ve uygun şekilde yanıtla ──────────────────── #
def _route(token: str, chat_id: str, brain: Hullar, text: str) -> None:
    t = text.strip()

    # Çok dilli: kullanıcı dili tr değilse mesajı Türkçe'ye çevir (komutlar tr çalışır).
    # /komutlar ve linkler olduğu gibi kalsın.
    if not t.startswith("/") and not re.search(r"https?://", t):
        try:
            from actions.i18n import get_lang, to_turkish
            if get_lang() != "tr":
                t = to_turkish(t)
        except Exception:
            pass

    # Botu kapat (kendini sonlandır) — "bilgisayarı kapat"tan FARKLI
    if re.search(r"\b(botu kapat|botu durdur|bot kapan|kendini kapat|hullar kapat|"
                 r"hullar dur)\b", t, re.I) or t.lower() in ("/kapatbot", "/stopbot"):
        _send(token, chat_id, "👋 HULLAR kapanıyor. Açmak için PC'de start.bat.")
        import os
        os._exit(0)

    # Menü
    if t.lower() in ("/start", "/menu", "menü", "menu"):
        _send(token, chat_id, _MENU_INTRO, _main_menu())
        return

    # SESLİ yanıt: "sesli <komut>" → komutu çalıştır, sonucu SES olarak gönder
    msl = re.match(r"\s*sesli\s+(.+)", t, re.I)
    if msl:
        ic = msl.group(1).strip()
        # "sesli rapor/durum" → durum metni; değilse komutu çalıştır
        if re.match(r"(rapor|durum|özet)", ic, re.I):
            cevap = brain.handle("sistem raporu")
        else:
            cevap = brain.handle(ic)
        cevap = cevap or "Sonuç yok."
        _send(token, chat_id, cevap[:600])
        og = _tts_ogg(cevap[:400])
        if og:
            _send_voice(token, chat_id, og)
        return

    # DURUM: ekran fotosu + sistem özeti tek mesajda
    if t.lower() in ("durum", "durum raporu", "/durum", "pc durum"):
        data = _screen_jpeg(quality=60)
        if data:
            _send_photo_bytes(token, chat_id, data, "📸 Şu anki ekran")
        _send(token, chat_id, brain.handle("sistem raporu"))
        return

    # SON EKRAN: hızlı güncel ekran görüntüsü
    if re.search(r"\b(son ekran|güncel ekran|ekranı (gönder|at))\b", t, re.I):
        data = _screen_jpeg(quality=70)
        if data and _send_photo_bytes(token, chat_id, data, "🖥️ Son ekran"):
            return
        _send(token, chat_id, "Ekran alınamadı.")
        return

    # İNDİR: linkten dosya indir → Telegram'a gönder
    mi = re.match(r"\s*(?:indir|download)\s+(https?://\S+)", t, re.I)
    if mi:
        url = mi.group(1)
        _send(token, chat_id, "⬇️ İndiriliyor...")
        try:
            import urllib.parse
            ad = urllib.parse.unquote(url.split("/")[-1].split("?")[0]) or "dosya"
            dest = _DOWNLOAD_DIR / ad
            _DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(requests.get(url, timeout=120,
                             headers={"User-Agent": "Mozilla/5.0"}).content)
            if not _send_document(token, chat_id, str(dest), ad):
                _send(token, chat_id, f"İndirildi ama gönderilemedi (büyük olabilir): {dest}")
        except Exception as exc:
            _send(token, chat_id, f"İndirilemedi: {exc}")
        return

    # Webcam → foto
    if t.startswith("/webcam") or _WEBCAM_KW.search(t):
        from actions.webcam import capture_photo
        _send(token, chat_id, "📷 Kameradan çekiyorum...")
        path = capture_photo()
        if path and _send_photo(token, chat_id, path, "Webcam"):
            return
        _send(token, chat_id, "Kameraya erişemedim (bağlı değil veya kullanımda).")
        return

    # Canlı izlemeyi durdur
    if re.search(r"\b(izlemeyi durdur|canlı.*durdur|canli.*durdur|izleme dur|stop izle)\b", t, re.I):
        _LIVE["on"] = False
        _send(token, chat_id, "📡 Canlı izleme durduruldu.")
        return

    # Canlı ekran izleme → TEK mesajı güncelle (diske yazmaz, hızlı)
    if t.startswith("/izle") or re.search(r"\b(ekran[ıi]?\s*izle|canlı ekran|canli ekran|ekran[ıi]?\s*takip)\b", t, re.I):
        if _LIVE.get("on"):
            _send(token, chat_id, "Zaten izliyorum. 'izlemeyi durdur' de.")
            return
        m = re.search(r"(\d+)", t)
        sure = min(int(m.group(1)), 300) if m else 60   # saniye
        _LIVE["on"] = True
        first = _screen_jpeg(quality=40, scale=0.6)
        if not first:
            _LIVE["on"] = False
            _send(token, chat_id, "Ekran yakalanamadı.")
            return
        mid = _send_photo_bytes(token, chat_id, first, "📡 Canlı ekran")
        _send(token, chat_id, f"📡 Canlı izleme açık (~{sure} sn). Durdurmak: 'izlemeyi durdur'")

        def _watch(message_id):
            t0 = time.time()
            gecikme = 0.4   # mümkün olduğunca hızlı; 429 olursa kendi yavaşlar
            while _LIVE.get("on") and (time.time() - t0) < sure and message_id:
                c0 = time.time()
                data = _screen_jpeg(quality=35, scale=0.55)
                if data:
                    ok = _edit_photo_bytes(token, chat_id, message_id, data)
                    if ok is False:
                        gecikme = min(gecikme + 0.25, 2.0)   # 429 → yavaşla
                    elif gecikme > 0.4:
                        gecikme = max(0.4, gecikme - 0.1)     # düzeldiyse hızlan
                kalan = gecikme - (time.time() - c0)
                if kalan > 0:
                    time.sleep(kalan)
            _LIVE["on"] = False

        import threading
        threading.Thread(target=_watch, args=(mid,), daemon=True).start()
        return

    # Ekran kaydı → video gönder (sonra dosyayı sil)
    if t.startswith("/kayit") or re.search(r"\b(ekran(ı)?\s*kaydet|ekran kayd|video kaydet|kayda al)\b", t, re.I):
        m = re.search(r"(\d+)", t)
        sec = min(int(m.group(1)), 60) if m else 8
        _send(token, chat_id, f"🎥 {sec} sn ekran kaydı alınıyor...")
        from actions.ekran_kaydi import record_screen
        path = record_screen(sec)
        if path and _send_video(token, chat_id, path, f"🎥 {sec} sn kayıt"):
            try:
                Path(path).unlink()   # gönderince sil (depolama dolmasın)
            except Exception:
                pass
            return
        _send(token, chat_id, "Ekran kaydı yapılamadı.")
        return

    # Ekran görüntüsü → foto (DİSKE YAZMADAN)
    if t.startswith("/ekran") or _SCREENSHOT_KW.search(t):
        data = _screen_jpeg(quality=70)
        if data and _send_photo_bytes(token, chat_id, data, "🖥️ Ekran"):
            return
        _send(token, chat_id, "Ekran görüntüsü alınamadı.")
        return

    # PC → telefon dosya gönder
    if t.lower().startswith("/dosya") or re.match(r"^\s*dosya\s+(gönder|yolla|at)\b", t, re.I):
        m = re.search(r"([A-Za-z]:\\[^\n]+)", t)
        if not m:
            _send(token, chat_id, "Kullanım: /dosya C:\\tam\\yol\\dosya.txt")
            return
        path = m.group(1).strip().strip('"')
        if not Path(path).exists():
            _send(token, chat_id, f"Dosya bulunamadı: {path}")
            return
        if not _send_document(token, chat_id, path, Path(path).name):
            _send(token, chat_id, "Dosya gönderilemedi (çok büyük olabilir, limit 50MB).")
        return

    # Son indirilen dosyayı gönder
    if re.search(r"\b(son indirilen|son indirdiğim|son dosyayı gönder)\b", t, re.I):
        dl = Path.home() / "Downloads"
        files = [p for p in dl.glob("*") if p.is_file()] if dl.exists() else []
        if not files:
            _send(token, chat_id, "İndirilenler boş.")
            return
        newest = max(files, key=lambda p: p.stat().st_mtime)
        _send(token, chat_id, f"📤 Gönderiliyor: {newest.name}")
        if not _send_document(token, chat_id, str(newest), newest.name):
            _send(token, chat_id, "Gönderilemedi (50MB üstü olabilir).")
        return

    # Dosya ara + gönder: "X dosyasını bul gönder" / "/bul X"
    mfind = re.match(r"^/bul\s+(.+)", t, re.I) or \
            re.search(r"\b(.+?)\s*(?:dosyas[ıi]n[ıi]?|dosyay[ıi])?\s*(?:bul|ara)\b.{0,15}\b(gönder|yolla|at|getir)\b", t, re.I)
    if mfind:
        ad = (mfind.group(1) if t.lower().startswith("/bul") else mfind.group(1)).strip()
        _send(token, chat_id, f"🔎 '{ad}' aranıyor...")
        hit = _find_file(ad)
        if not hit:
            _send(token, chat_id, f"'{ad}' bulunamadı (Masaüstü/İndirilenler/Belgeler).")
            return
        _send(token, chat_id, f"📤 Bulundu: {Path(hit).name}")
        if not _send_document(token, chat_id, hit, Path(hit).name):
            _send(token, chat_id, "Gönderilemedi (50MB üstü olabilir).")
        return

    # Aktif (öndeki) pencerenin görüntüsü
    if re.search(r"\b(aktif pencere|öndeki pencere|açık pencere(yi)? göster|şu an açık olan)\b", t, re.I):
        data = _active_window_jpeg()
        if data and _send_photo_bytes(token, chat_id, data, "🪟 Aktif pencere"):
            return
        _send(token, chat_id, brain.handle("aktif pencere"))
        return

    # Gözcü modu: her N dakikada otomatik ekran fotosu
    if re.search(r"\b(gözcü|gozcu|gözetle|gozetle|takip modu)\b", t, re.I):
        if "durdur" in t.lower() or "kapat" in t.lower():
            _GUARD["on"] = False
            _send(token, chat_id, "👁️ Gözcü kapatıldı.")
            return
        m = re.search(r"(\d+)\s*(?:dakika|dk)", t, re.I)
        dk = max(1, int(m.group(1))) if m else 5
        _GUARD["on"] = True
        _send(token, chat_id, f"👁️ Gözcü açık — her {dk} dk'da ekran fotosu gelir. Durdurmak: 'gözcü durdur'")
        def _guard():
            while _GUARD.get("on"):
                time.sleep(dk * 60)
                if not _GUARD.get("on"):
                    break
                d = _screen_jpeg(quality=50, scale=0.7)
                if d:
                    _send_photo_bytes(token, chat_id, d, "👁️ Gözcü")
        import threading
        threading.Thread(target=_guard, daemon=True).start()
        return

    # Normal: beyin (t zaten Türkçe'ye çevrildi; çıkışı _send çevirir)
    reply = brain.handle(t)
    _send(token, chat_id, reply or "(cevap yok)")


def _handle_callback(token: str, brain: Hullar, cb: dict, allowed: set[str]) -> None:
    data = cb.get("data", "")
    chat_id = str(cb.get("message", {}).get("chat", {}).get("id", ""))
    cb_id = cb.get("id", "")
    # Tıklamayı onayla (saatin dönmesini durdurur)
    try:
        requests.post(_API.format(token=token, method="answerCallbackQuery"),
                      json={"callback_query_id": cb_id}, timeout=10)
    except Exception:
        pass
    if chat_id not in allowed:
        return

    # Tıklanan menü mesajının id'si — onu YERİNDE güncelle (yeni menü açma)
    mid = cb.get("message", {}).get("message_id")

    # Ana menü → aynı mesajı düzenle
    if data in ("home", "menu"):
        _edit_text(token, chat_id, mid, _MENU_INTRO, _main_menu())
        return

    # Kategori aç → aynı mesajı o kategorinin butonlarıyla değiştir
    if data.startswith("c:"):
        key = data[2:]
        kb = _category_menu(key)
        if kb:
            title = _CATEGORIES[key][0]
            _edit_text(token, chat_id, mid,
                       f"{title}\nBir komuta dokun (ya da direkt yazabilirsin):", kb)
        return

    # Komut çalıştır: x:<kategori>:<index> → sonucu ayrı mesaj, menü durur
    if data.startswith("x:"):
        try:
            _, key, idx = data.split(":", 2)
            label, cmd = _CATEGORIES[key][1][int(idx)]
            _route(token, chat_id, brain, cmd)
        except Exception as exc:
            logger.error("callback komut hatası: %s", exc)
        return


# Tek instance kilidi (iki bot aynı anda çalışıp menüyü 2 kez açmasın)
_MUTEX = None


def _acquire_single_instance() -> bool:
    """Windows named mutex; başka instance çalışıyorsa False döner."""
    global _MUTEX
    try:
        import ctypes
        _MUTEX = ctypes.windll.kernel32.CreateMutexW(None, False, "HULLAR_BOT_SINGLETON")
        ERROR_ALREADY_EXISTS = 183
        return ctypes.windll.kernel32.GetLastError() != ERROR_ALREADY_EXISTS
    except Exception:
        return True  # mutex kurulamazsa engelleme


# ── Ana döngü ─────────────────────────────────────────────────────────── #
def _sistemi_uyanik_tut():
    """PC'yi uyumaktan alıkoyar (ekran kapanabilir ama sistem açık kalır →
    bot her zaman erişilebilir). ES_DISPLAY yok → monitör normal kapanır."""
    try:
        import ctypes
        ES_CONTINUOUS = 0x80000000
        ES_SYSTEM_REQUIRED = 0x00000001
        ctypes.windll.kernel32.SetThreadExecutionState(
            ES_CONTINUOUS | ES_SYSTEM_REQUIRED)
    except Exception:
        pass


def run() -> None:
    if not _acquire_single_instance():
        print("⚠️ HULLAR botu zaten çalışıyor (tek instance). Çıkılıyor.")
        return

    _sistemi_uyanik_tut()   # ekran kapalıyken/uyku yerine açık kalsın

    token, allowed = _load_creds()
    if not token:
        print("❌ Telegram bot token'ı yok.")
        print("   data/telegram.json oluştur:")
        print('   {"bot_token": "BOTFATHER_TOKEN", "chat_id": SENIN_CHAT_ID}')
        print("   veya ortam değişkeni: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID")
        return

    brain = Hullar()

    # Bağlantıyı tekrar tekrar dene — ağ geç gelirse/giderse bot ölmesin
    bot_name = "?"
    deneme = 0
    while True:
        try:
            me = requests.get(_API.format(token=token, method="getMe"), timeout=15).json()
            if me.get("ok"):
                bot_name = me.get("result", {}).get("username", "?")
                print(f"✅ HULLAR Telegram'da aktif: @{bot_name}")
                break
        except Exception as exc:
            deneme += 1
            print(f"⏳ Telegram'a bağlanılamadı (deneme {deneme}), 15 sn sonra tekrar... [{exc}]")
            time.sleep(15)

    if allowed:
        print(f"   İzinli chat: {', '.join(allowed)}")
    else:
        print("   ⚠️ İzinli chat yok — İLK yazana kilitlenecek.")
    print("   Komutlar: /menu (buton paneli), /webcam, /ekran, /dosya <yol>")

    offset = 0
    while True:
        try:
            resp = requests.get(
                _API.format(token=token, method="getUpdates"),
                params={"offset": offset, "timeout": 30,
                        "allowed_updates": json.dumps(["message", "callback_query"])},
                timeout=40,
            ).json()
        except Exception as exc:
            logger.warning("getUpdates hatası: %s", exc)
            time.sleep(3)
            continue

        for upd in resp.get("result", []):
            offset = upd["update_id"] + 1

            # Buton tıklaması
            if "callback_query" in upd:
                try:
                    _handle_callback(token, brain, upd["callback_query"], allowed)
                except Exception as exc:
                    logger.error("callback hatası: %s", exc)
                continue

            msg = upd.get("message") or upd.get("edited_message")
            if not msg:
                continue
            chat_id = str(msg.get("chat", {}).get("id", ""))

            # İlk yazana kilitlen
            if not allowed:
                allowed.add(chat_id)
                print(f"   🔒 Bot {chat_id} chat'ine kilitlendi.")
            if chat_id not in allowed:
                _send(token, chat_id, "⛔ Yetkin yok.")
                continue

            # Gelen dosya/foto → PC'ye indir
            doc = msg.get("document")
            photos = msg.get("photo")
            if doc:
                name = doc.get("file_name", "")
                path = _download_incoming(token, doc["file_id"], name)
                _send(token, chat_id, f"📥 Dosya indirildi: {path}" if path
                      else "Dosya indirilemedi.")
                continue
            if photos:
                fid = photos[-1]["file_id"]   # en büyük boyut
                path = _download_incoming(token, fid, f"foto_{int(time.time())}.jpg")
                _send(token, chat_id, f"📥 Fotoğraf indirildi: {path}" if path
                      else "Fotoğraf indirilemedi.")
                continue

            # Sesli mesaj → metne çevir → çalıştır
            voice = msg.get("voice") or msg.get("audio")
            if voice:
                _send(token, chat_id, "🎙️ Sesi çözüyorum...")
                metin = _voice_to_text(token, voice["file_id"])
                if not metin:
                    _send(token, chat_id, "Sesi anlayamadım, tekrar dener misin?")
                    continue
                _send(token, chat_id, f"🗣️ Anladım: {metin}")
                try:
                    _route(token, chat_id, brain, metin)
                except Exception as exc:
                    _send(token, chat_id, f"Hata: {exc}")
                continue

            text = msg.get("text", "")
            if not text:
                continue
            logger.info("[%s] %s", chat_id, text)
            try:
                _route(token, chat_id, brain, text)
            except Exception as exc:
                logger.error("route hatası: %s", exc)
                _send(token, chat_id, f"Hata: {exc}")


if __name__ == "__main__":
    run()
