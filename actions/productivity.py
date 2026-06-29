"""Verimlilik araçları: zamanlayıcı, not, takvim, hesap, şifre üretici, Pomodoro."""

import math
import os
import random
import re
import secrets
import string
import subprocess
import threading
import time
import webbrowser
from datetime import datetime
from pathlib import Path

# Not dosyası konumu
_NOTES_FILE = Path.home() / ".jarvis" / "notes.txt"
_NOTES_FILE.parent.mkdir(parents=True, exist_ok=True)

# Aktif zamanlayıcılar {id: threading.Timer}
_timers: dict[str, threading.Timer] = {}


def _notify(title: str, message: str):
    """Windows toast bildirimi."""
    try:
        from plyer import notification  # type: ignore
        notification.notify(title=title, message=message, timeout=10)
    except Exception:
        subprocess.run(
            f'msg * /TIME:15 "{message}"', shell=True,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )


# ── Zamanlayıcı ─────────────────────────────────────────────────────── #
def set_timer(parameters: dict, **_) -> str:
    seconds = int((parameters or {}).get("seconds", 0))
    minutes = int((parameters or {}).get("minutes", 0))
    label   = (parameters or {}).get("label", "Zamanlayıcı")
    total   = seconds + minutes * 60
    if total <= 0:
        return "Efendim, süre belirtir misiniz?"

    tid = f"timer_{int(time.time())}"

    def _fire():
        _notify("JARVIS Zamanlayıcı", f"{label} — {total // 60}:{total % 60:02d} doldu!")
        _timers.pop(tid, None)

    t = threading.Timer(total, _fire)
    t.daemon = True
    t.start()
    _timers[tid] = t

    m, s = divmod(total, 60)
    return f"Efendim, {m} dakika {s} saniye zamanlayıcı başlatıldı: '{label}'"


def cancel_timer(parameters: dict, **_) -> str:
    if not _timers:
        return "Efendim, aktif zamanlayıcı yok."
    for tid, t in list(_timers.items()):
        t.cancel()
        _timers.pop(tid)
    return "Efendim, tüm zamanlayıcılar iptal edildi."


# ── Pomodoro ─────────────────────────────────────────────────────────── #
_pomodoro_timer: threading.Timer | None = None


def pomodoro(parameters: dict, **_) -> str:
    global _pomodoro_timer
    work_min  = int((parameters or {}).get("work", 25))
    break_min = int((parameters or {}).get("break", 5))

    def _work_done():
        _notify("JARVIS Pomodoro", f"{work_min} dakika çalışma bitti! {break_min} dk mola.")

    if _pomodoro_timer:
        _pomodoro_timer.cancel()
    _pomodoro_timer = threading.Timer(work_min * 60, _work_done)
    _pomodoro_timer.daemon = True
    _pomodoro_timer.start()
    return f"Efendim, {work_min} dakika Pomodoro başlatıldı. Odaklanın!"


# ── Not defteri ──────────────────────────────────────────────────────── #
def take_note(parameters: dict, **_) -> str:
    content = (parameters or {}).get("content", parameters.get("note", "")).strip()
    if not content:
        return "Efendim, not içeriğini belirtir misiniz?"
    ts  = datetime.now().strftime("%Y-%m-%d %H:%M")
    line = f"[{ts}] {content}\n"
    with open(_NOTES_FILE, "a", encoding="utf-8") as f:
        f.write(line)
    return f"Efendim, not kaydedildi: '{content}'"


def read_notes(parameters: dict, **_) -> str:
    if not _NOTES_FILE.exists() or _NOTES_FILE.stat().st_size == 0:
        return "Efendim, kayıtlı not bulunmuyor."
    lines = _NOTES_FILE.read_text(encoding="utf-8").strip().splitlines()
    last  = lines[-10:]  # Son 10 not
    return "Efendim, son notlarınız:\n" + "\n".join(last)


def clear_notes(parameters: dict, **_) -> str:
    _NOTES_FILE.write_text("", encoding="utf-8")
    return "Efendim, tüm notlar silindi."


# ── Hesaplama ────────────────────────────────────────────────────────── #
def calculate(parameters: dict, **_) -> str:
    expr = (parameters or {}).get("expression", parameters.get("ifade", "")).strip()
    if not expr:
        return "Efendim, hesaplanacak ifadeyi belirtir misiniz?"
    # Güvenli eval
    safe = re.sub(r"[^0-9\s\+\-\*\/\(\)\.\,\^sqrt%]", "", expr.replace("^", "**").replace(",", "."))
    try:
        result = eval(safe, {"__builtins__": {}, "sqrt": math.sqrt, "pi": math.pi, "e": math.e})
        return f"Efendim, sonuç: {result}"
    except Exception as exc:
        return f"Efendim, hesaplanamadı: {exc}"


# ── Şifre üretici ────────────────────────────────────────────────────── #
def generate_password(parameters: dict, **_) -> str:
    length  = int((parameters or {}).get("length", 16))
    symbols = (parameters or {}).get("symbols", True)
    chars   = string.ascii_letters + string.digits
    if symbols:
        chars += "!@#$%^&*()-_=+[]{}|;:,.<>?"
    pwd = "".join(secrets.choice(chars) for _ in range(length))
    try:
        import pyperclip  # type: ignore
        pyperclip.copy(pwd)
        return f"Efendim, şifre oluşturuldu ve panoya kopyalandı: {pwd}"
    except Exception:
        return f"Efendim, oluşturulan şifre: {pwd}"


# ── Takvim ───────────────────────────────────────────────────────────── #
def open_calendar(parameters: dict, **_) -> str:
    subprocess.Popen("start outlookcal:", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    webbrowser.open("https://calendar.google.com")
    return "Efendim, takvim açıldı."


def time_date(parameters: dict, **_) -> str:
    now = datetime.now()
    days_tr = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
    months_tr = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
                 "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
    gun  = days_tr[now.weekday()]
    ay   = months_tr[now.month - 1]
    return (
        f"Efendim, şu an saat {now.strftime('%H:%M')}. "
        f"Bugün {gun}, {now.day} {ay} {now.year}."
    )


# ── Zar / Rastgele ───────────────────────────────────────────────────── #
def roll_dice(parameters: dict, **_) -> str:
    sides = int((parameters or {}).get("sides", 6))
    count = int((parameters or {}).get("count", 1))
    results = [random.randint(1, sides) for _ in range(count)]
    total   = sum(results)
    if count == 1:
        return f"Efendim, {sides} yüzlü zar: {results[0]}"
    return f"Efendim, {count}×{sides} yüzlü zar: {results}  Toplam: {total}"


def flip_coin(parameters: dict, **_) -> str:
    return f"Efendim, yazı-tura: {'Yazı ✓' if random.random() > 0.5 else 'Tura ✓'}"


# ── Kelime sayısı ────────────────────────────────────────────────────── #
def word_count(parameters: dict, **_) -> str:
    text = (parameters or {}).get("text", "").strip()
    if not text:
        return "Efendim, kelime sayılacak metni belirtir misiniz?"
    words = len(text.split())
    chars = len(text)
    return f"Efendim, kelime: {words}  |  Karakter: {chars}"
