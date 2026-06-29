"""
JARVIS çalışma-zamanı durumu — modüller arası paylaşılan değişken durum.
(Dil, ruh hali/ses tonu, son konuşma bağlamı.)
"""

LANG = "tr"            # "tr" | "en"  → prompt dili + TTS sesi
MOOD = "notr"          # ses tonu: notr/mutlu/heyecanli/uzgun/sakin
VOICE = "default"      # ses profili (#9): default/kadin/erkek/jarvis
CHARACTER = "jarvis"   # kişilik (#14): jarvis/ironman/sherlock/yoda/komik
LAST_USER_MSG = ""     # bağlam: son kullanıcı mesajı (#7)
LAST_REPLY = ""        # bağlam: JARVIS'in son cevabı (#7)


CHARACTER_PROMPTS = {
    "jarvis": "",        # varsayılan — sistem promptuyla aynı
    "ironman": (
        "ROL: Şu andan itibaren Tony Stark gibi konuşuyorsun — kendine güvenli, "
        "esprili, biraz şımarık, akıllı ve hızlı. Sık sık 'ben dahiyim Efendim' tarzı "
        "espriler yap. Teknolojiden coşkuyla bahset. Yine 'Efendim' dersin."),
    "sherlock": (
        "ROL: Sherlock Holmes gibi konuşuyorsun — keskin gözlem, soğuk mantık, kısa "
        "ve doğrudan cümleler. 'İlginç', 'Elementary' der gibi başla. Detaylara önem "
        "ver. 'Efendim' kullanmayı bırak, 'Sevgili Watson' tarzı hitap et."),
    "yoda": (
        "ROL: Yoda gibi konuşuyorsun — devrik cümleler kur. Bilgece ifadeler kullan. "
        "'Yapacaksın bunu, evet.' / 'Güç senle olsun.' tarzı cümleler. Kısa söyle, "
        "felsefi söyle. 'Efendim' yerine 'genç dost' kullan."),
    "komik": (
        "ROL: Stand-up komedyen gibi konuşuyorsun. Her cevaba ufak bir gözlem-espri "
        "ekle, ironi kullan. Yine 'Efendim' dersin ama gevşek bir üslupla."),
}


def set_lang(lang: str):
    global LANG
    LANG = "en" if str(lang).lower().startswith("en") else "tr"


def set_voice(v: str):
    global VOICE
    VOICE = v or "default"


def set_character(c: str):
    """#14 — JARVIS'in kişiliğini değiştir."""
    global CHARACTER
    c = (c or "jarvis").lower()
    if c not in CHARACTER_PROMPTS:
        c = "jarvis"
    CHARACTER = c
    # Karakterler ses profiliyle de gelir
    if c == "ironman":
        set_voice("jarvis"); set_mood("heyecanli")
    elif c == "sherlock":
        set_voice("erkek"); set_mood("sakin")
    elif c == "yoda":
        set_voice("erkek"); set_mood("sakin")
    elif c == "komik":
        set_voice("default"); set_mood("mutlu")
    else:
        set_voice("default"); set_mood("notr")


def set_mood(mood: str):
    global MOOD
    MOOD = mood or "notr"


def set_context(user_msg: str = None, reply: str = None):
    global LAST_USER_MSG, LAST_REPLY
    if user_msg is not None:
        LAST_USER_MSG = user_msg
    if reply is not None:
        LAST_REPLY = reply
