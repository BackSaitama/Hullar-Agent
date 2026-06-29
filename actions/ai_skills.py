"""
JARVIS AI Skill'leri — Yapay zeka gerektiren, derin anlama/üretim işleri.
Her fonksiyon, konfigürasyona göre Gemini veya Ollama'yı kullanır.

10 Skill:
  1.  film_oner        — Film/dizi önerisi
  2.  oyun_oner        — Oyun önerisi
  3.  muzik_oner       — Müzik/playlist önerisi
  4.  tarif_ver        — Yemek tarifi
  5.  kod_yaz          — Kod yazma / debug
  6.  ozet_al          — Metin veya konu özetleme
  7.  icerik_yaz       — Hikaye, şiir, slogan, email taslağı vb.
  8.  gunluk_plan      — Günlük / haftalık plan oluşturma
  9.  dil_pratik       — Yabancı dil pratik / çeviri + açıklama
  10. genel_asistan    — Derin soru-cevap, analiz, tavsiye
"""

import os
import re
import logging

logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════════════════════════ #
#  Ortak AI çağrı katmanı                                                   #
# ══════════════════════════════════════════════════════════════════════════ #

from datetime import datetime as _dt

_JARVIS_BASE = (
    "Sen JARVIS'sin — bir Windows otomasyon asistanının yapay zeka beyni. "
    "Kullanıcıya 'Efendim' diye hitap eder, daima Türkçe konuşursun.\n\n"
    "KİMLİK & YETENEK:\n"
    "- Bir komut sistemine bağlısın: uygulama açma, dosya, sistem kontrolü, "
    "mesaj gönderme gibi işleri ARAÇLAR (tools) yapar; sen yalnızca aracın "
    "olmadığı düşünme/üretme/bilgi işlerini üstlenirsin.\n"
    "- Bir araç bir işi zaten yapabiliyorsa, o işi anlatma — sistem onu çalıştırır.\n"
    "- Yapamadığın bir eylem istenirse sistem otomatik 'kodunu yazıp "
    "çalıştırayım mı?' diye sorar; sen bunu tekrarlamazsın.\n\n"
    "ÜSLUP:\n"
    "- ÖZ ve NET ol. Gereksiz giriş/kapanış cümlesi kurma, lafı uzatma.\n"
    "- Basit soruya 1-3 cümle; karmaşık konuda kısa madde/başlık kullan.\n"
    "- Emin değilsen 'emin değilim' de — ASLA bilgi uydurma, kaynak/sayı uydurma.\n"
    "- Soru belirsizse en olası yorumu yap, gerekiyorsa tek netleştirme sorusu sor.\n\n"
    f"BAĞLAM: Bugün {_dt.now():%d.%m.%Y}. İşletim sistemi Windows. "
    "Kullanıcı Türkçe konuşan tek kişidir.\n"
    "GÜVENLİK: Tehlikeli/geri dönüşsüz işlemleri (kapatma, silme, biçimlendirme) "
    "kendin önermezsin; bunlar onay/PIN ile yapılır."
)


def _ask_gemini(system: str, user: str) -> str:
    key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY", "")
    if not key:
        raise RuntimeError("Google/Gemini anahtarı yok")
    model = os.getenv("GOOGLE_MODEL") or os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    try:
        import google.generativeai as genai  # type: ignore
        genai.configure(api_key=key)
        gm = genai.GenerativeModel(model, system_instruction=system)
        return gm.generate_content(user).text.strip()
    except ImportError:
        # SDK yoksa REST ile
        import requests  # type: ignore
        r = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}",
            json={"system_instruction": {"parts": [{"text": system}]},
                  "contents": [{"parts": [{"text": user}]}]}, timeout=40)
        r.raise_for_status()
        return r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception as exc:
        raise RuntimeError(f"Gemini: {exc}") from exc


def _ask_anthropic(system: str, user: str) -> str:
    import requests  # type: ignore
    key = os.getenv("ANTHROPIC_API_KEY", "")
    if not key:
        raise RuntimeError("Anthropic anahtarı yok")
    model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")
    r = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={"x-api-key": key, "anthropic-version": "2023-06-01",
                 "content-type": "application/json"},
        json={"model": model, "max_tokens": 1024, "system": system,
              "messages": [{"role": "user", "content": user}]},
        timeout=40)
    r.raise_for_status()
    return r.json()["content"][0]["text"].strip()


def _ask_openai(system: str, user: str) -> str:
    import requests  # type: ignore
    key = os.getenv("OPENAI_API_KEY", "")
    if not key:
        raise RuntimeError("OpenAI anahtarı yok")
    model = os.getenv("OPENAI_MODEL", "gpt-4o")
    r = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {key}",
                 "Content-Type": "application/json"},
        json={"model": model, "temperature": 0.5,
              "messages": [{"role": "system", "content": system},
                           {"role": "user", "content": user}]},
        timeout=40)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"].strip()


def _ask_ollama(system: str, user: str) -> str:
    import requests  # type: ignore
    base  = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    model = os.getenv("OLLAMA_MODEL", "llama3")
    r = requests.post(
        f"{base}/api/chat",
        json={
            "model": model,
            "messages": [
                {"role": "system",  "content": system},
                {"role": "user",    "content": user},
            ],
            "stream": False,
            "options": {"temperature": 0.7},
        },
        timeout=60,
    )
    r.raise_for_status()
    return r.json()["message"]["content"].strip()


def _ask_openrouter(system: str, user: str) -> str:
    import requests  # type: ignore
    key = os.getenv("OPENROUTER_API_KEY", "")
    if not key:
        raise RuntimeError("OpenRouter API anahtarı yok")
    model = os.getenv("OPENROUTER_MODEL", "google/gemini-2.0-flash-001")
    r = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={"Authorization": f"Bearer {key}",
                 "Content-Type": "application/json"},
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user",   "content": user},
            ],
            "temperature": 0.5,
        },
        timeout=40,
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"].strip()


# backend adı → fonksiyon
_BACKENDS = {
    "openrouter": _ask_openrouter,
    "ollama":     _ask_ollama,
    "gemini":     _ask_gemini,
    "google":     _ask_gemini,
    "anthropic":  _ask_anthropic,
    "openai":     _ask_openai,
}

_FALLBACK = ("ollama", "openrouter", "google", "anthropic", "openai")

# Anahtar gerektiren backend'ler → ilgili .env değişkeni
_KEY_ENV = {"openrouter": "OPENROUTER_API_KEY", "google": "GOOGLE_API_KEY",
            "gemini": "GEMINI_API_KEY", "anthropic": "ANTHROPIC_API_KEY",
            "openai": "OPENAI_API_KEY"}


def _has_key(backend: str) -> bool:
    env = _KEY_ENV.get(backend)
    if not env:
        return True   # ollama → anahtar gerekmez
    if os.getenv(env):
        return True
    if backend == "google" and os.getenv("GEMINI_API_KEY"):
        return True
    return False


def _ask_ai(system: str, user: str) -> str:
    """Önce seçili backend, çökerse/kotada diğerlerine düşer."""
    backend = os.getenv("AI_BACKEND", "ollama").lower()
    # Seçilen backend anahtar istiyor ama girilmemişse → net uyarı (sessiz başarısızlık yok)
    if not _has_key(backend):
        env = _KEY_ENV.get(backend, "API_KEY")
        return (f"🔑 {backend.upper()} API anahtarı girilmemiş. "
                f"Lütfen anahtarını gir: setup.py çalıştır ya da .env dosyasına "
                f"{env}=<anahtarın> ekle. (Ücretsiz seçenek: AI_BACKEND=ollama)")
    # sıra: seçili backend + kalan yedekler (tekrarsız)
    sira = [backend] + [b for b in _FALLBACK if b != backend]
    errors = []
    for name in sira:
        fn = _BACKENDS.get(name)
        if not fn:
            continue
        try:
            cevap = fn(system, user)
            if cevap:
                return cevap
        except Exception as e:
            errors.append(f"{name}: {str(e)[:80]}")
    logger.error("AI hataları: %s", errors)
    return "Efendim, AI servisi şu anda yanıt vermiyor. Lütfen biraz sonra tekrar deneyin."


def _ask_zor(system: str, user: str) -> str:
    """ZOR/yaratıcı işler için: doğrudan Ollama (yerel, güçlü, kotasız)."""
    try:
        return _ask_ollama(system, user)
    except Exception:
        return _ask_ai(system, user)


# ══════════════════════════════════════════════════════════════════════════ #
#  Parametre çıkarıcılar                                                    #
# ══════════════════════════════════════════════════════════════════════════ #

def _clean(msg: str, *remove_patterns: str) -> str:
    """Verilen regex pattern'leri mesajdan temizler."""
    result = msg
    for pat in remove_patterns:
        result = re.sub(pat, "", result, flags=re.I | re.UNICODE)
    return result.strip(" .,;:?!-")


def _extract_film(msg: str) -> dict:
    q = _clean(msg,
        r"\b(film|dizi|movie|series|öner|oner|tavsiye|öneri|önerilebilir|"
        r"izlesem|izleyeyim|izleyebilir|ne|bana|beni|bir|tane|güzel|iyi)\b")
    return {"konu": q}


def _extract_oyun(msg: str) -> dict:
    q = _clean(msg,
        r"\b(oyun|game|öner|oner|tavsiye|öneri|oynasam|oynayayım|"
        r"ne|bana|beni|bir|tane|güzel|iyi|hangi|steam)\b")
    return {"tarz": q}


def _extract_muzik(msg: str) -> dict:
    q = _clean(msg,
        r"\b(müzik|muzik|music|şarkı|sarki|playlist|liste|çalma|calma|"
        r"öner|oner|tavsiye|dinlesem|dinleyeyim|ne|bana|bir)\b")
    return {"ruh_hali": q}


def _extract_tarif(msg: str) -> dict:
    q = _clean(msg,
        r"\b(tarif|nasıl yapılır|nasil yapilir|nasıl pişirilir|"
        r"yemek|yap|pişir|pisir|tarifi|recipe)\b")
    return {"yemek": q}


def _extract_kod(msg: str) -> dict:
    # Dil tespiti
    lang_map = {
        "python": "Python", "py": "Python",
        "javascript": "JavaScript", "js": "JavaScript",
        "typescript": "TypeScript", "ts": "TypeScript",
        "java": "Java", "c#": "C#", "csharp": "C#",
        "c\\+\\+": "C++", "cpp": "C++",
        "rust": "Rust", "go": "Go", "golang": "Go",
        "php": "PHP", "ruby": "Ruby", "swift": "Swift",
        "kotlin": "Kotlin", "sql": "SQL",
    }
    lang = "Python"
    for pat, name in lang_map.items():
        if re.search(rf"\b{pat}\b", msg, re.I):
            lang = name
            break

    q = _clean(msg,
        r"\b(kod|code|yaz|write|oluştur|olustur|yap|make|"
        r"script|fonksiyon|function|program|debug|düzelt|duzelt|fix)\b")
    q = re.sub(r"\b" + "|".join(lang_map.keys()) + r"\b", "", q, flags=re.I).strip()
    return {"dil": lang, "gorev": q}


def _extract_ozet(msg: str) -> dict:
    # "şunu özetle: metin" veya "şunu özetle metin"
    m = re.search(r"(?:özetle|ozet|summarize|özetini ver)[:\s]+(.+)", msg, re.I | re.DOTALL)
    content = m.group(1).strip() if m else _clean(msg,
        r"\b(özetle|ozet|ozeti|özetini|özetler|summarize|ver|bana|lütfen)\b")
    return {"icerik": content}


def _extract_icerik(msg: str) -> dict:
    # Tür tespiti
    tur_map = {
        r"\b(şiir|siir|poem)\b": "şiir",
        r"\b(hikaye|hikâye|story)\b": "hikaye",
        r"\b(slogan)\b": "slogan",
        r"\b(email|e-?posta|mail)\b": "email",
        r"\b(makale|article|blog)\b": "makale",
        r"\b(özür|ozur|apology)\b": "özür mesajı",
        r"\b(davet|invitation)\b": "davet mesajı",
        r"\b(ilan|duyuru|announcement)\b": "ilan",
        r"\b(tweet|post|gönderi)\b": "sosyal medya gönderisi",
        r"\b(biyografi|bio)\b": "biyografi",
    }
    tur = "metin"
    for pat, name in tur_map.items():
        if re.search(pat, msg, re.I):
            tur = name
            break

    q = _clean(msg,
        r"\b(yaz|oluştur|olustur|üret|uret|hazırla|hazirla|write|"
        r"create|generate|şiir|siir|hikaye|hikâye|slogan|email|"
        r"e-?posta|makale|özür|ozur|davet|bana|bir|tane|lütfen)\b")
    return {"tur": tur, "konu": q}


def _extract_plan(msg: str) -> dict:
    # Süre tespiti
    sure = "günlük"
    if re.search(r"\b(haftalık|haftalik|weekly|hafta)\b", msg, re.I):
        sure = "haftalık"
    elif re.search(r"\b(aylık|aylik|monthly|ay)\b", msg, re.I):
        sure = "aylık"
    q = _clean(msg,
        r"\b(plan|program|günlük|gunluk|haftalık|haftalik|aylık|aylik|"
        r"yap|oluştur|olustur|hazırla|hazirla|weekly|daily|monthly|schedule|"
        r"bana|bir|tane|lütfen|öner|oner)\b")
    return {"sure": sure, "konu": q}


def _extract_dil(msg: str) -> dict:
    lang_map = {
        "ingilizce": "İngilizce", "english": "İngilizce",
        "almanca": "Almanca", "german": "Almanca",
        "fransızca": "Fransızca", "french": "Fransızca",
        "ispanyolca": "İspanyolca", "spanish": "İspanyolca",
        "italyanca": "İtalyanca", "italian": "İtalyanca",
        "japonca": "Japonca", "japanese": "Japonca",
        "rusça": "Rusça", "russian": "Rusça",
        "arapça": "Arapça", "arabic": "Arapça",
        "çince": "Çince", "chinese": "Çince",
        "korece": "Korece", "korean": "Korece",
    }
    dil = "İngilizce"
    for pat, name in lang_map.items():
        if pat in msg.lower():
            dil = name
            break

    q = _clean(msg,
        r"\b(dil|language|pratik|practice|öğren|ogren|konuş|konus|"
        r"anlat|çevir|cevir|translate|" +
        "|".join(lang_map.keys()) + r")\b")
    return {"dil": dil, "konu": q}


def _extract_genel(msg: str) -> dict:
    return {"soru": msg}


# ══════════════════════════════════════════════════════════════════════════ #
#  SKILL 1: Film / Dizi Önerisi                                             #
# ══════════════════════════════════════════════════════════════════════════ #
def film_oner(parameters: dict = None, **_) -> str:
    p = parameters or {}
    konu = p.get("konu", "").strip()

    system = (
        f"{_JARVIS_BASE}\n\n"
        "Film ve dizi konusunda uzman bir öneri asistanısın. "
        "Önerilerini şu formatta ver:\n"
        "**[Film Adı]** (Yıl) — Kısa açıklama (1 cümle)\n"
        "En fazla 2 öneri ver. Türkçe konuş."
    )
    user = (
        f"Bana {'\"' + konu + '\" temasında ' if konu else ''}film veya dizi öner. "
        f"Hem eski hem yeni, hem Türk hem yabancı olabilir."
    )
    return _ask_ai(system, user)


# ══════════════════════════════════════════════════════════════════════════ #
#  SKILL 2: Oyun Önerisi                                                    #
# ══════════════════════════════════════════════════════════════════════════ #
def oyun_oner(parameters: dict = None, **_) -> str:
    p = parameters or {}
    tarz = p.get("tarz", "").strip()

    system = (
        f"{_JARVIS_BASE}\n\n"
        "Oyun önerisi konusunda uzman bir asistanısın. "
        "Önerilerini şu formatta ver:\n"
        "**[Oyun Adı]** — Platform | Tür | Kısa açıklama\n"
        "En fazla 3 öneri ver. Türkçe konuş."
    )
    user = (
        f"Bana {'\"' + tarz + '\" tarzında ' if tarz else ''}oyun öner. "
        f"PC, konsol veya mobil olabilir. Hem indie hem AAA düşün."
    )
    return _ask_ai(system, user)


# ══════════════════════════════════════════════════════════════════════════ #
#  SKILL 3: Müzik / Playlist Önerisi                                        #
# ══════════════════════════════════════════════════════════════════════════ #
def muzik_oner(parameters: dict = None, **_) -> str:
    p = parameters or {}
    ruh_hali = p.get("ruh_hali", "").strip()

    system = (
        f"{_JARVIS_BASE}\n\n"
        "Müzik önerisi konusunda uzman bir asistanısın. "
        "Önerilerini şu formatta ver:\n"
        "🎵 **[Şarkı/Playlist Adı]** — Sanatçı | Tür \n"
        "En fazla 6 öneri ver. Türkçe konuş."
    )
    user = (
        f"{'\"' + ruh_hali + '\" ruh haline uygun ' if ruh_hali else 'Genel '}"
        f"müzik veya playlist öner. "
        f"Türkçe ve yabancı şarkıları karıştırabilirsin."
    )
    return _ask_ai(system, user)


# ══════════════════════════════════════════════════════════════════════════ #
#  SKILL 4: Yemek Tarifi                                                    #
# ══════════════════════════════════════════════════════════════════════════ #
def tarif_ver(parameters: dict = None, **_) -> str:
    p = parameters or {}
    yemek = p.get("yemek", "").strip()

    if not yemek:
        return "Efendim, hangi yemeğin tarifini istediğinizi belirtir misiniz?"

    system = (
        f"{_JARVIS_BASE}\n\n"
        "Deneyimli bir aşçısın. Tarifleri şu formatta ver:\n"
        "**Malzemeler** (liste)\n"
        "**Yapılış** (adım adım)\n"
        "**İpuçları** (varsa)\n"
        "Türkçe konuş. Pratik ve anlaşılır ol."
    )
    user = f"{yemek} tarifi ver."
    return _ask_ai(system, user)


# ══════════════════════════════════════════════════════════════════════════ #
#  SKILL 5: Kod Yazma / Debug                                               #
# ══════════════════════════════════════════════════════════════════════════ #
def kod_yaz(parameters: dict = None, **_) -> str:
    p = parameters or {}
    dil   = p.get("dil", "Python")
    gorev = p.get("gorev", "").strip()

    if not gorev:
        return f"Efendim, {dil} ile ne yapmamı istediğinizi belirtir misiniz?"

    system = (
        f"{_JARVIS_BASE}\n\n"
        f"Uzman bir {dil} programcısısın. "
        f"Kod yazarken:\n"
        f"- Temiz, yorumlu ve çalışır kod yaz\n"
        f"- Kodu ```{dil.lower()}``` bloğu içine koy\n"
        f"- Kısa bir açıklama ekle\n"
        f"Türkçe konuş."
    )
    user = f"{dil} ile {gorev}"
    return _ask_ai(system, user)


# ══════════════════════════════════════════════════════════════════════════ #
#  SKILL 6: Metin / Konu Özetleme                                           #
# ══════════════════════════════════════════════════════════════════════════ #
def ozet_al(parameters: dict = None, **_) -> str:
    p = parameters or {}
    icerik = p.get("icerik", "").strip()

    if not icerik:
        return "Efendim, özetlememi istediğiniz metni veya konuyu belirtin."

    system = (
        f"{_JARVIS_BASE}\n\n"
        "Mükemmel bir özetleme asistanısın. "
        "Verilen metni veya konuyu:\n"
        "- Ana başlıklar ve alt noktalar halinde özetle\n"
        "- Gereksiz detayları at, özü koru\n"
        "- Türkçe ve anlaşılır bir dil kullan"
    )
    user = f"Şunu özetle:\n\n{icerik}"
    return _ask_ai(system, user)


# ══════════════════════════════════════════════════════════════════════════ #
#  SKILL 7: İçerik Üretme (hikaye, şiir, email, slogan...)                  #
# ══════════════════════════════════════════════════════════════════════════ #
def icerik_yaz(parameters: dict = None, **_) -> str:
    p = parameters or {}
    tur   = p.get("tur", "metin")
    konu  = p.get("konu", "").strip()

    tur_yonergeler = {
        "şiir":               "Yaratıcı, ritimli ve dokunaklı bir şiir yaz.",
        "hikaye":             "Başlangıç-gelişme-sonuç yapısında, sürükleyici kısa bir hikaye yaz.",
        "slogan":             "Akılda kalıcı, özlü 3-5 slogan seçeneği yaz.",
        "email":              "Profesyonel, nazik ve net bir email taslağı yaz.",
        "makale":             "Giriş-gelişme-sonuç yapısında bilgilendirici bir makale yaz.",
        "özür mesajı":        "Samimi ve özlü bir özür mesajı yaz.",
        "davet mesajı":       "Sıcak ve davetkar bir davet mesajı yaz.",
        "sosyal medya gönderisi": "Dikkat çekici, emoji destekli bir sosyal medya gönderisi yaz.",
        "biyografi":          "Kısa, etkileyici bir biyografi yaz.",
        "ilan":               "Net ve dikkat çekici bir ilan metni yaz.",
    }
    yonerge = tur_yonergeler.get(tur, f"Kaliteli bir {tur} yaz.")

    system = (
        f"{_JARVIS_BASE}\n\n"
        f"Yaratıcı bir yazar asistanısın. {yonerge} "
        f"Türkçe konuş. Akıcı ve özgün ol."
    )
    user = konu if konu else f"Genel konulu bir {tur} yaz."
    return _ask_ai(system, user)


# ══════════════════════════════════════════════════════════════════════════ #
#  SKILL 8: Günlük / Haftalık Plan                                          #
# ══════════════════════════════════════════════════════════════════════════ #
def gunluk_plan(parameters: dict = None, **_) -> str:
    from datetime import datetime
    p = parameters or {}
    sure  = p.get("sure", "günlük")
    konu  = p.get("konu", "").strip()

    bugun = datetime.now().strftime("%A, %d %B %Y")
    system = (
        f"{_JARVIS_BASE}\n\n"
        f"Üretkenlik ve zaman yönetimi uzmanısın. "
        f"{sure.capitalize()} planları şu formatta hazırla:\n"
        f" [Saat] — [Görev/Aktivite]\n"
        f"Dengeli, gerçekçi ve motive edici bir plan yap. Türkçe konuş."
    )
    user = (
        f"Bugün {bugun}. "
        f"{'\"' + konu + '\" odaklı ' if konu else ''}"
        f"{'bir ' + sure} plan hazırla."
    )
    return _ask_ai(system, user)


# ══════════════════════════════════════════════════════════════════════════ #
#  SKILL 9: Dil Pratik & Öğrenme                                            #
# ══════════════════════════════════════════════════════════════════════════ #
def dil_pratik(parameters: dict = None, **_) -> str:
    p = parameters or {}
    dil   = p.get("dil", "İngilizce")
    konu  = p.get("konu", "").strip()

    system = (
        f"{_JARVIS_BASE}\n\n"
        f"Deneyimli bir {dil} dil öğretmenisin. "
        f"Öğrenciye yardım ederken:\n"
        f"- Türkçe açıklama + {dil} örnek ver\n"
        f"- Telaffuz ipuçları ekle (gerekirse)\n"
        f"- Pratik cümleler ve bağlam sun\n"
        f"- Alıştırma sorusu sor"
    )
    user = konu if konu else f"{dil} dili hakkında temel bilgi ver ve pratik yaptır."
    return _ask_ai(system, user)


# ══════════════════════════════════════════════════════════════════════════ #
#  SKILL 10: Genel Asistan — Derin Soru-Cevap & Analiz                      #
# ══════════════════════════════════════════════════════════════════════════ #
def genel_asistan(parameters: dict = None, **_) -> str:
    p = parameters or {}
    soru = p.get("soru", "").strip()

    if not soru:
        return "Efendim, sormak istediğiniz soruyu veya konuyu belirtin."

    system = (
        f"{_JARVIS_BASE}\n\n"
        "Ansiklopedik bilgiye sahip, analitik düşünen bir asistanısın. "
        "Sorulara:\n"
        "- Doğru, güncel ve kapsamlı cevap ver\n"
        "- Gerekirse adım adım açıkla\n"
        "- Farklı bakış açılarını sun\n"
        "- Türkçe, akıcı ve anlaşılır konuş"
    )
    return _ask_ai(system, soru)
