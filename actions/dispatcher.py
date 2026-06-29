"""
JARVIS Action Dispatcher — kural tabanlı yönlendirici.
Eşleşme yoksa None döner → çağıran AI'a iletir.
"""

import logging
import re
import time
from typing import Callable

logger = logging.getLogger(__name__)

# ── Import'lar ────────────────────────────────────────────────────────── #
from .open_app         import open_app
from .send_message     import send_message
from .whatsapp_auto    import whatsapp_send
from .email_action     import email_gonder, _extract_email
from .screen_read      import screen_read, _extract_screen
from .clipboard_ai     import clipboard_ai, _extract_clip_ai
import sys as _sys
_sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent))
from core.scheduler    import schedule_action, _extract_schedule
from .web_search     import web_search
from .weather        import weather_action
from .reminder       import reminder
from .youtube        import youtube
from .volume_control import volume_control
from .salad import salad_ac, salad_kapat
from .streaming import netflix_ac, twitch_ac, tiktok_ac, twitter_ac, instagram_ac, _extract_twitch
from .windows_extras import (
    oyun_modu, fokus_modu, parlaklik_ayarla, mikrofon_toggle,
    emoji_paneli, clipboard_gecmis,
    _extract_oyun_modu, _extract_fokus, _extract_parlaklik,
)

from .system_control import (
    screenshot, lock_screen, shutdown, restart, sleep_mode,
    cancel_shutdown, empty_recycle_bin, show_desktop,
)
from .system_info import (
    battery_status, cpu_ram_usage, disk_usage, system_info,
    ip_info, running_apps, kill_process, wifi_info,
)
from .file_ops import (
    create_file, delete_file, open_file, find_file,
    create_folder, copy_file, move_file, rename_file,
    zip_files, unzip_file, list_files, open_folder, recent_files,
)
from .web_tools import (
    translate_text, maps_open, wikipedia_search, news_open,
    currency_info, define_word, open_url, image_search,
    flight_search, shopping_search,
)
from .productivity import (
    set_timer, cancel_timer, pomodoro, take_note, read_notes,
    clear_notes, calculate, generate_password, open_calendar,
    time_date, roll_dice, flip_coin, word_count,
)
from .media_control import (
    media_play_pause, media_next, media_prev, media_stop,
    spotify_open, open_radio, open_podcast,
)
from .quick_tools import (
    qr_generate, clipboard_read, clipboard_write, unit_convert,
    color_info, text_reverse, text_upper, text_lower,
    encoding_base64, hash_text,
)
from .window_manager import (
    minimize_all, restore_all, task_view, take_screenshot_region,
    open_task_manager, open_control_panel, run_command,
    ping_host, check_internet,
)
from .game_install import oyun_yukle, _extract_oyun
from .ai_skills import (
    film_oner, oyun_oner, muzik_oner, tarif_ver, kod_yaz,
    ozet_al, icerik_yaz, gunluk_plan, dil_pratik, genel_asistan,
    _extract_film, _extract_oyun as _extract_oyun_ai, _extract_muzik,
    _extract_tarif, _extract_kod, _extract_ozet, _extract_icerik,
    _extract_plan, _extract_dil, _extract_genel,
)
from .nlp import extract_query, stem, detect_intent
from .pc_automation import (
    list_windows, focus_window, close_window, maximize_window, minimize_window,
    type_text, press_hotkey, scroll_page,
    clear_temp, flush_dns, create_restore_point,
    list_startup_apps, open_startup_folder,
    toggle_night_mode, reset_network, open_network_settings,
    show_wifi_passwords, open_display_settings, open_sound_settings,
    open_windows_update, set_wallpaper, active_window_title,
)

# ── HERMES uzaktan / ek skill'ler ─────────────────────────────────────── #
from .approval        import bekleyenler, onayla, iptal, _extract_approve
from .game_mode       import oyun_hazirlik, steam_guncelle, mod_degistir, _extract_mod
from .anti_afk        import anti_afk, _extract_afk
from .discord_extra   import (discord_mute, discord_durum,
                              _extract_discord_mute, _extract_discord_durum)
from .media_extra     import spotify_mood, _extract_mood
from .net_tools       import hiz_testi
from .app_limit       import uygulama_limit, _extract_limit
from .self_code       import kendi_kodunu_yaz
from .notify          import bildirim_gonder, gunluk_ozet, _extract_notify
from .remote_security import (gorev_ekle, gorevler, gorev_calistir,
                              komut_gecmisi, _extract_task)
from .intent_router   import classify, normalize_command
from .webcam          import webcam_action
from .auto_clicker    import auto_clicker, _extract_clicker
from .macro           import macro_record, macro_play, macro_list, _extract_macro
from .order           import (order, open_cart, open_site,
                               _extract_order, _extract_cart, _extract_site)
from .mouse_control    import (mouse_click, mouse_move, mouse_drag, mouse_position,
                               _extract_click, _extract_move, _extract_drag)
from .smart_click      import smart_click, _extract_smart_click
from .extra_skills     import (konus, ekran_kapat, kripto_fiyat, en_cok_kaynak,
                               pano_temizle, bos_disk, uyanik_kal, uyku_serbest,
                               pc_bildirim, uyari_cal, tarayicilari_kapat,
                               _extract_konus, _extract_kripto, _extract_bildirim)
from .ekran_kaydi      import ekran_kaydi, _extract_kayit
from .power_skills     import (panik_modu, ekran_oku, ekran_ozetle, guc_plani,
                               zamanli_kapat, sabah_rutini, pil_uyari, pil_uyari_kapat,
                               zamanli_uyari, _extract_guc, _extract_zamanli, _extract_uyari)
from .auto_advanced    import (tus_tut, tus_spam, bekle_tikla, renge_tikla,
                               snippet_kaydet, snippet_yaz, snippet_liste,
                               pencere_diz, coklu_makro, blok_kir,
                               _extract_tus_tut, _extract_tus_spam, _extract_bekle_tikla,
                               _extract_renge_tikla, _extract_snip_kaydet,
                               _extract_snip_yaz, _extract_pencere_diz, _extract_coklu_makro,
                               _extract_blok_kir, mc_komut, _extract_mc_komut)
from .oneblock        import (oneblock, balik_tut, auto_eat,
                              _extract_oneblock, _extract_balik, _extract_eat)
from .yardim          import yardim
from .mc_agent        import mc_yap, _extract_mc_yap
from .mega1           import (uzak_terminal, kod_calistir, soru_coz, arastir,
                              doviz_altin, tam_saglik, gizlilik_modu, akilli_pano,
                              otomatik_cevap, hizli_ayar, _extract_terminal,
                              _extract_kod_calistir, _extract_arastir, _extract_cevap)
from .mega2           import (sayac_widget, toplanti_notu, sesli_kitap, kim_kullandi,
                              webcam_timelapse, supheli_giris, akilli_hatirlatici,
                              _extract_sayac, _extract_toplanti, _extract_kitap,
                              _extract_kim, _extract_timelapse, _extract_supheli,
                              _extract_akilli_hat)
from .vision_agent    import (gor_ekran, gor_yap, gor_oyna,
                              _extract_gor, _extract_gor_yap, _extract_oyna)
from .wol             import wol_uyandir, wol_bilgi, wol_etkinlestir, _extract_wol
from .akilli_ev       import (akilli_ev, akilli_ev_ekle, akilli_ev_liste,
                              _extract_ev, _extract_ev_ekle)
from .custom_cmd      import (komut_yarat, komut_sil, komut_liste, match_custom,
                              _extract_yarat, _extract_sil)
from .ajan            import ajan, _extract_ajan
from .routines        import eve_geliyorum, kilitle_raporla, pc_birak
from .release_skills   import (bot_loglari, bot_yeniden_baslat, komut_ara,
                               favoriler, pano_gecmisi, ekran_yayin, pil_esik,
                               konum, ne_indirdim, _extract_log, _extract_ara,
                               _extract_fav, _extract_yayin, _extract_pil_esik)
from .batch3          import (klasor_izle, kaynak_uyari, disk_dolu_uyari, desen_tikla,
                              akilli_afk, acik_pencere_sayisi, net_kullanan,
                              hizli_temizlik, rastgele_sec,
                              _extract_klasor, _extract_kaynak, _extract_desen,
                              _extract_afk2, _extract_rastgele)
from .batch4          import (sesli_not, pano_cevir, toplu_adlandir, ses_transkript,
                              resim_metin, dosya_sifrele, kod_hatasi, madde_ozet,
                              cevir_seslioku, gunluk_hatirlatici,
                              _extract_sesli_not, _extract_pano_cevir, _extract_toplu,
                              _extract_sifrele, _extract_madde, _extract_cevir_oku,
                              _extract_gunluk)
from .more_skills      import (bu_ne, zamanli_tekrar, watchdog, ram_temizle, ses_cihazi,
                               _extract_tekrar, _extract_watchdog)
from .auto_advanced    import koprusu, envanter_at, _extract_koprusu
from .vision_skills    import qr_oku, yuz_algila
from .media2_skills     import (now_playing, spotify_cal, ekran_cevir, gunluk_brief,
                                metin_trigger, farm_bekci, _extract_spotify_cal,
                                _extract_cevir, _extract_trigger, _extract_farm)
from .monitor2         import (site_izle, net_izle, yagmur_uyari, fiyat_takip,
                               _extract_site_izle, _extract_net_izle,
                               _extract_yagmur, _extract_fiyat)
from .files2           import (buyuk_dosya, resim_boyut, resim_pdf, video_gif,
                               _extract_resim_boyut, _extract_path, _extract_video_gif)
from .extra2           import (odak_engelle, kronometre, uygulama_istatistik,
                               pencere_seffaf, surucu_guncelle, disk_saglik,
                               json_guzel, kisa_link, wifi_qr, web_ozet, email_taslak,
                               sesli_dikte, zamanli_mesaj, discord_mesaj,
                               _extract_odak, _extract_krono, _extract_istat,
                               _extract_seffaf, _extract_json, _extract_kisa,
                               _extract_wifi_qr, _extract_web_ozet, _extract_email_taslak,
                               _extract_dikte, _extract_zamanli_mesaj, _extract_discord_mesaj)


# ── Parametre çıkarıcılar ────────────────────────────────────────────── #
def _p(**kw): return lambda _: kw          # sabit parametreler
def _empty(_): return {}                    # parametre yok


# ── Akıllı app adı çıkarıcı (nlp.py destekli) ────────────────────────── #
def _extract_app(msg):
    """
    "Notepad aç" → notepad   |   "VLC'yi başlat" → vlc
    Eylem kelimesinden SONRA gelen ilk anlamlı token'ı alır.
    """
    # Eylem kelimesinden sonrasını bul
    m = re.search(
        r"\b(?:aç|başlat|çalıştır|calistir|open|start|launch|run)\b\s*['\"]?\s*(.+)",
        msg, re.I
    )
    if m:
        candidate = m.group(1).strip().rstrip(".'\",;")
        # Sadece kısa bir isim bekliyoruz (uygulama adı)
        return {"app_name": candidate.split()[0] if candidate else msg}

    # Eylem sonda: "VLC aç" → VLC önde
    m2 = re.search(
        r"^(.+?)\s+(?:aç|başlat|çalıştır|open|start|launch)\b",
        msg, re.I
    )
    if m2:
        return {"app_name": m2.group(1).strip()}

    q = extract_query(msg)
    return {"app_name": q or msg}


def _extract_msg(msg):
    m = re.search(
        r"(whatsapp|telegram|discord|instagram|messenger|wp|tg|ig)?\s*"
        r"([^\s']+(?:\s+\w+)?)'(?:y?[ae])\s+(.+?)\s+"
        r"(de|yaz|gönder|ilet|söyle|at)\b",
        msg, re.I,
    )
    if m:
        plat = m.group(1) or "whatsapp"
        return {"receiver": m.group(2).strip(), "message_text": m.group(3).strip(), "platform": plat}
    return {}


def _extract_weather(msg):
    # "İstanbul'da hava nasıl" → city=istanbul
    m = re.search(
        r"([\w\s]+?)(?:'[dnt]\w*)?\s+(?:hava|weather|iklim)",
        msg, re.I
    )
    city = m.group(1).strip() if m else extract_query(msg, {"hava","durumu","weather","nasil","nasıl","bugün","yarın","hafta"})
    when = next((w for w in ("yarın","hafta sonu","hafta","tomorrow","weekend") if w in msg.lower()), "bugün")
    return {"city": city, "time": when}


def _extract_reminder(msg):
    from datetime import date, timedelta
    date_m = re.search(r"(\d{4}-\d{2}-\d{2})", msg)
    time_m = re.search(r"(\d{1,2}[:.](\d{2}))", msg)
    today  = date.today()
    d_str  = date_m.group(1) if date_m else (today + timedelta(days=1) if "yarın" in msg else today).strftime("%Y-%m-%d")
    t_str  = time_m.group(1).replace(".", ":") if time_m else "09:00"
    clean  = re.sub(r"\d{4}-\d{2}-\d{2}|\d{1,2}[:.]?\d{2}", "", msg)
    for kw in ("hatırlat","hatırlatıcı","reminder","saat","yarın","bugün"):
        clean = re.sub(kw, "", clean, flags=re.I)
    return {"date": d_str, "time": t_str, "message": clean.strip(" .,;")}


def _extract_youtube(msg):
    """
    "YouTube aç"              → query="" (ana sayfa)
    "YouTube'da lofi müzik"   → query="lofi müzik"
    "Lofi müzik YouTube'da"   → query="lofi müzik"
    "Bilim videosu izle"      → query="bilim videosu"
    """
    q = extract_query(msg, extra_stop={
        "youtube", "yt", "video", "izle", "oynat", "cal", "çal",
        "play", "ara", "search", "aç", "ac", "başlat", "baslat",
        "git", "gir", "open", "bana", "lütfen", "lutfen", "da", "de",
    })
    return {"action": "play", "query": q}


def _extract_volume(msg):
    low = msg.lower()
    m = re.search(r"(\d+)", msg)
    v = int(m.group(1)) if m else 10
    # 1) Yön belirten anahtar kelimeler önceliklidir ("sesi 10 artır" → +10)
    for kws, act in [
        (["azalt", "düşür", "dusur", "kıs", "kis", "lower", "down"], "azalt"),
        (["kapat", "mute", "sessize", "kes", "sustur"],              "kapat"),
        (["unmute", "geri aç", "geri ac"],                           "aç"),
        (["artır", "arttır", "artir", "yükselt", "yukselt", "up"],   "artır"),
    ]:
        if any(k in low for k in kws):
            return {"action": act, "value": v}
    # 2) Sayı var, yön yok → mutlak seviye ("sesi 100 yap", "ses 50", "ses %0")
    if m:
        return {"action": "set", "value": v}
    # 3) Sayısız "ses aç" → aç
    if "aç" in low or "ac" in low:
        return {"action": "aç", "value": v}
    return {"action": "artır", "value": v}


def _extract_timer(msg):
    m_min = re.search(r"(\d+)\s*(dakika|dk|min)", msg, re.I)
    m_sec = re.search(r"(\d+)\s*(saniye|sn|sec)", msg, re.I)
    label = re.sub(r"\d+\s*(dakika|dk|min|saniye|sn|sec|zamanlayıcı|timer|kur|ayarla)", "", msg, flags=re.I).strip()
    return {
        "minutes": int(m_min.group(1)) if m_min else 0,
        "seconds": int(m_sec.group(1)) if m_sec else 0,
        "label":   label or "Zamanlayıcı",
    }


def _extract_calc(msg):
    # Önce saf matematiksel ifade ara
    math_m = re.search(r"[\d\s\+\-\*\/\^\(\)\.]+", msg)
    if math_m and any(op in math_m.group() for op in "+-*/^"):
        return {"expression": math_m.group().strip()}
    e = extract_query(msg, {"hesapla","kaça","eder","ne","sonucu","calculate","nedir","eşittir","topla","çarp","böl","çıkar"})
    return {"expression": e}


def _extract_note(msg):
    # "not al: içerik" veya "şunu not et içerik"
    m = re.search(r"(?:not\s+al|not\s+ekle|kaydet|remember)[:\s]+(.+)", msg, re.I)
    c = m.group(1).strip() if m else extract_query(msg, {"not","al","ekle","kaydet","yaz","note","remember","bunu","şunu"})
    return {"content": c}


def _extract_translate(msg):
    # "X'i ingilizceye çevir" veya "çevir: X"
    m = re.search(r"(?:çevir|translate|tercüme)[:\s]+(.+?)(?:\s+(?:türkçe|ingilizce|almanca|fransızca|ispanyolca))?$", msg, re.I)
    text = m.group(1).strip() if m else extract_query(msg, {"çevir","translate","tercüme","et","lütfen"})
    tgt  = "tr"
    for lang, code in [("ingilizce","en"),("almanca","de"),("fransızca","fr"),("ispanyolca","es"),("türkçe","tr"),("rusça","ru"),("japonca","ja")]:
        if lang in msg.lower(): tgt = code; break
    if "türkçe" not in msg.lower() and tgt == "tr": tgt = "tr"
    return {"text": text, "target": tgt}


def _extract_maps(msg):
    # "Beşiktaş'a nasıl gidilir" → location=Beşiktaş
    m = re.search(r"([\w\s]+?)(?:'[ye]\w*)?\s+(?:nasıl gidilir|yol tarifi|nerede|konumu)", msg, re.I)
    loc = m.group(1).strip() if m else extract_query(msg, {"harita","maps","nerede","yol","tarifi","nereye","konum","gitmek","konumu","nasıl","gidilir"})
    return {"location": loc}


def _extract_wiki(msg):
    q = extract_query(msg, {"wikipedia","vikipedi","wiki","nedir","kimdir","hakkında","tarihçesi","anlat","bilgi","ver"})
    return {"query": q}


def _extract_news(msg):
    t = extract_query(msg, {"haber","news","gündem","son","dakika","göster","getir","var","mı"})
    return {"topic": t}


def _extract_currency(msg):
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*([A-Za-z]+(?:\s+lira|si|'si)?)\s*(?:kaç|ne kadar|=|to)?\s*([A-Za-z]+)?", msg, re.I)
    if m:
        codes = {"dolar":"USD","euro":"EUR","pound":"GBP","sterlin":"GBP","yen":"JPY","lira":"TRY","try":"TRY","usd":"USD","eur":"EUR"}
        f = codes.get(m.group(2).lower(), m.group(2).upper())
        t = codes.get((m.group(3) or "TRY").lower(), (m.group(3) or "TRY").upper())
        return {"amount": m.group(1).replace(",","."), "from": f, "to": t}
    return {"amount": "1", "from": "USD", "to": "TRY"}


def _extract_define(msg):
    w = extract_query(msg, {"tanımı","anlamı","nedir","define","meaning","sözlük","tdk","ne","demek"})
    return {"word": w}


def _extract_file(msg):
    m = re.search(r"(?:aç|open)\s+(.+)", msg, re.I)
    return {"path": m.group(1).strip() if m else msg}


def _extract_find(msg):
    q = extract_query(msg, {"bul","find","ara","search","dosya","klasör","nerede"})
    return {"name": q or msg}


def _extract_create_file(msg):
    m = re.search(r"(?:oluştur|create|yeni)\s+(?:dosya\s+)?(.+)", msg, re.I)
    return {"path": m.group(1).strip() if m else "yeni_dosya.txt"}


def _extract_folder(msg):
    m = re.search(r"(?:klasör|dizin|folder)\s+(?:oluştur|aç)?\s*(.+)|(?:oluştur|create)\s+(?:klasör|dizin|folder)\s+(.+)", msg, re.I)
    name = (m.group(1) or m.group(2) or "Yeni Klasör").strip() if m else "Yeni Klasör"
    return {"path": name}


def _extract_kill(msg):
    q = extract_query(msg, {"kapat","sonlandır","öldür","kill","close","uygulamayı","programı","prosesi"})
    return {"name": q or ""}


def _extract_screenshot(msg):
    return {}


def _extract_shutdown(msg):
    m = re.search(r"(\d+)\s*(saniye|dakika|sn|dk)", msg, re.I)
    if m:
        val = int(m.group(1)) * (60 if "dakika" in m.group(2) or "dk" in m.group(2) else 1)
        return {"delay": val}
    return {"delay": 0}


def _extract_unit(msg):
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*(\w+)\s*(?:=|kaç|ne kadar|to|→)?\s*(\w+)?", msg, re.I)
    if m:
        return {"value": m.group(1).replace(",","."), "from": m.group(2).lower(), "to": (m.group(3) or "").lower()}
    return {}


def _extract_ping(msg):
    m = re.search(r"ping\s+([^\s]+)", msg, re.I)
    return {"host": m.group(1) if m else "google.com"}


def _extract_run_cmd(msg):
    m = re.search(r"(?:çalıştır|run|komu[tu])\s+(.+)", msg, re.I)
    return {"command": m.group(1).strip() if m else ""}


def _extract_dice(msg):
    m = re.search(r"(\d+)\s*[yx][üu][zZ]?l[üu]", msg, re.I)
    sides = int(m.group(1)) if m else 6
    mc    = re.search(r"(\d+)\s*(?:adet|tane|kez)", msg, re.I)
    return {"sides": sides, "count": int(mc.group(1)) if mc else 1}


def _extract_hash(msg):
    alg  = next((a for a in ["sha256","sha512","sha1","md5"] if a in msg.lower()), "sha256")
    text = extract_query(msg, {"hash","özetle","md5","sha256","sha512","sha1","checksum","hesapla"})
    return {"text": text, "algorithm": alg}


def _extract_clip_write(msg):
    m = re.search(r"(?:kopyala|panoya\s+kopyala|copy)\s+(.+)", msg, re.I)
    return {"text": m.group(1).strip() if m else ""}


def _extract_qr(msg):
    url_m = re.search(r"(https?://\S+)", msg)
    if url_m:
        return {"text": url_m.group(1).strip()}
    text = extract_query(msg, {"qr","kod","oluştur","yap","üret","al","çıkar","kodu","linkin"})
    return {"text": text}


def _extract_word_translate(msg):
    """'hello ne demek', 'merhaba ingilizcesi' gibi sorular için."""
    m = re.search(r"^(.+?)\s+ne\s+demek\b", msg, re.I)
    if m:
        word = m.group(1).strip()
        is_latin = bool(re.match(r"^[a-zA-Z\s]+$", word))
        return {"text": word, "target": "tr" if is_latin else "en"}
    m2 = re.search(r"^(.+?)\s+(nasıl\s+(?:söylenir|yazılır|denir|çevrilir))\b", msg, re.I)
    if m2:
        return {"text": m2.group(1).strip(), "target": "en"}
    lang_map = {"türkçesi": "tr", "ingilizcesi": "en", "almancası": "de",
                "fransızcası": "fr", "ispanyolcası": "es", "rusçası": "ru",
                "japonca": "ja", "arapçası": "ar"}
    for suffix, code in lang_map.items():
        if suffix in msg.lower():
            word = re.sub(suffix, "", msg, flags=re.I).strip()
            return {"text": word, "target": code}
    return {"text": msg, "target": "tr"}


def _extract_whatsapp_send(msg):
    """
    Esnek WhatsApp parametre çıkarıcı.
    Örnekler:
      "Ahmet'e mesaj gönder: merhaba nasılsın"
      "Ahmet'e şunu yaz merhaba"
      "whatsapp'tan Ahmet'e merhaba de"
      "Ahmet Yılmaz'a whatsapp at mesajım şu merhaba"
      "Ahmet'e whatsapp mesajı gönder merhaba nasılsın bugün ne yapıyorsun"
    """
    # Edatlar / bağlaçlar receiver olamaz
    _SKIP = {"ile", "bir", "bu", "şu", "o", "ve", "ya", "da", "de", "ki",
             "ben", "sen", "biz", "siz", "whatsapp", "wp", "mesaj", "mesaji"}

    def _clean_receiver(name: str) -> str:
        parts = name.strip().split()
        # Baştaki edatı at
        while parts and parts[0].lower() in _SKIP:
            parts = parts[1:]
        return " ".join(parts)

    # Kalıp 1: "KISI'e/a ... FIIL [:]  MESAJ"  (fiilden sonrası mesaj)
    m = re.search(
        r"([A-ZÇĞİÖŞÜa-zçğışöüı][^\s']{1,30}(?:\s+[A-ZÇĞİÖŞÜa-zçğışöüı][^\s']{1,20})?)"
        r"'(?:y?[ae])\s+(?:whatsapp\s+)?(?:mesaj[ıi]?\s+)?"
        r"(?:gönder|at|yaz|ilet|söyle|de)[:\s]+(.+)",
        msg, re.I,
    )
    if m:
        recv = _clean_receiver(m.group(1))
        if recv:
            return {"receiver": recv, "message_text": m.group(2).strip()}

    # Kalıp 2: "KISI'e şunu yaz/de: MESAJ"  veya  "şunu yaz KISI'e: MESAJ"
    m2 = re.search(
        r"([A-ZÇĞİÖŞÜa-zçğışöüı][^\s']{1,30}(?:\s+[A-ZÇĞİÖŞÜa-zçğışöüı][^\s']{1,20})?)"
        r"'(?:y?[ae])\s+(?:şunu\s+)?(?:yaz|de|söyle|gönder|at|ilet)\s+(.+)",
        msg, re.I,
    )
    if m2:
        recv = _clean_receiver(m2.group(1))
        if recv:
            return {"receiver": recv, "message_text": m2.group(2).strip()}

    # Kalıp 3: whatsapp ile/dan/üzerinden  KISI'e  MESAJ
    m3 = re.search(
        r"(?:whatsapp|wp)\s*(?:ile|'[dt]an|üzerinden|'(?:y?[ae]))?\s+"
        r"([A-ZÇĞİÖŞÜa-zçğışöüı][^\s']{1,30}(?:\s+[A-ZÇĞİÖŞÜa-zçğışöüı][^\s']{1,20})?)"
        r"'(?:y?[ae]).{0,20}?(?:gönder|at|yaz|ilet|söyle|de)[:\s]+(.+)",
        msg, re.I,
    )
    if m3:
        return {"receiver": m3.group(1).strip(), "message_text": m3.group(2).strip()}

    # Kalıp 4: son çare — "KISI" + "whatsapp" + geri kalan = mesaj
    m4 = re.search(
        r"([A-ZÇĞİÖŞÜa-zçğışöüı][^\s']{1,30}(?:\s+[A-ZÇĞİÖŞÜa-zçğışöüı][^\s']{1,20})?)"
        r"'(?:y?[ae]).+?(?:gönder|at|yaz|ilet|söyle|de)[,:\s]+(.+)",
        msg, re.I,
    )
    if m4:
        return {"receiver": m4.group(1).strip(), "message_text": m4.group(2).strip()}

    return {}


def _extract_window_title(msg):
    kws = r"\b(pencere|window|uygulama|program)\b"
    verbs = r"\b(kapat|büyüt|küçült|öne getir|odaklan|focus|maximize|minimize|close)\b"
    clean = re.sub(kws, "", re.sub(verbs, "", msg, flags=re.I), flags=re.I).strip(" .,;?")
    return {"title": clean}


def _extract_type_text(msg):
    m = re.search(r"(?:yaz|type|söyle|gir)\s*[:\-]?\s*(.+)", msg, re.I)
    return {"text": m.group(1).strip() if m else msg}


def _extract_hotkey(msg):
    # "ctrl+c gönder", "win+d bas", "alt f4"
    m = re.search(r"([a-z]+(?:[+\s][a-z0-9]+)+)", msg, re.I)
    return {"keys": m.group(1).replace(" ", "+") if m else msg}


def _extract_scroll(msg):
    direction = "aşağı" if any(w in msg.lower() for w in ["aşağı","down","alta","aşa"]) else "yukarı"
    m = re.search(r"(\d+)", msg)
    return {"direction": direction, "amount": int(m.group(1)) if m else 5}


def _extract_wallpaper(msg):
    m = re.search(r"([A-Za-z]:\\[^\s]+\.(jpg|jpeg|png|bmp|webp))", msg, re.I)
    return {"path": m.group(1) if m else ""}


def _extract_night(msg):
    if any(w in msg.lower() for w in ["aç","open","enable","on","aktif"]):
        return {"action": "aç"}
    if any(w in msg.lower() for w in ["kapat","off","disable","kapa"]):
        return {"action": "kapat"}
    return {"action": "toggle"}


def _extract_restore_point(msg):
    clean = re.sub(r"\b(geri yükleme|noktası|oluştur|restore|point|create)\b", "", msg, flags=re.I).strip()
    return {"description": clean or "JARVIS Yedek Noktası"}


def _extract_search(msg):
    q = re.sub(r"\b(ara|search|google|bul|tara|web|internet)\b", "", msg, flags=re.I).strip()
    return {"query": q}


def _extract_image_search(msg):
    q = re.sub(r"\b(görsel|resim|fotoğraf|image|photo|picture|ara|search|bul)\b", "", msg, flags=re.I).strip()
    return {"query": q}


def _extract_spotify(msg):
    q = extract_query(msg, extra_stop={
        "spotify", "muzik", "müzik", "music", "cal", "çal",
        "oynat", "dinle", "ac", "aç", "baslat", "başlat",
        "git", "gir", "open", "start",
    })
    return {"query": q}


def _extract_shopping(msg):
    q = re.sub(r"\b(trendyol|satın al|al|sipariş|ürün|shopping|shop|mağaza)\b", "", msg, flags=re.I).strip()
    return {"query": q}


def _extract_flight(msg):
    m = re.search(r"(?:nereden|kalkış|from)\s+(\w+).+(?:nereye|varış|to)\s+(\w+)", msg, re.I)
    if m: return {"from": m.group(1), "to": m.group(2)}
    parts = re.findall(r"\b([A-ZÇĞİÖŞÜa-zçğışöüı]{3,15})\b", re.sub(r"\b(uçuş|uçak|bilet|flight|ara|bul)\b", "", msg, flags=re.I))
    if len(parts) >= 2: return {"from": parts[0], "to": parts[1]}
    return {}


def _extract_pomodoro(msg):
    m = re.search(r"(\d+)", msg)
    return {"work": int(m.group(1)) if m else 25}


def _extract_password(msg):
    m = re.search(r"(\d+)", msg)
    return {"length": int(m.group(1)) if m else 16}


# ====================================================================== #
#  KURAL TABLOSU  (regex_list, handler, extractor)                       #
#  Sıra önemli — daha spesifik kurallar önce gelir.                     #
# ====================================================================== #
_RULES: list[tuple[list[str], Callable, Callable]] = [

    # ── Hesap makinesi → gerçek calc.exe; AMA kod/site isteği DEĞİLSE ──── #
    ([r"^(?!.*\b(html|kod|python|javascript|js|css|site|web|proje|yazılım|uygulama yaz)\b)"
      r".*\b(hesap makin[ae]s[ıi]|hesaplayıcı|calculator|kalkülatör)\b.*\b(aç|ac|başlat|getir)\b",
      r"^\s*(hesap makin[ae]s[ıi]|hesaplayıcı|calculator)\s*$"],
     open_app, lambda _: {"app_name": "hesap makinesi"}),

    # ── Rutinler (telefondan tek komut) ───────────────────────────────── #
    ([r"\b(eve geliyorum|eve geldim|geliyorum|hazırla beni)\b"],
     eve_geliyorum, _empty),
    ([r"\b(kilitle ve raporla|kilitle.*koru|çıkıyorum koru|koruyarak kilitle)\b"],
     kilitle_raporla, _empty),
    ([r"\b(bilgisayarı bırak|pcyi bırak|çıkıyorum uyut|işim bitti uyut)\b"],
     pc_birak, _empty),

    # ── Yayın öncesi cila skilleri (1-10) ─────────────────────────────── #
    ([r"\b(bot log\w*|loglar\w*|log göster|hata kayd\w*|bot kayd\w*)\b"],
     bot_loglari, _extract_log),
    ([r"\b(botu yeniden başlat|botu restart|bot restart|yeniden başlat bot|"
      r"botu tekrar başlat|bot resetle)\b"],
     bot_yeniden_baslat, _empty),
    ([r"\b(komut ara|skill ara|hangi komut\w*)\b", r"^\s*ara\s+\w+"],
     komut_ara, _extract_ara),
    ([r"\bfavori\w*\s*(ekle|sil)\b", r"\b(favorilerim|favoriler\w*)\b"],
     favoriler, _extract_fav),
    ([r"\b(pano geçmiş\w*|kopyalad\w* geçmiş|clipboard geçmiş|son kopyalad\w*)\b"],
     pano_gecmisi, _empty),
    ([r"\b(ekran yayın\w*|ekranı yayınla|kısa yayın|canlı yayın)\b"],
     ekran_yayin, _extract_yayin),
    ([r"\bpil\b.{0,12}\b(olunca|altına|düşünce|inince|uyar\w*|haber)\b",
      r"\b(pil eşik\w*|pil takib\w*|şarj uyar\w*)\b"],
     pil_esik, _extract_pil_esik),
    ([r"\b(konum\w*|neredey\w*|lokasyon\w*|location|nerede bu)\b"],
     konum, _empty),
    ([r"\b(ne indirdim|son indir\w*|indirilenler\w*|indirdiklerim)\b"],
     ne_indirdim, _empty),

    # ── Ajan (çok adımlı görev/proje/kod — istenen dilde dosya yazar) ─── #
    ([r"\bajan\b\s*[:\-]",
      r"\b(html|css|javascript|python|web|site|uygulama|program|proje)\b.{0,30}\b(yap|yaz|kur|oluştur)\b",
      r"\b(proje (yap|oluştur)|uygulama yap|site yap|oyun yap)\b"],
     ajan, _extract_ajan),

    # ── Ajan (çok adımlı görev: proje yap, kur+çalıştır) ──────────────── #
    ([r"\bajan\b\s*[:\-]", r"\b(proje (yap|oluştur)|uygulama yap|site yap)\b.{0,40}"],
     ajan, _extract_ajan),

    # ── Özel komut yönetimi (yarat/sil/liste) ─────────────────────────── #
    ([r"\bkomut\s*(yarat|ekle|oluştur|tanımla)\b.{0,40}[:\-]"],
     komut_yarat, _extract_yarat),
    ([r"\bkomut\s*(sil|kaldır)\b"],
     komut_sil, _extract_sil),
    ([r"\b(komutlar[ıi]m|özel komutlar|komut listesi)\b"],
     komut_liste, _empty),

    # ── Yardım / neler yapabilirsin (EN ÖNCE) ─────────────────────────── #
    ([r"\bneler?\s*yapab", r"\bne\s*yapab", r"\byapabildikl", r"\byetenek",
      r"\bkomutlar", r"\bskill", r"^\s*/?skills?\s*$", r"^\s*yardım\s*$",
      r"^\s*help\s*$", r"\bnasıl kullan", r"\bne işe yara",
      r"\b(rehber|kullanım kılavuzu|kılavuz|kullanım)\b"],
     yardim, _empty),

    # ── Minecraft chat/komut (EN ÖNCE — 'gamemode' vb. kelimeleri kapsın) ── #
    # T'ye bas → komutu yaz → Enter. run_command/oyun_modu'ndan önce gelmeli.
    ([r"\b(mc|minecraft)\s*(komut|chat|chate|yaz|mesaj)\b",
      r"\bt'?ye\s*bas(?:ıp)?\b.{0,15}\b(yaz|komut)\b",
      r"\bsohbete?\s*yaz\b"],
     mc_komut, _extract_mc_komut),

    # ── Zamanlı tekrar (EN ÖNCE — "her 5 dk <komut>") ─────────────────── #
    ([r"\btekrar[ıi]?\s*(durdur|iptal|kapat)\b"],
     zamanli_tekrar, lambda _: {"action": "stop"}),
    ([r"\bher\s*\d+\s*(saniye|sn|dakika|dk|saat)\b"],
     zamanli_tekrar, _extract_tekrar),

    # ── Watchdog (open_app'tan ÖNCE — "X kapanırsa aç") ───────────────── #
    ([r"\bwatchdog\b",
      r"\b[\w\.]+\s*(kapan[ıi]rsa|giderse|çökerse|cokerse)\b.{0,10}\b(aç|ac|başlat|baslat)\b"],
     watchdog, _extract_watchdog),

    # ── QR oku (qr_generate'ten ÖNCE) ─────────────────────────────────── #
    ([r"\bqr\b.{0,10}\b(oku|çöz|coz|tara|decode|ne yazıyor|nedir)\b",
      r"\bekrandaki\s*qr\b"],
     qr_oku, _empty),

    # ── Yüz algıla (webcam'den ÖNCE) ──────────────────────────────────── #
    ([r"\byüz\s*(algıla|algila|var|tan[ıi]|kontrol|say)\b",
      r"\bkamerada\s*(kim|yüz|biri|insan)\b", r"\bkim\s*var\b.{0,10}\bkamera"],
     yuz_algila, _empty),

    # ── Şu an çalan şarkı ─────────────────────────────────────────────── #
    ([r"\b(ne çalıyor|şu an çalan|çalan şarkı|now playing|hangi şarkı|şarkı ne)\b"],
     now_playing, _empty),

    # ── Spotify'da şarkı çal/ara (spotify_open'dan ÖNCE) ──────────────── #
    ([r"\bspotif\w*\b.{0,30}\b(çal|cal|ara)\b",
      r"\b[\w\s]{2,30}\s*(şarkısını|şarkısı|sarkisini)\s*(çal|cal|aç|ara)\b",
      r"\bçal\b.{0,20}\bspotif"],
     spotify_cal, _extract_spotify_cal),

    # ── Ekrandaki yazıyı çevir (translate/ekran_oku'dan ÖNCE) ─────────── #
    ([r"\bekran\w*\b.{0,18}\bçevir\b",
      r"\bekrandaki\b.{0,15}\b(yazıyı|metni)\b.{0,10}\bçevir"],
     ekran_cevir, _extract_cevir),

    # ── Metin görününce bildir (OCR izleme) ───────────────────────────── #
    ([r"\bekranda\b.{0,40}\b(görününce|gorununce|çıkınca|cikinca|belirince|gelince|bitince|tamamlan\w*|olunca|yazınca)\b.{0,18}\b(haber ver|bildir|söyle|uyar|mesaj at)\b",
      r"\bizlemeyi (bırak|durdur)\b"],
     metin_trigger, _extract_trigger),

    # ── Farm bekçisi ──────────────────────────────────────────────────── #
    ([r"\bfarm\s*(bekçi|bekci|izle|takip|gözcü|gozcu)\b", r"\bfarmı izle\b"],
     farm_bekci, _extract_farm),

    # ── Günlük brief (hava+haber) ─────────────────────────────────────── #
    ([r"\b(günlük brief|sabah özeti|sabah brief|brief ver|hava.*haber)\b"],
     gunluk_brief, _empty),

    # ── MC: Köprü kur ─────────────────────────────────────────────────── #
    ([r"\bköprü(yü)?\s*(kur|yap|durdur|bırak|birak|dur)\b", r"\bkopru\s*(kur|yap)\b",
      r"\bbridge\b"],
     koprusu, _extract_koprusu),

    # ── MC: Envanteri at ──────────────────────────────────────────────── #
    ([r"\b(envanteri|envanter|eşyaları|esyalari)\s*(at|boşalt|bosalt|sil|dök|dok|temizle)\b"],
     envanter_at, _empty),

    # ══ YENİ BATCH (üst öncelik — çakışan eski kurallardan önce) ════════ #
    # Web sayfası özetle (ozet_al'dan ÖNCE)
    ([r"\b(sayfayı|siteyi|linki|web)\b.{0,15}\bözetle\b",
      r"\bözetle\b.{0,10}(https?://|\b[\w\-]+\.[a-z]{2,}/)"],
     web_ozet, _extract_web_ozet),

    # Zamanlı mesaj (whatsapp/schedule'dan ÖNCE)
    ([r"\bsaat\s*\d{1,2}[:.]\d{2}\b.{0,30}\b(whatsapp|wp|mesaj|yaz|gönder|at)\b"],
     zamanli_mesaj, _extract_zamanli_mesaj),

    # E-posta taslağı (icerik_yaz'dan ÖNCE)
    ([r"\b(e-?posta|email|mail)\s*(taslağı|taslak)\b",
      r"\b(e-?posta|email|mail)\s*(yaz|hazırla|oluştur)\b.{0,40}"],
     email_taslak, _extract_email_taslak),

    # Kısa link
    ([r"\b(kısalt|kisalt|kısa link|link kısalt|url kısalt)\b"],
     kisa_link, _extract_kisa),

    # WiFi QR
    ([r"\bwifi\s*qr\b"],
     wifi_qr, _extract_wifi_qr),

    # JSON güzelleştir
    ([r"\bjson\b.{0,12}\b(güzelleştir|guzellestir|formatla|düzenle|indent)\b"],
     json_guzel, _extract_json),

    # Sesli dikte (TTS/konuş'tan ÖNCE)
    ([r"\b(dikte|konuşarak yaz|sesle yaz|sesli yaz|söyledikçe yaz)\b"],
     sesli_dikte, _extract_dikte),

    # Discord'a mesaj (discord_mute/durum'dan ÖNCE)
    ([r"\bdiscord'?[ae]?\s*(yaz|mesaj|gönder)\b.{0,5}[:\-]"],
     discord_mesaj, _extract_discord_mesaj),

    # Odak engelleyici (fokus_modu'dan ÖNCE — farklı: dikkat dağıtanı kapatır)
    ([r"\bodak\s*engelle\b", r"\bdikkat dağıtan", r"\bçalışma modu\b",
      r"\bodak modu (durdur|kapat|bitir)\b"],
     odak_engelle, _extract_odak),

    # Kronometre
    ([r"\bkronometre\b", r"\b(süre tut|kronometreyi)\b"],
     kronometre, _extract_krono),

    # Uygulama istatistiği
    ([r"\buygulama\s*(istatisti|takibi|kullanım süre|süresi)",
      r"\bhangi uygulamada ne kadar\b"],
     uygulama_istatistik, _extract_istat),

    # Pencere şeffaflığı
    ([r"\bpencere\w*\s*(şeffaf|seffaf|opaklık|saydam)"],
     pencere_seffaf, _extract_seffaf),

    # Sürücü/güncelleme kontrolü
    ([r"\b(sürücü|surucu)\s*güncelle", r"\bgüncelleme\s*(var mı|kontrol|bak)\b",
      r"\bwinget upgrade\b"],
     surucu_guncelle, _empty),

    # Disk sağlığı (disk_usage'dan ÖNCE)
    ([r"\bdisk\s*(sağlığı|sagligi|sağlık|health|smart)\b"],
     disk_saglik, _empty),

    # En büyük dosyalar
    ([r"\b(en büyük dosya|büyük dosyalar|yer kaplayan|disk dolduran)\b"],
     buyuk_dosya, _empty),

    # Resim → PDF (resim_boyut'tan ÖNCE)
    ([r"\bresim\w*\b.{0,15}\bpdf\b", r"\bpdf\s*yap\b.{0,30}resim"],
     resim_pdf, _extract_path),

    # Video → GIF
    ([r"\b(video\w*|mp4)\b.{0,15}\bgif\b", r"\bgif\s*yap\b"],
     video_gif, _extract_video_gif),

    # Resim boyutlandır / format
    ([r"\bresm?i?\b.{0,15}\b(küçült|kucult|boyutlandır|yeniden boyut)\b",
      r"\b(png|jpg|jpeg|webp)\b.{0,10}\b(yap|çevir|dönüştür)\b.{0,40}\.(jpg|jpeg|png|webp|bmp)"],
     resim_boyut, _extract_resim_boyut),

    # Site izle / internet izle / yağmur / fiyat takip
    ([r"\bsite\w*\s*izle", r"\bsiteyi izle\b", r"\bsite izlemeyi durdur\b"],
     site_izle, _extract_site_izle),
    ([r"\binternet\w*\s*izle", r"\binterneti izle\b", r"\binternet izlemeyi durdur\b"],
     net_izle, _extract_net_izle),
    ([r"\byağmur\b", r"\bşemsiye\b"],
     yagmur_uyari, _extract_yagmur),
    ([r"\bfiyat\s*(takip|izle|takibi)\b"],
     fiyat_takip, _extract_fiyat),

    # ══ BATCH3/4 (üst öncelik) ═════════════════════════════════════════ #
    ([r"\bklasör\w*\s*izle", r"\bklasör izlemeyi durdur\b", r"\bdosya gelince\b"],
     klasor_izle, _extract_klasor),
    ([r"\bkaynak\s*uyar", r"\b(cpu|ram)\b.{0,15}\b(yüksek|dolarsa|olunca)\b.{0,10}\b(uyar|bildir|haber)\b"],
     kaynak_uyari, _extract_kaynak),
    ([r"\bdisk\s*(dolu|doluyor|doluluk)\b", r"\bdisk dolmak\b"],
     disk_dolu_uyari, _empty),
    ([r"\bdesen\s*(tıkla|durdur)\b", r"\b(sağ\s*sol|sol\s*sağ)\s*tıkla", r"\bdeğişimli tıkla\b"],
     desen_tikla, _extract_desen),
    ([r"\b(akıllı afk|akilli afk)\b", r"\bafk kalma\b"],
     akilli_afk, _extract_afk2),
    ([r"\b(açık pencere say|kaç pencere|pencere sayısı|kaç sekme)\b"],
     acik_pencere_sayisi, _empty),
    ([r"\b(internet kullanan|net kullanan|hangi (program|uygulama).{0,12}internet)\b"],
     net_kullanan, _empty),
    ([r"\b(hızlı temizlik|hizli temizlik|her şeyi temizle|bilgisayarı temizle)\b"],
     hizli_temizlik, _empty),
    ([r"\b(rastgele\s*(seç|sec|karar)|karar ver|hangisini? seç|benim için seç)\b"],
     rastgele_sec, _extract_rastgele),

    ([r"\bsesli\s*not\b", r"\bnotu? sesle\b", r"\bkonuşarak not\b"],
     sesli_not, _extract_sesli_not),
    ([r"\b(panoyu?|kopyaladığım[ıi]?|clipboard)\b.{0,12}\bçevir\b",
      r"\bçevir\b.{0,10}\bpano"],
     pano_cevir, _extract_pano_cevir),
    ([r"\btoplu\s*(adlandır|isimlendir|yeniden adlandır)\b"],
     toplu_adlandir, _extract_toplu),
    ([r"\bses\w*\s*(metne|yazıya|transkri)", r"\b(transkript|deşifre)\b"],
     ses_transkript, _extract_path),
    ([r"\bresim\w*\s*(metn|yazı)\b.{0,8}\b(çıkar|al|oku)\b", r"\bresimden metin\b",
      r"\bfotodan yazı\b"],
     resim_metin, _extract_path),
    ([r"\bdosya\s*(şifrele|sifrele|çöz|coz|kilitle|şifre aç)\b"],
     dosya_sifrele, _extract_sifrele),
    ([r"\b(kod hatası|hatayı (oku|çöz|açıkla)|bu hata ne|error.{0,10}açıkla)\b"],
     kod_hatasi, _empty),
    ([r"\b(madde madde|maddeler halinde)\s*özetle", r"\bmaddele(yip)?\s*özetle\b"],
     madde_ozet, _extract_madde),
    ([r"\b(çevir.{0,8}sesli|sesli\s*oku.{0,8}çevir|çevirip oku)\b", r"\bçevir seslioku\b"],
     cevir_seslioku, _extract_cevir_oku),
    ([r"\bher\s*gün\b.{0,30}\bhatırlat\b", r"\bgünlük hatırlat"],
     gunluk_hatirlatici, _extract_gunluk),

    # ══ VISION AJANI (gerçek ekran görme — Gemini gibi) ════════════════ #
    # Ekrana bakıp YAP (eylem içerir) — gör/anlat'tan ÖNCE
    ([r"\bekrana?\s*bak(ıp|arak)?\b.{0,45}\b(yap|bas|tıkla|tikla|aç|gir|seç|sec|oyna|başlat|baslat|devam)\b",
      r"\bgör(üp)?\s*yap\b", r"\bgemini gibi\b.{0,25}\b(yap|tıkla|bas|aç)\b",
      r"\bbakarak\s*yap\b"],
     gor_yap, _extract_gor_yap),
    # Vision ile OYNA (döngü) — gör/yap'tan ÖNCE
    ([r"\b(oyunu? oyna|vision (ile )?oyna|ekrana bakarak oyna|oyunu durdur|oyna\s*:)\b"],
     gor_oyna, _extract_oyna),
    # Ekranı gör ve anlat (gerçek vision)
    ([r"\bekrana?\s*bak\b", r"\bne görüyorsun\b", r"\bekranı? gör\b",
      r"\bekranda ne (var|oluyor|görüyorsun)\b", r"\bgemini gibi (bak|gör)\b",
      r"\bgörsel olarak (bak|gör|incele)\b"],
     gor_ekran, _extract_gor),

    # ══ MEGA batch (güçlü skiller) ═════════════════════════════════════ #
    # Python kod çalıştır → terminal'den ÖNCE (python çalıştır: ...)
    ([r"\b(python|kod)\s*(çalıştır|calistir|run)\b\s*[:\-]?"],
     kod_calistir, _extract_kod_calistir),
    ([r"\b(çalıştır|calistir)\s*[:\-]", r"\b(terminal|cmd|komut çalıştır)\b\s*[:\-]"],
     uzak_terminal, _extract_terminal),
    ([r"\b(soruyu? çöz|ödevi? çöz|bunu çöz|çöz şunu|ekrandaki soru)\b"],
     soru_coz, _empty),
    ([r"\b(araştır|arastir)\b"],
     arastir, _extract_arastir),
    ([r"\b(döviz|dolar|euro|altın|altin)\b.{0,15}\b(kur\w*|kaç|fiyat\w*|ne kadar|durum\w*)\b",
      r"\b(döviz kur\w*|altın fiyat\w*|gram altın|kurlar)\b",
      r"^\s*(dolar|euro|altın|altin|döviz)\s*$"],
     doviz_altin, _empty),
    ([r"\b(tam )?(sistem|pc|bilgisayar)\s*(rapor\w*|sağlık\w*|durum\w*)\b",
      r"\bsağlık rapor\w*\b"],
     tam_saglik, _empty),
    ([r"\b(gizlilik modu|izleri sil|geçmişi temizle|gizli temizlik)\b"],
     gizlilik_modu, _empty),
    ([r"\b(akıllı pano|panoda ne|panoyu tanı|kopyaladığım ne)\b"],
     akilli_pano, _empty),
    ([r"\b(cevap öner|yanıt öner|ne cevap (vereyim|yazayım))\b"],
     otomatik_cevap, _extract_cevap),
    ([r"\b(hızlı ayar|hızlı ayarlar|action center|denetim merkezi)\b"],
     hizli_ayar, _empty),

    ([r"\b(geri sayım|sayaç widget|ekranda sayaç|sayaç başlat)\b"],
     sayac_widget, _extract_sayac),
    ([r"\b(toplantı not\w*|ders not\w*|toplantıyı kaydet|dersi kaydet|kaydet özetle)\b"],
     toplanti_notu, _extract_toplanti),
    ([r"\b(sesli oku|kitap oku|oku bana|sesli kitap)\b"],
     sesli_kitap, _extract_kitap),
    ([r"\b(kim kullandı|kim kullanmış|beni kim|aktivite (izle|raporu)|gözetle kim)\b"],
     kim_kullandi, _extract_kim),
    ([r"\b(webcam timelapse|timelapse|hızlandırılmış (kayıt|çekim)|zaman atlamalı)\b"],
     webcam_timelapse, _extract_timelapse),
    ([r"\b(şüpheli giriş|koruma (modu|aç)|dokunan olursa|hırsız modu|koruma durdur)\b"],
     supheli_giris, _extract_supheli),
    ([r"\bakıllı hatırlat\b"],
     akilli_hatirlatici, _extract_akilli_hat),

    # ══ Akıllı ev ═════════════════════════════════════════════════════ #
    ([r"\bakıllı ev ekle\b.{0,40}https?://"],
     akilli_ev_ekle, _extract_ev_ekle),
    ([r"\b(akıllı ev liste|akıllı cihazlar|cihaz listesi)\b"],
     akilli_ev_liste, _empty),
    ([r"\b(ışığı|ışıkları|lamba\w*|prizi|klima\w*|perde\w*|fanı|televizyon\w*|tv'?yi)\b.{0,12}\b(aç|kapat|yak|söndür)\b",
      r"\bakıllı ev\b"],
     akilli_ev, _extract_ev),

    # ══ Wake-on-LAN (PC'yi uzaktan aç) ═════════════════════════════════ #
    ([r"\b(wol bilgi|pc bilgi|mac adresi|bu pc'?nin mac|wake bilgi)\b"],
     wol_bilgi, _empty),
    ([r"\b(wol (aç|etkinleştir|kur)|wake on lan aç|uzaktan açmayı (aç|kur))\b"],
     wol_etkinlestir, _empty),
    ([r"\b(uyandır|wake|wol gönder|pcyi aç(?!ıl)|bilgisayarı aç)\b.{0,30}"
      r"[0-9a-f]{2}[:\-]?[0-9a-f]{2}",
      r"\b(uyandır|wake on lan|wol)\b"],
     wol_uyandir, _extract_wol),

    # ── E-posta (WhatsApp kurallarından ÖNCE gelir) ───────────────────── #
    # @ içeren adres VE mail/e-posta kelimesi → email_gonder
    ([r"[\w.+-]+@[\w-]+\.[a-zA-Z]{2,}.{0,60}\b(mail|e-?posta|gönder|at|yaz)\b",
      r"\b(mail|e-?posta)\b.{0,60}[\w.+-]+@[\w-]+\.[a-zA-Z]{2,}",
      r"\b(e-?posta\s+gönder|mail\s+at|mail\s+gönder|mail\s+yaz)\b"],
     email_gonder, _extract_email),

    # ── Kısmi mesaj niyeti → çok adımlı soru akışı ───────────────────── #
    # Bu kural, alıcı/mesaj belirtilmeden sadece "mesaj gönder" denilince tetiklenir.
    # Tam eşleşme kuralları daha spesifik olduğu için önce kontrol edilir —
    # oradan geçemeyen kısmi ifadeler buraya düşer.
    ([r"^\s*(?:bir\s+)?mesaj\s+(?:gönder|at|yaz|ilet)\s*$",
      r"^\s*(?:whatsapp|telegram|discord|instagram|messenger)\s*(?:'[dt]an|ile|üzerinden)?\s*(?:mesaj\s+)?(?:gönder|at|yaz)\s*$",
      r"^\s*(?:birine\s+)?mesaj\s+atmak\s+istiyorum\s*$"],
     whatsapp_send, lambda _: {}),

    # ── WhatsApp ekran otomasyonu ─────────────────────────────────────── #
    # Geniş pattern: "X'e mesaj", "X'e yaz", "X'e at", whatsapp içersin/içermesin
    ([r"[A-ZÇĞİÖŞÜa-zçğışöüı][^\s']{1,30}'(?:y?[ae])\s+(?:whatsapp\s+)?(?:mesaj[ıi]?\s+)?(?:gönder|at|yaz|ilet|söyle|de)\b",
      r"(?:whatsapp|wp).{0,40}'(?:y?[ae]).{0,30}(?:yaz|gönder|at|ilet|söyle|de)\b",
      r"[A-ZÇĞİÖŞÜa-zçğışöüı][^\s']{1,30}'(?:y?[ae])\s+(?:şunu\s+)?(?:yaz|de|söyle)\s+\S"],
     whatsapp_send, _extract_whatsapp_send),

    # ════════════════════════════════════════════════════════════════════ #
    #  HERMES UZAKTAN / EK SKILL'LER  (yüksek öncelik)                      #
    # ════════════════════════════════════════════════════════════════════ #

    # ── Onay kuyruğu ──────────────────────────────────────────────────── #
    ([r"\b(onay bekleyen|bekleyen iş|bekleyenler|onay kuyru|ne bekliyor|pending)"],
     bekleyenler, lambda _: {}),
    ([r"\b(onayla|onaylıyorum|onay ver|kabul ediyorum|approve)\b"],
     onayla, _extract_approve),
    # "iptal" — ama zamanlayıcı/kapatma iptali DEĞİLSE (onlar kendi kurallarına gider)
    ([r"^(?!.*(zamanlayıcı|timer|kapat|shutdown)).*\b(iptal|vazgeç|vazgec|reddet|cancel)\b"],
     iptal, _extract_approve),

    # ── Mod değiştir (oyun_modu kuralından ÖNCE) ──────────────────────── #
    ([r"\b(oyun|iş|is|çalışma|calisma|work)\s*mod(?:un)?a?\s*(geç|gec|al|geçir|gecir)\b"],
     mod_degistir, _extract_mod),
    ([r"\b(oyun(?:a|\s*öncesi)?\s*hazırla|oyuna hazır|oyun hazırlık|game prep)\b"],
     oyun_hazirlik, lambda _: {}),
    ([r"\b(steam\s*güncelle|steam güncelleme|oyunları güncelle|steam indirme)\b"],
     steam_guncelle, lambda _: {}),

    # ── Anti-AFK ──────────────────────────────────────────────────────── #
    ([r"\banti[\s-]?afk\b", r"\bafk\s*(engelle|önle|onle)\b"],
     anti_afk, _extract_afk),

    # ── Discord mute / deafen (mesajlaşma kuralından ÖNCE) ────────────── #
    ([r"\bdiscord\b.{0,15}\b(sustur|mute|sus|mikrofon|kulaklık|kulaklik|deafen|sağır|sagir)\b"],
     discord_mute, _extract_discord_mute),
    ([r"\bdiscord\b.{0,15}\b(durum|meşgul|mesgul|rahatsız|rahatsiz|çevrimiçi|cevrimici|görünmez|gorunmez|boşta|bosta)\b"],
     discord_durum, _extract_discord_durum),

    # ── Spotify mood (spotify_open ve muzik_oner'den ÖNCE) ────────────── #
    ([r"\b(çalışma|calisma|odak|uyku|spor|parti|lofi|sakin|yolculuk|mutlu)\s*(müzi|muzi|şarkı|sarki|playlist)",
      r"\b(müzik|muzik)\b.{0,12}\b(mod[uu]?|ruh hali|mood)\b"],
     spotify_mood, _extract_mood),

    # ── İnternet hız testi ────────────────────────────────────────────── #
    ([r"\b(hız testi|hiz testi|speed\s*test|internet hız\w*|net hız\w*|indirme hız\w*)\b"],
     hiz_testi, lambda _: {}),

    # ── Uygulama süre limiti (set_timer'dan ÖNCE) ─────────────────────── #
    ([r"\b(uygulama\s*)?(süre\s*|sure\s*)?limit(i)?\b.{0,20}\b(koy|kur|ayarla|ekle)\b",
      r"'?(?:a|e|ya|ye)\s+\d+\s*(?:dk|dakika|saat)\s*limit"],
     uygulama_limit, _extract_limit),

    # ── Proaktif bildirim (PC → Telegram) ─────────────────────────────── #
    ([r"\b(bana bildir|haber ver|push gönder|push gonder)\b"],
     bildirim_gonder, _extract_notify),

    # ── Akşam / günlük özet ───────────────────────────────────────────── #
    ([r"\b(akşam özeti|aksam ozeti|günlük özet|gunluk ozet|günü özetle|gunu ozetle)\b"],
     gunluk_ozet, lambda _: {}),

    # ── Görev kuyruğu ─────────────────────────────────────────────────── #
    ([r"\b(görev ekle|gorev ekle|kuyruğa ekle|kuyruga ekle|sonra yap)\b"],
     gorev_ekle, _extract_task),
    ([r"\b(görevler|gorevler|görev kuyruğu|gorev kuyrugu|bekleyen görev|bekleyen gorev)\b"],
     gorevler, lambda _: {}),
    ([r"\b(görev çalıştır|gorev calistir|sıradaki görev|siradaki gorev|kuyruğu çalıştır|kuyrugu calistir)\b"],
     gorev_calistir, lambda _: {}),
    ([r"\b(komut geçmişi|komut gecmisi|uzaktan komutlar|son komutlar|command log)\b"],
     komut_gecmisi, lambda _: {}),

    # ── Diğer mesajlaşma (telegram / discord vb.) ─────────────────────── #
    ([r"(telegram|discord|instagram|messenger|tg|ig).{0,40}(mesaj|yaz|gönder|de)\b",
      r"[^\s]+'(?:y?[ae])\s+.+\s+(de|yaz|gönder|ilet|söyle|at)\b"],
     send_message, _extract_msg),

    # ── Salad (GPU kazanç) ────────────────────────────────────────────── #
    ([r"\b(salad)\b.{0,20}(aç|başlat|çalıştır|start|aktif)",
      r"\b(aç|başlat|çalıştır)\b.{0,20}\b(salad)\b",
      r"\bgpu\b.{0,20}(para|kazan|madenci|mine)",
      r"\b(para kazan|kazanç).{0,20}\bgpu\b"],
     salad_ac, _empty),

    ([r"\b(salad)\b.{0,20}(kapat|durdur|bitir|stop|kapa)",
      r"\b(kapat|durdur)\b.{0,20}\b(salad)\b"],
     salad_kapat, _empty),

    # ── Netflix ───────────────────────────────────────────────────────── #
    ([r"\b(netflix)\b",
      r"\b(dizi|film)\b.{0,20}\b(izle|aç)\b.{0,20}(?!youtube|twitch)"],
     netflix_ac, _empty),

    # ── Twitch ────────────────────────────────────────────────────────── #
    ([r"\b(twitch)\b"],
     twitch_ac, _extract_twitch),

    # ── TikTok ────────────────────────────────────────────────────────── #
    ([r"\b(tiktok|tik tok)\b"],
     tiktok_ac, _empty),

    # ── Twitter / X ───────────────────────────────────────────────────── #
    ([r"\b(twitter|x\.com)\b"],
     twitter_ac, _empty),

    # ── Instagram ─────────────────────────────────────────────────────── #
    ([r"\b(instagram|insta)\b.*\b(aç|gir|git)\b",
      r"\b(aç|gir)\b.{0,15}\b(instagram|insta)\b"],
     instagram_ac, _empty),

    # ── Oyun Modu ─────────────────────────────────────────────────────── #
    ([r"\b(oyun\s*mod[uu]?n?u?|game\s*mode|gaming\s*mode)\b"],
     oyun_modu, _extract_oyun_modu),

    # ── Fokus / Odak Modu ─────────────────────────────────────────────── #
    ([r"\b(fokus|rahatsiz\s*etme|do not disturb|focus assist|sessiz mod)\b",
      r"\bodak\s*mod"],
     fokus_modu, _extract_fokus),

    # ── Ekran Parlaklığı ──────────────────────────────────────────────── #
    ([r"\b(parlaklık|parlaklik|brightness)\b",
      r"\b(ekranı?\s*(karart|aydınlat|parlat))\b"],
     parlaklik_ayarla, _extract_parlaklik),

    # ── Mikrofon Toggle ───────────────────────────────────────────────── #
    ([r"\b(mikrofon|mikrofonu?)\b.{0,15}\b(sustur|kapat|mute|aç|unmute|aktif)\b",
      r"\b(mute|unmute)\b.{0,15}\b(mikrofon|mic)\b"],
     mikrofon_toggle, _empty),

    # ── Emoji Paneli ──────────────────────────────────────────────────── #
    ([r"\b(emoji|emoticon)\b.{0,20}\b(panel|aç|göster)\b",
      r"\b(emoji\s*panel|win\s*\+\s*\.)\b"],
     emoji_paneli, _empty),

    # ── Pano Geçmişi ──────────────────────────────────────────────────── #
    ([r"\bpano\s*gecmi",
      r"\bpano\s*geçmi",
      r"\bkopyaladiklarim\b",
      r"\bkopyaladıklarım\b",
      r"\bclipboard\s*gecmi",
      r"\bclipboard\s*geçmi"],
     clipboard_gecmis, _empty),

    # ── YouTube ───────────────────────────────────────────────────────── #
    # \byoutube (sonda \b YOK) → "youtube", "youtube'da", "youtubeden" hepsini yakalar
    # yazım hataları: yutub, yutup, yutub, yt
    ([r"\byoutube", r"\byutu[bp]", r"\byou\s*tube", r"\byt\b.{0,8}\b(aç|ac|izle|gir)\b",
      r"\b(izle|oynat)\b.{0,20}\b(video|youtube|yt|yutub)\b"],
     youtube, _extract_youtube),

    # ── Hava durumu ───────────────────────────────────────────────────── #
    ([r"\b(hava\s*durum\w*|hava\s*nasıl|weather|hava nasıl)\b", r"^\s*hava\s*$"],
     weather_action, _extract_weather),

    # ── Hatırlatıcı ───────────────────────────────────────────────────── #
    ([r"\b(hatırlat|hatırlatıcı|reminder|alarm kur)\b"],
     reminder, _extract_reminder),

    # ── Zamanlayıcı (not: 'uyar' → zamanli_uyari'ye bırakıldı) ────────── #
    ([r"\b(zamanlayıcı|timer|süre ayarla)\b",
      r"\b\d+\s*(dakika|dk|saniye|sn)\b.{0,20}\b(zamanlayıcı|timer|haber ver)\b"],
     set_timer, _extract_timer),

    ([r"\b(zamanlayıcı iptal|timer iptal|zamanlayıcıyı durdur)\b"],
     cancel_timer, _empty),

    # ── Pomodoro ──────────────────────────────────────────────────────── #
    ([r"\b(pomodoro)\b"],
     pomodoro, _extract_pomodoro),

    # ── Not ───────────────────────────────────────────────────────────── #
    ([r"\b(not al|not ekle|bunu kaydet|remember this|şunu not)\b"],
     take_note, _extract_note),

    ([r"\b(notlar[ıi]m[ıi]|notlarıma bak|notlarımı göster|read notes|notları oku)\b"],
     read_notes, _empty),

    ([r"\b(notları temizle|tüm notları sil|clear notes)\b"],
     clear_notes, _empty),

    # ── Hesaplama ─────────────────────────────────────────────────────── #
    ([r"\b(hesapla|kaça eder|ne eder|topla|çarp|böl|calculate|sonucu nedir)\b",
      r"\d+\s*[\+\-\*\/\^]\s*\d+"],
     calculate, _extract_calc),

    # ── Şifre ─────────────────────────────────────────────────────────── #
    ([r"\b(şifre|parola|password)\b.{0,8}\b(oluştur|üret|ver|yap|lazım|gerek)\b",
      r"\b(güçlü şifre|rastgele şifre|random password)\b"],
     generate_password, _extract_password),

    # ── Saat/Tarih ────────────────────────────────────────────────────── #
    ([r"\b(saat kaç|tarih nedir|bugün ne|günün tarihi|what time|what date|"
      r"günlerden ne|hangi gün)\b", r"^\s*saat\s*$", r"^\s*tarih\s*$"],
     time_date, _empty),

    # ── Takvim ────────────────────────────────────────────────────────── #
    ([r"\b(takvim|calendar|ajanda)\b.*\b(aç|göster|bak)\b"],
     open_calendar, _empty),

    # ── Zar / Para ────────────────────────────────────────────────────── #
    ([r"\b(zar at|zar roll|dice)\b"],
     roll_dice, _extract_dice),

    ([r"\b(yazı tura|flip coin|para at)\b"],
     flip_coin, _empty),

    # ── Ekran görüntüsü ───────────────────────────────────────────────── #
    ([r"\b(ekran görüntüsü|screenshot|ekran al|ekran at|ss al|ekranı çek)\b"],
     screenshot, _extract_screenshot),

    ([r"\b(snipping|ekran alıntısı|bölge ekran)\b"],
     take_screenshot_region, _empty),

    # ── Webcam fotoğrafı ──────────────────────────────────────────────── #
    ([r"\b(webcam|kamera|selfie|fotoğraf çek|foto çek|foto cek)\b"],
     webcam_action, _empty),

    # ── Çoklu makro (doğal dil) — fare/tıkla kurallarından ÖNCE ───────── #
    # "makro: ..." veya "makro 5 kez: ..." (kez/defa araya girebilir)
    ([r"\bmakro\b[^:\n]{0,25}:\s*\S"],
     coklu_makro, _extract_coklu_makro),

    # ── Bekle-ve-tıkla (EN ÖNCE): "X çıkınca tıkla" ───────────────────── #
    ([r"\bekranda\b.{0,40}\b(çıkınca|cikinca|görününce|gorununce|belirince|olunca|gelince)\b.{0,20}\b(tıkla|tikla|bas)\b",
      r"\b(çıkınca|görününce|belirince|gelince)\b.{0,15}\b(tıkla|bas)\b",
      r"\bbekle.{0,20}\btıkla\b"],
     bekle_tikla, _extract_bekle_tikla),

    # ── Renge tıkla (smart_click'ten ÖNCE) ────────────────────────────── #
    ([r"\b(kırmızı|kirmizi|yeşil|yesil|mavi|sarı|sari|turuncu|beyaz|siyah|mor|pembe|pink|red|green|blue|yellow)\w*\s*(?:renge|renkli|olan|noktaya|yere)?\s*(tıkla|tikla|bas)\b"],
     renge_tikla, _extract_renge_tikla),

    # ── Akıllı tıklama (OCR — ekrandaki yazıya tıkla) ─────────────────── #
    ([r"\bekranda\w*\b.{0,50}\b(tıkla|tikla|bas|bastır|seç|sec)\b",
      r"\b\w+.{0,30}\b(yazısına|yazına|butonuna|tuşuna|linkine|seçeneğine|metnine)\b.{0,12}\b(tıkla|tikla|bas|seç|sec)\b"],
     smart_click, _extract_smart_click),

    # ── Fare kontrolü (koordinat) ─────────────────────────────────────── #
    # "X Y'den X Y'ye sürükle" (4 sayı) — tıkla kuralından ÖNCE
    ([r"\d+\s+\d+.{0,15}\d+\s+\d+.{0,15}\b(sürükle|surukle|drag|taşı.*bırak)\b",
      r"\bsürükle\b.{0,30}\d+.{0,10}\d+"],
     mouse_drag, _extract_drag),

    ([r"\bfare(?:yi)?\s*(?:imleci)?\s*\d+\s+\d+.{0,10}\b(götür|gotur|taşı|tasi|git|move)\b",
      r"\bimleci\s*\d+\s+\d+",
      r"\bfareyi\s*\d+"],
     mouse_move, _extract_move),

    ([r"\b\d+\s+\d+\s*('?[ye]|ye|ya|'?a)?\s*(çift\s*)?(sağ\s*|sol\s*|orta\s*)?tıkla\b",
      r"\b(çift|sağ|sol|orta)\s*tıkla\b",
      r"\btıkla\b.{0,15}\d+\s+\d+",
      r"^\s*(çift tıkla|sağ tıkla|sağ tık|çift tık)\s*$"],
     mouse_click, _extract_click),

    ([r"\b(fare|imleç|imlec|mouse)\s*(nerede|konumu|pozisyon|koordinat)\b"],
     mouse_position, _empty),

    # ── MC: Balık tut ─────────────────────────────────────────────────── #
    ([r"\bbalık\s*(tut|botu?|avla)\b", r"\bbalık\s*durdur\b", r"\bfishing\b"],
     balik_tut, _extract_balik),

    # ── MC: Auto-eat ──────────────────────────────────────────────────── #
    ([r"\b(auto[\s-]?eat|otomatik\s*ye|otomatik yemek|yemeyi durdur|aç kalma)\b"],
     auto_eat, _extract_eat),

    # ── Minecraft OneBlock botu (blok kır kuralından ÖNCE) ────────────── #
    ([r"\boneblock\b", r"\bone block\b",
      r"\bmc\b.{0,15}\b(bot|otomatik|kır|farm)\b",
      r"\b(otomatik|akıllı)\s*(kaz|kır|farm)\b"],
     oneblock, _extract_oneblock),

    # ── AI: bu ne / ekranı yorumla ────────────────────────────────────── #
    ([r"\bbu\s*ne(dir)?\b", r"\bekran[ıi]?\s*(yorumla|analiz et|açıkla|incele)\b",
      r"\bekranda ne (var|oluyor)\b.{0,12}\b(açıkla|yorumla|söyle)\b"],
     bu_ne, _empty),

    # ── RAM temizle ───────────────────────────────────────────────────── #
    ([r"\b(ram|bellek|hafıza)\b.{0,12}\b(temizle|boşalt|optimize|rahatlat)\b",
      r"\b(ram optimize|belleği temizle)\b"],
     ram_temizle, _empty),

    # ── Ses çıkış cihazı ──────────────────────────────────────────────── #
    ([r"\b(ses|çıkış|cikis)\s*cihaz", r"\b(kulaklığa|hoparlöre|hoparlore)\s*geç\b",
      r"\bses çıkışı\b"],
     ses_cihazi, _empty),

    # ── Minecraft: blok kır/koy (fare tuşunu basılı tut) ──────────────── #
    ([r"\b(kırmayı|kirmayi|blok kırmayı)\s*(durdur|bırak|birak|dur)\b"],
     blok_kir, lambda _: {"action": "stop"}),
    ([r"\bblok\s*(kır|kir|koy|yerleştir|yerlestir)\b",
      r"\b\d+\s*(saniye|sn|dakika|dk)\b.{0,12}\b(boyunca\s*)?(kır|kir|blok kır|kaz)",
      r"\b(kır|kir|kaz)maya?\s*(devam|başla|basla)\b",
      r"\b(madencilik|maden kaz)\b"],
     blok_kir, _extract_blok_kir),

    # ── Tuşu basılı tut ───────────────────────────────────────────────── #
    ([r"\b[a-z0-9]\s*'?[ye]?\s*(tuşunu?)?\s*\d+(?:[.,]\d+)?\s*(?:saniye|sn|s)\b.{0,10}\b(bas|tut)\b",
      r"\b\d+\s*(?:saniye|sn)\b.{0,10}\b[a-z0-9]\s*'?[ye]?\s*(?:tuşunu?\s*)?(bas|tut)\b",
      r"\b([a-z0-9])\s*'?(?:ye|ya)\s*basılı tut\b"],
     tus_tut, _extract_tus_tut),

    # ── Tuş spam ──────────────────────────────────────────────────────── #
    ([r"\b(space|boşluk|enter|tab|esc|[a-z0-9])\s*'?[ye]?\s*(tuşuna|harfine)?\s*\d+\s*(?:kez|defa|kere)\s*bas\b",
      r"\b\d+\s*(?:kez|defa|kere)\s*(space|boşluk|enter|tab|[a-z0-9])\s*(?:tuşuna)?\s*bas\b"],
     tus_spam, _extract_tus_spam),

    # ── Snippet (hazır metin) ─────────────────────────────────────────── #
    ([r"\bsnippet\s*(kaydet|ekle)\s+[\w\-]+\s*[:\-]"],
     snippet_kaydet, _extract_snip_kaydet),
    ([r"\b(snippet listesi|snippetler|snippet'ler|kayıtlı snippet)\b"],
     snippet_liste, _empty),
    ([r"\bsnippet\s+yaz\s+[\w\-]+",
      r"\b(imza|adres|iban|mail|email|telefon|tel|numara)\s+yaz\b"],
     snippet_yaz, _extract_snip_yaz),

    # ── Pencere diz (snap) ────────────────────────────────────────────── #
    ([r"\bpencere(yi)?\b.{0,15}\b(sol|sağ|sag)\s*(yarı|tarafa|köşe)?\b.{0,10}\b(yapıştır|diz|at|gönder|taşı)\b",
      r"\bpencere(yi)?\s*(sola|sağa|saga)\s*(yapıştır|diz|yasla)\b",
      r"\b(pencere\s*diz|snap|ekranı böl)\b"],
     pencere_diz, _extract_pencere_diz),

    # ── Sesli konuşma (TTS) ───────────────────────────────────────────── #
    ([r"\b(sesli\s*(söyle|oku|seslen)|seslen|sesli\s*okur?)\b",
      r"^\s*konuş\b"],
     konus, _extract_konus),

    # ── Monitörü kapat ────────────────────────────────────────────────── #
    ([r"\b(monitörü?|ekranı?)\s*(kapat|söndür|sondur|karart)\b",
      r"\b(ekran|monitör)\s*kapat\b"],
     ekran_kapat, _empty),

    # ── Kripto fiyat ──────────────────────────────────────────────────── #
    ([r"\b(bitcoin|btc|ethereum|eth|solana|doge|kripto|bnb|xrp|avax|shib)\b.{0,20}\b(fiyat\w*|kaç|ne kadar|değer|kur)\b",
      r"\b(kripto|bitcoin|btc)\s*fiyat",
      r"^\s*(bitcoin|btc|ethereum|eth|kripto)\s*$"],
     kripto_fiyat, _extract_kripto),

    # ── En çok kaynak kullananlar ─────────────────────────────────────── #
    ([r"\b(en çok|hangi).{0,15}\b(ram|bellek|kaynak|cpu)\b.{0,15}\b(kullan|yiyen|tüket)",
      r"\b(kaynak|ram)\s*kullanan\b"],
     en_cok_kaynak, _empty),

    # ── Pano temizle ──────────────────────────────────────────────────── #
    ([r"\b(panoyu?\s*temizle|clipboard\s*temizle|kopyalananı sil)\b"],
     pano_temizle, _empty),

    # ── Boş disk ──────────────────────────────────────────────────────── #
    ([r"\b(boş\s*(disk|alan)|disk(te)?\s*ne kadar (boş|yer)|free disk)\b"],
     bos_disk, _empty),

    # ── Ekran kaydı (video) ───────────────────────────────────────────── #
    ([r"\b(ekran(ı)?\s*kaydet|ekran kayd|video kaydet|kayda al|record screen)\b"],
     ekran_kaydi, _extract_kayit),

    # ── PC ekranında büyük bildirim göster ────────────────────────────── #
    ([r"\b(pc\s*bildirim|ekranda göster|masaüstüne yaz|bildirim göster)\b",
      r"\bekrana?\s*(sesli\s*|sessiz\s*)?(mesaj|yaz|bildir|duyur)",
      r"\bekrana\s*(sesli|sessiz)\b"],
     pc_bildirim, _extract_bildirim),

    # ── Tüm tarayıcıları kapat ────────────────────────────────────────── #
    ([r"\b(tarayıcıları kapat|tüm tarayıcı|bütün tarayıcı|tarayıcıyı kapat|browser.*kapat)\b"],
     tarayicilari_kapat, _empty),

    # ── Panik modu ────────────────────────────────────────────────────── #
    ([r"\b(panik|panic)\s*mod", r"^\s*panik\s*$", r"\bacil durdur\b"],
     panik_modu, _empty),

    # ── Ekranı AI ile özetle (ekran_oku'dan ÖNCE) ─────────────────────── #
    ([r"\bekran[ıi]?\b.{0,15}\b(özetle|ozetle|özet)\b",
      r"\bekranda ne (var|oluyor|yazıyor)\b.{0,10}\bözetle\b"],
     ekran_ozetle, _empty),

    # ── Ekrandaki yazıyı oku (OCR) ────────────────────────────────────── #
    ([r"\bekran(daki)?\b.{0,15}\b(yazıyı|metni|yazıları)\b.{0,10}\b(oku|kopyala|al)\b",
      r"\bekran[ıi]?\s*oku\b", r"\bekrandaki yazı\b"],
     ekran_oku, _empty),

    # ── Güç planı ─────────────────────────────────────────────────────── #
    ([r"\b(güç|guc|enerji|power)\s*plan", r"\b(performans|tasarruf)\s*mod"],
     guc_plani, _extract_guc),

    # ── Zamanlı sesli uyarı (reminder'dan ÖNCE) ───────────────────────── #
    ([r"\b\d+\s*(saat|dakika|dk|saniye|sn)\b.{0,15}\b(sonra\s*)?(uyar|alarm)",
      r"\b(zamanlı|gecikmeli)\s*uyar"],
     zamanli_uyari, _extract_uyari),

    # ── Zamanlı kapatma (genel shutdown'dan ÖNCE) ─────────────────────── #
    ([r"\b\d+\s*(saat|dakika|dk)\b.{0,15}\b(sonra\s*)?(kapat|kapan)",
      r"\b(zamanlı|gecikmeli)\s*kapat"],
     zamanli_kapat, _extract_zamanli),

    # ── Sabah rutini ──────────────────────────────────────────────────── #
    ([r"\b(sabah rutini|güne başla|rutini başlat|günlük uygulamalar)\b"],
     sabah_rutini, _empty),

    # ── Pil uyarısı ───────────────────────────────────────────────────── #
    ([r"\b(pil uyarısı.*(kapat|durdur)|pil takibini durdur)\b"],
     pil_uyari_kapat, _empty),
    ([r"\b(pil uyarısı|pili izle|pil takip|şarj uyar|pil bitince)\b"],
     pil_uyari, _empty),

    # ── Uyku engelle / serbest ────────────────────────────────────────── #
    ([r"\b(uyku(yu)?\s*(serbest|aç|kapat\s*ma|izin)|uyuyabilir|uyku normal)\b"],
     uyku_serbest, _empty),
    ([r"\b(uyuma|uykuyu engelle|uyanık kal|açık kal|uykuya geçme|uyutma|keep awake|caffeine)\b"],
     uyanik_kal, _empty),

    # ── Otomatik tıklayıcı (autoclicker) ──────────────────────────────── #
    ([r"\b(otomatik tıkla|oto tıkla|autoclick|auto click|tıklayıcı)\b",
      r"\btıklama(?:yı)?\s*(durdur|dur|kapat|başlat|baslat)\b",
      r"\bsaniyede\s*\d+\s*(?:kez|defa)?\s*tıkla\b",
      r"\b\d+\s*(?:kez|defa|kere)\s*tıkla\b"],
     auto_clicker, _extract_clicker),

    # ── Makro: kaydet / oynat / liste ─────────────────────────────────── #
    ([r"\bmakro(?:yu)?\s*(kaydet|kayıt|record)\b"],
     macro_record, _extract_macro),
    ([r"\bmakro(?:yu)?\s*(oynat|çalıştır|calistir|play)\b"],
     macro_play, _extract_macro),
    ([r"\b(makrolar(?:ım)?|makro listesi|kayıtlı makro)\b"],
     macro_list, _empty),

    # ── Ekranı kilitle ────────────────────────────────────────────────── #
    ([r"\b(ekranı kilitle|bilgisayarı kilitle|lock screen|lock)\b"],
     lock_screen, _empty),

    # ── Kapat / Yeniden başlat ────────────────────────────────────────── #
    ([r"\b(bilgisayarı kapat|sistemi kapat|shutdown|kapat\s+bilgisayar)\b"],
     shutdown, _extract_shutdown),

    ([r"\b(yeniden başlat|restart|reboot|bilgisayarı yeniden)\b"],
     restart, _p(delay=0)),

    ([r"\b(uyku moduna al|uyku modu|sleep mode|hibernate|uyut|uyusun)\b",
      r"^\s*uyu\s*$"],
     sleep_mode, _empty),

    ([r"\b(kapatmayı iptal|shutdown iptal|cancel shutdown)\b"],
     cancel_shutdown, _empty),

    # ── Pil / CPU / Disk (ek-toleranslı + tek kelime) ─────────────────── #
    ([r"\b(pil|batarya|şarj|battery)\b"],
     battery_status, _empty),

    ([r"\b(cpu|işlemci|ram|bellek|memory)\b.{0,10}\b(kullan\w*|kaç|yüzde|nasıl|durum\w*|doluluk)\b",
      r"\bsistem yükü\b", r"^\s*(cpu|ram)\s*$"],
     cpu_ram_usage, _empty),

    ([r"\b(disk|depolama|storage|sürücü)\b.{0,10}\b(kullan\w*|kaç|dolu\w*|boş|durum\w*)\b",
      r"^\s*disk\s*$"],
     disk_usage, _empty),

    ([r"\b(sistem bilgisi|bilgisayar bilgisi|system info|donanım bilgisi)\b"],
     system_info, _empty),

    ([r"\bip\s*adres\w*", r"\bip\s*bilgi\w*", r"\b(public ip|genel ip|my ip)\b",
      r"\bip'?(?:m|im)\b", r"^\s*ip\s*$"],
     ip_info, _empty),

    ([r"\b(wifi|kablosuz|internet bağlantı|ağ bilgisi|network info)\b.*\b(bilgi|durum|nasıl)\b"],
     wifi_info, _empty),

    ([r"\b(çalışan uygulamalar|running apps|process listesi|hangi uygulamalar)\b"],
     running_apps, _empty),

    ([r"\b(kapat|sonlandır|öldür|kill)\b.{0,20}\b(uygulama|process|program)\b"],
     kill_process, _extract_kill),

    # ── Dosya işlemleri ───────────────────────────────────────────────── #
    ([r"\b(dosya aç|open file|dosyayı aç)\b",
      r"\baç\b.{1,40}\b\.(txt|pdf|docx|xlsx|py|mp3|mp4|jpg|png|zip)\b"],
     open_file, _extract_file),

    ([r"\b(dosya oluştur|yeni dosya|create file)\b"],
     create_file, _extract_create_file),

    ([r"\b(dosya sil|dosyayı sil|delete file)\b"],
     delete_file, _extract_file),

    ([r"\b(dosya bul|dosya ara|find file|search file)\b"],
     find_file, _extract_find),

    ([r"\b(klasör oluştur|yeni klasör|create folder|dizin oluştur)\b"],
     create_folder, _extract_folder),

    ([r"\b(klasör aç|open folder|dizin aç)\b"],
     open_folder, _extract_file),

    ([r"\b(dosyaları listele|klasör içeriği|list files)\b"],
     list_files, _empty),

    ([r"\b(son dosyalar|son açılan|recent files)\b"],
     recent_files, _empty),

    ([r"\b(zip|sıkıştır|arşivle|compress)\b"],
     zip_files, _extract_file),

    ([r"\b(unzip|çıkart|aç\s+zip|extract)\b"],
     unzip_file, _extract_file),

    # ── "X ne demek" / "X ingilizcesi" → çeviri (Wikipedia'dan ÖNCE) ──── #
    ([r"^\s*[\w\s\-']+\s+ne\s+demek\b",
      r"^\s*[\w\s\-']+\s+(ingilizcesi|türkçesi|almancası|fransızcası|rusçası|japonca|arapçası)\b",
      r"^\s*[\w\s\-']+\s+nasıl\s+(söylenir|denir|yazılır|çevrilir)\b"],
     translate_text, _extract_word_translate),

    # ── Çeviri (açık komut) ───────────────────────────────────────────── #
    ([r"\b(çevir|translate|tercüme et)\b"],
     translate_text, _extract_translate),

    # ── Harita ────────────────────────────────────────────────────────── #
    ([r"\b(harita|maps|yol tarifi|nerede|konumu göster|nasıl gidilir)\b"],
     maps_open, _extract_maps),

    # ── Wikipedia ─────────────────────────────────────────────────────── #
    ([r"\b(wikipedia|vikipedi|wiki)\b",
      r".{2,50}\b(nedir|kimdir|hakkında bilgi|tarihçesi)\b"],
     wikipedia_search, _extract_wiki),

    # ── Haber ─────────────────────────────────────────────────────────── #
    ([r"\b(haber|news|gündem|son dakika)\b"],
     news_open, _extract_news),

    # ── Döviz ─────────────────────────────────────────────────────────── #
    ([r"\b(döviz|kur|dolar|euro|pound|sterlin)\b.{0,20}\b(kaç|ne kadar|fiyat)\b",
      r"\b\d+\s*(dolar|euro|tl|try|usd|eur)\b.{0,20}\b(kaç|ne|to)\b"],
     currency_info, _extract_currency),

    # ── Kelime tanımı ─────────────────────────────────────────────────── #
    ([r"\b(tanımı|anlamı|sözlük|tdk)\b"],
     define_word, _extract_define),

    # ── Uçuş arama ────────────────────────────────────────────────────── #
    ([r"\b(uçuş|uçak bileti|flight)\b"],
     flight_search, _extract_flight),

    # ── Sepeti / ödemeyi aç (sipariş kuralından ÖNCE) ─────────────────── #
    ([r"\b(sepeti aç|sepet aç|sepetim|ödeme(?:yi)? aç|ödeme sayfası|checkout)\b"],
     open_cart, _extract_cart),

    # ── Site ana sayfasını aç: "yemeksepeti aç", "trendyol aç" ────────── #
    ([r"\b(trendyol|hepsiburada|amazon|n11|yemeksepeti|getir|trendyolyemek)\w*\s*(aç|ac|git|gir)\b"],
     open_site, _extract_site),

    # ── Sipariş (GÜVENLİ: ürünü açar, ödemeyi kullanıcı yapar) ────────── #
    # Not: site adları ekli olabilir ("yemeksepetinden") → \w* ile yakala.
    ([r"\b(sipariş\s*et|siparis\s*et|ısmarla|ismarla|satın\s*al|satin\s*al)\b",
      r"\byemeksepeti\w*", r"\bgetir(?:den|e|den|'?den)?\b.{0,40}\b(al|söyle|sipariş)\b",
      r"\b(trendyolyemek|trendyol\s*yemek)\w*",
      r"\byemek\s*(?:söyle|siparişi|sipariş)\b",
      r"\b(trendyol|hepsiburada|amazon|n11)\w*.{0,40}\b(al|sipariş|satın|söyle)\b"],
     order, _extract_order),

    # ── Alışveriş (genel ürün arama) ──────────────────────────────────── #
    ([r"\b(trendyol|ürün ara|shopping|fiyat(?:ına)?\s*bak)\b"],
     shopping_search, _extract_shopping),

    # ── Görsel arama ──────────────────────────────────────────────────── #
    ([r"\b(görsel|resim|fotoğraf|image|photo)\b.{0,20}\b(ara|bul|search|göster)\b"],
     image_search, _extract_image_search),

    # ── Ses seviyesi (mutlak) — "sesi 100 yap", "ses 50", "ses %0" ──────── #
    # Sayı içeren ses komutları önce: _extract_volume yön kelimesi varsa
    # (artır/azalt) ona, yoksa mutlak 'set'e karar verir.
    ([r"\bses\w*\b.{0,12}\b\d{1,3}\b",
      r"\bvolume\b.{0,8}\b\d{1,3}\b",
      r"\bses\w*\b.{0,12}\b(yap|ayarla|olsun|seviye)\b"],
     volume_control, _extract_volume),

    # ── Ses (medya) — ek-toleranslı ───────────────────────────────────── #
    ([r"\bses\w*\s*(artır|arttır|yükselt|aç)\b", r"\bvolume\s*(up|artır)\b"],
     volume_control, lambda m: {"action": "artır", "value": 10}),

    ([r"\bses\w*\s*(azalt|kıs|düşür)\b", r"\bvolume\s*(down|azalt)\b"],
     volume_control, lambda m: {"action": "azalt", "value": 10}),

    ([r"\bses\w*\s*(kapat|kes|sustur|mute)\b"],
     volume_control, lambda m: {"action": "kapat", "value": 0}),

    # ── Medya kontrol ─────────────────────────────────────────────────── #
    ([r"\b(duraklat|durdur|pause|oynatmayı\s+durdur)\b"],
     media_play_pause, _empty),

    ([r"\b(oynat|devam et|play|resume)\b.{0,20}\b(müzik|şarkı|video|medya)\b"],
     media_play_pause, _empty),

    ([r"\b(sonraki\s*(şarkı|parça|video)|next track|next song|ileri)\b"],
     media_next, _empty),

    ([r"\b(önceki\s*(şarkı|parça|video|sarki)|previous track|prev song|prev)\b"],
     media_prev, _empty),

    # ── Oyun Yükleme (Steam) ──────────────────────────────────────────── #
    # Spesifik: "X yükle/indir/kur" — genel "aç/başlat" kurallarından ÖNCE gelir
    ([r"\b\w[\w\s]{1,40}\b(yükle|yukle|indir|kur|install)\b",
      r"\b(yükle|yukle|indir|kur|install)\b.{1,40}\b(oyun|game)\b",
      r"\bsteam\b.{0,20}\b(yükle|yukle|indir|kur|install|ekle)\b"],
     oyun_yukle, _extract_oyun),

    # ── Spotify ───────────────────────────────────────────────────────── #
    ([r"\bspotif?y?\b", r"\bspoti\b", r"\bmüzik\s*aç\b", r"\bmuzik\s*aç\b"],
     spotify_open, _extract_spotify),

    # ── Radyo ─────────────────────────────────────────────────────────── #
    ([r"\b(radyo|radio)\b"],
     open_radio, lambda m: {"station": re.sub(r"\b(radyo|radio|aç|dinle)\b", "", m, flags=re.I).strip()}),

    # ── Podcast ───────────────────────────────────────────────────────── #
    ([r"\b(podcast)\b"],
     open_podcast, lambda m: {"query": re.sub(r"\b(podcast|dinle|aç)\b", "", m, flags=re.I).strip()}),

    # ── Görev zamanlama ───────────────────────────────────────────────── #
    ([r"\bher\s*(gün|sabah|akşam|öğle)\b",
      r"\b(saat\s*\d{1,2}|（?\d{1,2}[:.]\d{2})\b.{0,30}\b(hatırlat|söyle|yap|zamanla|planla)\b",
      r"\b(planlı|zamanlı)\s*görev",
      r"\b(görev|hatırlatma)\b.{0,15}\b(zamanla|planla)\b"],
     schedule_action, _extract_schedule),

    # ── Ekran analizi (AI vision) ─────────────────────────────────────── #
    ([r"\bekran[ıi]?m?d?a?\b.{0,20}\b(ne var|ne görüyorsun|ne görüyor|oku|analiz|incele)\b",
      r"\b(ekran[ıi]?\s*(oku|analiz et|incele|göster))\b",
      r"\bne görüyorsun\b"],
     screen_read, _extract_screen),

    # ── Pano AI (özetle/çevir/açıkla) ─────────────────────────────────── #
    ([r"\b(kopyaladığım[ıi]?|panodaki|pano(yu)?|clipboard)\b.{0,20}\b(özetle|çevir|açıkla|ne diyor)\b",
      r"\b(özetle|çevir|açıkla)\b.{0,15}\b(kopyaladığım|panodaki|pano)\b"],
     clipboard_ai, _extract_clip_ai),

    # ── Panoya (basit oku/yaz) ────────────────────────────────────────── #
    ([r"\b(panoyu oku|panoda ne var|clipboard oku|kopyalanmış)\b"],
     clipboard_read, _empty),

    ([r"\b(panoya kopyala|kopyala)\b.{1,100}"],
     clipboard_write, _extract_clip_write),

    # ── QR Kod — "qr oluştur", "şu linkin qr kodu", veya saf URL + qr ─── #
    ([r"\b(qr\s*kod|qr\s*code|qr oluştur|qr üret|qr al)\b",
      r"https?://\S+.{0,30}\b(qr|kod)\b",
      r"\b(qr|kod)\b.{0,30}https?://\S+"],
     qr_generate, _extract_qr),

    # ── Birim çevirme ─────────────────────────────────────────────────── #
    ([r"\b(birim\s*çevir|convert|kaç\s*(km|mil|kg|pound|m|ft|cm|inch|gb|mb|litre|galon))\b"],
     unit_convert, _extract_unit),

    # ── Hash ──────────────────────────────────────────────────────────── #
    ([r"\b(hash|md5|sha256|sha512|checksum)\b"],
     hash_text, _extract_hash),

    # ── Geri dönüşüm kutusu ───────────────────────────────────────────── #
    ([r"\b(geri dönüşüm|çöp kutusu|recycle bin|boşalt)\b"],
     empty_recycle_bin, _empty),

    # ── PC Otomasyon ──────────────────────────────────────────────────── #

    ([r"\b(açık pencereler|pencere listesi|list windows|hangi pencereler)\b"],
     list_windows, _empty),

    ([r"\b(aktif pencere|şu an hangi pencere|foreground window|pencere başlığı)\b"],
     active_window_title, _empty),

    ([r"\b(pencere öne getir|öne getir|focus|odaklan)\b.{0,30}\b\w+\b"],
     focus_window, _extract_window_title),

    ([r"\b(pencereyi kapat|şu pencereyi kapat)\b"],
     close_window, _extract_window_title),

    ([r"\b(pencereyi büyüt|tam ekran yap|maximize)\b"],
     maximize_window, _extract_window_title),

    ([r"\b(pencereyi küçült|minimize et)\b"],
     minimize_window, _extract_window_title),

    ([r"\b(şunu yaz|şu metni yaz|klavyeyle yaz|type text)\b"],
     type_text, _extract_type_text),

    ([r"\b(tuş kombinasyonu|kısayol gönder|hotkey|tuşlara bas|bas)\b.{0,20}[a-z]+\+[a-z]+"],
     press_hotkey, _extract_hotkey),

    ([r"\b(sayfayı aşağı kaydır|scroll down|aşağı kaydır)\b",
      r"\b(sayfayı yukarı kaydır|scroll up|yukarı kaydır)\b"],
     scroll_page, _extract_scroll),

    ([r"\b(geçici dosyaları? temizle|temp temizle|temp klasörü|clear temp|geçici dosyalar)\b",
      r"%temp%",
      r"\btemp\b.{0,20}\b(temizle|sil|boşalt|bosalt)",
      r"\b(temizle|sil|boşalt)\b.{0,20}\btemp\b"],
     clear_temp, _empty),

    ([r"\b(dns temizle|dns önbelleği|flush dns|dns cache)\b"],
     flush_dns, _empty),

    ([r"\b(geri yükleme noktası|restore point|sistem yedeği al)\b"],
     create_restore_point, _extract_restore_point),

    ([r"\b(başlangıç programları|startup uygulamaları|hangi programlar başlarken açılıyor)\b"],
     list_startup_apps, _empty),

    ([r"\b(başlangıç klasörü|startup folder|autostart klasörü)\b"],
     open_startup_folder, _empty),

    ([r"\b(gece modu|gece ışığı|night mode|night light|mavi ışık)\b"],
     toggle_night_mode, _extract_night),

    ([r"\b(ağı sıfırla|internet sıfırla|ağ adaptörü sıfırla|network reset|winsock reset)\b"],
     reset_network, _empty),

    ([r"\b(ağ ayarları|network settings|bağlantı ayarları)\b"],
     open_network_settings, _empty),

    ([r"\b(wifi şifresi|wifi password|kablosuz şifre|saved wifi|kayıtlı wifi)\b"],
     show_wifi_passwords, _empty),

    ([r"\b(ekran ayarları|display settings|çözünürlük ayarları)\b"],
     open_display_settings, _empty),

    ([r"\b(ses ayarları|sound settings|ses cihazı ayarları)\b"],
     open_sound_settings, _empty),

    ([r"\b(windows update|güncelleştirme|güncelleme ayarları|sistem güncellemesi)\b"],
     open_windows_update, _empty),

    ([r"\b(duvar kağıdı değiştir|wallpaper değiştir|masaüstü resmi)\b"],
     set_wallpaper, _extract_wallpaper),

    # ── Genel pencere yönetimi ────────────────────────────────────────── #
    ([r"\b(tüm pencereleri küçült|masaüstünü göster|show desktop|minimize all)\b"],
     minimize_all, _empty),

    ([r"\b(pencereleri geri yükle|restore windows)\b"],
     restore_all, _empty),

    ([r"\b(görev yöneticisi|task manager)\b"],
     open_task_manager, _empty),

    ([r"\b(denetim masası|control panel)\b"],
     open_control_panel, _empty),

    ([r"\b(internet bağlantısı var mı|internet çalışıyor mu|bağlantı kontrol)\b"],
     check_internet, _empty),

    ([r"\bping\b"],
     ping_host, _extract_ping),

    # ── Uygulama aç ───────────────────────────────────────────────────── #
    ([r"\b(aç|başlat|çalıştır|open|launch|start)\b.{1,30}\b(chrome|krom|firefox|edge|spotify|spoti|discord|diskord|telegram|whatsapp|vatsap|vscode|code|notepad|hesap|calculator|paint|explorer|powershell|cmd|terminal|steam|epic|obs|figma|blender|word|excel|powerpoint|zoom|teams|slack|capcut|notion|brave|opera|roblox|minecraft|valorant|lol|fortnite|cs2|csgo|twitch|netflix|vlc|outlook|github|lunar)\b",
      r"\b(chrome|firefox|edge|spotify|discord|telegram|whatsapp|vscode|notepad|steam|roblox|minecraft|valorant|fortnite|twitch|netflix|vlc|lunar)\b.{0,12}\b(aç|başlat|open|çalıştır)\b"],
     open_app, _extract_app),

    # ── Tek kelime uygulama adı → aç (chrome, not defteri...) ─────────── #
    ([r"^\s*(chrome|krom|firefox|edge|discord|whatsapp|telegram|steam|notepad|"
      r"not defteri|explorer|dosya gezgini|valorant|roblox|minecraft|lunar|obs|"
      r"vscode|epic|paint|word|excel)\s*$"],
     open_app, _extract_app),

    # ── Google / tarayıcı ana sayfa ──────────────────────────────────────#
    ([r"\bgoogle\b.{0,20}\b(aç|başlat|gir|git)\b",
      r"\b(aç|başlat|git)\b.{0,15}\bgoogle\b",
      r"^\s*google\s*$"],
     open_url, lambda _: {"url": "https://www.google.com"}),

    # ── URL aç (qr isteği olmayan) ────────────────────────────────────── #
    ([r"^https?://\S+$",
      r"\b(aç|git|ziyaret et|open)\b.{0,20}https?://",
      r"https?://\S+.{0,20}\b(aç|git|ziyaret)\b"],
     open_url, lambda m: {"url": re.search(r"https?://\S+", m).group(0) if re.search(r"https?://\S+", m) else m.strip()}),

    # ── Genel "X aç/başlat" → uygulama aç (Start menüsünden bulur) ─────── #
    # En sona yakın: spesifik kurallar (ses/pencere/site vb.) önce yakalar.
    # Bilinen NON-app kelimeleri hariç tut.
    ([r"^\s*(?!ses|sesi|pencere|pencereyi|sepet|sepeti|menü|menu|kapı|göz|"
      r"dosya|klasör|tarayıcı|tarayıcıları|ekran|monitör|gece|google|site|"
      r"link|url|qr|kamera|webcam|oyun|fokus|odak|wifi|dns|temp|ram|disk)"
      r"[\wçğışöü\.]{2,20}\s+(aç|ac|başlat|baslat|çalıştır|calistir)\b"],
     open_app, _extract_app),

    # ── Web araması (genel, en sona) ──────────────────────────────────── #
    ([r"\b(google'da ara|web'de ara|internette ara|arama yap)\b"],
     web_search, _extract_search),

    # ── Minecraft AI ajanı (geç — özel MC kuralları önce) ─────────────── #
    # "minecraftta elmas ver", "mc'de duvar ör" → AI komut üretir, çalıştırır
    ([r"\bminecraft'?t[ae]\b", r"\bmc'?d[ae]\b",
      r"\bminecraft\b.{0,25}\byap\b", r"\bmc\b.{0,20}\byap\b"],
     mc_yap, _extract_mc_yap),

    # ════════════════════════════════════════════════════════════════════ #
    #  AI SKILL'LER — Yapay zeka gerektiren işler (en sona gelir)        #
    # ════════════════════════════════════════════════════════════════════ #

    # ── Film / Dizi Önerisi ───────────────────────────────────────────── #
    ([r"\b(film|movie|dizi|series)\b.{0,30}\b(öner|oner|tavsiye|öneri|izlesem|izleyeyim)\b",
      r"\b(izlesem|izleyeyim|ne izlesem)\b.{0,30}\b(film|dizi|movie|series)\b",
      r"\b(iyi|güzel|kaliteli)\b.{0,20}\b(film|dizi)\b.{0,20}\b(öner|tavsiye)\b"],
     film_oner, _extract_film),

    # ── Oyun Önerisi ──────────────────────────────────────────────────── #
    ([r"\b(oyun)\b.{0,30}\b(öner|oner|tavsiye|öneri|oynasam|oynayayım)\b",
      r"\b(oynasam|oynayayım|ne oynasam)\b.{0,30}\b(oyun|game)\b",
      r"\b(iyi|güzel)\b.{0,15}\b(oyun|game)\b.{0,20}\b(öner|tavsiye)\b"],
     oyun_oner, _extract_oyun_ai),

    # ── Müzik Önerisi ─────────────────────────────────────────────────── #
    ([r"\b(müzik|muzik|şarkı|sarki|playlist)\b.{0,30}\b(öner|oner|tavsiye|dinlesem)\b",
      r"\b(dinlesem|ne dinlesem)\b.{0,30}\b(müzik|şarkı)\b",
      r"\b(ruh hali|mood)\b.{0,30}\b(müzik|şarkı|playlist)\b"],
     muzik_oner, _extract_muzik),

    # ── Yemek Tarifi ──────────────────────────────────────────────────── #
    ([r"\b(tarif|recipe)\b",
      r"\b(nasıl yapılır|nasıl pişirilir)\b.{0,30}\b(yemek|yiyecek|içecek)\b",
      r"\b\w+\b.{0,10}\b(tarifi|nasıl yapılır|nasıl pişirilir)\b"],
     tarif_ver, _extract_tarif),

    # ── Kod Yazma / Debug ─────────────────────────────────────────────── #
    ([r"\b(kod|code|script|program)\b.{0,30}\b(yaz|write|oluştur|yap|debug|düzelt|fix)\b",
      r"\b(python|javascript|java|csharp|c\+\+|rust|go|php)\b.{0,30}\b(yaz|code|oluştur|yap)\b",
      r"\b(fonksiyon|function|class|sınıf|metot|method)\b.{0,30}\b(yaz|oluştur)\b"],
     kod_yaz, _extract_kod),

    # ── Özetleme ──────────────────────────────────────────────────────── #
    ([r"\b(özetle|ozet|özetini|özetler|summarize|özetle)\b",
      r"\b(kısaca|kisaca)\b.{0,20}\b(anlat|anlatır mısın|açıkla)\b"],
     ozet_al, _extract_ozet),

    # ── İçerik Üretme (şiir, hikaye, email, slogan...) ───────────────── #
    ([r"\b(şiir|siir|poem)\b.{0,30}\b(yaz|oluştur|söyle)\b",
      r"\b(hikaye|hikâye|story)\b.{0,30}\b(yaz|anlat|oluştur)\b",
      r"\b(slogan|ilan|duyuru|tweet|post)\b.{0,30}\b(yaz|oluştur|üret)\b",
      r"\b(email|e-?posta|mail)\b.{0,30}\b(yaz|oluştur|taslak|hazırla)\b",
      r"\b(özür|davet|tebrik)\b.{0,20}\b(mesaj|yaz|oluştur)\b"],
     icerik_yaz, _extract_icerik),

    # ── Günlük / Haftalık Plan ────────────────────────────────────────── #
    ([r"\b(günlük|gunluk|haftalık|haftalik|aylık|aylik)\b.{0,30}\b(plan|program|schedule)\b",
      r"\b(plan|program)\b.{0,30}\b(yap|oluştur|hazırla|öner)\b",
      r"\b(bugün|bu hafta)\b.{0,20}\b(plan|program|ne yapayım|ne yapsam)\b"],
     gunluk_plan, _extract_plan),

    # ── Dil Pratik / Öğrenme ──────────────────────────────────────────── #
    ([r"\b(ingilizce|almanca|fransızca|ispanyolca|japonca|rusça|arapça|italyanca|korece)\b"
      r".{0,30}\b(pratik|practice|öğren|konuş|ders|alıştırma)\b",
      r"\b(dil\s+pratik|language\s+practice|yabancı\s+dil)\b"],
     dil_pratik, _extract_dil),

    # ── Genel AI Asistan (derin soru-cevap, en son kural) ─────────────── #
    # Sadece açık "açıkla / analiz et / düşün" ifadelerinde tetikle
    ([r"\b(açıkla|analiz\s+et|değerlendir|degerlendır|yorumla|ne\s+düşünüyorsun)\b",
      r"\b(bana\s+anlat|bana\s+açıkla|detaylı\s+anlat)\b",
      r"\b(neden|nasıl\s+çalışır|nasıl\s+mümkün|mantığı\s+ne)\b.{10,}"],
     genel_asistan, _extract_genel),
]


# ====================================================================== #
#  Dispatcher sınıfı                                                      #
# ====================================================================== #
def _normalize(text: str) -> str:
    """Türkçe karakterleri ASCII karşılıklarına çevir."""
    pairs = [("ç","c"),("ğ","g"),("ı","i"),("ş","s"),("ö","o"),("ü","u"),
             ("Ç","C"),("Ğ","G"),("İ","I"),("Ş","S"),("Ö","O"),("Ü","U")]
    for tr, en in pairs:
        text = text.replace(tr, en)
    return text


# ── Çok dilli anahtar kelime katmanı (İngilizce/EN → Türkçe komut) ────── #
# Yabancılar İngilizce yazınca AI'sız anında eşleşsin. (Diğer dilleri AI çevirir.)
# Uzun ifadeler önce gelmeli (sıralama uzunluğa göre yapılır).
_MULTI_TR = {
    # çok kelimeli ifadeler
    "turn off": "kapat", "turn on": "aç", "shut down": "bilgisayarı kapat",
    "volume up": "ses artır", "volume down": "ses azalt",
    "take a screenshot": "ekran görüntüsü", "screen shot": "ekran görüntüsü",
    "what time": "saat kaç", "lock screen": "ekranı kilitle",
    "open the": "aç", "system info": "sistem raporu", "battery level": "pil",
    # tek kelimeler
    "open": "aç", "launch": "aç", "start": "aç", "close": "kapat",
    "battery": "pil", "volume": "ses", "mute": "ses kapat", "unmute": "ses aç",
    "screenshot": "ekran görüntüsü", "screen": "ekran", "lock": "kilitle",
    "sleep": "uyut", "shutdown": "bilgisayarı kapat", "restart": "yeniden başlat",
    "reboot": "yeniden başlat", "weather": "hava", "time": "saat", "date": "tarih",
    "location": "konum", "search": "ara", "music": "müzik aç", "download": "indir",
    "status": "durum", "memory": "ram", "password": "şifre oluştur", "record": "kaydet",
    "calculator": "hesap makinesi", "camera": "kamera", "webcam": "webcam",
    "help": "yardım", "play": "aç", "increase": "artır", "decrease": "azalt",
    "brightness": "parlaklık", "speed": "hız", "logs": "loglar",
    "wallpaper": "duvar kağıdı", "clipboard": "pano", "notes": "not",
    "translate": "çevir", "calculate": "hesapla", "news": "haber",
    "stocks": "borsa", "crypto": "kripto", "dollar": "dolar", "gold": "altın",
    "price": "fiyat", "cost": "fiyat", "file": "dosya", "send": "gönder",
    "list": "liste", "show": "göster", "read": "oku",

    # ── Almanca (de) ──
    "neu starten": "yeniden başlat", "öffne": "aç", "öffnen": "aç",
    "schließe": "kapat", "schließen": "kapat", "batterie": "pil", "akku": "pil",
    "lautstärke": "ses", "lauter": "ses artır", "leiser": "ses azalt",
    "stummschalten": "ses kapat", "bildschirm": "ekran", "sperren": "kilitle",
    "schlafen": "uyut", "herunterfahren": "bilgisayarı kapat",
    "neustart": "yeniden başlat", "wetter": "hava", "uhrzeit": "saat",
    "standort": "konum", "musik": "müzik aç", "herunterladen": "indir",
    "passwort": "şifre oluştur", "wetterbericht": "hava durumu",

    # ── İspanyolca (es) ──
    "abre": "aç", "abrir": "aç", "cierra": "kapat", "cerrar": "kapat",
    "batería": "pil", "volumen": "ses", "subir volumen": "ses artır",
    "bajar volumen": "ses azalt", "silenciar": "ses kapat", "pantalla": "ekran",
    "bloquear": "kilitle", "dormir": "uyut", "apagar": "bilgisayarı kapat",
    "reiniciar": "yeniden başlat", "clima": "hava", "hora": "saat",
    "ubicación": "konum", "música": "müzik", "descargar": "indir",
    "contraseña": "şifre oluştur", "precio": "fiyat", "captura": "ekran görüntüsü",

    # ── Fransızca (fr) ──
    "mot de passe": "şifre oluştur", "couper le son": "ses kapat", "ouvre": "aç",
    "ouvrir": "aç", "ferme": "kapat", "fermer": "kapat", "écran": "ekran",
    "verrouiller": "kilitle", "éteindre": "bilgisayarı kapat",
    "redémarrer": "yeniden başlat", "météo": "hava", "heure": "saat",
    "localisation": "konum", "musique": "müzik aç", "télécharger": "indir",
    "capture": "ekran görüntüsü", "prix": "fiyat", "monter le son": "ses artır",
}
_MULTI_SORTED = sorted(_MULTI_TR.items(), key=lambda kv: -len(kv[0]))


def _to_tr_keywords(text: str) -> str:
    """İngilizce komut kelimelerini Türkçe karşılığıyla değiştirir."""
    t = text
    for en, tr in _MULTI_SORTED:
        if en in t:
            t = re.sub(r"\b" + re.escape(en) + r"\b", tr, t)
    return t


# ── OPTİMİZASYON: tüm kuralları bir kez derle (her mesajda yeniden derleme yok) #
# Her kural için orijinal + normalize edilmiş pattern'ler önceden compile edilir.
_COMPILED: list[tuple[list, Callable, Callable]] = []
for _rule_pats, _rule_h, _rule_e in _RULES:
    _cps = []
    for _pat in _rule_pats:
        try:
            _cps.append(re.compile(_pat, re.I))
        except re.error:
            continue
        _npat = _normalize(_pat)
        if _npat != _pat:
            try:
                _cps.append(re.compile(_npat, re.I))
            except re.error:
                pass
    _COMPILED.append((_cps, _rule_h, _rule_e))


# ── Çok adımlı sohbet için soru-cevap şablonları ──────────────────────── #
# Her şablon: {"field": alan_adı, "question": soru_metni, "platform_hint": bool}
_CLARIFY_FLOWS: dict[str, list[dict]] = {
    "whatsapp_send": [
        {"field": "platform",      "question": "Efendim, hangi platformdan göndereyim? (WhatsApp, Telegram, Discord, Instagram)"},
        {"field": "receiver",      "question": "Efendim, mesajı kime gönderelim?"},
        {"field": "message_text",  "question": "Efendim, ne yazmamı istersiniz?"},
    ],
    "send_message_partial": [
        {"field": "platform",      "question": "Efendim, hangi platformdan göndereyim? (WhatsApp, Telegram, Discord, Instagram)"},
        {"field": "receiver",      "question": "Efendim, mesajı kime gönderelim?"},
        {"field": "message_text",  "question": "Efendim, ne yazmamı istersiniz?"},
    ],
}

_PLATFORM_MAP = {
    "whatsapp": "whatsapp", "wp": "whatsapp",
    "telegram": "telegram", "tg": "telegram",
    "discord": "discord",
    "instagram": "instagram", "ig": "instagram",
    "messenger": "messenger",
}


def _detect_platform(text: str) -> str | None:
    tl = text.lower()
    for k, v in _PLATFORM_MAP.items():
        if k in tl:
            return v
    return None


# ── Self-code teklifi: mesaj bir EYLEM isteği mi? ─────────────────────── #
_TASK_VERBS = re.compile(
    r"\b(yap|yapar\s+mısın|oluştur|olustur|kapat|ayarla|çalıştır|calistir|"
    r"indir|kur|sil|taşı|tasi|kopyala|düzenle|duzenle|hesapla|dönüştür|donustur|"
    r"üret|uret|listele|ekle|başlat|baslat|durdur|tara|birleştir|birlestir|"
    r"ayıkla|ayikla|çek|kaydet|yeniden adlandır|rename|convert|generate|"
    r"otomatik|toplu|script|kod|yede(?:k|ğ|g)\w*|backup|çiz|ciz|raporla|"
    r"izle|sırala|sirala|temizle|filtrele|topla|grafik)\b",
    re.I,
)
# Bunlar soru/sohbet → teklif etme, AI'a bırak
_QUESTION_HINT = re.compile(
    r"\b(nedir|kimdir|neden|niçin|nicin|ne zaman|nasıl|nasil|ne düşün|"
    r"açıkla|aciklا|anlat|yorumla|mı|mi|mu|mü)\b",
    re.I,
)


def _looks_like_task(msg: str) -> bool:
    m = msg.strip()
    if not m or m.endswith("?"):
        return False
    if _QUESTION_HINT.search(m):
        return False
    return bool(_TASK_VERBS.search(m))


# ── LLM router → handler eşlemesi ─────────────────────────────────────── #
# İsimler intent_router._CATALOG ile BİREBİR aynı olmalı.
# Regex bir aracı kaçırınca router doğru aracı bulur, buradan çağrılır.
_ROUTER_MAP: dict[str, tuple[Callable, Callable]] = {
    "open_app":      (open_app, _extract_app),
    "youtube":       (youtube, _extract_youtube),
    "web_search":    (web_search, _extract_search),
    "weather":       (weather_action, _extract_weather),
    "screenshot":    (screenshot, _extract_screenshot),
    "volume":        (volume_control, _extract_volume),
    "lock_screen":   (lock_screen, _empty),
    "shutdown":      (shutdown, _extract_shutdown),
    "restart":       (restart, _p(delay=0)),
    "battery":       (battery_status, _empty),
    "cpu_ram":       (cpu_ram_usage, _empty),
    "disk":          (disk_usage, _empty),
    "running_apps":  (running_apps, _empty),
    "kill_process":  (kill_process, _extract_kill),
    "create_folder": (create_folder, _extract_folder),
    "find_file":     (find_file, _extract_find),
    "list_files":    (list_files, _empty),
    "calculate":     (calculate, _extract_calc),
    "translate":     (translate_text, _extract_translate),
    "wikipedia":     (wikipedia_search, _extract_wiki),
    "timer":         (set_timer, _extract_timer),
    "reminder":      (reminder, _extract_reminder),
    "take_note":     (take_note, _extract_note),
    "spotify":       (spotify_open, _extract_spotify),
    "clear_temp":    (clear_temp, _empty),
    "minimize_all":  (minimize_all, _empty),
    "task_manager":  (open_task_manager, _empty),
    "hiz_testi":     (hiz_testi, lambda _: {}),
}

# Bekleyen akış bu kadar saniye sonra düşer → eski mesajı yanlışlıkla çalıştırma
_PENDING_TTL = 90

# Geri dönüşsüz işlemler → çalıştırmadan önce onay sorulur
_DANGER = {"shutdown", "restart", "empty_recycle_bin"}


class ActionDispatcher:

    def __init__(self):
        self._pending: dict = {}
        # pending = {
        #   "flow":    "whatsapp_send",
        #   "steps":   [...remaining step dicts...],
        #   "params":  {"platform": "whatsapp", ...},
        # }

    # ── Çok adımlı akış ──────────────────────────────────────────────── #
    def _start_flow(self, flow_name: str, known_params: dict) -> str:
        steps = [s for s in _CLARIFY_FLOWS[flow_name]
                 if not known_params.get(s["field"])]
        if not steps:
            return self._execute_flow(flow_name, known_params)
        self._pending = {"flow": flow_name, "steps": steps,
                         "params": known_params, "ts": time.time()}
        return steps[0]["question"]

    def _continue_flow(self, user_message: str) -> str:
        step   = self._pending["steps"].pop(0)
        field  = step["field"]
        params = self._pending["params"]

        # Platform alanı için kısa eşleme
        if field == "platform":
            p = _detect_platform(user_message)
            params[field] = p or user_message.strip().lower()
        else:
            params[field] = user_message.strip()

        if self._pending["steps"]:
            return self._pending["steps"][0]["question"]

        flow = self._pending["flow"]
        self._pending = {}
        return self._execute_flow(flow, params)

    def _execute_flow(self, flow_name: str, params: dict) -> str:
        platform = params.get("platform", "whatsapp").lower()
        if platform in ("whatsapp", "wp"):
            from .whatsapp_auto import whatsapp_send
            return whatsapp_send(parameters=params)
        else:
            from .send_message import send_message
            return send_message(parameters=params)

    # ── Akıllı geri-dönüş: OpenRouter mesajı temiz komuta çevirir ─────── #
    def _maybe_offer_self_code(self, user_message: str, _routed: bool = False) -> str | None:
        """
        Regex hiçbir kurala uymadı. AKILLI AKIŞ:
          1. OpenRouter mesajı anlar → bilinen TEMİZ KOMUTA çevirir (bozuk dil çözümü)
             → o komutu yeniden dispatch et (regex artık tutar)
          2. SOHBET dediyse → AI cevaplasın (None)
          3. KOD dediyse → otomatik kod yaz + çalıştır
          4. LLM yoksa → eski regex-task sezgisi
        """
        # Zaten bir kez yönlendirildiyse tekrar LLM'e gitme (sonsuz döngü engeli)
        if not _routed:
            try:
                komut = normalize_command(user_message)
            except Exception:
                komut = ""
            if komut == "SOHBET":
                return None                              # AI sohbet etsin
            if komut == "KOD":
                logger.info("LLM: KOD → self-code: %s", user_message[:50])
                return kendi_kodunu_yaz(parameters={"istek": user_message,
                                                    "background": True})
            if komut and komut.lower() != user_message.lower().strip():
                logger.info("LLM normalize: '%s' → '%s'", user_message[:40], komut)
                sonuc = self.dispatch(komut, _routed=True)   # temiz komutu çalıştır
                if sonuc is not None:
                    return sonuc

        # LLM yok/başarısız → eylem gibi duruyorsa kodunu yaz
        if not _looks_like_task(user_message) and _QUESTION_HINT.search(user_message):
            return None
        if _looks_like_task(user_message):
            logger.info("Skill yok → otomatik self-code: %s", user_message[:50])
            return kendi_kodunu_yaz(parameters={"istek": user_message,
                                                "background": True})
        return None   # → AI'a ilet

    def _handle_self_code_offer(self, user_message: str) -> str | None:
        istek = self._pending.get("istek", "")
        low = user_message.lower().strip()
        if re.search(r"\b(evet|olur|tamam|yes|yap|çalıştır|calistir|onayla|hadi|ok|olsun)\b", low):
            self._pending = {}
            return kendi_kodunu_yaz(parameters={"istek": istek, "background": True})
        if re.search(r"\b(hayır|hayir|yok|no|gerek yok|vazgeç|vazgec|iptal|istemem|boşver|bosver)\b", low):
            self._pending = {}
            return "Peki Efendim, vazgeçtim."
        # Belirsiz cevap → teklifi DÜŞÜR ve YENİ mesajı normal akışta işle.
        # (Eski isteği ASLA çalıştırma — "eski mesajları çalıştırma" sorununun çözümü.)
        self._pending = {}
        return self.dispatch(user_message)

    # ── Ana dispatch ─────────────────────────────────────────────────── #
    def dispatch(self, user_message: str, _routed: bool = False,
                 _skip_custom: bool = False) -> str | None:
        # Süresi geçmiş bekleyen akışı temizle → eski mesajı yanlış çalıştırma
        if self._pending:
            ts = self._pending.get("ts", 0)
            if ts and (time.time() - ts) > _PENDING_TTL:
                logger.info("Bekleyen akış zaman aşımına uğradı, temizlendi.")
                self._pending = {}

        # Devam eden akış varsa önce onu tamamla
        if self._pending:
            if self._pending.get("flow") == "self_code_offer":
                return self._handle_self_code_offer(user_message)
            # Ekrana mesaj için girdi bekleniyordu → gelen mesajı yaz
            if self._pending.get("flow") == "ask_pc_bildirim":
                sesli = self._pending.get("sesli", False)
                self._pending = {}
                return pc_bildirim(parameters={"text": user_message.strip(),
                                               "sesli": sesli})
            # Tehlikeli işlem onayı bekleniyordu
            if self._pending.get("flow") == "confirm_danger":
                saved = self._pending
                self._pending = {}
                if re.search(r"\b(evet|onayl\w*|tamam|yes|olur|devam|kapat)\b",
                             user_message, re.I):
                    return saved["handler"](parameters=saved["params"])
                return "❌ İptal edildi, işlem yapılmadı."
            return self._continue_flow(user_message)

        # Özel komut/sahne eşleşmesi → eylem dizisini sırayla çalıştır
        if not _skip_custom:
            try:
                eylem = match_custom(user_message)
            except Exception:
                eylem = None
            if eylem:
                sonuc = []
                for adim in eylem.split(";"):
                    adim = adim.strip()
                    if adim:
                        r = self.dispatch(adim, _skip_custom=True)
                        if r:
                            sonuc.append(r)
                        time.sleep(0.3)
                return "✨ " + (" | ".join(s[:60] for s in sonuc) if sonuc else "Komut çalıştı.")

        ml  = user_message.lower().strip()
        ml2 = _normalize(ml)
        # İngilizce/yabancı kelimeleri Türkçe komuta çevrilmiş varyant (AI'sız)
        ml3 = _normalize(_to_tr_keywords(ml))
        if ml3 == ml2:
            ml3 = None

        for patterns, handler, extractor in _COMPILED:
            for rx in patterns:
                if rx.search(ml) or rx.search(ml2) or (ml3 and rx.search(ml3)):
                    try:
                        params = extractor(user_message)
                        logger.info("Kural: %s → %s", rx.pattern[:40], handler.__name__)
                        if params is None:
                            return None

                        # Ekrana mesaj: metin boşsa SORMA değil, BEKLE (kafasına göre yazma)
                        if handler.__name__ == "pc_bildirim" and not params.get("text"):
                            self._pending = {"flow": "ask_pc_bildirim",
                                             "sesli": params.get("sesli", False),
                                             "ts": time.time()}
                            return ("📺 Ekrana ne yazayım? Mesajı yaz, gönderince "
                                    "ekrana basacağım." +
                                    (" (sesli)" if params.get("sesli") else ""))

                        # Mesaj gönderme: eksik parametre varsa sor
                        if handler.__name__ in ("whatsapp_send", "send_message"):
                            if not params.get("receiver") or not params.get("message_text"):
                                known = {k: v for k, v in params.items() if v}
                                # Platform bilgisini mesajdan çek
                                if not known.get("platform"):
                                    p = _detect_platform(user_message)
                                    if p:
                                        known["platform"] = p
                                return self._start_flow("whatsapp_send", known)

                        # Tehlikeli/geri dönüşsüz işlem → önce onay iste
                        if handler.__name__ in _DANGER:
                            self._pending = {"flow": "confirm_danger",
                                             "handler": handler, "params": params,
                                             "ts": time.time()}
                            return (f"⚠️ Bu işlem geri alınamaz: "
                                    f"'{user_message.strip()}'\n"
                                    f"Onaylıyor musun? 'evet' yaz, iptal için 'hayır'.")

                        result = handler(parameters=params)
                        return result
                    except Exception as exc:
                        logger.error("Action hatası [%s]: %s", handler.__name__, exc)
                        return f"Efendim, işlem sırasında hata oluştu: {exc}"

        return self._maybe_offer_self_code(user_message, _routed=_routed)   # regex yok → OpenRouter normalize / AI
