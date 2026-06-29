"""Dosya sistemi araçları."""

import os
from pathlib import Path

_DESKTOP = Path(os.environ.get("USERPROFILE", "")) / "Desktop"


def _resolve(path: str) -> Path:
    """Kısayolları çöz: desktop, downloads, documents."""
    low = path.lower().strip()
    shortcuts = {
        "desktop": _DESKTOP,
        "masaüstü": _DESKTOP,
        "downloads": Path(os.environ.get("USERPROFILE", "")) / "Downloads",
        "indirilenler": Path(os.environ.get("USERPROFILE", "")) / "Downloads",
        "documents": Path(os.environ.get("USERPROFILE", "")) / "Documents",
        "belgeler": Path(os.environ.get("USERPROFILE", "")) / "Documents",
    }
    for k, v in shortcuts.items():
        if low == k:
            return v
        if low.startswith(k + "/") or low.startswith(k + "\\"):
            return v / path[len(k)+1:]
    p = Path(path)
    return p if p.is_absolute() else _DESKTOP / path


def write_file(ctx, path: str, content: str) -> str:
    """Metin dosyası oluşturur/yazar."""
    fp = _resolve(path)
    fp.parent.mkdir(parents=True, exist_ok=True)
    fp.write_text(content, encoding="utf-8")
    return f"Dosya yazıldı: {fp} ({len(content)} karakter)"


def read_file(ctx, path: str) -> str:
    fp = _resolve(path)
    if not fp.exists():
        return f"HATA: dosya yok: {fp}"
    return fp.read_text(encoding="utf-8", errors="ignore")[:5000]


def append_file(ctx, path: str, content: str) -> str:
    fp = _resolve(path)
    fp.parent.mkdir(parents=True, exist_ok=True)
    with fp.open("a", encoding="utf-8") as f:
        f.write(content + "\n")
    return f"Eklendi: {fp}"


def list_dir(ctx, path: str = "desktop") -> str:
    fp = _resolve(path)
    if not fp.is_dir():
        return f"HATA: klasör yok: {fp}"
    items = [x.name for x in fp.iterdir()][:50]
    return f"{fp} içeriği: " + ", ".join(items)


def register(box):
    box.add("write_file", "Metin dosyası oluşturur/üzerine yazar (.txt vb)",
            {"path": "dosya yolu veya 'desktop/ad.txt'", "content": "içerik"}, write_file)
    box.add("read_file", "Dosya içeriğini okur",
            {"path": "dosya yolu"}, read_file)
    box.add("append_file", "Dosyanın sonuna ekler",
            {"path": "dosya yolu", "content": "eklenecek"}, append_file)
    box.add("list_dir", "Klasör içeriğini listeler",
            {"path": "klasör (desktop/downloads/...)"}, list_dir)
