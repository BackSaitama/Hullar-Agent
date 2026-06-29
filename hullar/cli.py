"""
HULLAR — CMD / REPL arayüzü (Hermes 'chat' gibi).

Kullanım:
    python -m hullar          # interaktif
    python -m hullar "saat kaç"   # tek komut
"""

from __future__ import annotations

import sys

from hullar.brain import Hullar


def _print(text: str) -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    print(text)


def run(argv: list[str] | None = None) -> None:
    argv = argv if argv is not None else sys.argv[1:]
    brain = Hullar()

    # Tek seferlik komut: python -m hullar "mesaj"
    if argv:
        _print(brain.handle(" ".join(argv)))
        return

    # İnteraktif mod
    _print("╭─ HULLAR ─ Windows asistanı (çıkış: 'q' veya Ctrl+C)")
    _print("│  Komutlarını yaz, ben yapayım.\n")
    while True:
        try:
            msg = input("● ").strip()
        except (EOFError, KeyboardInterrupt):
            _print("\nGörüşürüz Efendim.")
            break
        if msg.lower() in ("q", "quit", "exit", "çık", "cik"):
            _print("Görüşürüz Efendim.")
            break
        if not msg:
            continue
        _print(brain.handle(msg))


if __name__ == "__main__":
    run()
