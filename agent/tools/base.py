"""Tool temel sınıfı ve kayıt sistemi."""

from dataclasses import dataclass
from typing import Callable


@dataclass
class Tool:
    name: str
    description: str
    params: dict          # {param_adı: açıklama}
    func: Callable        # (ctx, **params) -> str


class ToolBox:
    """Tüm araçları tutar, LLM'e spec verir, çalıştırır."""

    def __init__(self, ctx):
        self._tools: dict[str, Tool] = {}
        self._ctx = ctx   # paylaşılan bağlam (vision, memory, llm)

    def register(self, tool: Tool):
        self._tools[tool.name] = tool

    def add(self, name, description, params, func):
        self.register(Tool(name, description, params, func))

    def names(self) -> list[str]:
        return list(self._tools.keys())

    def spec(self) -> str:
        """LLM'e verilecek araç listesi metni."""
        lines = []
        for t in self._tools.values():
            p = ", ".join(f"{k}: {v}" for k, v in t.params.items()) or "yok"
            lines.append(f"- {t.name}({p}): {t.description}")
        return "\n".join(lines)

    def run(self, name: str, params: dict) -> str:
        tool = self._tools.get(name)
        if not tool:
            return f"HATA: '{name}' adlı araç yok. Mevcut: {', '.join(self.names())}"
        try:
            return tool.func(self._ctx, **(params or {}))
        except TypeError as exc:
            return f"HATA: '{name}' parametreleri yanlış: {exc}"
        except Exception as exc:
            return f"HATA: '{name}' çalışırken: {exc}"
