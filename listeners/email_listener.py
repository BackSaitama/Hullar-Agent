"""
IMAP e-posta dinleyici.
Her N saniyede bir gelen kutusu kontrol edilir;
yeni mesaj varsa `new_email` sinyali yayılır.
"""

import imaplib
import logging
import os
import email as email_lib
from email.header import decode_header

from PyQt6.QtCore import QThread, pyqtSignal

logger = logging.getLogger(__name__)


def _decode_header_value(value: str) -> str:
    parts = decode_header(value)
    result = []
    for part, charset in parts:
        if isinstance(part, bytes):
            result.append(part.decode(charset or "utf-8", errors="replace"))
        else:
            result.append(part)
    return "".join(result)


class EmailListener(QThread):
    """
    Gelen kutusu arka planda izler.
    new_email(sender, subject) sinyali yayar.
    """

    new_email = pyqtSignal(str, str)   # (gönderen, konu)
    error_occurred = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._address = os.getenv("GMAIL_ADDRESS", "")
        self._password = os.getenv("GMAIL_APP_PASSWORD", "")
        self._interval = int(os.getenv("EMAIL_CHECK_INTERVAL", "60"))
        self._running = False
        self._seen_ids: set[bytes] = set()

    def run(self):
        if not self._address or not self._password:
            logger.warning("Gmail kimlik bilgileri .env dosyasında eksik. E-posta dinleyici devre dışı.")
            return

        self._running = True
        logger.info("E-posta dinleyici başladı (%s)", self._address)

        # İlk çalıştırmada mevcut mesajları "görülmüş" say (bildirim verme)
        self._init_seen_ids()

        while self._running:
            try:
                self._check_inbox()
            except Exception as exc:
                logger.error("E-posta kontrol hatası: %s", exc)
                self.error_occurred.emit(str(exc))

            # Belirlenen süre kadar bekle (interrupt'a duyarlı)
            for _ in range(self._interval * 10):
                if not self._running:
                    break
                self.msleep(100)

    def stop(self):
        self._running = False
        self.quit()
        self.wait(3000)

    def _connect(self) -> imaplib.IMAP4_SSL:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(self._address, self._password)
        mail.select("INBOX")
        return mail

    def _init_seen_ids(self):
        try:
            mail = self._connect()
            _, data = mail.search(None, "ALL")
            if data and data[0]:
                self._seen_ids = set(data[0].split())
            mail.logout()
        except Exception as exc:
            logger.warning("İlk e-posta listesi alınamadı: %s", exc)

    def _check_inbox(self):
        mail = self._connect()
        _, data = mail.search(None, "ALL")
        if not data or not data[0]:
            mail.logout()
            return

        all_ids = set(data[0].split())
        new_ids = all_ids - self._seen_ids

        for msg_id in new_ids:
            try:
                _, msg_data = mail.fetch(msg_id, "(RFC822)")
                raw = msg_data[0][1]
                msg = email_lib.message_from_bytes(raw)

                sender = _decode_header_value(msg.get("From", "Bilinmeyen"))
                subject = _decode_header_value(msg.get("Subject", "(Konu yok)"))

                logger.info("Yeni e-posta: %s | %s", sender, subject)
                self.new_email.emit(sender, subject)
                self._seen_ids.add(msg_id)
            except Exception as exc:
                logger.error("E-posta ayrıştırma hatası: %s", exc)

        mail.logout()
