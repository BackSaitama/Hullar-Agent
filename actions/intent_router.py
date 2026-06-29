"""
JARVIS Akıllı Niyet Yönlendirici (LLM router).

Regex kuralları eşleşmediğinde devreye girer. Mesajı LLM'e sınıflandırtır:
  - answer        : bilgi/sohbet sorusu       → AI cevaplasın
  - tool:<isim>   : aslında bir aracımız var, regex kaçırdı → onu çağır
  - code          : gerçek bir eylem ama araç yok → self-code teklifi

Böylece iki sorun çözülür:
  • "skilleri unutuyor"  → regex kaçırınca LLM doğru aracı bulur
  • "soruya kod teklif"  → soru 'answer' sınıfına düşer, kod teklif edilmez

LLM yoksa/başarısızsa {"intent": "unknown"} döner; çağıran eski regex
tahminine (fallback) güvenir. Yani LLM çökse bile sistem çalışır.
"""

import json
import logging
import re

logger = logging.getLogger(__name__)

# Router'ın seçebileceği araç kataloğu: kanonik isim → kısa açıklama.
# Yalnızca sık kaçırılan/önemli araçlar; gerisini regex zaten yakalıyor.
# Buradaki isimler dispatcher._ROUTER_MAP ile BİREBİR aynı olmalı.
_CATALOG = {
    "open_app":      "bir uygulama/program aç veya başlat",
    "youtube":       "youtube'da video aç veya ara",
    "web_search":    "internette / google'da arama yap",
    "weather":       "hava durumu",
    "screenshot":    "ekran görüntüsü al",
    "volume":        "ses seviyesi (aç / kıs / kapat)",
    "lock_screen":   "ekranı kilitle",
    "shutdown":      "bilgisayarı kapat",
    "restart":       "bilgisayarı yeniden başlat",
    "battery":       "pil / şarj durumu",
    "cpu_ram":       "cpu / ram kullanımı",
    "disk":          "disk / depolama durumu",
    "running_apps":  "çalışan uygulamaları listele",
    "kill_process":  "bir uygulamayı / işlemi sonlandır",
    "create_folder": "klasör oluştur",
    "find_file":     "dosya bul / ara",
    "list_files":    "klasör içeriğini listele",
    "calculate":     "matematik hesapla",
    "translate":     "metin çevir",
    "wikipedia":     "wikipedia'dan bilgi getir",
    "timer":         "zamanlayıcı kur",
    "reminder":      "hatırlatıcı kur",
    "take_note":     "not al",
    "spotify":       "spotify aç / müzik çal",
    "clear_temp":    "geçici (temp) dosyaları temizle",
    "minimize_all":  "tüm pencereleri küçült / masaüstünü göster",
    "task_manager":  "görev yöneticisini aç",
    "hiz_testi":     "internet hız testi yap",
}

_VALID = {"answer", "tool", "code"}


def _build_prompt() -> str:
    catalog_txt = "\n".join(f"- {k}: {v}" for k, v in _CATALOG.items())
    return (
        "Sen bir niyet sınıflandırıcısın. Kullanıcının Türkçe mesajını oku ve "
        "SADECE tek satırlık JSON döndür. Üç seçenek:\n"
        '  {"intent":"answer"}            → bilgi/açıklama/tanım/sohbet sorusu\n'
        '  {"intent":"tool","tool":"AD"}  → aşağıdaki araçlardan biri tam karşılıyor\n'
        '  {"intent":"code"}              → bir BİLGİSAYAR EYLEMİ ama listede uygun araç yok\n\n'
        "Araçlar:\n" + catalog_txt + "\n\n"
        "Kurallar:\n"
        "• 'X nedir', 'neden', 'nasıl çalışır' gibi bilgi soruları → answer\n"
        "• Listedeki bir araç işi yapıyorsa → tool (doğru AD'ı yaz)\n"
        "• Dosya/otomasyon/sistem işi ama listede yoksa → code\n"
        "• Başka HİÇBİR şey yazma, açıklama yapma, sadece JSON."
    )


def classify(msg: str) -> dict:
    """
    LLM ile niyet sınıflandır.
    Dönüş: {"intent": "answer"|"tool"|"code", "tool": "..."?}
           veya başarısızsa {"intent": "unknown"}.
    """
    msg = (msg or "").strip()
    if not msg:
        return {"intent": "unknown"}
    try:
        from .ai_skills import _ask_ai
        raw = (_ask_ai(_build_prompt(), msg) or "").strip()
    except Exception as exc:
        logger.info("router LLM kullanılamadı: %s", exc)
        return {"intent": "unknown"}

    m = re.search(r"\{.*?\}", raw, re.S)
    if not m:
        logger.info("router JSON bulunamadı: %s", raw[:80])
        return {"intent": "unknown"}
    try:
        data = json.loads(m.group(0))
    except Exception:
        return {"intent": "unknown"}

    intent = data.get("intent")
    if intent not in _VALID:
        return {"intent": "unknown"}
    if intent == "tool" and data.get("tool") not in _CATALOG:
        # LLM olmayan bir araç uydurdu → güvenli tarafta koda/AI'a bırak
        return {"intent": "unknown"}
    return data


# ════════════════════════════════════════════════════════════════════════ #
#  AKILLI KOMUT NORMALLEŞTİRME (bozuk/doğal dili temiz komuta çevirir)     #
#  Regex tutmadığında: OpenRouter mesajı anlar → bilinen bir komuta çevirir #
# ════════════════════════════════════════════════════════════════════════ #
# Botun anladığı temiz komut örnekleri (LLM bunlardan birine benzetir)
_ORNEK_KOMUTLAR = """youtube aç | spotify aç | chrome aç | <uygulama> aç
ses 50 yap | ses kapat | sesi artır | oynat duraklat | sonraki şarkı
ekran görüntüsü | webcam | ekranı izle | ekran kaydet 10 | monitörü kapat
ekrandaki yazıyı oku | ekranı özetle | bu ne | qr oku
sistem bilgisi | cpu ram kaç | pil durumu | boş disk alanı | ram temizle | disk sağlığı
ekranı kilitle | uyut | bilgisayarı kapat | yeniden başlat | 1 saat sonra kapat | uyanık kal
hız testi | ip adresim | wifi bilgisi nasıl | dns temizle | siteyi izle X | kısalt <link>
dosya bul X gönder | son indirileni gönder | en büyük dosyalar | hızlı temizlik
yemeksepetinden X al | trendyolda Y al | sepeti aç
oneblock 5 dakika | blok kır 30 saniye | mc komut /time set day | minecraftta elmas ver | balık tut
W'ye 5 saniye bas | space'e 50 kez bas | 500 300'e tıkla | ekranda X'e tıkla | yeşile tıkla
makro: tıkla X; yaz Y; enter | imza yaz | pencereyi sola yapıştır
saat kaç | hesapla 5*8 | şifre üret | bitcoin kaç | kripto fiyat | hava durumu
not al X | notlarımı göster | çevir X | kod yaz X | film öner | tarif ver
panik modu | tarayıcıları kapat | ekrana yaz | gözcü 5 | her 5 dakika ekran görüntüsü
kronometre | odak engelle 30 dakika | uygulama istatistiği | sürücü güncelle
şu sayfayı özetle <link> | email taslağı yaz X | dikte | discorda yaz: X
botu kapat | menü"""

_NORM_SYS = (
    "Sen bir komut çeviricisin. Kullanıcı bozuk/günlük/argo Türkçe yazabilir. "
    "Görevin: mesajı, botun anladığı TEK temiz komuta çevirmek.\n\n"
    "Bot şu komutları anlar (örnekler, | ile ayrık):\n" + _ORNEK_KOMUTLAR + "\n\n"
    "KURALLAR:\n"
    "• Mesaj bu komutlardan birine uyuyorsa → SADECE o temiz komutu yaz "
    "(parametreyi koru: 'yutub ac la' → 'youtube aç'; 'sesi 70 yap moruk' → 'ses 70 yap').\n"
    "• Bir bilgi/sohbet sorusuysa (nedir, neden, kim, açıkla, ne düşünüyorsun) → SOHBET\n"
    "• Bir bilgisayar eylemi ama listede yok (özel script gerekiyor) → KOD\n"
    "• Başka HİÇBİR şey yazma. Açıklama yok. Sadece komut veya SOHBET veya KOD."
)


def normalize_command(msg: str) -> str:
    """Bozuk/doğal mesajı temiz komuta çevirir.
    Dönüş: temiz komut | 'SOHBET' | 'KOD' | '' (LLM yok)."""
    msg = (msg or "").strip()
    if not msg:
        return ""
    try:
        from .ai_skills import _ask_ai
        raw = (_ask_ai(_NORM_SYS, msg) or "").strip()
    except Exception as exc:
        logger.info("normalize_command LLM yok: %s", exc)
        return ""
    # ilk satır, tırnak/markdown temizliği
    raw = raw.splitlines()[0].strip().strip("`\"' ")
    if not raw:
        return ""
    up = raw.upper()
    if up.startswith("SOHBET"):
        return "SOHBET"
    if up.startswith("KOD"):
        return "KOD"
    # çok uzun dönerse (LLM açıklama yapmış) → güvenme
    if len(raw) > 80:
        return ""
    return raw
