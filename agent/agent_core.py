"""
Agent Core — otonom karar motoru.
ReAct döngüsü: Düşün → Araç seç → Çalıştır → Gözlemle → Tekrar.
Vision ile ekranı görür, hatadan toparlanır.
"""

import logging
from types import SimpleNamespace

from .llm import AgentLLM
from .memory import Memory
from .vision import Vision
from .planner import Planner
from .tools import build_toolbox

logger = logging.getLogger(__name__)

AGENT_SYSTEM = """Sen JARVIS, otonom bir Windows PC ajanısın.
Bir hedefi adım adım, araçları kullanarak tamamlarsın.

Her turda SADECE şu JSON'u ver:
{"thought": "kısa düşünce", "action": "araç_adı", "params": {...}}

Bittiğinde:
{"thought": "...", "action": "finish", "result": "kullanıcıya kısa özet"}

KURALLAR:
- WhatsApp görevleri için 'whatsapp_open_chat' kullan (open_app+click_element DEĞİL)
- WhatsApp mesajlarını okumak için 'read_messages' kullan
- 'click_element' görsel arama yapar; çok güvenilir değil, mümkünse özel araçları tercih et
- Bir araç HATA dönerse AYNI aracı tekrar deneme — farklı bir yol seç
- Aynı eylemi 2 kez deneyip başarısız olursan finish ile durumu bildir
- Sadece var olan araçları kullan (ask_user gibi araç YOK)
- Gereksiz konuşma yok, sadece JSON

ÖNEMLİ: Analiz/özet için AYRI bir "analiz" adımı YOK. read_messages'tan sonra
DOĞRUDAN summarize_and_save kullan — o hem analiz eder hem dosyaya yazar.
'analyze_text' gibi olmayan araçlar UYDURMA.

ÖRNEK (WhatsApp analizi — SADECE 4 adım):
1. {"thought":"sohbeti aç","action":"whatsapp_open_chat","params":{"contact":"ahmet"}}
2. {"thought":"mesajları oku","action":"read_messages","params":{}}
3. {"thought":"analiz edip kaydet","action":"summarize_and_save","params":{"path":"desktop/ahmet_analiz.txt","instruction":"konuşmayı özetle"}}
4. {"thought":"bitti","action":"finish","result":"ahmet konuşması analiz edilip masaüstüne kaydedildi"}

MEVCUT ARAÇLAR:
{tools}"""


class Agent:
    MAX_STEPS = 18
    MAX_RETRY = 2

    def __init__(self):
        self.llm     = AgentLLM()
        self.memory  = Memory()
        self.vision  = Vision(self.llm)
        self.planner = Planner(self.llm)
        # Paylaşılan bağlam (scratch: araçlar arası veri taşıma)
        self.ctx = SimpleNamespace(
            llm=self.llm, vision=self.vision, memory=self.memory,
            scratch={}
        )
        self.tools = build_toolbox(self.ctx)
        self._on_step = None   # opsiyonel: (mesaj) -> None ilerleme callback

    def set_progress_callback(self, cb):
        self._on_step = cb

    # Araç adı → kullanıcı dostu Türkçe etiket
    _LABELS = {
        "whatsapp_open_chat": "WhatsApp sohbeti açılıyor",
        "read_messages":      "Mesajlar okunuyor",
        "read_screen":        "Ekran inceleniyor",
        "summarize_and_save": "Analiz edilip kaydediliyor",
        "analyze":            "İçerik analiz ediliyor",
        "write_file":         "Dosya yazılıyor",
        "open_app":           "Uygulama açılıyor",
        "focus_window":       "Pencere öne getiriliyor",
        "open_url":           "Sayfa açılıyor",
        "web_search":         "Web'de aranıyor",
        "youtube":            "YouTube açılıyor",
        "click_element":      "Tıklanıyor",
        "type_text":          "Yazılıyor",
        "press_key":          "Tuş basılıyor",
        "scroll":             "Kaydırılıyor",
    }

    def _notify(self, msg: str, user: bool = True):
        """Logger'a teknik, kullanıcıya temiz mesaj."""
        logger.info("[AGENT] %s", msg)
        if user and self._on_step:
            try:
                self._on_step(msg)
            except Exception:
                pass

    def _notify_action(self, action: str):
        """Kullanıcıya araç için temiz Türkçe etiket göster."""
        label = self._LABELS.get(action, action)
        logger.info("[AGENT] çalıştırılıyor: %s", action)
        if self._on_step:
            try:
                self._on_step(label)
            except Exception:
                pass

    # ── Ana çalıştırma ────────────────────────────────────────────────── #
    def run(self, goal: str) -> str:
        self._notify("Görevi planlıyorum...")

        # 1. Planla
        plan = self.planner.plan(goal, self.memory.context_summary())
        plan_text = "\n".join(f"{i+1}. {s}" for i, s in enumerate(plan))
        logger.info("[AGENT] Plan: %s", plan)

        # 2. ReAct döngüsü
        system = AGENT_SYSTEM.replace("{tools}", self.tools.spec())
        history = []
        observation = ""
        steps_done = 0
        fail_count: dict[str, int] = {}    # eylem → başarısızlık sayısı
        call_count: dict[str, int] = {}    # eylem → toplam çağrı sayısı
        cached: dict[str, str] = {}        # okuma araçlarının sonucu (cache)
        empty_json = 0

        # Aynı veriyi tekrar üretmesi anlamsız olan "okuma" araçları
        READ_TOOLS = {"read_messages", "read_screen", "read_file", "list_windows", "list_dir"}

        for step in range(self.MAX_STEPS):
            prompt = self._build_prompt(goal, plan_text, history, observation)
            decision = self.llm.ask_json(prompt, system=system)

            action = decision.get("action", "")
            params = decision.get("params", {})
            thought = decision.get("thought", "")

            if not action:
                empty_json += 1
                if empty_json >= 3:
                    return "Efendim, model geçerli komut üretemedi. Görev iptal edildi."
                observation = 'SADECE JSON ver: {"thought":"...","action":"araç","params":{}}'
                continue
            empty_json = 0

            # Teknik thought yerine temiz Türkçe etiket göster
            logger.info("[AGENT] düşünce: %s", thought)

            # Bitiş
            if action == "finish":
                result = decision.get("result", "Görev tamamlandı.")
                self.memory.log_task(goal, True, steps_done)
                self._notify("✓ Tamamlandı")
                return result

            # 3 kez başarısız aracı engelle (kullanıcıya gösterme, logla)
            if fail_count.get(action, 0) >= 3:
                observation = (
                    f"'{action}' 3 kez başarısız, ARTIK KULLANMA. "
                    f"Başka araç seç veya finish."
                )
                history.append(("system", observation))
                continue

            self._notify_action(action)

            # Okuma aracı zaten başarıyla çalıştıysa → tekrar çalıştırma, cache'i ver
            if action in READ_TOOLS and action in cached:
                observation = (
                    f"'{action}' zaten okundu (sonuç aşağıda). TEKRAR OKUMA. "
                    f"Şimdi bir SONRAKİ adıma geç (analiz/write_file/finish).\n"
                    f"--- OKUNAN VERİ ---\n{cached[action][:1500]}"
                )
                history.append(("system", observation))
                continue

            call_count[action] = call_count.get(action, 0) + 1

            # Aracı çalıştır
            observation = self.tools.run(action, params)
            steps_done += 1

            if observation.startswith("HATA"):
                fail_count[action] = fail_count.get(action, 0) + 1
                # Kullanıcıya hata gösterme — sadece logla (model toparlar)
                logger.warning("[AGENT] %s başarısız: %s", action, observation[:80])
            else:
                fail_count[action] = 0
                # Başarılı okuma → cache'le
                if action in READ_TOOLS:
                    cached[action] = observation

            history.append((action, observation))
            history = history[-8:]

        # Adım limiti doldu
        self.memory.log_task(goal, False, steps_done)
        return f"Efendim, görev {steps_done} adımda tamamlanamadı. Son durum: {observation[:120]}"

    # ── Prompt kurucu ─────────────────────────────────────────────────── #
    def _build_prompt(self, goal, plan_text, history, observation) -> str:
        hist = "\n".join(f"[{a}] → {o[:150]}" for a, o in history) or "(henüz adım yok)"
        return (
            f"HEDEF: {goal}\n\n"
            f"PLAN:\n{plan_text}\n\n"
            f"YAPILAN ADIMLAR:\n{hist}\n\n"
            f"SON GÖZLEM: {observation or '(yok)'}\n\n"
            f"Sıradaki tek eylemi JSON ver."
        )
