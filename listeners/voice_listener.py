"""
Sürekli sesli komut dinleyici.
PyAudio yoksa sounddevice ile otomatik çalışır.
"""

import io
import logging
import wave

from PyQt6.QtCore import QThread, pyqtSignal

logger = logging.getLogger(__name__)


def _get_microphone_backend() -> str:
    """Hangi ses arka ucunun kurulu olduğunu döndür."""
    try:
        import pyaudio  # type: ignore
        pyaudio.PyAudio()
        return "pyaudio"
    except Exception:
        pass
    try:
        import sounddevice  # type: ignore
        return "sounddevice"
    except Exception:
        pass
    return "none"


class VoiceListener(QThread):
    command_received = pyqtSignal(str)
    error_occurred   = pyqtSignal(str)
    listening_started = pyqtSignal()
    speech_detected   = pyqtSignal()   # #14 konuşma başladı (anında kesme için)

    WAKE_WORD = ""
    # "jarvis" yaygın yanlış duyumları (Google STT Türkçe)
    WAKE_VARIANTS = ("jarvis", "carvis", "cervis", "javis", "jervis",
                     "carvıs", "carbis", "carwis", "jarvıs", "çarvis")
    # #29 Özel "acil" kelimeleri → panik komutu
    PANIC_WORDS = ("acil", "panik", "hızlı gizle", "imdat")

    def __init__(self, language: str = "tr-TR", wake_word: str | None = None):
        super().__init__()
        self._language = language
        self._running  = False
        # wake_word verilmezse env, o da yoksa varsayılan "jarvis"
        import os
        self._wake = (wake_word if wake_word is not None
                      else os.getenv("WAKE_WORD", "jarvis")).strip().lower()

    # ------------------------------------------------------------------ #
    #  Ana döngü                                                           #
    # ------------------------------------------------------------------ #
    def run(self):
        try:
            import speech_recognition as sr  # type: ignore
        except ImportError:
            self.error_occurred.emit(
                "SpeechRecognition bulunamadı. pip install speechrecognition çalıştırın."
            )
            return

        backend = _get_microphone_backend()
        logger.info("Ses arka ucu: %s", backend)

        if backend == "pyaudio":
            self._run_pyaudio(sr)
        elif backend == "sounddevice":
            self._run_sounddevice(sr)
        else:
            self.error_occurred.emit(
                "Mikrofon kütüphanesi bulunamadı. "
                "Kurulum betiğini tekrar çalıştırın."
            )

    # ------------------------------------------------------------------ #
    #  PyAudio yolu (standart)                                             #
    # ------------------------------------------------------------------ #
    def _run_pyaudio(self, sr):
        rec = sr.Recognizer()
        rec.dynamic_energy_threshold = True
        rec.pause_threshold = 0.8
        self._running = True

        with sr.Microphone() as source:
            rec.adjust_for_ambient_noise(source, duration=1)
            self.listening_started.emit()
            while self._running:
                try:
                    audio = rec.listen(source, timeout=5, phrase_time_limit=10)
                    self._recognize(rec, audio)
                except sr.WaitTimeoutError:
                    continue
                except Exception as exc:
                    logger.error("PyAudio döngü hatası: %s", exc)

    # ------------------------------------------------------------------ #
    #  SoundDevice yolu (PyAudio yoksa)                                    #
    # ------------------------------------------------------------------ #
    def _run_sounddevice(self, sr):
        import numpy as np          # type: ignore
        import sounddevice as sd    # type: ignore

        RATE      = 16000
        BLOCKSIZE = 8000   # 0.5 sn'lik blok
        SILENCE_THRESHOLD = 500
        MAX_SECONDS = 8

        rec = sr.Recognizer()
        self._running = True
        self.listening_started.emit()
        logger.info("SoundDevice ile dinleniyor...")

        while self._running:
            try:
                frames = []
                silent_blocks = 0
                recording = False

                with sd.InputStream(samplerate=RATE, channels=1,
                                    dtype="int16", blocksize=BLOCKSIZE) as stream:
                    # Enerji tabanlı VAD (Voice Activity Detection)
                    for _ in range(int(RATE / BLOCKSIZE * MAX_SECONDS)):
                        if not self._running:
                            break
                        block, _ = stream.read(BLOCKSIZE)
                        energy = np.abs(block).mean()

                        if energy > SILENCE_THRESHOLD:
                            # #14 — konuşma başlangıcı (güçlü) → anında kesme sinyali
                            if not recording and energy > SILENCE_THRESHOLD * 2.5:
                                self.speech_detected.emit()
                            recording = True
                            silent_blocks = 0
                            frames.append(block.copy())
                        elif recording:
                            silent_blocks += 1
                            frames.append(block.copy())
                            if silent_blocks > 4:   # ~2 sn sessizlik → cümle bitti
                                break

                if not frames or not recording:
                    continue

                # numpy array → WAV bytes → AudioData
                audio_np = np.concatenate(frames, axis=0)
                buf = io.BytesIO()
                with wave.open(buf, "wb") as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(RATE)
                    wf.writeframes(audio_np.tobytes())
                buf.seek(0)

                with sr.AudioFile(buf) as source:
                    audio_data = rec.record(source)

                self._recognize(rec, audio_data)

            except Exception as exc:
                logger.error("SoundDevice döngü hatası: %s", exc)
                self.msleep(500)

    # ------------------------------------------------------------------ #
    #  Ortak tanıma                                                        #
    # ------------------------------------------------------------------ #
    def _recognize(self, rec, audio_data):
        import speech_recognition as sr  # type: ignore
        try:
            text = rec.recognize_google(audio_data, language=self._language).strip()
            if not text:
                return
            logger.info("Tanındı: %s", text)

            # #29 Özel panik kelimesi → wake gerekmez, direkt panik komutu
            low_full = text.lower()
            if any(p in low_full for p in self.PANIC_WORDS):
                self.command_received.emit("panik")
                return

            # Wake word modu: 'jarvis' (veya varyantı) geçmeyen cümleleri yoksay
            if self._wake:
                low = text.lower()
                hit = next((v for v in self.WAKE_VARIANTS if v in low), None)
                if not hit:
                    return
                # Wake word'ü ve sonrasını ayıkla → komut
                idx = low.find(hit)
                text = text[idx + len(hit):].strip(" ,.!?:")
                if not text:
                    # Sadece "Jarvis" denildi → dinlemeye hazır sinyali
                    self.command_received.emit("__WAKE__")
                    return
            self.command_received.emit(text)
        except sr.UnknownValueError:
            pass
        except sr.RequestError as exc:
            logger.warning("Google STT hatası: %s", exc)
            self.error_occurred.emit(f"Ses tanıma hatası: {exc}")

    def stop(self):
        self._running = False
        self.quit()
        self.wait(2000)
