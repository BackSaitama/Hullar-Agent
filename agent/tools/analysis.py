"""
Analiz araçları — LLM ile metin analizi/özetleme.
Okunan veriyi (scratch) işler, küçük modelin veri kopyalamasına gerek kalmaz.
"""


def _last_data(ctx) -> str:
    """Son okunan veriyi al (read_messages/read_screen scratch'e koyar)."""
    if hasattr(ctx, "scratch"):
        return ctx.scratch.get("last_read", "")
    return ""


def analyze(ctx, instruction: str = "Özetle ve ana noktaları çıkar") -> str:
    """
    Son okunan metni (WhatsApp mesajları vb.) LLM ile analiz eder.
    Sonucu scratch'e koyar ve döndürür.
    """
    data = _last_data(ctx)
    if not data:
        return "HATA: Önce read_messages veya read_screen ile veri oku."
    if not (ctx and ctx.llm):
        return "HATA: LLM yok."

    prompt = (
        f"Aşağıdaki WhatsApp/ekran içeriğini analiz et.\n"
        f"Görev: {instruction}\n\n"
        f"--- İÇERİK ---\n{data[:4000]}\n\n"
        f"Türkçe, net ve maddeler halinde analiz/özet ver."
    )
    result = ctx.llm.ask(prompt)
    if hasattr(ctx, "scratch"):
        ctx.scratch["analysis"] = result
    return result


def summarize_and_save(ctx, path: str, instruction: str = "Konuşmayı analiz et ve özetle") -> str:
    """
    Son okunan metni analiz eder VE doğrudan dosyaya yazar (tek adımda).
    Küçük modelin uzun metni kopyalamasına gerek kalmaz.
    """
    data = _last_data(ctx)
    if not data:
        return "HATA: Önce read_messages ile veri oku."
    if not (ctx and ctx.llm):
        return "HATA: LLM yok."

    prompt = (
        f"Aşağıdaki içeriği analiz et. Görev: {instruction}\n\n"
        f"--- İÇERİK ---\n{data[:4000]}\n\n"
        f"Türkçe, başlıklı ve maddeli bir rapor yaz."
    )
    analysis = ctx.llm.ask(prompt)

    # Dosyaya SADECE analizi yaz (ham veri yok)
    from .file_system import write_file
    import time
    full = (
        f"KONUŞMA ANALİZİ\n"
        f"{time.strftime('%d.%m.%Y %H:%M')}\n"
        f"{'='*40}\n\n"
        f"{analysis}\n"
    )
    return write_file(ctx, path=path, content=full)


def register(box):
    box.add("analyze",
            "Son okunan metni (mesajlar/ekran) LLM ile analiz eder/özetler",
            {"instruction": "ne yapılacak, örn 'ana konuları çıkar'"}, analyze)
    box.add("summarize_and_save",
            "Son okunan metni analiz edip DOĞRUDAN dosyaya yazar (analiz+yazma tek adım)",
            {"path": "dosya yolu, örn desktop/analiz.txt", "instruction": "analiz görevi"},
            summarize_and_save)
