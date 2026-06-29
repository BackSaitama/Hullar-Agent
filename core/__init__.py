# HULLAR sadece core.scheduler kullanır; AIBrain/ToolRegistry ağır import
# zincirini (ve yan etkilerini) tetiklememek için LAZY yüklenir.
# Eski kod 'from core import AIBrain' yaparsa yine çalışır.

__all__ = ["AIBrain", "ToolRegistry"]


def __getattr__(name):
    if name == "AIBrain":
        from .ai_brain import AIBrain
        return AIBrain
    if name == "ToolRegistry":
        from .tools import ToolRegistry
        return ToolRegistry
    raise AttributeError(f"module 'core' has no attribute {name!r}")
