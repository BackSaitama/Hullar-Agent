"""HULLAR batch4 — ses, dosya, AI skilleri."""

from __future__ import annotations

import re
import threading
import time
from pathlib import Path


def _push(text: str):
    try:
        from .notify import push
        push(text)
    except Exception:
        pass


# ── Sesli not al (mikrofon → metin → dosya) ───────────────────────────── #
def sesli_not(parameters: dict | None = None) -> str:
    sure = int((parameters or {}).get("sure", 8))
    try:
        import sounddevice as sd  # type: ignore
        import speech_recognition as sr  # type: ignore
        fs = 16000
        _push(f"🎙️ {sure} sn not için dinliyorum...")
        rec = sd.rec(int(sure * fs), samplerate=fs, channels=1, dtype="int16")
        sd.wait()
        r = sr.Recognizer()
        audio = sr.AudioData(rec.tobytes(), fs, 2)
        metin = r.recognize_google(audio, language="tr-TR")
        # not olarak kaydet
        try:
            from .productivity import take_note
            take_note(parameters={"content": metin})
        except Exception:
            f = Path(__file__).parent.parent / "data" / "sesli_notlar.txt"
            f.parent.mkdir(exist_ok=True)
            with open(f, "a", encoding="utf-8") as fp:
                fp.write(metin + "\n")
        return f"🎙️ Not kaydedildi: {metin}"
    except Exception as exc:
        return f"Anlayamadım: {exc}"


def _extract_sesli_not(msg: str) -> dict:
    m = re.search(r"(\d+)\s*(?:saniye|sn)", msg, re.I)
    return {"sure": int(m.group(1)) if m else 8}


# ── Panodakini çevir ──────────────────────────────────────────────────── #
def pano_cevir(parameters: dict | None = None) -> str:
    try:
        import pyperclip  # type: ignore
        metin = pyperclip.paste().strip()
    except Exception:
        return "Pano okunamadı."
    if not metin:
        return "Pano boş."
    hedef = (parameters or {}).get("target", "tr")
    try:
        from .web_tools import translate_text
        return "🌐 " + translate_text(parameters={"text": metin[:2000], "target": hedef})
    except Exception as exc:
        return f"Çevrilemedi: {exc}"


def _extract_pano_cevir(msg: str) -> dict:
    tgt = "tr"
    for lang, code in [("ingilizce", "en"), ("almanca", "de"), ("türkçe", "tr")]:
        if lang in msg.lower():
            tgt = code
    return {"target": tgt}


# ── Toplu yeniden adlandır ────────────────────────────────────────────── #
def toplu_adlandir(parameters: dict | None = None) -> str:
    p = parameters or {}
    yol = (p.get("path") or "").strip().strip('"')
    onek = (p.get("onek") or "dosya").strip()
    root = Path(yol) if yol else None
    if not root or not root.is_dir():
        return "Kullanım: 'toplu adlandır C:\\klasör foto' → foto1, foto2..."
    try:
        items = sorted([x for x in root.iterdir() if x.is_file()])
        n = 0
        for i, x in enumerate(items, 1):
            hedef = root / f"{onek}{i}{x.suffix}"
            if hedef != x and not hedef.exists():
                x.rename(hedef)
                n += 1
        return f"🔤 {n} dosya yeniden adlandırıldı ({onek}1, {onek}2...)."
    except Exception as exc:
        return f"Adlandırılamadı: {exc}"


def _extract_toplu(msg: str) -> dict:
    yol = re.search(r"([A-Za-z]:\\[^\n]+?)(?:\s+(\w+))?$", msg)
    out = {}
    p = re.search(r"([A-Za-z]:\\[^\s]+)", msg)
    if p:
        out["path"] = p.group(1)
    o = re.search(r"[A-Za-z]:\\[^\s]+\s+(\w+)", msg)
    if o:
        out["onek"] = o.group(1)
    return out


# ── Ses dosyasını metne çevir (transkript) ────────────────────────────── #
def ses_transkript(parameters: dict | None = None) -> str:
    yol = (parameters or {}).get("path", "").strip().strip('"')
    if not yol or not Path(yol).exists():
        return "Kullanım: 'ses metne çevir C:\\yol\\ses.mp3'"
    try:
        import subprocess
        import speech_recognition as sr  # type: ignore
        wav = str(Path(yol).with_suffix(".__tmp.wav"))
        subprocess.run(f'ffmpeg -y -i "{yol}" -ar 16000 -ac 1 "{wav}"',
                       shell=True, capture_output=True, timeout=120)
        r = sr.Recognizer()
        with sr.AudioFile(wav) as src:
            audio = r.record(src)
        metin = r.recognize_google(audio, language="tr-TR")
        try:
            Path(wav).unlink()
        except Exception:
            pass
        return f"📝 Transkript:\n{metin[:3000]}"
    except Exception as exc:
        return f"Çevrilemedi: {exc}"


# ── Resimden metin çıkar (OCR → kaydet) ───────────────────────────────── #
def resim_metin(parameters: dict | None = None) -> str:
    yol = (parameters or {}).get("path", "").strip().strip('"')
    if not yol or not Path(yol).exists():
        return "Kullanım: 'resimden metin C:\\yol\\foto.png'"
    try:
        from .smart_click import _ensure_tesseract
        import pytesseract  # type: ignore
        from PIL import Image  # type: ignore
        _ensure_tesseract()
        txt = pytesseract.image_to_string(Image.open(yol), lang="tur+eng").strip()
        if not txt:
            return "Resimde yazı bulunamadı."
        out = Path(yol).with_suffix(".txt")
        out.write_text(txt, encoding="utf-8")
        return f"📖 Metin çıkarıldı → {out.name}\n\n{txt[:1500]}"
    except Exception as exc:
        return f"Okunamadı: {exc}"


# ── Dosya şifrele / çöz (parola ile) ──────────────────────────────────── #
def _key(parola: str):
    import base64
    import hashlib
    return base64.urlsafe_b64encode(hashlib.sha256(parola.encode()).digest())


def dosya_sifrele(parameters: dict | None = None) -> str:
    p = parameters or {}
    yol = (p.get("path") or "").strip().strip('"')
    parola = (p.get("parola") or "").strip()
    coz = p.get("coz", False)
    if not yol or not parola or not Path(yol).exists():
        return "Kullanım: 'dosya şifrele C:\\yol\\dosya parola123' / 'dosya çöz ...'"
    try:
        from cryptography.fernet import Fernet  # type: ignore
        f = Fernet(_key(parola))
        data = Path(yol).read_bytes()
        if coz:
            out = Path(yol).with_suffix("").with_name(Path(yol).stem.replace("_sifreli", "") + "_cozuldu" + Path(yol).suffix.replace(".enc", ""))
            Path(yol if not yol.endswith(".enc") else yol).write_bytes  # noop guard
            cozuk = f.decrypt(data)
            out = Path(str(yol).replace(".enc", "")).with_name("cozuldu_" + Path(str(yol).replace(".enc","")).name)
            out.write_bytes(cozuk)
            return f"🔓 Çözüldü → {out.name}"
        else:
            out = Path(str(yol) + ".enc")
            out.write_bytes(f.encrypt(data))
            return f"🔒 Şifrelendi → {out.name} (çözmek için aynı parola)"
    except Exception as exc:
        return f"İşlenemedi (yanlış parola olabilir): {exc}"


def _extract_sifrele(msg: str) -> dict:
    coz = bool(re.search(r"\b(çöz|coz|decrypt|aç)\b", msg, re.I))
    pth = re.search(r"([A-Za-z]:\\[^\s]+)", msg)
    par = re.search(r"[A-Za-z]:\\[^\s]+\s+(\S+)", msg)
    return {"path": pth.group(1) if pth else "", "parola": par.group(1) if par else "",
            "coz": coz}


# ── Kod hatası açıkla (ekrandaki hatayı oku → AI) ─────────────────────── #
def kod_hatasi(parameters: dict | None = None) -> str:
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
        return "🐞 " + _ask_ai(
            "Ekranda bir kod/hata var. Hatayı bul, Türkçe kısa açıkla ve çözümü ver.",
            metin)
    except Exception as exc:
        return f"Çözümlenemedi: {exc}"


# ── Madde madde özetle ────────────────────────────────────────────────── #
def madde_ozet(parameters: dict | None = None) -> str:
    metin = (parameters or {}).get("text", "").strip()
    if not metin:
        return "Özetlenecek metni ver."
    try:
        from .ai_skills import _ask_ai
        return _ask_ai("Bu metni Türkçe, kısa MADDELER halinde özetle (• ile).",
                       metin[:4000])
    except Exception as exc:
        return f"Özetlenemedi: {exc}"


def _extract_madde(msg: str) -> dict:
    t = re.sub(r"\b(madde madde|maddeler|maddeler halinde|özetle|özet)\b", "", msg, flags=re.I)
    return {"text": t.strip(" :-")}


# ── Çevir + sesli oku ─────────────────────────────────────────────────── #
def cevir_seslioku(parameters: dict | None = None) -> str:
    metin = (parameters or {}).get("text", "").strip()
    if not metin:
        return "Çevrilecek metni ver: 'çevir seslioku hello world'"
    try:
        from .web_tools import translate_text
        ceviri = translate_text(parameters={"text": metin, "target": "tr"})
        from .extra_skills import konus
        konus(parameters={"text": ceviri})
        return f"🔊 {ceviri}"
    except Exception as exc:
        return f"Hata: {exc}"


def _extract_cevir_oku(msg: str) -> dict:
    t = re.sub(r"\b(çevir|seslioku|sesli oku|tercüme)\b", "", msg, flags=re.I)
    return {"text": t.strip(" :-")}


# ── Günlük hatırlatıcı (her gün saat X) ───────────────────────────────── #
_GUNLUK = {"on": False}


def gunluk_hatirlatici(parameters: dict | None = None) -> str:
    p = parameters or {}
    if p.get("action") == "stop":
        _GUNLUK["on"] = False
        return "📅 Günlük hatırlatıcı durduruldu."
    saat = (p.get("saat") or "").strip()
    mesaj = (p.get("mesaj") or "Hatırlatma").strip()
    if not saat:
        return "Kullanım: 'her gün 09:00 ilaç içmeyi hatırlat'"
    if _GUNLUK.get("on"):
        return "Zaten bir günlük hatırlatıcı var."
    _GUNLUK["on"] = True

    def _run():
        from datetime import datetime
        hh, mm = (saat.split(":") + ["0"])[:2]
        son = None
        while _GUNLUK.get("on"):
            now = datetime.now()
            key = now.strftime("%Y-%m-%d")
            if now.hour == int(hh) and now.minute == int(mm) and son != key:
                son = key
                _push(f"📅 Hatırlatma: {mesaj}")
                try:
                    from .extra_skills import pc_bildirim
                    pc_bildirim(parameters={"text": mesaj, "sesli": True})
                except Exception:
                    pass
            time.sleep(30)

    threading.Thread(target=_run, daemon=True).start()
    return f"📅 Her gün {saat}'te hatırlatacağım: '{mesaj}'. Durdur: 'günlük hatırlatıcı durdur'."


def _extract_gunluk(msg: str) -> dict:
    if any(w in msg.lower() for w in ("durdur", "iptal", "kapat")):
        return {"action": "stop"}
    saat = re.search(r"(\d{1,2}[:.]\d{2})", msg)
    mesaj = re.search(r"(?:\d{1,2}[:.]\d{2})\s+(.+?)(?:\s*hatırlat|$)", msg, re.I)
    return {"saat": saat.group(1).replace(".", ":") if saat else "",
            "mesaj": (mesaj.group(1).strip() if mesaj else "Hatırlatma")}
