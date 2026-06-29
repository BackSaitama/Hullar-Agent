"""
JARVIS Araç Kayıt Defteri (Tool Registry)
Jarvis'in çağırabileceği tüm fonksiyonlar burada tanımlanır.
"""

import os
import webbrowser
import subprocess
import urllib.parse
import logging
from typing import Callable

logger = logging.getLogger(__name__)


class ToolRegistry:
    """
    AI'ın çağırabileceği araçları (fonksiyonları) yönetir.
    Her araç: bir Python fonksiyonu + AI'a açıklayan JSON şeması içerir.
    """

    def __init__(self):
        self._tools: dict[str, dict] = {}
        self._register_defaults()

    # ------------------------------------------------------------------ #
    #  Dahili kayıt yardımcısı                                            #
    # ------------------------------------------------------------------ #
    def register(self, name: str, func: Callable, schema: dict):
        self._tools[name] = {"func": func, "schema": schema}

    def get_schemas(self) -> list[dict]:
        return [t["schema"] for t in self._tools.values()]

    def call(self, name: str, **kwargs) -> str:
        if name not in self._tools:
            return f"Araç bulunamadı: {name}"
        try:
            return self._tools[name]["func"](**kwargs)
        except Exception as exc:
            logger.error("Araç hatası [%s]: %s", name, exc)
            return f"Araç çalışırken hata oluştu: {exc}"

    # ------------------------------------------------------------------ #
    #  Varsayılan araçlar                                                  #
    # ------------------------------------------------------------------ #
    def _register_defaults(self):
        # Yeni skill'leri action modüllerinden bağla
        try:
            from actions.salad import salad_ac, salad_kapat
            from actions.streaming import netflix_ac, twitch_ac, tiktok_ac, twitter_ac, instagram_ac
            from actions.windows_extras import (
                oyun_modu, fokus_modu, parlaklik_ayarla,
                mikrofon_toggle, emoji_paneli, clipboard_gecmis,
            )
            self._salad_ac_fn    = salad_ac
            self._salad_kapat_fn = salad_kapat
            self._netflix_ac_fn  = netflix_ac
            self._twitch_ac_fn   = twitch_ac
            self._tiktok_ac_fn   = tiktok_ac
            self._twitter_ac_fn  = twitter_ac
            self._instagram_ac_fn = instagram_ac
            self._oyun_modu_fn   = oyun_modu
            self._fokus_modu_fn  = fokus_modu
            self._parlaklik_fn   = parlaklik_ayarla
            self._mikrofon_fn    = mikrofon_toggle
            self._emoji_fn       = emoji_paneli
            self._clipboard_fn   = clipboard_gecmis
        except ImportError:
            pass

        self._register_action_tools()

        self.register(
            "youtube_ac",
            self._youtube_ac,
            {
                "name": "youtube_ac",
                "description": (
                    "YouTube'u açar. Kullanıcı 'YouTube aç', 'YouTube'da bir şey izle' veya "
                    "belirli bir video/kanal aramak istediğinde çağır. "
                    "Eğer arama terimi belirtilmemişse sadece YouTube ana sayfasını aç."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "arama": {
                            "type": "string",
                            "description": "YouTube'da aranacak terim (isteğe bağlı, boş bırakılırsa ana sayfa açılır)",
                        }
                    },
                    "required": [],
                },
            },
        )

        self.register(
            "google_ac",
            self._google_ac,
            {
                "name": "google_ac",
                "description": (
                    "Google ana sayfasını açar. Kullanıcı 'Google aç' veya 'tarayıcı aç' dediğinde çağır."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            },
        )

        self.register(
            "salad_baslat",
            self._salad_baslat,
            {
                "name": "salad_baslat",
                "description": (
                    "Salad uygulamasını başlatır. Salad, GPU ile para kazanmayı sağlayan bir platform. "
                    "Kullanıcı 'Salad aç', 'Salad başlat', 'GPU ile para kazan' veya "
                    "'Salad çalıştır' dediğinde çağır."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            },
        )

        self.register(
            "salad_durdur",
            self._salad_durdur,
            {
                "name": "salad_durdur",
                "description": (
                    "Salad uygulamasını kapatır/durdurur. "
                    "Kullanıcı 'Salad kapat', 'Salad durdur' dediğinde çağır."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            },
        )

        self.register(
            "whatsapp_gonder",
            self._whatsapp_gonder,
            {
                "name": "whatsapp_gonder",
                "description": (
                    "Belirtilen kişiye WhatsApp üzerinden mesaj gönderir. "
                    "Kullanıcı birine WhatsApp mesajı göndermesini istediğinde çağır."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "kisi": {
                            "type": "string",
                            "description": "Mesaj gönderilecek kişinin adı veya telefon numarası (+905xxxxxxxxx formatında)",
                        },
                        "mesaj": {
                            "type": "string",
                            "description": "Gönderilecek mesaj metni",
                        },
                    },
                    "required": ["kisi", "mesaj"],
                },
            },
        )

        self.register(
            "email_ac",
            self._email_ac,
            {
                "name": "email_ac",
                "description": (
                    "Tarayıcıda e-posta oluşturma sayfasını açar. "
                    "Kullanıcı birine e-posta göndermek istediğinde çağır."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "alici": {
                            "type": "string",
                            "description": "Alıcının e-posta adresi",
                        },
                        "konu": {
                            "type": "string",
                            "description": "E-postanın konusu",
                        },
                        "icerik": {
                            "type": "string",
                            "description": "E-posta gövdesi/içeriği",
                        },
                    },
                    "required": ["alici"],
                },
            },
        )

        self.register(
            "web_ara",
            self._web_ara,
            {
                "name": "web_ara",
                "description": (
                    "Varsayılan tarayıcıda Google araması yapar veya doğrudan URL açar. "
                    "Kullanıcı internette bir şey aramak istediğinde çağır."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "sorgu": {
                            "type": "string",
                            "description": "Arama sorgusu veya URL",
                        }
                    },
                    "required": ["sorgu"],
                },
            },
        )

        self.register(
            "uygulama_ac",
            self._uygulama_ac,
            {
                "name": "uygulama_ac",
                "description": (
                    "Windows'ta bir uygulama veya program açar. "
                    "Kullanıcı program/uygulama açmak istediğinde çağır."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "uygulama": {
                            "type": "string",
                            "description": "Açılacak uygulamanın adı (örn: notepad, calc, chrome, spotify)",
                        }
                    },
                    "required": ["uygulama"],
                },
            },
        )

        self.register(
            "pano_kopyala",
            self._pano_kopyala,
            {
                "name": "pano_kopyala",
                "description": "Belirtilen metni panoya kopyalar.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "metin": {
                            "type": "string",
                            "description": "Panoya kopyalanacak metin",
                        }
                    },
                    "required": ["metin"],
                },
            },
        )

        # Dosya işlemleri — sağlam yol işleme (LLM \ kaçışıyla uğraşmasın).
        self.register(
            "dosya_olustur", self._dosya_olustur,
            {"name": "dosya_olustur",
             "description": "Yeni bir dosya oluşturur. Kullanıcı 'X dosyası oluştur/aç', "
                            "'masaüstüne not.txt yap' dediğinde çağır. Sadece dosya adını ver; "
                            "konum belirtilmezse masaüstüne koyar.",
             "parameters": {"type": "object", "properties": {
                 "yol": {"type": "string", "description": "Dosya adı veya yolu (örn: 'notlar.txt' veya 'masaüstü/notlar.txt')"},
                 "icerik": {"type": "string", "description": "Dosyanın içeriği (isteğe bağlı)"}},
                 "required": ["yol"]}})
        self.register(
            "klasor_olustur", self._klasor_olustur,
            {"name": "klasor_olustur",
             "description": "Yeni bir klasör oluşturur. 'X klasörü oluştur' deyince çağır. "
                            "Konum yoksa masaüstüne koyar.",
             "parameters": {"type": "object", "properties": {
                 "yol": {"type": "string", "description": "Klasör adı veya yolu"}},
                 "required": ["yol"]}})
        self.register(
            "dosya_listele", self._dosya_listele,
            {"name": "dosya_listele",
             "description": "Bir klasördeki dosyaları listeler. 'masaüstünde/indirilenlerde ne var' "
                            "deyince çağır.",
             "parameters": {"type": "object", "properties": {
                 "klasor": {"type": "string", "description": "masaüstü / indirilenler / belgeler veya tam yol"}},
                 "required": []}})
        self.register(
            "dosya_sil", self._dosya_sil,
            {"name": "dosya_sil",
             "description": "Belirtilen dosyayı siler.",
             "parameters": {"type": "object", "properties": {
                 "yol": {"type": "string", "description": "Silinecek dosya adı/yolu"}},
                 "required": ["yol"]}})

        # Kod/proje üretme — gerçek kaliteli kod yazar (web sitesi, uygulama, oyun, bot, script).
        self.register(
            "proje_olustur", self._proje_olustur,
            {"name": "proje_olustur",
             "description": ("Kullanıcı bir WEB SİTESİ, sayfa, UYGULAMA, OYUN (yılan/tetris/...), "
                             "DİSCORD/TELEGRAM BOT'u, PYTHON programı veya herhangi bir KOD/PROJE "
                             "yazmamı istediğinde çağır. Örn: 'manga satış sitesi yap', 'yılan oyunu', "
                             "'discord bot kodla', 'pyqt ile not defteri yap'. Tek dosya da, "
                             "ÇOK DOSYALI proje de (HTML+CSS+JS ayrı) üretilir."),
             "parameters": {"type": "object", "properties": {
                 "istek": {"type": "string", "description": "Ne yapılacağı; tür/özellik/tema belirt"},
                 "dosya_adi": {"type": "string", "description": "İstenen ad (örn: manga.html, bot.py). Yoksa otomatik."},
                 "cok_dosya": {"type": "boolean", "description": "Birden çok dosya (örn HTML+CSS+JS ayrı) için true. Web projelerinde önerilir."}},
                 "required": ["istek"]}})

        # Mevcut bir siteyi/kodu iyileştir.
        self.register(
            "siteyi_iyilestir", self._siteyi_iyilestir,
            {"name": "siteyi_iyilestir",
             "description": "Var olan bir HTML/CSS/JS/Python dosyasını daha modern, kaliteli, şık hâle getirir. "
                            "'şu siteyi modernleştir', 'bu kodu güzelleştir' deyince çağır.",
             "parameters": {"type": "object", "properties": {
                 "yol": {"type": "string", "description": "Dosya adı veya yolu"},
                 "talep": {"type": "string", "description": "Nasıl iyileştirilsin (boş bırakılabilir)"}},
                 "required": ["yol"]}})

        # Bir HTML'in renk temasını değiştir.
        self.register(
            "tema_degistir", self._tema_degistir,
            {"name": "tema_degistir",
             "description": "Bir HTML dosyasının renk temasını değiştirir. 'siteyi kırmızı temaya çevir' deyince çağır.",
             "parameters": {"type": "object", "properties": {
                 "yol": {"type": "string", "description": "HTML dosyası"},
                 "tema": {"type": "string", "description": "İstenen tema (kırmızı, mavi, koyu, açık, neon, pastel...)"}},
                 "required": ["yol", "tema"]}})

        # Kod açıklama.
        self.register(
            "kod_aciklat", self._kod_aciklat,
            {"name": "kod_aciklat",
             "description": "Bir kod dosyasını okuyup ne yaptığını Türkçe açıklar.",
             "parameters": {"type": "object", "properties": {
                 "yol": {"type": "string", "description": "Açıklanacak dosya"}},
                 "required": ["yol"]}})

        # Kod hatasını bul ve düzelt.
        self.register(
            "kod_duzelt", self._kod_duzelt,
            {"name": "kod_duzelt",
             "description": "Bir kod dosyasındaki hatayı/sorunu bulup düzeltir, dosyayı günceller. "
                            "'şu kodun hatasını düzelt' deyince çağır.",
             "parameters": {"type": "object", "properties": {
                 "yol": {"type": "string", "description": "Düzeltilecek dosya"},
                 "hata": {"type": "string", "description": "Hata mesajı/açıklama (varsa)"}},
                 "required": ["yol"]}})

        # PC temizleme (#42)
        self.register(
            "pc_temizle", self._pc_temizle,
            {"name": "pc_temizle",
             "description": "Temp klasörlerini, çöp kutusunu ve eski log dosyalarını temizler, kazanılan alanı bildirir. "
                            "'pc'yi temizle', 'bilgisayarı temizle' deyince çağır.",
             "parameters": {"type": "object", "properties": {}}})

        # Sesli arama: Spotify / WhatsApp / Telegram (#30, #31)
        self.register(
            "spotify_arat", self._spotify_arat,
            {"name": "spotify_arat",
             "description": "Spotify'ı açar ve belirtilen şarkı/sanatçıyı çalmaya çalışır. "
                            "'spotifyda X çal' deyince çağır.",
             "parameters": {"type": "object", "properties": {
                 "sorgu": {"type": "string", "description": "Çalınacak şarkı/sanatçı"}},
                 "required": ["sorgu"]}})
        self.register(
            "whatsapp_ara", self._whatsapp_ara,
            {"name": "whatsapp_ara",
             "description": "WhatsApp Web üzerinden bir kişiye sesli/görüntülü arama başlatır.",
             "parameters": {"type": "object", "properties": {
                 "kisi": {"type": "string", "description": "Aranacak kişi adı/numarası"}},
                 "required": ["kisi"]}})
        self.register(
            "telegram_ara", self._telegram_ara,
            {"name": "telegram_ara",
             "description": "Telegram'da bir kişi/kullanıcı adı için sohbet/arama açar.",
             "parameters": {"type": "object", "properties": {
                 "kisi": {"type": "string", "description": "Telegram kullanıcı adı (@ olmadan da olur)"}},
                 "required": ["kisi"]}})

        # Kendine özellik ekleme (#48) — JARVIS kendi kodunu yazıp kaydeder.
        self.register(
            "kendine_ozellik_ekle",
            self._kendine_ozellik_ekle,
            {
                "name": "kendine_ozellik_ekle",
                "description": (
                    "Kullanıcı 'kendine X özelliği ekle', 'şunu yapabilen bir özellik yaz' "
                    "gibi KALICI yeni bir yetenek istediğinde kullan. Görevi yapan Python "
                    "kodunu SIFIRDAN yaz; kod plugins/ klasörüne kaydedilir ve hemen "
                    "çalıştırılır. Kod, çalıştırılacak işi 'def calistir():' fonksiyonu "
                    "içine koymalı ve sonucu return etmeli."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "isim": {"type": "string", "description": "Özelliğin kısa adı (dosya adı olur)"},
                        "kod": {"type": "string", "description": "calistir() fonksiyonu içeren Python kodu"},
                    },
                    "required": ["isim", "kod"],
                },
            },
        )

        # Evrensel kod çalıştırıcı — hazır bir araç olmayan HER görev için.
        self.register(
            "kod_calistir",
            self._kod_calistir,
            {
                "name": "kod_calistir",
                "description": (
                    "EVRENSEL KOD ÇALIŞTIRICI. Yukarıdaki hazır araçlardan HİÇBİRİ "
                    "uygun değilse bu aracı kullan. İstediğin görevi yerine getiren "
                    "Python 3 kodunu SIFIRDAN sen yaz; kod arka planda exec() ile "
                    "çalıştırılır. Hesaplama, tarih/saat, dosya okuma/yazma, klasör "
                    "listeleme, sistem bilgisi (psutil), internet isteği (requests), "
                    "metin/veri işleme gibi her şey için uygundur. Sonucu görebilmem "
                    "için kodda MUTLAKA print(...) kullan ya da değeri 'sonuc' adlı "
                    "değişkene ata. İhtiyacın olan modülleri kodun içinde import et."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "kod": {
                            "type": "string",
                            "description": (
                                "Çalıştırılacak Python 3 kaynak kodu. Çıktı için "
                                "print() kullan veya sonucu 'sonuc' değişkenine ata."
                            ),
                        }
                    },
                    "required": ["kod"],
                },
            },
        )

    # ------------------------------------------------------------------ #
    #  Araç implementasyonları                                             #
    # ------------------------------------------------------------------ #
    def _register_action_tools(self):
        """Dispatcher action fonksiyonlarını tool olarak kaydet."""
        _none = lambda **kw: None

        def _wrap(fn, p=None):
            def _call(**kwargs):
                params = p(str(kwargs)) if p else kwargs
                return fn(parameters=params)
            return _call

        # Streaming
        if hasattr(self, "_netflix_ac_fn"):
            self.register("netflix_ac", lambda **_: self._netflix_ac_fn({}), {"name": "netflix_ac", "description": "Netflix açar. 'Netflix aç', 'dizi izlemek istiyorum' deniğinde çağır.", "parameters": {"type": "object", "properties": {}, "required": []}})
            self.register("twitch_ac",  lambda **kw: self._twitch_ac_fn({"kanal": kw.get("kanal", "")}), {"name": "twitch_ac", "description": "Twitch açar. İsteğe bağlı kanal adı alır.", "parameters": {"type": "object", "properties": {"kanal": {"type": "string", "description": "Twitch kanal adı"}}, "required": []}})
            self.register("tiktok_ac",  lambda **_: self._tiktok_ac_fn({}), {"name": "tiktok_ac", "description": "TikTok açar.", "parameters": {"type": "object", "properties": {}, "required": []}})
            self.register("twitter_ac", lambda **_: self._twitter_ac_fn({}), {"name": "twitter_ac", "description": "Twitter/X açar.", "parameters": {"type": "object", "properties": {}, "required": []}})
            self.register("instagram_ac", lambda **_: self._instagram_ac_fn({}), {"name": "instagram_ac", "description": "Instagram açar.", "parameters": {"type": "object", "properties": {}, "required": []}})

        # Salad
        if hasattr(self, "_salad_ac_fn"):
            self.register("salad_baslat", lambda **_: self._salad_ac_fn({}), {"name": "salad_baslat", "description": "Salad GPU kazanç uygulamasını başlatır. 'Salad aç', 'GPU ile para kazan' deniğinde çağır.", "parameters": {"type": "object", "properties": {}, "required": []}})
            self.register("salad_durdur", lambda **_: self._salad_kapat_fn({}), {"name": "salad_durdur", "description": "Salad'ı kapatır.", "parameters": {"type": "object", "properties": {}, "required": []}})

        # Windows extras
        if hasattr(self, "_oyun_modu_fn"):
            self.register("oyun_modu",       lambda **kw: self._oyun_modu_fn(kw), {"name": "oyun_modu", "description": "Windows Oyun Modunu açar/kapatır.", "parameters": {"type": "object", "properties": {"durum": {"type": "string", "description": "aç veya kapat"}}, "required": []}})
            self.register("fokus_modu",       lambda **kw: self._fokus_modu_fn(kw), {"name": "fokus_modu", "description": "Odak/rahatsız etme modunu açar/kapatır.", "parameters": {"type": "object", "properties": {"durum": {"type": "string", "description": "aç veya kapat"}}, "required": []}})
            self.register("parlaklik_ayarla", lambda **kw: self._parlaklik_fn(kw), {"name": "parlaklik_ayarla", "description": "Ekran parlaklığını ayarlar.", "parameters": {"type": "object", "properties": {"yuzde": {"type": "integer", "description": "0-100 arası parlaklık yüzdesi"}}, "required": []}})
            self.register("mikrofon_toggle",  lambda **_: self._mikrofon_fn({}), {"name": "mikrofon_toggle", "description": "Mikrofonu susturur veya açar.", "parameters": {"type": "object", "properties": {}, "required": []}})
            self.register("emoji_paneli",     lambda **_: self._emoji_fn({}), {"name": "emoji_paneli", "description": "Windows emoji panelini açar (Win+.).", "parameters": {"type": "object", "properties": {}, "required": []}})
            self.register("clipboard_gecmis", lambda **_: self._clipboard_fn({}), {"name": "clipboard_gecmis", "description": "Pano geçmişini gösterir (Win+V).", "parameters": {"type": "object", "properties": {}, "required": []}})

    @staticmethod
    def _youtube_ac(arama: str = "") -> str:
        if arama:
            # Önce ilk videoyu bulup OYNAT (pywhatkit), olmazsa arama sayfası
            try:
                import pywhatkit  # type: ignore
                pywhatkit.playonyt(arama)
                return f"Efendim, YouTube'da '{arama}' açılıp oynatılıyor."
            except Exception:
                pass
            url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(arama)}"
            webbrowser.open(url)
            return f"Efendim, YouTube'da '{arama}' arandı."
        else:
            webbrowser.open("https://www.youtube.com")
            return "Efendim, YouTube açıldı."

    @staticmethod
    def _google_ac() -> str:
        webbrowser.open("https://www.google.com")
        return "Efendim, Google açıldı."

    @staticmethod
    def _salad_baslat() -> str:
        # Salad'ın olası kurulum yolları
        salad_paths = [
            r"C:\Program Files\Salad\Salad.exe",
            os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Salad", "Salad.exe"),
            os.path.join(os.environ.get("LOCALAPPDATA", ""), "Salad Technologies", "Salad", "Salad.exe"),
            r"C:\Program Files\Salad Technologies\Salad\Salad.exe",
            r"C:\Program Files (x86)\Salad Technologies\Salad\Salad.exe",
            os.path.join(os.environ.get("APPDATA", ""), "Salad", "Salad.exe"),
        ]

        for path in salad_paths:
            if os.path.exists(path):
                try:
                    subprocess.Popen([path])
                    return f"Efendim, Salad başlatıldı. GPU ile para kazanmaya başlıyorsunuz."
                except Exception as exc:
                    return f"Salad başlatılamadı: {exc}"

        # Bulunamadıysa masaüstünde kısayol ara
        desktop = os.path.join(os.environ.get("USERPROFILE", ""), "Desktop")
        for f in os.listdir(desktop) if os.path.exists(desktop) else []:
            if "salad" in f.lower():
                try:
                    subprocess.Popen(["start", "", os.path.join(desktop, f)], shell=True)
                    return "Efendim, Salad masaüstü kısayolundan başlatıldı."
                except Exception:
                    pass

        # Son çare: Windows'un bulmasına bırak
        try:
            subprocess.Popen("Salad", shell=True)
            return "Efendim, Salad başlatıldı."
        except Exception:
            return (
                "Efendim, Salad bulunamadı. Lütfen Salad'ın kurulu olduğundan emin olun. "
                "salad.com adresinden indirebilirsiniz."
            )

    @staticmethod
    def _salad_durdur() -> str:
        try:
            subprocess.run(["taskkill", "/f", "/im", "Salad.exe"], capture_output=True)
            return "Efendim, Salad durduruldu."
        except Exception as exc:
            return f"Salad durdurulamadı: {exc}"

    @staticmethod
    def _whatsapp_gonder(kisi: str, mesaj: str) -> str:
        try:
            import pywhatkit as kit  # type: ignore

            if not kisi.startswith("+"):
                url = f"https://web.whatsapp.com/send?text={urllib.parse.quote(mesaj)}"
                webbrowser.open(url)
                return (
                    f"Efendim, '{kisi}' için WhatsApp web arayüzü açıldı. "
                    f"Lütfen kişiyi seçip mesajı gönderin."
                )

            import datetime
            now = datetime.datetime.now()
            kit.sendwhatmsg(kisi, mesaj, now.hour, now.minute + 2, wait_time=15)
            return f"Efendim, '{kisi}' numarasına WhatsApp mesajı zamanlandı: \"{mesaj}\""
        except ImportError:
            url = f"https://web.whatsapp.com/send?phone={kisi}&text={urllib.parse.quote(mesaj)}"
            webbrowser.open(url)
            return "Efendim, WhatsApp web arayüzü açıldı."

    @staticmethod
    def _email_ac(alici: str, konu: str = "", icerik: str = "") -> str:
        mailto = f"mailto:{alici}"
        params = []
        if konu:
            params.append(f"subject={urllib.parse.quote(konu)}")
        if icerik:
            params.append(f"body={urllib.parse.quote(icerik)}")
        if params:
            mailto += "?" + "&".join(params)
        webbrowser.open(mailto)
        return f"Efendim, '{alici}' adresine e-posta taslağı açıldı."

    @staticmethod
    def _web_ara(sorgu: str) -> str:
        if sorgu.startswith("http://") or sorgu.startswith("https://"):
            webbrowser.open(sorgu)
            return f"Efendim, '{sorgu}' adresi tarayıcıda açıldı."
        url = f"https://www.google.com/search?q={urllib.parse.quote(sorgu)}"
        webbrowser.open(url)
        return f"Efendim, '{sorgu}' için Google araması açıldı."

    @staticmethod
    def _uygulama_ac(uygulama: str) -> str:
        try:
            subprocess.Popen(uygulama, shell=True)
            return f"Efendim, '{uygulama}' uygulaması başlatıldı."
        except Exception as exc:
            return f"Uygulama açılamadı: {exc}"

    @staticmethod
    def _pano_kopyala(metin: str) -> str:
        try:
            import pyperclip  # type: ignore
            pyperclip.copy(metin)
            return "Efendim, metin panoya kopyalandı."
        except Exception:
            return "Pano işlemi gerçekleştirilemedi."

    @staticmethod
    def _kendine_ozellik_ekle(isim: str, kod: str) -> str:
        """JARVIS'in kendi kodunu yazıp plugins/ altına kaydetmesi (#48)."""
        import re
        from pathlib import Path

        if not kod or not kod.strip():
            return "Eklenecek kod boş Efendim."
        safe = re.sub(r"[^a-zA-Z0-9_]", "_", (isim or "ozellik").strip().lower()) or "ozellik"
        pdir = Path(__file__).parent.parent / "plugins"
        try:
            pdir.mkdir(exist_ok=True)
            (pdir / "__init__.py").touch(exist_ok=True)
            path = pdir / f"{safe}.py"
            path.write_text(kod, encoding="utf-8")
        except Exception as exc:
            return f"Özellik kaydedilemedi: {exc}"

        # Hemen çalıştır (varsa calistir())
        try:
            ns: dict = {"__name__": "__jarvis_plugin__"}
            exec(kod, ns)
            fn = ns.get("calistir")
            if callable(fn):
                sonuc = fn()
                return (f"Efendim, '{safe}' özelliğini yazdım, kaydettim ve çalıştırdım. "
                        f"Sonuç: {sonuc}")
        except Exception as exc:
            return (f"Efendim, '{safe}' kaydedildi (plugins/{safe}.py) ama çalıştırılırken "
                    f"hata oluştu: {exc}")
        return f"Efendim, '{safe}' özelliğini plugins/{safe}.py olarak kaydettim."

    @staticmethod
    def _kod_calistir(kod: str) -> str:
        """
        Evrensel kod çalıştırıcı: modelin sıfırdan yazdığı Python kodunu exec()
        ile çalıştırır ve çıktısını (print + 'sonuc'/'result' değişkeni) metin
        olarak döndürür. Döndürülen çıktı tekrar modele beslenir.
        """
        import io
        import contextlib
        import traceback

        if not kod or not kod.strip():
            return "Çalıştırılacak kod boş."

        buffer = io.StringIO()
        ortam: dict = {"__name__": "__jarvis_exec__"}
        try:
            with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(buffer):
                exec(kod, ortam)
            cikti = buffer.getvalue().strip()
            sonuc = ortam.get("sonuc", ortam.get("result"))
            if sonuc is not None:
                sonuc_str = str(sonuc)
                cikti = f"{cikti}\n{sonuc_str}".strip() if cikti else sonuc_str
            return cikti or "(Kod başarıyla çalıştı, ekrana çıktı verilmedi.)"
        except Exception:
            logger.error("kod_calistir hatası", exc_info=True)
            return "Kod çalıştırılırken hata oluştu:\n" + traceback.format_exc(limit=3)

    # ── Dosya işlemleri (sağlam yol işleme) ──────────────────────────── #
    @staticmethod
    def _coz_yol(yol: str, **kw) -> str:
        """Esnek yol çözücü: 'masaüstü/test.txt', 'test.txt', tam yol → mutlak yol.
        Konum anahtar kelimesi yoksa masaüstüne koyar."""
        import re
        home = os.environ.get("USERPROFILE", "")
        y = (yol or kw.get("dosya_adi") or kw.get("isim") or kw.get("ad")
             or kw.get("path") or kw.get("name") or "yeni_dosya.txt")
        y = str(y).strip().strip("\"'").replace("\\", "/")
        if os.path.isabs(y):
            return os.path.normpath(y)
        low = y.lower()
        if any(k in low for k in ("indir", "download")):
            base = os.path.join(home, "Downloads")
        elif any(k in low for k in ("belge", "document", "döküman", "dokuman")):
            base = os.path.join(home, "Documents")
        else:
            base = os.path.join(home, "Desktop")     # varsayılan
        ad = os.path.basename(y) or y
        ad = re.sub(r"(masa[uü]st[uü]\w*|desktop|indirilenler\w*|downloads|belge\w*|documents)",
                    "", ad, flags=re.I).strip(" /:-'\"")
        return os.path.join(base, ad or "yeni_dosya")

    @staticmethod
    def _dosya_olustur(yol: str = "", icerik: str = "", **kw) -> str:
        try:
            path = ToolRegistry._coz_yol(yol, **kw)
            if "." not in os.path.basename(path):
                path += ".txt"
            os.makedirs(os.path.dirname(path), exist_ok=True)
            content = icerik or kw.get("content") or kw.get("metin") or ""
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            return f"Efendim, dosya oluşturuldu: {path}"
        except Exception as exc:
            return f"Dosya oluşturulamadı: {exc}"

    @staticmethod
    def _klasor_olustur(yol: str = "", **kw) -> str:
        try:
            path = ToolRegistry._coz_yol(yol, **kw)
            os.makedirs(path, exist_ok=True)
            return f"Efendim, klasör oluşturuldu: {path}"
        except Exception as exc:
            return f"Klasör oluşturulamadı: {exc}"

    @staticmethod
    def _dosya_listele(klasor: str = "", **kw) -> str:
        try:
            home = os.environ.get("USERPROFILE", "")
            k = str(klasor or kw.get("yol") or "masaüstü").lower()
            if any(x in k for x in ("indir", "download")):
                base = os.path.join(home, "Downloads")
            elif any(x in k for x in ("belge", "document")):
                base = os.path.join(home, "Documents")
            elif os.path.isabs(klasor or ""):
                base = klasor
            else:
                base = os.path.join(home, "Desktop")
            items = os.listdir(base)
            if not items:
                return f"Efendim, '{base}' klasörü boş."
            return f"Efendim, {os.path.basename(base)} içinde {len(items)} öğe var:\n" + \
                   ", ".join(items[:40])
        except Exception as exc:
            return f"Klasör listelenemedi: {exc}"

    @staticmethod
    def _dosya_sil(yol: str = "", **kw) -> str:
        try:
            path = ToolRegistry._coz_yol(yol, **kw)
            if os.path.exists(path):
                os.remove(path)
                return f"Efendim, dosya silindi: {path}"
            return f"Efendim, '{path}' bulunamadı."
        except Exception as exc:
            return f"Dosya silinemedi: {exc}"

    # ── Kod/proje üretme (uzman kod modeliyle) ───────────────────────── #
    @staticmethod
    def _coder_uret(prompt: str) -> str:
        """
        İstenen kodu üretir. ÖNCE Gemini (en kaliteli), olmazsa
        yerel kod modeli (qwen2.5-coder).
        """
        # 1) Gemini — SADECE backend gemini/google ise (ollama'da cloud isteme)
        backend = os.getenv("AI_BACKEND", "ollama").strip().lower()
        key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY", "")
        if backend in ("gemini", "google") and key and not key.startswith("YOUR_"):
            try:
                import google.generativeai as genai  # type: ignore
                genai.configure(api_key=key)
                m = genai.GenerativeModel(os.getenv("GEMINI_MODEL", "gemini-2.5-flash"))
                txt = (m.generate_content(prompt).text or "").strip()
                if txt:
                    logger.info("Kod Gemini ile üretildi.")
                    return txt
            except Exception as exc:
                logger.warning("Gemini kod üretemedi, yerel modele düşülüyor: %s", exc)

        # 2) Yerel kod modeli (qwen2.5-coder) — yedek
        import requests
        base = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        model = os.getenv("OLLAMA_CODER_MODEL", "qwen2.5-coder:7b")
        try:
            r = requests.post(
                f"{base}/api/chat",
                json={"model": model,
                      "messages": [{"role": "user", "content": prompt}],
                      "stream": False, "options": {"temperature": 0.4}},
                timeout=240)
            r.raise_for_status()
            return (r.json().get("message", {}).get("content") or "").strip()
        except Exception as exc:
            logger.warning("Kod modeli hatası: %s", exc)
            return ""

    @staticmethod
    def _temizle_kod(code: str) -> str:
        """Modelin koduna eklediği ``` çitlerini ve açıklamaları temizler."""
        import re
        c = code.strip()
        c = re.sub(r"^```[a-zA-Z]*\s*", "", c)
        c = re.sub(r"\s*```$", "", c)
        return c.strip()

    @staticmethod
    def _tur_tespit(istek: str, ad: str) -> tuple[str, str]:
        """İstek/ad'dan proje türünü (uzantı, kategori) tahmin et."""
        low = (istek + " " + ad).lower()
        if ad and "." in os.path.basename(ad):
            ext = os.path.basename(ad).rsplit(".", 1)[1].lower()
        elif any(k in low for k in ("discord", "telegram", "bot ", "telegram bot", "discord bot")):
            ext = "py"
        elif any(k in low for k in ("yılan", "yilan", "tetris", "oyun", "game", "pong", "snake")):
            # Oyun: tarayıcıda HTML olarak en kolay
            ext = "html"
        elif any(k in low for k in ("python", "betik", "script", " py", "pyqt", "tkinter", "flask", "django")):
            ext = "py"
        else:
            ext = "html"
        # Kategori
        if "bot" in low and ext == "py":
            kat = "bot"
        elif ext == "html" and any(k in low for k in ("oyun", "game", "yılan", "tetris", "snake", "pong")):
            kat = "oyun"
        elif ext == "html":
            kat = "site"
        else:
            kat = "script"
        return ext, kat

    @staticmethod
    def _proje_olustur(istek: str = "", dosya_adi: str = "", cok_dosya: bool = False, **kw) -> str:
        import re
        istek = istek or kw.get("konu") or kw.get("aciklama") or kw.get("aciklamasi") or kw.get("description") or ""
        ad = (dosya_adi or kw.get("yol") or kw.get("dosya") or kw.get("isim") or "").strip().strip("\"'")
        if not istek and not ad:
            return "Efendim, ne yapmamı istediğinizi söyleyin (örn: 'manga satış sitesi')."

        ext, kat = ToolRegistry._tur_tespit(istek, ad)

        # ── ÇOK DOSYALI MOD (HTML+CSS+JS ayrı) ─────────────────────────── #
        if cok_dosya and ext in ("html", "htm"):
            prompt = (
                "Sen uzman bir front-end geliştiricisin. Aşağıdaki istek için MODERN, ŞIK, "
                "RESPONSIVE bir web projesi yaz — index.html, style.css, script.js olarak ÜÇ "
                "AYRI dosya. HTML, CSS'i <link>, JS'i <script src> ile bağlamalı. Görseller "
                "için https://picsum.photos kullan; en az 6 örnek içerik. "
                "ÇIKTI FORMATI (kesin uy):\n"
                "===FILE: index.html===\n<html buraya>\n"
                "===FILE: style.css===\n<css buraya>\n"
                "===FILE: script.js===\n<js buraya>\n"
                "BAŞKA hiçbir açıklama, yorum veya ``` YAZMA.\n\n"
                f"İSTEK: {istek}")
            txt = ToolRegistry._coder_uret(prompt)
            if not txt:
                return "Efendim, kod üretilemedi."
            files = {}
            for part in re.split(r"===FILE:\s*", txt):
                part = part.strip()
                if not part or "===" not in part and "\n" not in part:
                    continue
                head, _, body = part.partition("\n")
                fname = head.strip().rstrip("=").strip()
                if fname and body.strip():
                    files[fname] = ToolRegistry._temizle_kod(body)
            if not files:
                return "Efendim, çok dosyalı çıktı ayrıştırılamadı; tek dosyaya geçiyorum.\n" + \
                       ToolRegistry._proje_olustur(istek=istek, dosya_adi=ad, cok_dosya=False)
            # Hepsini bir klasöre koy
            klas_ad = (ad and os.path.splitext(os.path.basename(ad))[0]) or "jarvis_proje"
            klas = ToolRegistry._coz_yol(klas_ad)
            os.makedirs(klas, exist_ok=True)
            for fn, body in files.items():
                with open(os.path.join(klas, fn), "w", encoding="utf-8") as f:
                    f.write(body)
            index = os.path.join(klas, "index.html")
            if os.path.exists(index):
                try:
                    webbrowser.open("file:///" + index.replace("\\", "/"))
                except Exception:
                    pass
            return (f"Efendim, çok dosyalı projeyi oluşturdum ({len(files)} dosya) ve açtım: {klas}")

        # ── TEK DOSYA — türe göre prompt ───────────────────────────────── #
        if kat == "bot":
            prompt = (
                f"Uzman bir Python geliştiricisin. Aşağıdaki istek için TEK dosyalık, ÇALIŞAN bir "
                f"bot yaz. Token/API anahtarı için os.environ kullan ve kodun başına yorum olarak "
                f"hangi paketlerin pip ile kurulacağını yaz (örn: # pip install discord.py). "
                f"SADECE ham Python kodu, ``` YAZMA.\n\nİSTEK: {istek}")
        elif kat == "oyun":
            prompt = (
                f"Uzman bir oyun geliştiricisin. Aşağıdaki istek için TEK dosyalık, OYNANABİLİR "
                f"bir HTML+CSS+JS oyunu yaz (canvas kullan, tüm kodu inline). Skor göster, "
                f"klavye/dokunmatik kontrol ekle, modern görünüm. SADECE ham HTML, ``` YAZMA.\n\nİSTEK: {istek}")
        elif kat == "site":
            prompt = (
                "Sen uzman bir front-end geliştiricisin. Aşağıdaki istek için TEK dosyalık, "
                "MODERN, ŞIK, KALİTELİ bir HTML sayfası yaz. Kurallar: inline <style> ve <script>; "
                "responsive; güzel renkler, gölgeler, hover animasyonları; başlık+içerik+footer; "
                "en az 6 örnek kart/içerik; görseller https://picsum.photos. "
                "SADECE ham HTML, ``` YAZMA.\n\n"
                f"İSTEK: {istek}")
        else:  # script
            prompt = (
                f"Uzman bir yazılımcısın. Aşağıdaki istek için kaliteli, ÇALIŞAN, tek dosyalık "
                f"{ext} kodu yaz. SADECE ham kod, ``` YAZMA.\n\nİSTEK: {istek}")

        code = ToolRegistry._coder_uret(prompt)
        if not code:
            return "Efendim, kod üretilemedi. Kod modeli yüklü mü kontrol edin."
        code = ToolRegistry._temizle_kod(code)

        path = ToolRegistry._coz_yol(ad or f"jarvis_proje.{ext}")
        if "." not in os.path.basename(path):
            path += "." + ext
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(code)
        except Exception as exc:
            return f"Proje kaydedilemedi: {exc}"

        if path.lower().endswith((".html", ".htm")):
            try:
                webbrowser.open("file:///" + path.replace("\\", "/"))
            except Exception:
                pass
            etiket = "oyununuzu" if kat == "oyun" else "web sitesini"
            return f"Efendim, kaliteli {etiket} oluşturdum ve tarayıcıda açtım: {path}"
        if kat == "bot":
            return f"Efendim, bot kodunuzu yazıp kaydettim: {path} (başında pip kurulum satırı var)"
        return f"Efendim, kodu yazıp kaydettim: {path}"

    # ── #2 Siteyi/kodu iyileştir ──────────────────────────────────────── #
    @staticmethod
    def _siteyi_iyilestir(yol: str = "", talep: str = "", **kw) -> str:
        path = ToolRegistry._coz_yol(yol, **kw)
        if not os.path.exists(path):
            return f"Efendim, dosya bulunamadı: {path}"
        try:
            mevcut = open(path, encoding="utf-8").read()
        except Exception as exc:
            return f"Dosya okunamadı: {exc}"
        ext = path.rsplit(".", 1)[-1].lower()
        ek = f"\nEK İSTEK: {talep}" if talep else ""
        prompt = (
            f"Aşağıdaki {ext} dosyasını DAHA modern, şık ve kaliteli hâle getir. Yapısı bozulmasın "
            f"ama tasarım/animasyon/kod kalitesi yükselsin. SADECE yeni hâlinin ham kodunu ver, "
            f"``` YAZMA.{ek}\n\n--- MEVCUT KOD ---\n{mevcut}")
        yeni = ToolRegistry._coder_uret(prompt)
        if not yeni:
            return "Efendim, iyileştirme üretilemedi."
        yeni = ToolRegistry._temizle_kod(yeni)
        # Yedek al
        try:
            yedek = path + ".yedek"
            with open(yedek, "w", encoding="utf-8") as f:
                f.write(mevcut)
            with open(path, "w", encoding="utf-8") as f:
                f.write(yeni)
        except Exception as exc:
            return f"Yazma hatası: {exc}"
        if ext in ("html", "htm"):
            try: webbrowser.open("file:///" + path.replace("\\", "/"))
            except Exception: pass
        return f"Efendim, '{os.path.basename(path)}' iyileştirildi (yedek: .yedek)."

    # ── #3 Tema değiştir ──────────────────────────────────────────────── #
    @staticmethod
    def _tema_degistir(yol: str = "", tema: str = "", **kw) -> str:
        path = ToolRegistry._coz_yol(yol, **kw)
        if not os.path.exists(path):
            return f"Efendim, dosya bulunamadı: {path}"
        mevcut = open(path, encoding="utf-8").read()
        prompt = (
            f"Aşağıdaki HTML dosyasının RENK TEMASINI '{tema}' olarak değiştir. İçerik ve yapı "
            f"AYNI kalsın, sadece renk/arka plan/vurgu değişsin, modern duruşunu koru. SADECE "
            f"yeni HTML'i ham olarak ver, ``` YAZMA.\n\n--- MEVCUT ---\n{mevcut}")
        yeni = ToolRegistry._temizle_kod(ToolRegistry._coder_uret(prompt))
        if not yeni:
            return "Efendim, tema uygulanamadı."
        with open(path + ".yedek", "w", encoding="utf-8") as f: f.write(mevcut)
        with open(path, "w", encoding="utf-8") as f: f.write(yeni)
        try: webbrowser.open("file:///" + path.replace("\\", "/"))
        except Exception: pass
        return f"Efendim, '{os.path.basename(path)}' tema '{tema}' olarak değişti."

    # ── #7 Kod açıkla ─────────────────────────────────────────────────── #
    @staticmethod
    def _kod_aciklat(yol: str = "", **kw) -> str:
        path = ToolRegistry._coz_yol(yol, **kw)
        if not os.path.exists(path):
            return f"Efendim, dosya bulunamadı: {path}"
        kod = open(path, encoding="utf-8").read()
        if len(kod) > 8000:
            kod = kod[:8000] + "\n... (kısaltıldı)"
        prompt = ("Aşağıdaki kodu kısa ve anlaşılır Türkçe ile açıkla: ne işe yarar, hangi "
                  "kısımları neyi yapar. Madde işaretli, en fazla 10 satır.\n\n--- KOD ---\n" + kod)
        a = ToolRegistry._coder_uret(prompt)
        return a or "Açıklama üretilemedi."

    # ── #8 Kod hatasını düzelt ────────────────────────────────────────── #
    @staticmethod
    def _kod_duzelt(yol: str = "", hata: str = "", **kw) -> str:
        path = ToolRegistry._coz_yol(yol, **kw)
        if not os.path.exists(path):
            return f"Efendim, dosya bulunamadı: {path}"
        kod = open(path, encoding="utf-8").read()
        hata_blok = f"\nHATA MESAJI: {hata}" if hata else ""
        prompt = ("Aşağıdaki kodda hata/sorun varsa BUL ve düzeltilmiş tam hâlini yaz. SADECE "
                  f"düzeltilmiş ham kodu ver, ``` veya açıklama YAZMA.{hata_blok}\n\n--- KOD ---\n{kod}")
        yeni = ToolRegistry._temizle_kod(ToolRegistry._coder_uret(prompt))
        if not yeni or yeni.strip() == kod.strip():
            return "Efendim, görünür bir hata bulamadım."
        with open(path + ".yedek", "w", encoding="utf-8") as f: f.write(kod)
        with open(path, "w", encoding="utf-8") as f: f.write(yeni)
        return f"Efendim, '{os.path.basename(path)}' düzeltildi (yedek: .yedek)."

    # ── #42 PC temizleme ──────────────────────────────────────────────── #
    @staticmethod
    def _pc_temizle(**kw) -> str:
        import shutil
        toplam = 0
        ayrintilar = []

        def _sil_dir(d):
            nonlocal toplam
            kazanc = 0
            if not os.path.isdir(d):
                return 0
            for root, dirs, files in os.walk(d, topdown=False):
                for fn in files:
                    fp = os.path.join(root, fn)
                    try:
                        kazanc += os.path.getsize(fp)
                        os.remove(fp)
                    except Exception:
                        pass
            toplam += kazanc
            return kazanc

        # Temp klasörleri
        for d in (os.environ.get("TEMP", ""), os.environ.get("TMP", ""),
                  os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Temp")):
            if d and os.path.isdir(d):
                k = _sil_dir(d)
                if k > 0:
                    ayrintilar.append(f"{os.path.basename(d) or d}: {k/1024/1024:.1f} MB")

        # Geri dönüşüm kutusu
        try:
            import subprocess
            subprocess.run(["powershell", "-NoProfile", "-Command", "Clear-RecycleBin -Force -ErrorAction SilentlyContinue"],
                           capture_output=True, timeout=10)
            ayrintilar.append("Çöp kutusu boşaltıldı")
        except Exception:
            pass

        mb = toplam / 1024 / 1024
        if mb < 0.5 and not ayrintilar:
            return "Efendim, temizlenecek pek bir şey yoktu — sisteminiz zaten temiz."
        return f"Efendim, PC temizliği tamam — yaklaşık {mb:.1f} MB alan kazanıldı. ({'; '.join(ayrintilar) or 'temp temizlendi'})"

    # ── #30 Spotify sesli arama ──────────────────────────────────────── #
    @staticmethod
    def _spotify_arat(sorgu: str = "", **kw) -> str:
        import subprocess, time
        sorgu = sorgu or kw.get("sarki") or kw.get("query") or ""
        if not sorgu:
            return "Efendim, ne çalmamı istersiniz?"
        # Önce protokol bağlantısıyla dene (Spotify kuruluysa direkt arama açar)
        try:
            import webbrowser
            webbrowser.open(f"spotify:search:{sorgu}")
            return f"Efendim, Spotify'da '{sorgu}' aratıldı — istediğinizi seçip oynatabilirsiniz."
        except Exception:
            pass
        # Yedek: web player
        import urllib.parse, webbrowser
        webbrowser.open(f"https://open.spotify.com/search/{urllib.parse.quote(sorgu)}")
        return f"Efendim, Spotify Web'de '{sorgu}' aratıldı."

    # ── #31 WhatsApp arama ────────────────────────────────────────────── #
    @staticmethod
    def _whatsapp_ara(kisi: str = "", **kw) -> str:
        kisi = (kisi or kw.get("kişi") or kw.get("isim") or "").strip()
        if not kisi:
            return "Efendim, kimi arayayım?"
        import urllib.parse, webbrowser
        if kisi.startswith("+") or kisi.replace(" ", "").isdigit():
            num = kisi.replace(" ", "").lstrip("+")
            webbrowser.open(f"https://wa.me/{num}")
        else:
            webbrowser.open("https://web.whatsapp.com")
        return (f"Efendim, WhatsApp '{kisi}' için açıldı. Sohbet açılınca "
                "sağ üstteki 📞 simgesinden arama başlatabilirsiniz.")

    # ── #31 Telegram arama ────────────────────────────────────────────── #
    @staticmethod
    def _telegram_ara(kisi: str = "", **kw) -> str:
        kisi = (kisi or "").strip().lstrip("@")
        if not kisi:
            return "Efendim, kimi arayayım?"
        import webbrowser
        # tg:// protokolü Telegram Desktop'ı açar
        try:
            webbrowser.open(f"tg://resolve?domain={kisi}")
        except Exception:
            pass
        webbrowser.open(f"https://t.me/{kisi}")
        return f"Efendim, Telegram'da '@{kisi}' sohbeti açıldı. Arama için ☎️ simgesini kullanın."
