"""Uygulama aç — Mark'ın open_app.py'si temel alındı, JARVIS için uyarlandı."""

import shutil
import subprocess
import time

_APP_ALIASES: dict[str, str] = {
    "chrome": "chrome", "google chrome": "chrome",
    "firefox": "firefox", "edge": "msedge",
    "brave": "brave", "opera": "opera",
    "whatsapp": "WhatsApp", "telegram": "Telegram",
    "discord": "Discord", "slack": "Slack",
    "zoom": "Zoom", "teams": "msteams",
    "spotify": "Spotify", "vlc": "vlc",
    "vscode": "code", "visual studio code": "code", "code": "code",
    "terminal": "wt", "cmd": "cmd.exe", "powershell": "powershell.exe",
    "notepad": "notepad.exe", "not defteri": "notepad.exe",
    "explorer": "explorer.exe", "dosya gezgini": "explorer.exe",
    "task manager": "taskmgr.exe", "görev yöneticisi": "taskmgr.exe",
    "settings": "ms-settings:", "ayarlar": "ms-settings:",
    "calculator": "calc.exe", "hesap makinesi": "calc.exe",
    "paint": "mspaint.exe",
    "word": "winword", "excel": "excel", "powerpoint": "powerpnt",
    "steam": "steam", "epic": "EpicGamesLauncher", "epic games": "EpicGamesLauncher",
    "instagram": "Instagram", "tiktok": "TikTok",
    "capcut": "CapCut", "notion": "Notion",
    "figma": "Figma", "blender": "blender",
    "obs": "obs64", "obs studio": "obs64",
    "görev zamanlayıcı": "taskschd.msc",
    # yaygın yazım hataları / kısaltmalar
    "diskord": "Discord", "diskort": "Discord", "disc": "Discord",
    "vatsap": "WhatsApp", "whatsap": "WhatsApp", "vasap": "WhatsApp", "wp": "WhatsApp",
    "telegram": "Telegram", "tg": "Telegram",
    "krom": "chrome", "chorme": "chrome", "google chrom": "chrome",
    "spoti": "Spotify", "spotfy": "Spotify",
    "stim": "steam", "buhar": "steam",
    # oyunlar / launcher'lar
    "roblox": "Roblox", "minecraft": "Minecraft", "mc": "Minecraft",
    "valorant": "VALORANT", "valo": "VALORANT",
    "league": "League of Legends", "lol": "League of Legends",
    "fortnite": "Fortnite", "fortnit": "Fortnite",
    "cs": "cs2", "cs2": "cs2", "csgo": "cs2", "counter strike": "cs2",
    "epic games": "EpicGamesLauncher", "epik": "EpicGamesLauncher",
    "riot": "RiotClientServices", "battlenet": "Battle.net", "battle.net": "Battle.net",
    "lunar": "Lunar Client", "lunar client": "Lunar Client",
    # uygulamalar
    "twitch": "Twitch", "netflix": "Netflix", "youtube": "chrome",
    "vlc": "vlc", "mpc": "mpc-hc", "winrar": "winrar", "7zip": "7zFM",
    "photoshop": "Photoshop", "premiere": "Adobe Premiere Pro",
    "github": "GitHub Desktop", "postman": "Postman",
    "pycharm": "pycharm64", "intellij": "idea64", "android studio": "studio64",
    "unity": "Unity", "godot": "Godot",
    "outlook": "outlook", "snipping": "SnippingTool", "ekran alıntısı": "SnippingTool",
    "store": "ms-windows-store:", "mağaza": "ms-windows-store:",
    "xbox": "Xbox", "ayarları aç": "ms-settings:",
}


def _normalize(name: str) -> str:
    key = name.lower().strip()
    if key in _APP_ALIASES:
        return _APP_ALIASES[key]
    for alias, cmd in _APP_ALIASES.items():
        if alias in key or key in alias:
            return cmd
    return name


def open_app(parameters: dict, **_) -> str:
    app_name = (parameters or {}).get("app_name", "").strip()
    if not app_name:
        return "Efendim, hangi uygulamayı açmamı istediğinizi belirtir misiniz?"

    normalized = _normalize(app_name)

    # 1. Doğrudan subprocess
    if shutil.which(normalized) or shutil.which(normalized.split(".")[0]):
        try:
            subprocess.Popen(normalized, shell=True,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(1.2)
            return f"Efendim, {app_name} açıldı."
        except Exception:
            pass

    # 2. ms-settings: gibi URI protokolleri
    if ":" in normalized:
        try:
            subprocess.Popen(f"start {normalized}", shell=True)
            time.sleep(0.8)
            return f"Efendim, {app_name} açıldı."
        except Exception:
            pass

    # 3. Başlat menüsü araması (pyautogui)
    try:
        import pyautogui  # type: ignore
        pyautogui.PAUSE = 0.1
        pyautogui.press("win")
        time.sleep(0.7)
        pyautogui.write(normalized, interval=0.05)
        time.sleep(0.9)
        pyautogui.press("enter")
        time.sleep(2.0)
        return f"Efendim, {app_name} başlatıldı."
    except Exception:
        pass

    return f"Efendim, {app_name} açılamadı. Kurulu olduğundan emin olun."
