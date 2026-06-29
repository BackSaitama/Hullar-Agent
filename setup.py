#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HULLAR — Kurulum Sihirbazı / Setup Wizard
Çalıştır:  python setup.py

İstediğin dili (5 dil) ve AI motorunu (Ollama / OpenRouter / Google Gemini /
Anthropic Claude / OpenAI) seçersin. .env ve data/telegram.json otomatik yazılır.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ENV = ROOT / ".env"
TG = ROOT / "data" / "telegram.json"

# ── Diller (5) ─────────────────────────────────────────────────────────── #
LANGS = {
    "1": ("tr", "Türkçe"),
    "2": ("en", "English"),
    "3": ("de", "Deutsch"),
    "4": ("es", "Español"),
    "5": ("fr", "Français"),
}

# Kurulum metinleri — her dil için
T = {
    "tr": {
        "welcome": "🤖 HULLAR Kurulum Sihirbazı",
        "ai_q": "Hangi yapay zekayı kullanacaksın?",
        "ai_opts": [
            "Ollama (yerel, BEDAVA, internetsiz çalışır) — önerilen",
            "OpenRouter (tek anahtar, çok model)",
            "Google Gemini API",
            "Anthropic Claude API",
            "OpenAI (ChatGPT) API",
        ],
        "key_q": "API anahtarını yapıştır",
        "model_q": "Model adı (boş bırak = varsayılan: {d})",
        "ollama_note": "Ollama kurulu olmalı (ollama.com). Modeller otomatik kullanılır.",
        "tg_q": "Telegram bot token (yoksa boş geç, sadece CMD)",
        "tg_id": "Telegram chat ID (senin ID'in)",
        "name_q": "Sana nasıl hitap edeyim? (isim)",
        "done": "✅ Kurulum bitti! Başlat: python -m hullar telegram   (veya start.bat)",
        "saved": "Kaydedildi",
        "invalid": "Geçersiz seçim, tekrar:",
        "tg_sec": "Telegram ID'ni gireceğiz — böylece BOTU SADECE SEN kontrol edebilirsin.",
        "tg_auto": "Otomatik bulalım: Telegram'da botuna herhangi bir mesaj at.",
        "tg_press": "Mesajı attıysan Enter'a bas",
        "tg_found": "ID bulundu",
        "tg_manual": "Otomatik bulunamadı, ID'yi elle gir:",
    },
    "en": {
        "welcome": "🤖 HULLAR Setup Wizard",
        "ai_q": "Which AI will you use?",
        "ai_opts": [
            "Ollama (local, FREE, works offline) — recommended",
            "OpenRouter (one key, many models)",
            "Google Gemini API",
            "Anthropic Claude API",
            "OpenAI (ChatGPT) API",
        ],
        "key_q": "Paste your API key",
        "model_q": "Model name (empty = default: {d})",
        "ollama_note": "Ollama must be installed (ollama.com). Models used automatically.",
        "tg_q": "Telegram bot token (leave empty for CMD-only)",
        "tg_id": "Telegram chat ID (your ID)",
        "name_q": "What should I call you? (name)",
        "done": "✅ Setup complete! Start: python -m hullar telegram   (or start.bat)",
        "saved": "Saved",
        "invalid": "Invalid choice, again:",
        "tg_sec": "We'll set your Telegram ID — so ONLY YOU can control the bot.",
        "tg_auto": "Auto-detect: open Telegram and send any message to your bot.",
        "tg_press": "Press Enter after you sent the message",
        "tg_found": "ID found",
        "tg_manual": "Couldn't auto-detect, enter ID manually:",
    },
    "de": {
        "welcome": "🤖 HULLAR Einrichtungsassistent",
        "ai_q": "Welche KI möchtest du nutzen?",
        "ai_opts": [
            "Ollama (lokal, KOSTENLOS, offline) — empfohlen",
            "OpenRouter (ein Schlüssel, viele Modelle)",
            "Google Gemini API",
            "Anthropic Claude API",
            "OpenAI (ChatGPT) API",
        ],
        "key_q": "API-Schlüssel einfügen",
        "model_q": "Modellname (leer = Standard: {d})",
        "ollama_note": "Ollama muss installiert sein (ollama.com).",
        "tg_q": "Telegram Bot-Token (leer für nur CMD)",
        "tg_id": "Telegram Chat-ID (deine ID)",
        "name_q": "Wie soll ich dich nennen? (Name)",
        "done": "✅ Fertig! Start: python -m hullar telegram   (oder start.bat)",
        "saved": "Gespeichert",
        "invalid": "Ungültig, nochmal:",
        "tg_sec": "Wir setzen deine Telegram-ID — so kannst NUR DU den Bot steuern.",
        "tg_auto": "Automatisch: sende deinem Bot eine beliebige Nachricht in Telegram.",
        "tg_press": "Drücke Enter, nachdem du die Nachricht gesendet hast",
        "tg_found": "ID gefunden",
        "tg_manual": "Nicht gefunden, ID manuell eingeben:",
    },
    "es": {
        "welcome": "🤖 Asistente de instalación de HULLAR",
        "ai_q": "¿Qué IA usarás?",
        "ai_opts": [
            "Ollama (local, GRATIS, sin internet) — recomendado",
            "OpenRouter (una clave, muchos modelos)",
            "Google Gemini API",
            "Anthropic Claude API",
            "OpenAI (ChatGPT) API",
        ],
        "key_q": "Pega tu clave API",
        "model_q": "Nombre del modelo (vacío = por defecto: {d})",
        "ollama_note": "Ollama debe estar instalado (ollama.com).",
        "tg_q": "Token del bot de Telegram (vacío = solo CMD)",
        "tg_id": "ID de chat de Telegram (tu ID)",
        "name_q": "¿Cómo te llamo? (nombre)",
        "done": "✅ ¡Listo! Inicia: python -m hullar telegram   (o start.bat)",
        "saved": "Guardado",
        "invalid": "Opción inválida, otra vez:",
        "tg_sec": "Configuraremos tu ID de Telegram — así SOLO TÚ controlas el bot.",
        "tg_auto": "Detección automática: envía cualquier mensaje a tu bot en Telegram.",
        "tg_press": "Pulsa Enter cuando hayas enviado el mensaje",
        "tg_found": "ID encontrado",
        "tg_manual": "No se detectó, introduce el ID manualmente:",
    },
    "fr": {
        "welcome": "🤖 Assistant d'installation HULLAR",
        "ai_q": "Quelle IA vas-tu utiliser ?",
        "ai_opts": [
            "Ollama (local, GRATUIT, hors ligne) — recommandé",
            "OpenRouter (une clé, plusieurs modèles)",
            "Google Gemini API",
            "Anthropic Claude API",
            "OpenAI (ChatGPT) API",
        ],
        "key_q": "Colle ta clé API",
        "model_q": "Nom du modèle (vide = défaut : {d})",
        "ollama_note": "Ollama doit être installé (ollama.com).",
        "tg_q": "Token du bot Telegram (vide = CMD seulement)",
        "tg_id": "ID de chat Telegram (ton ID)",
        "name_q": "Comment dois-je t'appeler ? (nom)",
        "done": "✅ Terminé ! Démarre : python -m hullar telegram   (ou start.bat)",
        "saved": "Enregistré",
        "invalid": "Choix invalide, encore :",
        "tg_sec": "On va définir ton ID Telegram — ainsi TOI SEUL contrôles le bot.",
        "tg_auto": "Détection auto : envoie un message à ton bot sur Telegram.",
        "tg_press": "Appuie sur Entrée après avoir envoyé le message",
        "tg_found": "ID trouvé",
        "tg_manual": "Non détecté, entre l'ID manuellement :",
    },
}

# AI backend kodları + varsayılan modeller
BACKENDS = {
    "1": ("ollama", {"OLLAMA_MODEL": "aya-expanse:8b",
                     "OLLAMA_CODER_MODEL": "qwen2.5-coder:7b",
                     "VISION_MODEL": "moondream"}),
    "2": ("openrouter", "google/gemini-3.5-flash"),
    "3": ("google", "gemini-2.0-flash"),
    "4": ("anthropic", "claude-sonnet-4-6"),
    "5": ("openai", "gpt-4o"),
}


def _detect_chat_id(token: str) -> str:
    """Bota gelen son mesajdan chat ID'sini otomatik bulur (getUpdates)."""
    try:
        import urllib.request
        url = f"https://api.telegram.org/bot{token}/getUpdates"
        with urllib.request.urlopen(url, timeout=15) as r:
            data = json.loads(r.read().decode())
        for upd in reversed(data.get("result", [])):
            msg = upd.get("message") or upd.get("edited_message") or {}
            cid = msg.get("chat", {}).get("id")
            if cid:
                return str(cid)
    except Exception:
        pass
    return ""


def ask(prompt: str) -> str:
    try:
        return input(prompt + " > ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\nİptal."); sys.exit(0)


def choose(prompt: str, options: list, t: dict) -> str:
    print("\n" + prompt)
    for i, o in enumerate(options, 1):
        print(f"  {i}) {o}")
    while True:
        c = ask("")
        if c in {str(i) for i in range(1, len(options) + 1)}:
            return c
        print(t.get("invalid", "?"))


def main():
    print("=" * 50)
    # 1) Dil
    print("🌍 Dil / Language / Sprache / Idioma / Langue:")
    for k, (_, name) in LANGS.items():
        print(f"  {k}) {name}")
    lc = ask("")
    while lc not in LANGS:
        print("?"); lc = ask("")
    lang = LANGS[lc][0]
    t = T[lang]

    print("\n" + "=" * 50)
    print(t["welcome"])
    print("=" * 50)

    # 2) AI backend
    bsel = choose(t["ai_q"], t["ai_opts"], t)
    backend, default_model = BACKENDS[bsel]

    env = {"HULLAR_LANG": lang, "AI_BACKEND": backend,
           "OLLAMA_BASE_URL": "http://localhost:11434",
           "OLLAMA_MODEL": "aya-expanse:8b",
           "OLLAMA_CODER_MODEL": "qwen2.5-coder:7b",
           "VISION_MODEL": "moondream"}

    if backend == "ollama":
        print("ℹ️  " + t["ollama_note"])
    else:
        key = ask(t["key_q"])
        model = ask(t["model_q"].format(d=default_model)) or default_model
        keymap = {"openrouter": ("OPENROUTER_API_KEY", "OPENROUTER_MODEL"),
                  "google": ("GOOGLE_API_KEY", "GOOGLE_MODEL"),
                  "anthropic": ("ANTHROPIC_API_KEY", "ANTHROPIC_MODEL"),
                  "openai": ("OPENAI_API_KEY", "OPENAI_MODEL")}
        kname, mname = keymap[backend]
        env[kname] = key
        env[mname] = model

    # 3) İsim
    name = ask(t["name_q"])
    if name:
        env["USER_NAME"] = name

    # 4) Telegram — mevcut ayarları oku (token boş bırakılırsa korunur)
    existing = {}
    if TG.exists():
        try:
            existing = json.loads(TG.read_text(encoding="utf-8"))
        except Exception:
            existing = {}

    token = ask(t["tg_q"]).strip()
    if not token and existing.get("bot_token"):
        token = existing["bot_token"]
        print("ℹ️  " + t.get("tg_keep", "Mevcut bot token korunuyor."))

    chat_id = ""
    if token:
        print("🔒 " + t["tg_sec"])
        print(t["tg_auto"])
        ask(t["tg_press"])
        chat_id = _detect_chat_id(token)
        if chat_id:
            print(f"✅ {t['tg_found']}: {chat_id}")
        else:
            # otomatik bulunamadı → mevcut ID varsa onu kullan, yoksa elle sor
            if existing.get("chat_id"):
                chat_id = str(existing["chat_id"])
                print("ℹ️  " + t.get("tg_keep_id", "Mevcut ID korunuyor.") + f" ({chat_id})")
            else:
                print("⚠️ " + t["tg_manual"])
                chat_id = ask(t["tg_id"])

    # ── Yaz ───────────────────────────────────────────────────────────── #
    lines = ["# HULLAR — kurulum sihirbazı tarafından oluşturuldu"]
    for k, v in env.items():
        lines.append(f"{k}={v}")
    ENV.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"✅ {t['saved']}: {ENV}")

    if token:
        TG.parent.mkdir(parents=True, exist_ok=True)
        data = {"bot_token": token}
        if str(chat_id).isdigit():
            # Güvenlik: sadece SENİN ID'in bota komut verebilir (allowed listesi)
            data["chat_id"] = int(chat_id)
            data["allowed"] = [int(chat_id)]
        elif existing.get("chat_id"):
            data["chat_id"] = existing["chat_id"]
            data["allowed"] = existing.get("allowed", [existing["chat_id"]])
        TG.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"✅ {t['saved']}: {TG}")

    print("\n" + t["done"])


if __name__ == "__main__":
    main()
