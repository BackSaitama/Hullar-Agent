"""
Büyük ekran bildirimi (overlay) — ayrı süreç olarak çalışır.

pc_bildirim bunu 'pythonw overlay.py [sesli|sessiz]' ile başlatır.
Mesajı data/overlay_msg.txt'den okur. Büyük, ortalanmış, en üstte bir
pencere gösterir; tıklayınca/Esc ile veya ~12 sn sonra kapanır.
"""

import sys
import tkinter as tk
from pathlib import Path

_MSG = Path(__file__).parent.parent / "data" / "overlay_msg.txt"


def main():
    try:
        msg = _MSG.read_text(encoding="utf-8").strip() or "HULLAR"
    except Exception:
        msg = "HULLAR bildirimi"
    sesli = "sesli" in [a.lower() for a in sys.argv]

    if sesli:
        # Birkaç saniye alarm sesi (arka planda — pencere yine açılır)
        def _alarm():
            try:
                import winsound
                for _ in range(5):          # ~5 sn alarm
                    winsound.Beep(880, 300)
                    winsound.Beep(1320, 300)
            except Exception:
                pass
        import threading
        threading.Thread(target=_alarm, daemon=True).start()

    root = tk.Tk()
    root.title("HULLAR")
    root.configure(bg="#0b0f1a")
    root.attributes("-topmost", True)
    try:
        root.attributes("-alpha", 0.96)
    except Exception:
        pass

    sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
    w, h = int(sw * 0.6), int(sh * 0.4)
    x, y = (sw - w) // 2, (sh - h) // 3
    root.geometry(f"{w}x{h}+{x}+{y}")
    root.overrideredirect(True)  # çerçevesiz, temiz görünüm

    frame = tk.Frame(root, bg="#0b0f1a", highlightbackground="#3b82f6",
                     highlightthickness=3)
    frame.pack(fill="both", expand=True)

    tk.Label(frame, text="🔔 HULLAR", font=("Segoe UI", 22, "bold"),
             fg="#3b82f6", bg="#0b0f1a").pack(pady=(28, 10))
    tk.Label(frame, text=msg, font=("Segoe UI", 30, "bold"),
             fg="#ffffff", bg="#0b0f1a", wraplength=int(w * 0.85),
             justify="center").pack(expand=True, padx=30)
    tk.Label(frame, text="(kapatmak için tıkla)", font=("Segoe UI", 11),
             fg="#64748b", bg="#0b0f1a").pack(pady=(0, 18))

    def close(_=None):
        try:
            root.destroy()
        except Exception:
            pass

    root.bind("<Button-1>", close)
    root.bind("<Escape>", close)
    root.after(12000, close)   # 12 sn sonra otomatik kapan
    root.mainloop()


if __name__ == "__main__":
    main()
