"""
JARVIS Turkish NLP — Akıllı komut anlama motoru.

Türkçe gramer yapısını anlayarak:
- Fiil/eylem kelimelerini çıkarır
- Uygulama/site isimlerini tanır
- Türkçe ekleri soyar (YouTube'da → youtube, Spotify'ı → spotify)
- Temiz sorgu/içerik metnini döndürür
"""

import re

# ── Eylem (fiil) kelimeleri ───────────────────────────────────────────── #
# Tüm varyantlar + Türkçe ekleri ile
ACTION_WORDS: set[str] = {
    # Açma
    "aç", "ac", "açar", "acar", "açıyor", "aciyor", "açalım", "acacim",
    "açtır", "acdir", "açıver", "başlat", "baslat", "başlatıver",
    "çalıştır", "calistir", "çalıştırıver", "open", "start", "launch",
    "gir", "git", "gidelim", "gidiver", "girelim", "göster", "goster",
    "getir", "bak", "ziyaret", "ziyaretet",
    # Kapatma
    "kapat", "kapa", "kapatıver", "kapat", "durdur", "bitir", "sonlandır",
    "sonlandir", "close", "quit", "exit", "stop", "kill",
    # Arama
    "ara", "bul", "search", "find", "sorgula", "tara",
    # Oynatma
    "çal", "cal", "oynat", "dinle", "izle", "play", "stream",
    # Kurma
    "yükle", "yukle", "indir", "kur", "install", "download",
    # Gönderme
    "gönder", "gonder", "yaz", "ilet", "söyle", "soyle", "de", "at",
    # Diğer
    "ayarla", "değiştir", "degistir", "set", "change", "update",
    "al", "ekle", "sil", "temizle", "boşalt", "bosalt",
    # İsteme kalıpları
    "istiyorum", "isitiyorum", "ister misin", "olur mu", "yapabilir",
    "yaparmısın", "yaparmissin", "mümkün mü", "mumkun mu",
    "lütfen", "lutfen", "bana", "beni", "benim", "için", "icin",
    "misin", "musun", "mısın", "musun", "misiniz",
}

# ── Dolgu kelimeleri ──────────────────────────────────────────────────── #
FILLER_WORDS: set[str] = {
    "bir", "şu", "bu", "o", "ve", "de", "da", "ama", "ya", "ki",
    "ile", "için", "icin", "üzere", "uzere", "gibi", "kadar",
    "nasıl", "nasil", "ne", "neden", "niye", "niçin", "nicin",
    "acaba", "hemen", "şimdi", "simdi", "haydi", "hadi", "bakalım", "bakalim",
    "tamam", "peki", "olur", "tabii", "tabi", "evet", "hayır",
    "the", "a", "an", "of", "for", "with", "to", "in", "on", "at",
}

# ── Bilinen uygulama / site isimleri ─────────────────────────────────── #
APP_SITE_WORDS: set[str] = {
    "youtube", "yt", "google", "netflix", "twitch", "tiktok", "tik tok",
    "twitter", "x", "instagram", "insta", "facebook", "fb",
    "spotify", "discord", "whatsapp", "telegram", "slack", "zoom",
    "steam", "epic", "salad", "chrome", "firefox", "edge", "brave",
    "notepad", "excel", "word", "powerpoint", "vscode", "code",
    "explorer", "dosya gezgini", "calculator", "hesap makinesi",
    "paint", "cmd", "powershell", "terminal", "obs", "vlc",
    "maps", "harita", "wikipedia", "wiki",
}

# ── Türkçe ek tablosu (uzundan kısaya) ───────────────────────────────── #
# Apostrof + ek veya doğrudan ek
_TR_SUFFIXES = [
    # Apostrof'lu ekleri önce soy
    r"'[dn]an?",          # 'dan, 'den, 'tan, 'ten
    r"'[dt]e",            # 'de, 'te
    r"'[aey][ae]",        # 'ya, 'ye, 'a, 'e
    r"'y?[iıuü]",        # 'yi, 'yı, 'yu, 'yü, 'i, 'ı
    r"'n[uü]n",           # 'nun, 'nün
    r"'n[ıi]n",           # 'nın, 'nin
    r"'[aey]",            # 'a, 'e, 'y genel
    # Apostrufsuz
    r"[dt]an$", r"[dt]en$",  # ablative
    r"[dt]a$",  r"[dt]e$",   # locative
    r"ya$",     r"ye$",       # dative
    r"yı$",     r"yi$", r"yu$", r"yü$",  # accusative (y'li)
    r"ı$",      r"i$",  r"u$",  r"ü$",   # accusative
    r"nın$",    r"nin$", r"nun$", r"nün$",  # genitive
    r"ın$",     r"in$",  r"un$",  r"ün$",   # genitive short
    r"yla$",    r"yle$",  # instrumental (y'li)
    r"la$",     r"le$",   # instrumental
]

_SUFFIX_PATTERN = re.compile(
    "(" + "|".join(_TR_SUFFIXES) + ")",
    re.IGNORECASE | re.UNICODE,
)


def stem(word: str) -> str:
    """Türkçe eki soyulmuş kökü döndür (küçük harf, apostrof yok)."""
    w = word.lower().strip("'\".,;:!?")
    # Apostrof ile ayrılmış ek: "YouTube'da" → "youtube"
    if "'" in w or "'" in w or "'" in w:
        base = re.split(r"[''\']", w)[0]
        if len(base) >= 2:
            return base
    # Sona yapışık ekleri soy
    cleaned = _SUFFIX_PATTERN.sub("", w)
    # Çok kısa kalırsa orijinali döndür
    return cleaned if len(cleaned) >= 2 else w


def tokenize(msg: str) -> list[str]:
    """Cümleyi token listesine çevir (Türkçe'ye uyumlu)."""
    return re.findall(r"[\w''-]+", msg, re.UNICODE)


def is_stop(token: str, extra_stop: set[str] | None = None) -> bool:
    """Token, kaldırılması gereken bir kelime mi?"""
    s = stem(token)
    if s in ACTION_WORDS or s in FILLER_WORDS or s in APP_SITE_WORDS:
        return True
    if token.lower() in ACTION_WORDS or token.lower() in FILLER_WORDS:
        return True
    if extra_stop and (s in extra_stop or token.lower() in extra_stop):
        return True
    return False


def extract_query(msg: str, extra_stop: set[str] | None = None) -> str:
    """
    Komuttan temiz sorgu/içerik metnini çıkarır.

    Örnek:
      "YouTube'da lofi müzik ara"  →  "lofi müzik"
      "YouTube aç"                 →  ""            (boş = ana sayfa)
      "Spotify'da sad playlist çal" → "sad playlist"
      "Google'da Python nedir ara" → "Python nedir"
    """
    tokens = tokenize(msg)
    kept = [t for t in tokens if not is_stop(t, extra_stop)]
    return " ".join(kept).strip()


def extract_named_entity(msg: str, after_keywords: list[str]) -> str:
    """
    Belirli anahtar kelimelerden sonra gelen isim/entity'i çıkarır.
    Örnek: extract_named_entity("Ahmet'e mesaj gönder", ["'e","'a","'ye","'ya"]) → "Ahmet"
    """
    for kw in after_keywords:
        idx = msg.lower().find(kw.lower())
        if idx > 0:
            return msg[:idx].strip().split()[-1]
    return ""


def detect_intent(msg: str) -> str:
    """
    Birincil niyeti döndürür: open | close | search | play | install | send | other
    """
    ml = msg.lower()
    stems = {stem(t) for t in tokenize(ml)}

    if stems & {"aç", "ac", "başlat", "baslat", "gir", "git", "open", "start", "launch", "goster", "göster"}:
        return "open"
    if stems & {"kapat", "kapa", "durdur", "bitir", "sonlandır", "close", "stop", "quit"}:
        return "close"
    if stems & {"ara", "bul", "search", "find", "sorgula"}:
        return "search"
    if stems & {"çal", "cal", "oynat", "dinle", "izle", "play"}:
        return "play"
    if stems & {"yükle", "yukle", "indir", "kur", "install", "download"}:
        return "install"
    if stems & {"gönder", "gonder", "yaz", "ilet", "söyle", "at", "de"}:
        return "send"
    return "other"


def extract_app_name(msg: str) -> str:
    """
    Komuttaki uygulama/program adını çıkarır.
    "Notepad aç" → "notepad", "VLC'yi başlat" → "vlc"
    """
    tokens = tokenize(msg)
    for t in tokens:
        s = stem(t)
        if s not in ACTION_WORDS and s not in FILLER_WORDS and len(s) >= 2:
            # İlk anlamlı kelime (eylem değil)
            return s
    return ""
