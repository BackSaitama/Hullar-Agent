"""
Task Planning Engine — kullanıcı isteğini alt görevlere böler.
"""

import logging

logger = logging.getLogger(__name__)

PLANNER_SYSTEM = """Sen bir görev planlama motorusun. Kullanıcının isteğini,
bir Windows PC ajanının yürütebileceği SOMUT alt adımlara bölersin.

Kurallar:
- Her adım tek ve net bir eylem olsun
- Sıralı ve mantıklı olsun (önce uygulama aç, sonra işlem yap)
- Gereksiz adım ekleme
- En fazla 8 adım

SADECE şu JSON formatında yanıt ver:
{"steps": ["adım 1", "adım 2", ...]}

Mevcut özel araçlar: whatsapp_open_chat (sohbet açar), read_messages (mesaj okur),
summarize_and_save (okunan veriyi analiz edip DOĞRUDAN dosyaya yazar — analiz+yazma tek adım),
analyze (metni analiz eder), write_file, open_app, web_search, youtube.
Adımları bunlara göre yaz. Analiz+kaydetme için summarize_and_save kullan (ayrı analiz adımı YAZMA).

Örnek:
İstek: "WhatsApp'ta ahmet'ı aç ve konuşmayı analiz edip txt oluştur"
{"steps": [
  "whatsapp_open_chat ile ahmet sohbetini aç",
  "read_messages ile mesajları oku",
  "summarize_and_save ile masaüstüne ahmet_analiz.txt olarak analiz edip kaydet"
]}"""


class Planner:
    def __init__(self, llm):
        self._llm = llm

    def plan(self, goal: str, memory_ctx: str = "") -> list[str]:
        prompt = f"İstek: {goal}"
        if memory_ctx:
            prompt = f"[Hafıza]\n{memory_ctx}\n\n{prompt}"
        data = self._llm.ask_json(prompt, system=PLANNER_SYSTEM)
        steps = data.get("steps", [])
        if not steps:
            # Plan çıkmazsa tek adım olarak işle
            steps = [goal]
        logger.info("Plan (%d adım): %s", len(steps), steps)
        return steps
