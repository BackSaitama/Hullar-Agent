"""HULLAR mega2 — sayaç, kayıt, gözetim, akıllı hatırlatıcı."""

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


# ── Ekran sayaç widget (geri sayım overlay) ───────────────────────────── #
def sayac_widget(parameters: dict | None = None) -> str:
    sn = int((parameters or {}).get("saniye", 60))
    sn = max(5, min(sn, 36000))

    def _run():
        try:
            import tkinter as tk
            root = tk.Tk()
            root.overrideredirect(True)
            root.attributes("-topmost", True)
            try:
                root.attributes("-alpha", 0.85)
            except Exception:
                pass
            root.configure(bg="#0b0f1a")
            sw = root.winfo_screenwidth()
            root.geometry(f"260x110+{sw-280}+40")
            lbl = tk.Label(root, font=("Segoe UI", 40, "bold"),
                           fg="#3b82f6", bg="#0b0f1a")
            lbl.pack(expand=True)
            tk.Label(root, text="(tıkla: kapat)", font=("Segoe UI", 9),
                     fg="#64748b", bg="#0b0f1a").pack()
            root.bind("<Button-1>", lambda e: root.destroy())
            state = {"k": sn}

            def tick():
                k = state["k"]
                if k < 0:
                    try:
                        import winsound
                        for _ in range(4):
                            winsound.Beep(1000, 250)
                    except Exception:
                        pass
                    root.destroy()
                    return
                m, s = divmod(k, 60)
                lbl.config(text=f"{m:02d}:{s:02d}",
                           fg="#ef4444" if k <= 10 else "#3b82f6")
                state["k"] -= 1
                root.after(1000, tick)
            tick()
            root.mainloop()
        except Exception:
            pass

    threading.Thread(target=_run, daemon=True).start()
    m, s = divmod(sn, 60)
    return f"⏲️ Ekranda geri sayım başladı: {m:02d}:{s:02d} (bitince alarm)."


def _extract_sayac(msg: str) -> dict:
    total = 0
    h = re.search(r"(\d+)\s*saat", msg, re.I)
    mm = re.search(r"(\d+)\s*(dakika|dk)", msg, re.I)
    s = re.search(r"(\d+)\s*(saniye|sn)", msg, re.I)
    if h: total += int(h.group(1)) * 3600
    if mm: total += int(mm.group(1)) * 60
    if s: total += int(s.group(1))
    if total == 0:
        n = re.search(r"(\d+)", msg)
        total = int(n.group(1)) * 60 if n else 60
    return {"saniye": total}


# ── Toplantı/ders notu (kaydet → yazıya dök → özetle) ─────────────────── #
def toplanti_notu(parameters: dict | None = None) -> str:
    dk = int((parameters or {}).get("dakika", 5))
    dk = max(1, min(dk, 60))
    _push(f"🎙️ {dk} dk kayıt başladı (toplantı notu)...")

    def _run():
        try:
            import sounddevice as sd  # type: ignore
            import speech_recognition as sr  # type: ignore
            import numpy as np  # type: ignore
            fs = 16000
            rec = sd.rec(int(dk * 60 * fs), samplerate=fs, channels=1, dtype="int16")
            sd.wait()
            r = sr.Recognizer()
            # 50 sn'lik parçalara böl (Google limiti)
            metin = []
            parça = 50 * fs
            for i in range(0, len(rec), parça):
                chunk = rec[i:i+parça]
                try:
                    metin.append(r.recognize_google(
                        sr.AudioData(chunk.tobytes(), fs, 2), language="tr-TR"))
                except Exception:
                    continue
            tam = " ".join(metin).strip()
            if not tam:
                _push("🎙️ Kayıtta anlaşılır konuşma yok.")
                return
            try:
                from .ai_skills import _ask_ai
                ozet = _ask_ai("Bu toplantı/ders metnini Türkçe, kısa MADDELER halinde "
                               "özetle (ana noktalar + varsa görevler).", tam[:5000])
            except Exception:
                ozet = tam[:1500]
            _push(f"📝 Toplantı özeti:\n{ozet}")
        except Exception as exc:
            _push(f"Kayıt hatası: {exc}")

    threading.Thread(target=_run, daemon=True).start()
    return f"🎙️ {dk} dk dinleyip özetini Telegram'a göndereceğim."


def _extract_toplanti(msg: str) -> dict:
    m = re.search(r"(\d+)\s*(dakika|dk|saat)", msg, re.I)
    if m:
        return {"dakika": int(m.group(1)) * (60 if "saat" in m.group(2) else 1)}
    return {"dakika": 5}


# ── Sesli kitap (panodaki/verilen metni sesli oku) ────────────────────── #
def sesli_kitap(parameters: dict | None = None) -> str:
    metin = (parameters or {}).get("text", "").strip()
    if not metin:
        try:
            import pyperclip
            metin = pyperclip.paste().strip()
        except Exception:
            metin = ""
    if not metin:
        return "Okunacak metin yok. Bir şey kopyala ya da 'sesli oku: <metin>'."
    try:
        from .extra_skills import konus
        konus(parameters={"text": metin[:1500]})
        return f"📖 Sesli okuyorum ({len(metin)} karakter)."
    except Exception as exc:
        return f"Okunamadı: {exc}"


def _extract_kitap(msg: str) -> dict:
    m = re.search(r"(?:sesli oku|kitap oku|oku bana)\s*[:\-]\s*(.+)", msg, re.I)
    return {"text": m.group(1).strip() if m else ""}


# ── Kim kullandı (sen yokken aktivite logla) ──────────────────────────── #
_KIM = {"on": False, "log": []}


def kim_kullandi(parameters: dict | None = None) -> str:
    p = parameters or {}
    act = p.get("action", "start")
    if act == "report":
        if not _KIM["log"]:
            return "Kayıt yok. Önce 'kim kullandı izle' başlat."
        return "🕵️ Aktivite:\n" + "\n".join(_KIM["log"][-15:])
    if act == "stop":
        _KIM["on"] = False
        return "🕵️ İzleme durduruldu."
    if _KIM.get("on"):
        return "Zaten izliyorum. Rapor için 'kim kullandı raporu'."
    _KIM["on"] = True
    _KIM["log"] = []

    def _run():
        import datetime
        try:
            import pygetwindow as gw  # type: ignore
        except Exception:
            gw = None
        son = None
        ilk = True
        while _KIM.get("on"):
            try:
                if gw:
                    w = gw.getActiveWindow()
                    baslik = (w.title if w else "")[:40]
                    if baslik and baslik != son:
                        ts = datetime.datetime.now().strftime("%H:%M")
                        _KIM["log"].append(f"{ts} — {baslik}")
                        son = baslik
                        if ilk:    # ilk aktivite → webcam + uyarı
                            ilk = False
                            try:
                                from .webcam import capture_photo
                                capture_photo()
                            except Exception:
                                pass
                            _push(f"🕵️ Birisi PC'ni kullanmaya başladı: {baslik}")
            except Exception:
                pass
            time.sleep(8)

    threading.Thread(target=_run, daemon=True).start()
    return "🕵️ İzleme açık — sen yokken kullanılan uygulamaları kaydederim. 'kim kullandı raporu' / 'kim kullandı durdur'."


def _extract_kim(msg: str) -> dict:
    low = msg.lower()
    if "rapor" in low or "göster" in low:
        return {"action": "report"}
    if any(w in low for w in ("durdur", "kapat", "bitir")):
        return {"action": "stop"}
    return {"action": "start"}


# ── Webcam timelapse ──────────────────────────────────────────────────── #
def webcam_timelapse(parameters: dict | None = None) -> str:
    p = parameters or {}
    dk = int(p.get("dakika", 10))
    aralik = int(p.get("aralik", 5))
    dk = max(1, min(dk, 180))

    def _run():
        try:
            import cv2  # type: ignore
            cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
            if not cap.isOpened():
                cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                _push("Kameraya erişilemedi.")
                return
            out_dir = Path.home() / "Desktop" / "hullar" / "data"
            out_dir.mkdir(parents=True, exist_ok=True)
            path = str(out_dir / f"timelapse_{time.strftime('%H%M%S')}.mp4")
            ok, fr = cap.read()
            if not ok:
                cap.release(); return
            h, w = fr.shape[:2]
            vw = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*"mp4v"), 10, (w, h))
            son = time.time() + dk * 60
            while time.time() < son:
                for _ in range(3):
                    cap.read()
                ok, fr = cap.read()
                if ok:
                    vw.write(fr)
                time.sleep(aralik)
            vw.release(); cap.release()
            _push(f"📹 Timelapse hazır: {path}")
        except Exception as exc:
            _push(f"Timelapse hatası: {exc}")

    threading.Thread(target=_run, daemon=True).start()
    return f"📹 Webcam timelapse başladı ({dk} dk, {aralik} sn'de bir kare). Bitince haber veririm."


def _extract_timelapse(msg: str) -> dict:
    out = {}
    m = re.search(r"(\d+)\s*(dakika|dk|saat)", msg, re.I)
    if m:
        out["dakika"] = int(m.group(1)) * (60 if "saat" in m.group(2) else 1)
    return out


# ── Şüpheli giriş (PC'ye dokununca webcam + uyarı) ────────────────────── #
_SUP = {"on": False}


def supheli_giris(parameters: dict | None = None) -> str:
    p = parameters or {}
    if p.get("action") == "stop":
        _SUP["on"] = False
        return "🚨 Koruma kapatıldı."
    if _SUP.get("on"):
        return "Koruma zaten açık."
    _SUP["on"] = True

    def _run():
        try:
            import pyautogui  # type: ignore
        except Exception:
            return
        time.sleep(3)
        baz = pyautogui.position()
        while _SUP.get("on"):
            time.sleep(2)
            try:
                if pyautogui.position() != baz:
                    try:
                        from .webcam import capture_photo
                        capture_photo()
                    except Exception:
                        pass
                    _push("🚨 ALARM! Birisi bilgisayarına dokundu (webcam foto çekildi).")
                    try:
                        import winsound
                        for _ in range(4):
                            winsound.Beep(1200, 300)
                    except Exception:
                        pass
                    _SUP["on"] = False
                    break
            except Exception:
                pass

    threading.Thread(target=_run, daemon=True).start()
    return "🚨 Koruma açık — sen gittikten sonra fareye/PC'ye dokunan olursa webcam foto + alarm. ('koruma durdur')"


def _extract_supheli(msg: str) -> dict:
    return {"action": "stop"} if any(w in msg.lower() for w in ("durdur", "kapat", "iptal")) else {}


# ── Akıllı hatırlatıcı (doğal cümle → zaman + mesaj) ──────────────────── #
def akilli_hatirlatici(parameters: dict | None = None) -> str:
    istek = (parameters or {}).get("istek", "").strip()
    if not istek:
        return "Ne zaman hatırlatayım? Örn: 'akıllı hatırlat: 20 dk sonra çay'"
    dakika = 0
    mesaj = istek
    try:
        from .ai_skills import _ask_ai
        raw = _ask_ai(
            "Kullanıcının hatırlatma isteğini oku. SADECE şu formatta yaz: "
            "DAKIKA|MESAJ . DAKIKA = kaç dakika sonra (tam sayı). "
            "Örnek 'yarım saat sonra ara' → 30|ara . 'akşam 8'de' → şu ana göre dakika hesapla.",
            istek)
        m = re.match(r"\s*(\d+)\s*\|\s*(.+)", raw)
        if m:
            dakika = int(m.group(1)); mesaj = m.group(2).strip()
    except Exception:
        pass
    if dakika <= 0:
        m = re.search(r"(\d+)\s*(dakika|dk)", istek)
        dakika = int(m.group(1)) if m else 10
    def _run():
        time.sleep(dakika * 60)
        _push(f"⏰ Hatırlatma: {mesaj}")
        try:
            from .extra_skills import pc_bildirim
            pc_bildirim(parameters={"text": mesaj, "sesli": True})
        except Exception:
            pass
    threading.Thread(target=_run, daemon=True).start()
    return f"⏰ {dakika} dk sonra hatırlatacağım: {mesaj}"


def _extract_akilli_hat(msg: str) -> dict:
    m = re.search(r"(?:akıllı hatırlat|hatırlat)\s*[:\-]?\s*(.+)", msg, re.I)
    return {"istek": m.group(1).strip() if m else msg}
