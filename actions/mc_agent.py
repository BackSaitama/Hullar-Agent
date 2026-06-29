"""
HULLAR Minecraft AI ajanı.

"minecraftta elmas ver", "mc'de etrafıma duvar ör", "minecraftta gece yap" gibi
DOĞAL dil isteğini alır → AI ile Minecraft (Java) komutlarına çevirir →
T sohbetinden tek tek çalıştırır.

Komut gerektirmeyen şeyleri (madencilik, balık) zaten ayrı skiller yapar;
bu, /give /fill /tp /time /weather /effect /summon gibi komutları üretir.
"""

from __future__ import annotations

import re
import threading
import time


def _push(text: str):
    try:
        from .notify import push
        push(text)
    except Exception:
        pass


_SYS = (
    "Sen bir Minecraft Java Edition uzmanısın. Kullanıcının Türkçe isteğini "
    "yerine getiren Minecraft komutlarını üret. "
    "SADECE komutları ver, her satıra bir komut, başına / koy. "
    "Açıklama, markdown, numara YOK. En fazla 8 komut. "
    "Oyuncu için @s veya @p kullan. Koordinat gerekirse ~ (göreceli) kullan. "
    "Örnek istek 'elmas ver' → /give @s diamond 64 . "
    "Örnek 'etrafıma cam duvar' → /fill ~-3 ~ ~-3 ~3 ~3 ~3 glass hollow . "
    "Tehlikeli/yıkıcı komut (büyük /fill air, /kill @e) verme."
)


def _komutlari_uret(istek: str) -> list[str]:
    try:
        from .ai_skills import _ask_ai
        ham = _ask_ai(_SYS, istek)
    except Exception:
        return []
    cmds = []
    for satir in (ham or "").splitlines():
        s = satir.strip().strip("`").lstrip("0123456789. -")
        if not s:
            continue
        if not s.startswith("/"):
            s = "/" + s
        # basit güvenlik: kitlesel silme engelle
        low = s.lower()
        if "/kill @e" in low or re.search(r"/fill .* air\b.*\d{3,}", low):
            continue
        cmds.append(s)
    return cmds[:8]


def mc_yap(parameters: dict | None = None) -> str:
    istek = (parameters or {}).get("istek", "").strip()
    if not istek:
        return "Minecraft'ta ne yapayım? Örn: 'minecraftta elmas kılıç ver'"
    cmds = _komutlari_uret(istek)
    if not cmds:
        return ("Bunun için komut üretemedim (AI yanıt vermedi). "
                "Direkt komut için: 'mc komut /give @s diamond 64'")

    def _run():
        try:
            import pyautogui as g  # type: ignore
        except Exception:
            return
        for c in cmds:
            g.press("t")
            time.sleep(0.35)
            try:
                import pyperclip
                pyperclip.copy(c)
                g.hotkey("ctrl", "v")
            except Exception:
                g.write(c, interval=0.01)
            time.sleep(0.15)
            g.press("enter")
            time.sleep(0.5)
        _push("🎮 Minecraft: " + " | ".join(cmds))

    threading.Thread(target=_run, daemon=True).start()
    return ("🎮 Minecraft'ta yapıyorum:\n" + "\n".join(cmds) +
            "\n(Oyun penceresi önde olmalı.)")


def _extract_mc_yap(msg: str) -> dict:
    t = re.sub(r"\b(minecraft'?ta|minecraft'?te|minecraftta|mc'?de|mc'?da|mc)\b",
               "", msg, flags=re.I)
    t = re.sub(r"\b(yap|yapar mısın|oluştur|ver bana|yarat)\b", " ", t, flags=re.I)
    return {"istek": re.sub(r"\s+", " ", t).strip(" .,:-")}
