"""
Composio Trigger Listener — JARVIS için gerçek zamanlı event dinleyici.

Kullanım:
    listener = ComposioListener(on_event=jarvis_notify)
    listener.start()          # arka planda çalışır
    listener.add_trigger(...)
    listener.stop()
"""

import logging
import os
import threading
from typing import Callable

logger = logging.getLogger(__name__)


class ComposioListener:
    """
    Composio trigger event'lerini arka planda dinler.
    Her event gelince on_event(baslik, mesaj) callback'ini çağırır.
    """

    def __init__(self, on_event: Callable[[str, str], None] | None = None):
        self._on_event   = on_event
        self._api_key    = os.getenv("COMPOSIO_API_KEY", "")
        self._thread: threading.Thread | None = None
        self._stop_flag  = threading.Event()
        self._composio   = None
        self._subscription = None
        self._ready      = False

        if not self._api_key:
            logger.warning("COMPOSIO_API_KEY eksik — trigger listener başlatılmadı.")
            return

        try:
            from composio import Composio  # type: ignore
            self._composio = Composio(api_key=self._api_key)
            logger.info("Composio listener hazırlandı.")
        except Exception as exc:
            logger.warning("Composio başlatılamadı: %s", exc)

    # ── Trigger yönetimi ──────────────────────────────────────────────── #

    def add_trigger(
        self,
        slug: str,
        user_id: str | None = None,
        connected_account_id: str | None = None,
        config: dict | None = None,
    ) -> str | None:
        """
        Yeni bir trigger oluştur ve aktif et.

        Örnek:
            listener.add_trigger("GITHUB_COMMIT_EVENT",
                                 config={"owner": "kullanici_adi", "repo": "repo_adi"})

        Döndürür: trigger_id (başarılıysa) veya None
        """
        if not self._composio:
            return None
        try:
            result = self._composio.triggers.create(
                slug=slug,
                user_id=user_id,
                connected_account_id=connected_account_id,
                trigger_config=config or {},
            )
            tid = getattr(result, "trigger_id", None) or str(result)
            logger.info("Trigger oluşturuldu: %s → %s", slug, tid)
            return tid
        except Exception as exc:
            logger.error("Trigger oluşturulamadı [%s]: %s", slug, exc)
            return None

    def list_active_triggers(self) -> list[dict]:
        """Aktif trigger'ları listele."""
        if not self._composio:
            return []
        try:
            items = self._composio.triggers.list_active()
            return [dict(i) if hasattr(i, '__iter__') else vars(i) for i in items]
        except Exception as exc:
            logger.error("Trigger listesi alınamadı: %s", exc)
            return []

    # ── Dinleme ───────────────────────────────────────────────────────── #

    def start(self):
        """Arka planda trigger event dinlemeyi başlat."""
        if not self._composio or self._thread and self._thread.is_alive():
            return
        self._stop_flag.clear()
        self._thread = threading.Thread(
            target=self._listen_loop,
            name="ComposioListener",
            daemon=True,
        )
        self._thread.start()
        logger.info("Composio trigger listener başladı.")

    def stop(self):
        """Dinlemeyi durdur."""
        self._stop_flag.set()
        if self._subscription:
            try:
                self._subscription._alive = False
            except Exception:
                pass
        logger.info("Composio trigger listener durduruldu.")

    def _listen_loop(self):
        """Arka plan thread: Composio WebSocket'e bağlanır ve event'leri işler."""
        while not self._stop_flag.is_set():
            try:
                logger.info("Composio'ya bağlanılıyor...")
                self._subscription = self._composio.triggers.subscribe(timeout=20.0)

                # Tüm trigger event'lerini yakala
                @self._subscription.handle()
                def _on_any(event):
                    self._handle_event(event)

                logger.info("Composio trigger dinleniyor...")
                self._ready = True
                self._subscription.wait_forever()

            except Exception as exc:
                if self._stop_flag.is_set():
                    break
                logger.warning("Composio bağlantısı kesildi, yeniden bağlanılıyor: %s", exc)
                self._stop_flag.wait(5)   # 5 sn bekle, tekrar dene

        self._ready = False

    def _handle_event(self, event):
        """Gelen trigger event'ini işle ve callback'i çağır."""
        try:
            toolkit = event.get("toolkit_slug", "?")
            trigger = event.get("trigger_slug", "?")
            metadata = event.get("metadata", {})
            data     = metadata.get("trigger_data", {})

            logger.info("Composio event: %s / %s", toolkit, trigger)

            # Okunabilir başlık ve mesaj oluştur
            baslik, mesaj = self._format_event(toolkit, trigger, data)

            if self._on_event:
                self._on_event(baslik, mesaj)

        except Exception as exc:
            logger.error("Event işlenemedi: %s", exc)

    # ── Event formatlayıcı ────────────────────────────────────────────── #

    @staticmethod
    def _format_event(toolkit: str, trigger: str, data: dict) -> tuple[str, str]:
        """
        Toolkit + trigger + data'dan Türkçe başlık ve mesaj üretir.
        Bilinen trigger'lar için özelleştirilmiş format.
        """
        t = toolkit.upper()
        tr = trigger.upper()

        # ── GitHub ─────────────────────────────────────────────────────── #
        if t == "GITHUB":
            if "COMMIT" in tr or "PUSH" in tr:
                repo   = data.get("repository", {}).get("name", "?")
                pusher = data.get("pusher", {}).get("name", data.get("sender", {}).get("login", "?"))
                commits = data.get("commits", [])
                msg_txt = commits[0].get("message", "?") if commits else "?"
                return (
                    f"GitHub — {repo}",
                    f"Efendim, '{pusher}' yeni commit attı: \"{msg_txt}\""
                )
            if "ISSUE" in tr:
                action = data.get("action", "?")
                title  = data.get("issue", {}).get("title", "?")
                user   = data.get("sender", {}).get("login", "?")
                return (
                    "GitHub — Yeni Issue",
                    f"Efendim, '{user}' bir issue {action}: \"{title}\""
                )
            if "PULL" in tr or "PR" in tr:
                title = data.get("pull_request", {}).get("title", "?")
                user  = data.get("sender", {}).get("login", "?")
                return (
                    "GitHub — Pull Request",
                    f"Efendim, '{user}' PR açtı: \"{title}\""
                )
            if "STAR" in tr:
                user = data.get("sender", {}).get("login", "?")
                repo = data.get("repository", {}).get("name", "?")
                return (
                    "GitHub — Yıldız",
                    f"Efendim, '{user}' '{repo}' reposunu yıldızladı."
                )

        # ── Gmail ──────────────────────────────────────────────────────── #
        if t == "GMAIL":
            sender  = data.get("from", data.get("sender", "?"))
            subject = data.get("subject", "?")
            return (
                "Gmail — Yeni E-posta",
                f"Efendim, '{sender}' kişisinden yeni e-posta: \"{subject}\""
            )

        # ── Google Calendar ────────────────────────────────────────────── #
        if "CALENDAR" in t or "GOOGLECALENDAR" in t:
            summary = data.get("summary", data.get("title", "?"))
            start   = data.get("start", {}).get("dateTime", data.get("start", {}).get("date", "?"))
            return (
                "Google Calendar — Etkinlik",
                f"Efendim, yeni etkinlik: \"{summary}\" — {start}"
            )

        # ── Slack ──────────────────────────────────────────────────────── #
        if t == "SLACK":
            user    = data.get("user", data.get("username", "?"))
            channel = data.get("channel", "?")
            text    = data.get("text", "?")
            return (
                f"Slack — #{channel}",
                f"Efendim, '{user}' Slack'te yazdı: \"{text[:80]}\""
            )

        # ── Genel fallback ─────────────────────────────────────────────── #
        return (
            f"{toolkit} — {trigger}",
            f"Efendim, {toolkit} üzerinden yeni event: {str(data)[:120]}"
        )
