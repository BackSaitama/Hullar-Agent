"""
Oyun Yükleme — Steam entegrasyonu.
- Steam mağaza API'siyle oyunu ara → AppID bul
- Yerel Steam kütüphanelerinde yüklü mü diye kontrol et
- Yüklüyse bildir, değilse steam://install/<appid> ile yükleme başlat
"""

import glob
import os
import re
import subprocess
import webbrowser
from pathlib import Path

try:
    import requests as _req
    _REQ = True
except ImportError:
    _req = None
    _REQ = False


# ── Steam kurulum yollarını bul ───────────────────────────────────────── #
def _steam_root() -> Path | None:
    candidates = [
        Path(r"C:\Program Files (x86)\Steam"),
        Path(r"C:\Program Files\Steam"),
        Path(os.environ.get("PROGRAMFILES(X86)", ""), "Steam"),
        Path(os.environ.get("LOCALAPPDATA", ""), "Steam"),
    ]
    for p in candidates:
        if p.exists() and (p / "steam.exe").exists():
            return p
    # Registry'den dene
    try:
        import winreg
        k = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                           r"SOFTWARE\WOW6432Node\Valve\Steam")
        val, _ = winreg.QueryValueEx(k, "InstallPath")
        winreg.CloseKey(k)
        p = Path(val)
        if p.exists():
            return p
    except Exception:
        pass
    return None


def _library_folders(steam_root: Path) -> list[Path]:
    """Tüm Steam kütüphane klasörlerini döndür (steamapps dahil)."""
    folders = [steam_root / "steamapps"]

    vdf = steam_root / "steamapps" / "libraryfolders.vdf"
    if not vdf.exists():
        vdf = steam_root / "config" / "libraryfolders.vdf"

    if vdf.exists():
        text = vdf.read_text(encoding="utf-8", errors="ignore")
        # "path" anahtarlarını çek
        for m in re.finditer(r'"path"\s+"([^"]+)"', text):
            p = Path(m.group(1)) / "steamapps"
            if p.exists():
                folders.append(p)

    return list(dict.fromkeys(folders))  # benzersiz


def _installed_games(steam_root: Path) -> dict[int, str]:
    """appid → oyun adı sözlüğü döndürür."""
    games: dict[int, str] = {}
    for lib in _library_folders(steam_root):
        for acf in lib.glob("appmanifest_*.acf"):
            try:
                text = acf.read_text(encoding="utf-8", errors="ignore")
                id_m   = re.search(r'"appid"\s+"(\d+)"', text)
                name_m = re.search(r'"name"\s+"([^"]+)"', text)
                if id_m and name_m:
                    games[int(id_m.group(1))] = name_m.group(1)
            except Exception:
                pass
    return games


# ── Steam mağaza araması ──────────────────────────────────────────────── #
def _steam_search(query: str) -> list[dict]:
    """
    Steam Store arama API'si → [{"appid": int, "name": str, "type": str}, ...]
    """
    if not _REQ:
        return []
    try:
        url = "https://store.steampowered.com/api/storesearch/"
        r = _req.get(url, params={"term": query, "l": "turkish", "cc": "TR"},
                     timeout=8)
        r.raise_for_status()
        items = r.json().get("items", [])
        return [
            {"appid": int(it["id"]), "name": it["name"], "type": it.get("type", "")}
            for it in items
            if it.get("id")
        ]
    except Exception:
        return []


def _best_match(results: list[dict], query: str) -> dict | None:
    """Sorguyla en yakın eşleşen oyunu döndür."""
    if not results:
        return None
    q_lower = query.lower()
    # Tam eşleşme önce
    for r in results:
        if r["name"].lower() == q_lower:
            return r
    # İçerme
    for r in results:
        if q_lower in r["name"].lower() or r["name"].lower() in q_lower:
            return r
    # Kelime kelime örtüşme
    q_words = set(q_lower.split())
    best, best_score = None, 0
    for r in results:
        r_words = set(r["name"].lower().split())
        score = len(q_words & r_words)
        if score > best_score:
            best, best_score = r, score
    return best or results[0]


# ── Otomatik yükleme tıklayıcı ───────────────────────────────────────── #
def _start_install(appid: int, game_name: str) -> str:
    """
    steam://install/<appid> aç, diyalog penceresini bul,
    'İleri'/'Next' butonlarına tıklayıp yüklemeyi başlat.
    """
    import time
    import threading

    # Önce URI'yi aç
    subprocess.Popen(f"start steam://install/{appid}", shell=True)

    # Arka planda buton tıklama — UI'yı bloke etmesin
    def _click_thread():
        time.sleep(3)          # Diyalog açılsın
        _auto_click_install(game_name)

    threading.Thread(target=_click_thread, daemon=True).start()
    return f"Efendim, '{game_name}' yükleniyor. Onay pencereleri otomatik geçiliyor..."


def _auto_click_install(game_name: str) -> None:
    """
    Steam yükleme diyaloğundaki butonları sırayla otomatik tıklar.
    Önce pywinauto, yoksa win32+pyautogui ile dener.
    """
    import time

    # ── Yöntem 1: pywinauto (en güvenilir) ─────────────────────────────── #
    try:
        from pywinauto import Desktop  # type: ignore

        # Steam install penceresini bul (timeout 15 sn)
        deadline = time.time() + 15
        steam_dlg = None

        while time.time() < deadline:
            try:
                for w in Desktop(backend="uia").windows():
                    t = w.window_text()
                    # Steam install dialog başlığı genellikle oyun adını içerir
                    if t and (
                        game_name[:6].lower() in t.lower()
                        or "yükle"   in t.lower()
                        or "install" in t.lower()
                        or ("steam" in t.lower() and len(t) > 5)
                    ):
                        steam_dlg = w
                        break
            except Exception:
                pass
            if steam_dlg:
                break
            time.sleep(0.5)

        if steam_dlg is None:
            _fallback_click(game_name)
            return

        # Buton etiketleri (Türkçe + İngilizce Steam UI)
        next_labels   = ["İleri >", "Next >", "İleri", "Next", "Continue"]
        finish_labels = ["Bitir", "Yükle", "Install", "Finish"]

        # Steam install diyaloğu genellikle 2-3 sayfa:
        # Sayfa 1: kütüphane seç → İleri
        # Sayfa 2: kısayollar   → İleri
        # Sayfa 3: hazır        → Yükle / Bitir
        for _attempt in range(4):
            time.sleep(1.2)
            clicked = False

            # Önce "Bitir/Yükle" butonunu dene (son sayfa)
            for lbl in finish_labels:
                try:
                    btn = steam_dlg.child_window(title=lbl, control_type="Button")
                    if btn.exists() and btn.is_enabled():
                        btn.click_input()
                        clicked = True
                        break
                except Exception:
                    pass

            if not clicked:
                # "İleri/Next" butonunu dene
                for lbl in next_labels:
                    try:
                        btn = steam_dlg.child_window(title=lbl, control_type="Button")
                        if btn.exists() and btn.is_enabled():
                            btn.click_input()
                            clicked = True
                            break
                    except Exception:
                        pass

            if not clicked:
                # Hiçbiri bulunamadıysa diyalog kapandı ya da değişti
                break

        return

    except ImportError:
        pass

    # ── Yöntem 2: win32gui + pyautogui (fallback) ────────────────────────── #
    _fallback_click(game_name)


def _fallback_click(game_name: str) -> None:
    """win32gui ile pencereyi bul, pyautogui ile sağ-alt bölgeye tıkla."""
    import time
    try:
        import win32gui   # type: ignore
        import pyautogui  # type: ignore

        def _find_steam(hwnd, found):
            t = win32gui.GetWindowText(hwnd)
            if t and (
                game_name[:5].lower() in t.lower()
                or "yükle" in t.lower()
                or "install" in t.lower()
            ):
                found.append(hwnd)

        # 3 deneme, pencere gecikmeli açılabilir
        for _ in range(3):
            found: list[int] = []
            win32gui.EnumWindows(_find_steam, found)
            if found:
                break
            time.sleep(1)

        if not found:
            return

        hwnd = found[0]

        # "İleri" butonuna 3 kez tıkla (3 sayfa için)
        for _ in range(3):
            try:
                win32gui.SetForegroundWindow(hwnd)
                time.sleep(0.6)
                rect = win32gui.GetWindowRect(hwnd)
                # Buton genellikle sağ-altta; Steam diyaloğu ~496×356
                btn_x = rect[2] - 75
                btn_y = rect[3] - 45
                pyautogui.click(btn_x, btn_y)
                time.sleep(1.2)
            except Exception:
                break

    except ImportError:
        # pyautogui/win32gui yoksa sessize al — diyalog zaten açık
        pass


# ── Ana fonksiyon ─────────────────────────────────────────────────────── #
def oyun_yukle(parameters: dict = None, **_) -> str:
    p = parameters or {}
    oyun_adi = p.get("oyun", p.get("query", "")).strip()

    if not oyun_adi:
        return "Efendim, hangi oyunu yüklememi istediğinizi belirtir misiniz?"

    # Steam kurulu mu?
    steam = _steam_root()
    if not steam:
        # Steam yoksa mağazayı aç
        url = f"https://store.steampowered.com/search/?term={oyun_adi}"
        webbrowser.open(url)
        return (
            f"Efendim, Steam kurulu bulunamadı. "
            f"'{oyun_adi}' için Steam mağaza sayfası tarayıcıda açıldı."
        )

    # Steam mağazasında ara
    results = _steam_search(oyun_adi)
    match   = _best_match(results, oyun_adi)

    if not match:
        # API sonuç vermediyse mağazayı aç
        url = f"https://store.steampowered.com/search/?term={oyun_adi}"
        webbrowser.open(url)
        return (
            f"Efendim, '{oyun_adi}' Steam'de bulunamadı. "
            f"Arama sonuçları tarayıcıda açıldı."
        )

    appid     = match["appid"]
    game_name = match["name"]

    # Yüklü mü kontrol et
    installed = _installed_games(steam)
    if appid in installed:
        installed_name = installed[appid]
        subprocess.Popen(f"start steam://rungameid/{appid}", shell=True)
        return f"Efendim, '{installed_name}' zaten yüklü. Oyun başlatılıyor."

    # Yüklü değil → yükleme başlat + otomatik tıkla
    return _start_install(appid, game_name)


# ── Parametre çıkarıcı ────────────────────────────────────────────────── #
def _extract_oyun(msg: str) -> dict:
    # "X yükle", "X indir", "X kur", "oyun X yükle" vb.
    # Önce Steam ile ilgili kalıpları sil ("steam'den", "steam üzerinden" vb.)
    q = re.sub(r"\bsteam\b['\w]*", "", msg, flags=re.I)
    stop_words = (
        r"\b(yükle|yukle|indir|kur|install|download|oyunu?|"
        r"bul|ekle|al|satın|satin|lütfen|lutfen|bana|beni|için|icin|"
        r"üzerinden|uzerinden|den|dan|'dan|'den)\b"
    )
    q = re.sub(stop_words, "", q, flags=re.I)
    # Tek tırnak kalıntılarını da temizle
    q = re.sub(r"['‘’]", "", q).strip(" .,;:-'")
    return {"oyun": q}
