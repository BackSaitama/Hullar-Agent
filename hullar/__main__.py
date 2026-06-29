"""
HULLAR giriş noktası — mod seçer.

    python -m hullar              → CMD interaktif
    python -m hullar "saat kaç"   → tek komut
    python -m hullar telegram     → Telegram botu
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path


def _setup_logging() -> None:
    """Logları data/hullar.log dosyasına yaz (telefondan 'bot logları' ile görülür)."""
    try:
        log_path = Path(__file__).resolve().parent.parent / "data" / "hullar.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        fh = RotatingFileHandler(log_path, maxBytes=512_000, backupCount=2,
                                 encoding="utf-8")
        fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s",
                                          "%H:%M:%S"))
        root = logging.getLogger()
        root.setLevel(logging.INFO)
        if not any(isinstance(h, RotatingFileHandler) for h in root.handlers):
            root.addHandler(fh)
    except Exception:
        pass


def main() -> None:
    # Windows konsolunda emoji/Türkçe için UTF-8'e geç
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass
    _setup_logging()

    args = sys.argv[1:]
    if args and args[0].lower() in ("telegram", "tg", "bot"):
        from hullar.telegram_bot import run
        run()
    else:
        from hullar.cli import run
        run(args)


if __name__ == "__main__":
    main()
