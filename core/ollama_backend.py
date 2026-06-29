"""
Ollama yerel LLM arka ucu — Composio entegrasyonlu.

Akış:
  1. Composio tool'ları yükle (GitHub, Gmail, Calendar, vb.)
  2. Ollama OpenAI-uyumlu /v1 endpoint üzerinden çağrılır
  3. Tool çağrısı gelirse → Composio veya yerel ToolRegistry çalıştırır
  4. Composio tool yoksa → JSON prompt mühendisliğiyle yerel tool çağrısı
"""

import json
import logging
import os
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .tools import ToolRegistry

from .prompt import JARVIS_SYSTEM_PROMPT, system_prompt

logger = logging.getLogger(__name__)


class OllamaBackend:
    def __init__(self, tool_registry: "ToolRegistry"):
        self._base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self._model    = os.getenv("OLLAMA_MODEL", "llama3")
        self._tool_registry = tool_registry
        self._history: list[dict] = []

        self._check_connection()

        # Composio'yu OpenAI istemcisiyle bağla
        self._openai_client = None
        self._composio_toolset = None
        self._composio_tools: list[dict] = []
        self._init_composio()

        logger.info("Ollama backend hazır: %s @ %s", self._model, self._base_url)

    # ── Bağlantı ─────────────────────────────────────────────────────── #

    def _check_connection(self):
        import requests  # type: ignore
        try:
            r = requests.get(f"{self._base_url}/api/tags", timeout=5)
            r.raise_for_status()
            models = [m["name"] for m in r.json().get("models", [])]
            logger.info("Ollama modelleri: %s", models)
        except Exception as exc:
            raise ConnectionError(
                f"Ollama'ya bağlanılamadı ({self._base_url}). "
                f"Ollama'nın çalıştığından emin olun: {exc}"
            )

    def _init_composio(self):
        """Composio + OpenAI istemcisini başlat."""
        api_key = os.getenv("COMPOSIO_API_KEY", "")
        if not api_key:
            logger.info("COMPOSIO_API_KEY bulunamadı, Composio devre dışı.")
            return
        try:
            from openai import OpenAI  # type: ignore
            from composio_openai import ComposioToolSet  # type: ignore

            # Ollama'nın OpenAI-uyumlu endpoint'ine bağlan
            # timeout=75: yavaş modelde 10 dk takılmayı önler (varsayılan 600 sn!)
            self._openai_client = OpenAI(
                base_url=f"{self._base_url}/v1",
                api_key="ollama",   # Ollama için değer önemsiz
                timeout=75.0,
                max_retries=1,
            )
            self._composio_toolset = ComposioToolSet(api_key=api_key)

            # Bağlı tüm app'lerin araçlarını yükle
            self._composio_tools = self._composio_toolset.get_tools()
            logger.info(
                "Composio hazır: %d tool yüklendi.",
                len(self._composio_tools)
            )
        except Exception as exc:
            logger.warning("Composio başlatılamadı: %s", exc)
            self._openai_client = None
            self._composio_toolset = None
            self._composio_tools = []

    # ── Ana chat ─────────────────────────────────────────────────────── #

    def chat(self, user_message: str) -> str:
        # 0. Selam/sohbet → modele gitmeden kısa, sıcak yanıt (geveze model olmasın)
        st = self._smalltalk(user_message)
        if st is not None:
            return st

        # 1. Hızlı yerel komut eşleşmesi
        quick = self._quick_action(user_message)
        if quick is not None:
            return quick

        # 2. Composio + OpenAI istemcisi varsa → gerçek tool calling
        if self._openai_client and self._composio_toolset:
            return self._chat_with_composio(user_message)

        # 3. Fallback: salt Ollama JSON prompt
        return self._chat_plain(user_message)

    # ── Composio destekli sohbet ──────────────────────────────────────── #

    def _chat_with_composio(self, user_message: str) -> str:
        self._history.append({"role": "user", "content": user_message})

        messages = [{"role": "system", "content": system_prompt()}] + self._history

        # Yerel tool şemalarını OpenAI formatına çevir
        local_tools = self._local_tools_as_openai()

        # Composio + yerel tool'ları birleştir
        all_tools = self._composio_tools + local_tools

        try:
            response = self._openai_client.chat.completions.create(
                model=self._model,
                messages=messages,
                tools=all_tools if all_tools else None,
                temperature=0.3,
            )
        except Exception as exc:
            logger.error("Ollama/OpenAI hata: %s", exc)
            return self._chat_plain(user_message)

        msg = response.choices[0].message

        # Tool çağrısı var mı?
        if msg.tool_calls:
            results = []
            kod_calistirildi = False
            for tc in msg.tool_calls:
                name = tc.function.name
                try:
                    args = json.loads(tc.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}

                logger.info("Tool çağrısı: %s(%s)", name, args)

                # Önce yerel tool dene, sonra Composio
                if self._tool_registry and name in self._get_local_tool_names():
                    result = self._tool_registry.call(name, **args)
                else:
                    # Composio
                    try:
                        res = self._composio_toolset.execute_action(
                            action=name,
                            params=args,
                        )
                        result = str(res.get("data") or res.get("response") or res)
                    except Exception as exc2:
                        result = f"Araç hatası: {exc2}"

                if name == "kod_calistir":
                    kod_calistirildi = True

                results.append(result)

                # Geçmişe ekle
                self._history.append({
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [tc.model_dump()],
                })
                self._history.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result,
                })

            # kod_calistir çalıştıysa: çıktıyı tekrar modele besle, doğal cevap al.
            # (Function Calling geri-besleme adımı — son cevap TTS'e gider.)
            if kod_calistirildi:
                return self._son_cevabi_al()

            # Son sonucu döndür
            return "\n".join(results) if results else "İşlem tamamlandı."

        # Normal metin yanıtı — ama içinde JSON tool çağrısı olabilir
        text = msg.content or ""

        # Modelin yazdığı metinde {"tool": ...} var mı? varsa çalıştır
        tool_result = self._try_tool_call(text)
        if tool_result is not None:
            self._history.append({"role": "assistant", "content": text})
            return tool_result

        self._history.append({"role": "assistant", "content": text})
        return text

    # ── Ollama NATIVE tool calling (Composio gerekmez) ────────────────── #

    def _chat_plain(self, user_message: str) -> str:
        """
        Ollama'nın /api/chat 'tools' parametresiyle GERÇEK native tool calling.
        Composio çalışmasa bile yerel araçlar (kod_calistir dahil) çağrılır.
        Model olmayan bir araç uydurursa → düzeltici mesajla kod_calistir'a yönlendirir.
        """
        import requests  # type: ignore
        from .prompt import system_prompt_native

        if not self._history or self._history[-1].get("content") != user_message:
            self._history.append({"role": "user", "content": user_message})

        tools = self._local_tools_as_openai()
        known = self._get_local_tool_names()
        convo = [{"role": "system", "content": system_prompt_native()}] + list(self._history)

        def _post(with_tools: bool):
            payload = {
                "model": self._model,
                "messages": convo,
                "stream": False,
                "options": {"temperature": 0.2},
            }
            if with_tools and tools:
                payload["tools"] = tools
            r = requests.post(f"{self._base_url}/api/chat", json=payload, timeout=90)
            r.raise_for_status()
            return r.json().get("message", {})

        last_content = ""
        for _attempt in range(3):
            try:
                msg = _post(with_tools=True)
            except Exception as exc:
                logger.error("Ollama hata: %s", exc)
                return f"Üzgünüm Efendim, Ollama ile iletişimde hata oluştu: {exc}"

            last_content = (msg.get("content") or "").strip()
            tcs = msg.get("tool_calls") or []
            if not tcs:
                break   # araç yok → düz metin

            # Bilinen / uydurma araçları ayır
            valid, invalid = [], []
            for tc in tcs:
                nm = (tc.get("function") or {}).get("name", "")
                (valid if nm in known else invalid).append(tc)

            if valid:
                results = []
                kod_vardi = False
                for tc in valid:
                    fn = tc["function"]
                    name = fn.get("name", "")
                    args = fn.get("arguments", {})
                    if isinstance(args, str):
                        try:
                            args = json.loads(args)
                        except Exception:
                            args = {}
                    logger.info("Native tool çağrısı: %s(%s)", name, args)
                    result = self._tool_registry.call(name, **args)
                    results.append(result)
                    if name == "kod_calistir":
                        kod_vardi = True
                    self._history.append({
                        "role": "assistant", "content": msg.get("content") or "",
                        "tool_calls": [tc]})
                    self._history.append({
                        "role": "tool", "content": str(result), "name": name})

                # Araçlar zaten temiz Türkçe cümle döndürür (dosya_olustur, youtube_ac…)
                # → doğrudan döndür. Sadece kod_calistir'da ham çıktıyı modele yorumlat.
                joined = "\n".join(str(r) for r in results) if results else "İşlem tamamlandı."
                if not kod_vardi:
                    self._history.append({"role": "assistant", "content": joined})
                    return self._temizle(joined)
                convo = [{"role": "system", "content": system_prompt_native()}] + list(self._history)
                try:
                    final = _post(with_tools=False)
                    text = self._temizle((final.get("content") or "").strip())
                except Exception:
                    text = ""
                if not text:
                    text = joined
                self._history.append({"role": "assistant", "content": text})
                return text

            # Sadece UYDURMA araç(lar) → düzelt ve tekrar dene
            bad = (invalid[0].get("function") or {}).get("name", "?")
            logger.info("Uydurma araç '%s' → kod_calistir'a yönlendiriliyor.", bad)
            convo.append({"role": "assistant", "content": "", "tool_calls": [invalid[0]]})
            convo.append({
                "role": "tool", "name": bad,
                "content": (f"HATA: '{bad}' adında bir araç yok. Bu görevi 'kod_calistir' "
                            "aracıyla yap: gereken Python kodunu yaz ve sonucu print() ile döndür.")})

        # Araç çağrısı olmadı → düz metin (yine de JSON tool kalıbı varsa çalıştır)
        content = last_content
        tool_result = self._try_tool_call(content)
        if tool_result is not None:
            self._history.append({"role": "assistant", "content": content})
            return tool_result
        self._history.append({"role": "assistant", "content": content})
        return self._temizle(content)

    @staticmethod
    def _temizle(text: str) -> str:
        """Modelin gevezeliğini sadeleştir: '## başlık', kod bloğu, fazla satırı at."""
        if not text:
            return text
        import re
        t = text
        t = re.sub(r"```[\s\S]*?```", "", t)          # kod bloklarını at
        t = re.sub(r"(?m)^\s*#{1,6}\s*.*$", "", t)     # '## başlık' satırlarını at
        t = re.sub(r"\n{3,}", "\n\n", t).strip()
        return t or text.strip()

    # ── Yardımcılar ───────────────────────────────────────────────────── #

    def _local_tools_as_openai(self) -> list[dict]:
        """Yerel ToolRegistry şemalarını OpenAI tool formatına çevir."""
        if not self._tool_registry:
            return []
        result = []
        for schema in self._tool_registry.get_schemas():
            result.append({
                "type": "function",
                "function": {
                    "name": schema["name"],
                    "description": schema.get("description", ""),
                    "parameters": schema.get("parameters", {"type": "object", "properties": {}}),
                }
            })
        return result

    def _get_local_tool_names(self) -> set[str]:
        if not self._tool_registry:
            return set()
        return {s["name"] for s in self._tool_registry.get_schemas()}

    def _reply(self, text: str, ans: str) -> str:
        self._history.append({"role": "user", "content": text})
        self._history.append({"role": "assistant", "content": ans})
        return ans

    def _smalltalk(self, text: str) -> str | None:
        """Selam/teşekkür + tarih/saat/yıl → modele gitmeden temiz, doğru yanıt."""
        t = text.lower().strip(" .,!?")

        # ── Tarih / yıl / saat → GERÇEK saatten (model 2023 sanmasın) ──── #
        import datetime as _dt
        now = _dt.datetime.now()
        ay = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz",
              "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"][now.month - 1]
        gun = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma",
               "Cumartesi", "Pazar"][now.weekday()]
        if re.search(r"(hangi yıl|yıl kaç|kaç yıl|yılınday|yıldayız|hangi sene|sene kaç|"
                     r"kaç sene|what year|hangi senede)", t):
            return self._reply(text, f"{now.year} yılındayız Efendim.")
        if re.search(r"\b(ayın kaç|bugün ayın|hangi gün|günlerden ne|bugün ne|"
                     r"bugün günü|tarih ne|tarih kaç|bugünün tarih|what day|what.?s the date)", t):
            return self._reply(text, f"Bugün {now.day} {ay} {now.year}, {gun} Efendim.")
        if re.search(r"\b(saat kaç|kaçta|what time)", t):
            return self._reply(text, f"Saat {now.strftime('%H:%M')} Efendim.")

        if len(t) > 40:
            return None
        checks = [
            (r"^(merhaba|selam|sa|hey|alo|hello|hi)\b", "Merhaba Efendim, size nasıl yardımcı olabilirim?"),
            (r"\b(nasılsın|nasilsin|naber|ne haber|iyi misin|napıyorsun)\b", "Çok iyiyim Efendim, teşekkür ederim. Sizin için ne yapabilirim?"),
            (r"\b(günaydın|gunaydin)\b", "Günaydın Efendim! Bugün size nasıl yardımcı olabilirim?"),
            (r"\b(iyi geceler|iyi akşamlar|iyi aksamlar)\b", "İyi geceler Efendim, dinlenmenize bakın."),
            (r"\b(teşekkür|tesekkur|sağ ?ol|sag ?ol|eyvallah|çok yaşa)\b", "Rica ederim Efendim, her zaman buradayım."),
            (r"\b(kimsin|adın ne|sen kimsin|nesin)\b", "Ben JARVIS, kişisel yapay zeka asistanınızım Efendim."),
            (r"^(görüşürüz|hoşça kal|bay bay|kapat)\b", "Görüşmek üzere Efendim."),
        ]
        for pat, ans in checks:
            if re.search(pat, t):
                self._history.append({"role": "user", "content": text})
                self._history.append({"role": "assistant", "content": ans})
                return ans
        return None

    def _quick_action(self, text: str) -> str | None:
        t = text.lower().strip()
        checks = [
            (r"\byoutube\b.*(aç|başlat|gir|git)|(aç|başlat).*(youtube)", "youtube_ac"),
            (r"\bgoogle\b.*(aç|başlat|gir|git)|(aç|başlat).*(google)",   "google_ac"),
            (r"\bnetflix\b",                                               "netflix_ac"),
            (r"\btwitch\b",                                                "twitch_ac"),
            (r"\btiktok\b|\btik tok\b",                                    "tiktok_ac"),
            (r"\btwitter\b|\bx\.com\b",                                    "twitter_ac"),
            (r"\b(salad)\b.*(aç|başlat)|gpu.*(para|kazan)",               "salad_baslat"),
            (r"\b(salad)\b.*(kapat|durdur)",                               "salad_durdur"),
            (r"\bemoji\b.*(aç|panel)",                                     "emoji_paneli"),
            (r"pano\s*geçmi|kopyaladıklarım",                              "clipboard_gecmis"),
        ]
        for pattern, tool in checks:
            if re.search(pattern, t):
                return self._tool_registry.call(tool)
        return None

    def _try_tool_call(self, text: str) -> str | None:
        """
        Metindeki {"tool": ..., "args": {...}} bloğunu bulur ve çalıştırır.
        Multi-line JSON'u brace sayacıyla doğru şekilde çıkarır.
        """
        # "tool" anahtarı geçen tüm '{' pozisyonlarını bul
        for m in re.finditer(r'\{', text):
            start = m.start()
            # Bu pozisyondan itibaren brace dengesi sayarak tam JSON bloğu çıkar
            raw = self._extract_balanced(text, start)
            if raw is None:
                continue
            try:
                data = json.loads(raw)
                tool_name = data.get("tool")
                args = data.get("args", {})
                if tool_name:
                    logger.info("JSON tool yakalandı: %s(%s)", tool_name, args)
                    # kod_calistir → çalıştır, çıktıyı tekrar modele besle
                    if tool_name == "kod_calistir":
                        sonuc = self._tool_registry.call(tool_name, **args)
                        return self._kod_geri_besle(args.get("kod", ""), sonuc)
                    return self._tool_registry.call(tool_name, **args)
            except (json.JSONDecodeError, ValueError):
                continue
        return None

    # ── Function Calling geri-besleme ─────────────────────────────────── #

    def _son_cevabi_al(self) -> str:
        """
        Tool sonuçları geçmişe eklendikten sonra modeli (araçsız) tekrar çağırıp
        son doğal-dil cevabını üretir. OpenAI-uyumlu tool_calls yolu için.
        Bu cevap chat() tarafından döndürülür → mevcut TTS'e iletilir.
        """
        messages = [{"role": "system", "content": system_prompt()}] + self._history
        try:
            # tools verilmez → model tekrar tool çağırmasın, düz cevap üretsin
            response = self._openai_client.chat.completions.create(
                model=self._model,
                messages=messages,
                temperature=0.3,
            )
            text = (response.choices[0].message.content or "").strip()
        except Exception as exc:
            logger.error("Geri besleme hatası: %s", exc)
            return self._history[-1].get("content") or "İşlem tamamlandı."
        if not text:
            text = self._history[-1].get("content") or "İşlem tamamlandı."
        self._history.append({"role": "assistant", "content": text})
        return text

    def _kod_geri_besle(self, kod: str, sonuc: str) -> str:
        """
        kod_calistir çıktısını tekrar Ollama'ya besleyip son Türkçe cevabı üretir.
        JSON/plain yol için (OpenAI tool_calls kullanılamadığında).
        """
        import requests  # type: ignore

        besleme = self._history + [{
            "role": "user",
            "content": (
                "Az önce isteğim için yazdığın Python kodunu çalıştırdım. "
                "Aşağıdaki çıktıyı kullanarak bana kısa ve net bir Türkçe cevap ver. "
                "Kod ya da JSON yazma, yalnızca sonucu açıkla.\n\n"
                f"--- KOD ---\n{kod}\n\n--- ÇIKTI ---\n{sonuc}"
            ),
        }]
        payload = {
            "model": self._model,
            "messages": [{"role": "system", "content": system_prompt()}] + besleme,
            "stream": False,
            "options": {"temperature": 0.3},
        }
        try:
            r = requests.post(f"{self._base_url}/api/chat", json=payload, timeout=60)
            r.raise_for_status()
            return r.json()["message"]["content"].strip() or sonuc
        except Exception as exc:
            logger.error("Kod geri besleme hatası: %s", exc)
            return sonuc

    @staticmethod
    def _extract_balanced(text: str, start: int) -> str | None:
        """start pozisyonundan itibaren balanced { } bloğu döndürür."""
        depth = 0
        in_str = False
        escape = False
        for i in range(start, len(text)):
            ch = text[i]
            if escape:
                escape = False
                continue
            if ch == '\\' and in_str:
                escape = True
                continue
            if ch == '"':
                in_str = not in_str
                continue
            if in_str:
                continue
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    return text[start:i + 1]
        return None
