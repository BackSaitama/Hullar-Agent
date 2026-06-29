"""HULLAR rutinleri — telefondan tek komutla çoklu eylem."""

from __future__ import annotations

import subprocess
import time


def _push(text: str):
    try:
        from .notify import push
        push(text)
    except Exception:
        pass


# ── Eve geliyorum (PC'yi hazırla) ─────────────────────────────────────── #
def eve_geliyorum(parameters: dict | None = None) -> str:
    yapilan = []
    try:
        import ctypes
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000000 | 0x00000001)
        yapilan.append("uyanık tutuldu")
    except Exception:
        pass
    for cmd, ad in [("start chrome.exe", "chrome"), ("start spotify:", "spotify")]:
        try:
            subprocess.Popen(cmd, shell=True); yapilan.append(ad)
        except Exception:
            pass
    # akıllı ev "geldim" senaryosu varsa tetikle
    try:
        from .akilli_ev import akilli_ev
        akilli_ev(parameters={"istek": "ışıkları aç"})
    except Exception:
        pass
    return "🏡 Hoş geldin! Hazırladım: " + ", ".join(yapilan) + "."


# ── Kilitle ve raporla (çık + koru) ───────────────────────────────────── #
def kilitle_raporla(parameters: dict | None = None) -> str:
    try:
        from .mega2 import supheli_giris
        supheli_giris(parameters={})   # dokunan olursa webcam+alarm
    except Exception:
        pass
    try:
        subprocess.run("rundll32.exe user32.dll,LockWorkStation", shell=True)
    except Exception:
        pass
    return "🔒 Ekran kilitlendi + koruma açık (biri dokunursa webcam + alarm)."


# ── Bilgisayarı bırak (çıkarken uyut) ─────────────────────────────────── #
def pc_birak(parameters: dict | None = None) -> str:
    def _later():
        time.sleep(2)
        try:
            subprocess.run("rundll32.exe powrprof.dll,SetSuspendState 0,1,0", shell=True)
        except Exception:
            pass
    import threading
    threading.Thread(target=_later, daemon=True).start()
    return "😴 Tamam, bilgisayarı uykuya alıyorum. İyi günler!"
