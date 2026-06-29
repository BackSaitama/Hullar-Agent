"""Dosya işlemleri: oluştur, sil, aç, bul, kopyala, taşı, sıkıştır, listele."""

import os
import re
import shutil
import subprocess
import zipfile
from pathlib import Path
from datetime import datetime


def _resolve(path: str) -> Path:
    p = Path(path)
    if not p.is_absolute():
        p = Path.home() / "Desktop" / path
    return p


def create_file(parameters: dict, **_) -> str:
    path    = (parameters or {}).get("path", "").strip()
    content = (parameters or {}).get("content", "")
    if not path:
        return "Efendim, dosya yolunu belirtir misiniz?"
    p = _resolve(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return f"Efendim, '{p}' oluşturuldu."


def delete_file(parameters: dict, **_) -> str:
    path = (parameters or {}).get("path", "").strip()
    if not path:
        return "Efendim, silinecek dosya/klasörü belirtir misiniz?"
    p = _resolve(path)
    if not p.exists():
        return f"Efendim, '{p}' bulunamadı."
    if p.is_dir():
        shutil.rmtree(p)
    else:
        p.unlink()
    return f"Efendim, '{p}' silindi."


def open_file(parameters: dict, **_) -> str:
    path = (parameters or {}).get("path", "").strip()
    if not path:
        return "Efendim, açılacak dosyayı belirtir misiniz?"
    p = _resolve(path)
    if not p.exists():
        # Bul ve aç
        results = list(Path.home().rglob(path))
        if results:
            p = results[0]
        else:
            return f"Efendim, '{path}' bulunamadı."
    os.startfile(str(p))
    return f"Efendim, '{p.name}' açıldı."


def find_file(parameters: dict, **_) -> str:
    name    = (parameters or {}).get("name", "").strip()
    where   = (parameters or {}).get("where", str(Path.home()))
    if not name:
        return "Efendim, aranacak dosya adını belirtir misiniz?"
    found = list(Path(where).rglob(name))[:10]
    if not found:
        return f"Efendim, '{name}' bulunamadı."
    return "Efendim, bulunanlar:\n" + "\n".join(str(f) for f in found)


def create_folder(parameters: dict, **_) -> str:
    path = (parameters or {}).get("path", "").strip()
    if not path:
        return "Efendim, klasör adını belirtir misiniz?"
    p = _resolve(path)
    p.mkdir(parents=True, exist_ok=True)
    return f"Efendim, '{p}' klasörü oluşturuldu."


def copy_file(parameters: dict, **_) -> str:
    src  = (parameters or {}).get("source", "").strip()
    dest = (parameters or {}).get("destination", "").strip()
    if not src or not dest:
        return "Efendim, kaynak ve hedef yollarını belirtir misiniz?"
    s, d = _resolve(src), _resolve(dest)
    if not s.exists():
        return f"Efendim, '{s}' bulunamadı."
    shutil.copy2(str(s), str(d))
    return f"Efendim, '{s.name}' → '{d}' kopyalandı."


def move_file(parameters: dict, **_) -> str:
    src  = (parameters or {}).get("source", "").strip()
    dest = (parameters or {}).get("destination", "").strip()
    if not src or not dest:
        return "Efendim, kaynak ve hedef yollarını belirtir misiniz?"
    s, d = _resolve(src), _resolve(dest)
    if not s.exists():
        return f"Efendim, '{s}' bulunamadı."
    shutil.move(str(s), str(d))
    return f"Efendim, '{s.name}' → '{d}' taşındı."


def rename_file(parameters: dict, **_) -> str:
    path    = (parameters or {}).get("path", "").strip()
    new_name = (parameters or {}).get("new_name", "").strip()
    if not path or not new_name:
        return "Efendim, dosya yolu ve yeni adı belirtir misiniz?"
    p = _resolve(path)
    if not p.exists():
        return f"Efendim, '{p}' bulunamadı."
    p.rename(p.parent / new_name)
    return f"Efendim, '{p.name}' → '{new_name}' olarak yeniden adlandırıldı."


def zip_files(parameters: dict, **_) -> str:
    source  = (parameters or {}).get("source", "").strip()
    output  = (parameters or {}).get("output", "").strip()
    if not source:
        return "Efendim, sıkıştırılacak dosya/klasörü belirtir misiniz?"
    s = _resolve(source)
    if not output:
        output = str(s.parent / (s.stem + ".zip"))
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as zf:
        if s.is_dir():
            for f in s.rglob("*"):
                zf.write(f, f.relative_to(s.parent))
        else:
            zf.write(s, s.name)
    return f"Efendim, '{output}' oluşturuldu."


def unzip_file(parameters: dict, **_) -> str:
    path = (parameters or {}).get("path", "").strip()
    dest = (parameters or {}).get("destination", "").strip()
    if not path:
        return "Efendim, zip dosyasını belirtir misiniz?"
    p = _resolve(path)
    d = Path(dest) if dest else p.parent / p.stem
    with zipfile.ZipFile(str(p), "r") as zf:
        zf.extractall(str(d))
    return f"Efendim, '{p.name}' → '{d}' çıkartıldı."


def list_files(parameters: dict, **_) -> str:
    path = (parameters or {}).get("path", str(Path.home() / "Desktop")).strip()
    p    = Path(path)
    if not p.exists():
        return f"Efendim, '{path}' bulunamadı."
    items = sorted(p.iterdir(), key=lambda x: (x.is_file(), x.name))[:20]
    lines = [f"{'📁' if i.is_dir() else '📄'} {i.name}" for i in items]
    return f"Efendim, '{p}' içeriği:\n" + "\n".join(lines)


def open_folder(parameters: dict, **_) -> str:
    path = (parameters or {}).get("path", str(Path.home() / "Desktop")).strip()
    p    = _resolve(path)
    if not p.exists():
        return f"Efendim, '{path}' bulunamadı."
    os.startfile(str(p))
    return f"Efendim, '{p.name}' klasörü açıldı."


def recent_files(parameters: dict, **_) -> str:
    recent = Path(os.getenv("APPDATA", "")) / "Microsoft" / "Windows" / "Recent"
    if not recent.exists():
        return "Efendim, son dosyalar bulunamadı."
    files = sorted(recent.glob("*.lnk"), key=lambda f: f.stat().st_mtime, reverse=True)[:10]
    names = [f.stem for f in files]
    return "Efendim, son açılan dosyalar:\n" + "\n".join(names)
