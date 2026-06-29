"""HULLAR yardım — 'neler yapabilirsin' deyince kategorili yetenek listesi."""

from __future__ import annotations

_YARDIM = """🤖 HULLAR — Neler Yapabilirim

🖥️ EKRAN & KAMERA
• ekran görüntüsü / ekranı izle — anlık/canlı ekran
• ekran kaydet 10 — video kaydı
• webcam — kameradan foto
• ekrandaki yazıyı oku / çevir / özetle
• bu ne — ekranı AI yorumlar
• qr oku — ekrandaki QR kodu çözer

🎮 MINECRAFT / OYUN
• oneblock 10 dakika — akıllı blok kırma botu
• 10 dk blok kır — sürekli kırma
• mc komut /gamemode creative — komut yazar
• balık tut / köprü kur / envanteri at
• otomatik ye — auto-eat

🖱️ FARE & KLAVYE
• 500 300'e tıkla / sağ tıkla / sürükle
• ekranda Giriş Yap'a tıkla — yazıya tıklar (OCR)
• yeşile tıkla — renge tıklar
• W'ye 5 sn bas / Space'e 50 kez bas
• makro: tıkla X; yaz Y; enter — çoklu adım
• imza yaz — snippet (hazır metin)

🔊 SES & MEDYA
• sesi 50 yap / ses kapat / oynat-duraklat
• spotify aç / spotifyda tarkan çal
• ne çalıyor — şu an çalan şarkı

💻 SİSTEM & GÜÇ
• sistem bilgisi / cpu ram / pil / boş disk
• disk sağlığı / en çok ram / ram temizle
• kilitle / uyut / kapat / yeniden başlat
• 1 saat sonra kapat / sürücü güncelle
• uyumasın — ekran kapalı çalışsın

🌐 İNTERNET
• hız testi / ip adresim / wifi bilgisi
• siteyi izle X / interneti izle (çökerse haber)
• kısalt <link> / wifi qr <ad> <şifre>

📁 DOSYA
• dosya bul X gönder / son indirileni gönder
• en büyük dosyalar / resmi küçült / resimleri pdf yap
• video gif yap

🤖 OTOMASYON / ARKA PLAN
• her 5 dk <komut> — zamanlı tekrar
• chrome kapanırsa aç — watchdog
• gözcü 5 / farmı izle
• ekranda X bitince haber ver
• odak engelle 30 dk

🔔 UYARI
• yağmur var mı / fiyat takip <link> <TL>
• pil uyarısı / 10 dk sonra uyar: mola

🚨 ACİL
• panik modu / tarayıcıları kapat
• ekrana sesli yaz: <mesaj> — büyük alarmlı bildirim

🛒 SİPARİŞ
• yemeksepetinden X al / trendyolda Y al / sepeti aç

🧠 AI
• şu sayfayı özetle <link> / email taslağı yaz X
• çevir / kod yaz / film-oyun-müzik öner / tarif ver
• dikte — konuş, yazıya döker

🧰 ARAÇLAR
• hesapla / şifre üret / kripto fiyat / kronometre
• not al / qr üret / json güzelleştir / saat kaç

⚙️ KONTROL
• botu kapat — botu durdurur
• /menu — buton paneli (Telegram)

Detay için skil adını yaz, deneyelim! Toplam 225+ komut var."""


def yardim(parameters: dict | None = None) -> str:
    return _YARDIM
