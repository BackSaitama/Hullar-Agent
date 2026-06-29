"""
JARVIS Kendi Kodunu Yazma (self-coding) — akıllı, kendini düzelten, öğrenen.

Doğrudan komutla DEĞİL; bir istek hiçbir araca (tool) uymadığında dispatcher
bunu çağırır. Akış:
    1. Dispatcher hiçbir kurala uymayan EYLEM isteğini yakalar
    2. "Kodunu yazıp arka planda çalıştırayım mı?" diye sorar
    3. Kullanıcı "evet" derse → kendi_kodunu_yaz(background=True) çalışır

Arka planda (akıllı kısım):
    a. ÖĞRENME: Daha önce aynı/benzer iş için çalışan kod varsa onu yeniden
       kullanır (sıfırdan üretmez) — learned_tools.json
    b. KENDİNİ DÜZELTME: Kod hata verirse traceback'i AI'a geri verir,
       düzeltilmiş kodu alır, tekrar dener (en çok 3 deneme)
    c. Başarılı kodu öğrenir → bir dahaki sefere hazır araç olur
    d. Sonucu notify.push ile Telegram'dan bildirir

GÜVENLİK: Kod ancak kullanıcı "evet" dedikten sonra üretilip çalıştırılır.
Tehlikeli işlemler sistem prompt'unda yasaklanır.
"""

import json
import logging
import re
import subprocess
import sys
import threading
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

_GEN_DIR = Path(__file__).parent / "generated"
_LEARNED = Path(__file__).parent.parent / "data" / "learned_tools.json"
_REUSE_THRESHOLD = 0.6   # Jaccard benzerliği bu kadar üstüyse yeniden kullan
_MAX_TRIES = 3           # kendini düzeltme deneme sayısı

_SYS_PROMPT = (
    "Sen bir Python uzmanısın. Kullanıcının isteğini yerine getiren, "
    "TEK DOSYALIK, çalıştırılabilir bir Python betiği yaz. "
    "Sadece kodu döndür — açıklama, markdown, ``` işareti KULLANMA. "
    "Windows uyumlu ol. Mümkünse standart kütüphaneyi kullan. "
    "Tehlikeli işlemleri (disk biçimlendirme, sistem dosyası/registry silme, "
    "format, rmdir /s C:\\) ASLA yazma. Çıktıyı print ile göster."
)


# ── Kod üretimi (+ kendini düzeltme modu) ─────────────────────────────── #
def _clean_code(raw: str) -> str:
    raw = (raw or "").strip()
    raw = re.sub(r"^```(?:python)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    return raw.strip()


# AI yanıtı kod DEĞİL de hata/uyarı ise (anahtar yok, servis yok) — .py'a YAZMA
_AI_WARN = ("🔑", "API anahtarı girilmemiş", "AI servisi", "yanıt vermiyor",
            "GOOGLE_API_KEY=", "OPENAI_API_KEY=", "setup.py çalıştır")


def _looks_like_code(code: str) -> bool:
    if not code:
        return False
    if any(m in code for m in _AI_WARN):   # AI uyarısı → kod değil
        return False
    return any(tok in code for tok in ("import", "def ", "print", "=", "<html", "function"))


def _generate(istek: str, prev_code: str | None = None, error: str | None = None) -> str | None:
    """Normal üretim; prev_code+error verilirse DÜZELTME modunda üretir."""
    if prev_code and error:
        user = (f"Aşağıdaki Python kodu çalıştırılınca hata verdi. "
                f"Hatayı bul, düzelt ve SADECE tam düzeltilmiş kodu ver.\n\n"
                f"--- KOD ---\n{prev_code}\n\n--- HATA ---\n{error}")
    else:
        user = istek
    try:
        from .ai_skills import _ask_ai
        code = _clean_code(_ask_ai(_SYS_PROMPT, user))
    except Exception as exc:
        logger.error("Kod üretilemedi: %s", exc)
        return None
    return code if _looks_like_code(code) else None


def _save(code: str) -> Path:
    _GEN_DIR.mkdir(exist_ok=True)
    fpath = _GEN_DIR / f"gen_{datetime.now():%Y%m%d_%H%M%S_%f}.py"
    fpath.write_text(code, encoding="utf-8")
    return fpath


def _run(fpath: Path) -> tuple[bool, str]:
    """(başarılı_mı, çıktı_metni) döndürür."""
    try:
        r = subprocess.run([sys.executable, str(fpath)],
                           capture_output=True, text=True, timeout=180)
        out = (r.stdout or "").strip()
        err = (r.stderr or "").strip()
        ok = (r.returncode == 0) and not err
        text = out or "(çıktı yok)"
        if err:
            text += f"\n⚠️ {err}"
        return ok, text
    except Exception as exc:
        return False, f"çalıştırma hatası: {exc}"


# ── Öğrenme: çalışan kodu kaydet, benzer istekte yeniden kullan ───────── #
def _tokens(text: str) -> set[str]:
    return set(re.findall(r"\w+", (text or "").lower()))


def _load_learned() -> list[dict]:
    if _LEARNED.exists():
        try:
            return json.loads(_LEARNED.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


def _learn(istek: str, fpath: Path) -> None:
    items = _load_learned()
    items.append({
        "istek": istek.lower().strip(),
        "file": str(fpath),
        "created": datetime.now().strftime("%Y-%m-%d %H:%M"),
    })
    try:
        _LEARNED.parent.mkdir(exist_ok=True)
        _LEARNED.write_text(json.dumps(items, ensure_ascii=False, indent=2),
                            encoding="utf-8")
    except Exception as exc:
        logger.warning("öğrenilmiş araç kaydedilemedi: %s", exc)


def _find_learned(istek: str) -> dict | None:
    """İstekle yeterince örtüşen, dosyası hâlâ duran öğrenilmiş kodu bul."""
    words = _tokens(istek)
    if not words:
        return None
    best, best_score = None, 0.0
    for it in _load_learned():
        w2 = _tokens(it.get("istek", ""))
        if not w2:
            continue
        score = len(words & w2) / len(words | w2)
        if score > best_score:
            best, best_score = it, score
    if best and best_score >= _REUSE_THRESHOLD and Path(best["file"]).exists():
        return best
    return None


# ── Arka plan işi: öğren/üret → çalıştır → düzelt → öğren → bildir ────── #
def _push(text: str):
    try:
        from .notify import push
        push(text)
    except Exception:
        logger.info("self-code sonucu (push yok): %s", text[:200])


def _background_job(istek: str):
    # 1) Daha önce öğrenilmiş hazır kod var mı?
    learned = _find_learned(istek)
    if learned:
        ok, result = _run(Path(learned["file"]))
        if ok:
            _push(f"🧠 '{istek}' (öğrenilmiş araç: {Path(learned['file']).name}):\n{result[:1500]}")
            return
        logger.info("öğrenilmiş kod bozulmuş, yeniden üretiliyor.")

    # 2) Üret → çalıştır → hata olursa kendini düzelt (en çok _MAX_TRIES kez)
    code = _generate(istek)
    if not code:
        _push(f"🧠 '{istek}' için geçerli kod üretemedim.")
        return

    last_err = ""
    for attempt in range(_MAX_TRIES):
        fpath = _save(code)
        logger.info("self-code çalıştırılıyor (deneme %d): %s", attempt + 1, fpath.name)
        ok, result = _run(fpath)
        if ok:
            _learn(istek, fpath)            # başarılı → öğren
            tag = "" if attempt == 0 else f" ({attempt + 1}. denemede düzeldi)"
            _push(f"🧠 '{istek}' tamamlandı{tag} ({fpath.name}):\n{result[:1500]}")
            return
        last_err = result
        # Son deneme değilse düzeltmeye çalış
        if attempt < _MAX_TRIES - 1:
            fixed = _generate(istek, prev_code=code, error=result)
            if not fixed or fixed == code:
                break
            code = fixed

    _push(f"🧠 '{istek}' {_MAX_TRIES} denemede çalıştırılamadı:\n{last_err[:1200]}")


def kendi_kodunu_yaz(parameters: dict | None = None) -> str:
    """
    parameters:
        istek      : doğal dil istek
        background : True → arka planda öğren/üret+düzelt+çalıştır, hemen ack döner
    """
    params = parameters or {}
    istek = (params.get("istek") or "").strip()
    if not istek:
        return "Efendim, ne yapan bir kod yazayım?"

    if params.get("background"):
        threading.Thread(target=_background_job, args=(istek,), daemon=True).start()
        # Önceden öğrenilmişse kullanıcıya da haber ver
        if _find_learned(istek):
            return (f"🧠 '{istek}' için daha önce çalışan bir aracım var, "
                    f"onu çalıştırıyorum. Sonucu Telegram'dan ileteceğim.")
        return (f"🧠 Tamam Efendim, '{istek}' için kodu yazıp arka planda "
                f"çalıştırıyorum. Hata olursa kendim düzeltirim, bitince "
                f"Telegram'dan haber vereceğim.")

    # Senkron mod (gerekirse)
    code = _generate(istek)
    if not code:
        return "Efendim, geçerli bir kod üretemedim."
    fpath = _save(code)
    ok, result = _run(fpath)
    if ok:
        _learn(istek, fpath)
    return f"🧠 {fpath.name} çalıştı:\n{result[:1500]}"
