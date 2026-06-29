"""
HULLAR dosya/medya skilleri.

  • buyuk_dosya  : en çok yer kaplayan dosyaları bulur
  • resim_boyut  : resmi küçültür / formatını değiştirir (jpg↔png)
  • resim_pdf    : bir klasördeki/verilen resimleri tek PDF yapar
  • video_gif    : videoyu GIF'e çevirir (ffmpeg)
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path


def _push(text: str):
    try:
        from .notify import push
        push(text)
    except Exception:
        pass


# ── En büyük dosyalar ─────────────────────────────────────────────────── #
def buyuk_dosya(parameters: dict | None = None) -> str:
    roots = [Path.home() / "Desktop", Path.home() / "Downloads",
             Path.home() / "Documents", Path.home() / "Videos"]
    files = []
    for root in roots:
        if not root.exists():
            continue
        for p in root.rglob("*"):
            try:
                if p.is_file():
                    files.append((p.stat().st_size, p))
            except Exception:
                continue
    if not files:
        return "Dosya bulunamadı."
    files.sort(reverse=True)
    lines = ["📦 En büyük dosyalar:"]
    for size, p in files[:8]:
        mb = size / (1024 * 1024)
        lines.append(f"• {p.name} — {mb:.0f} MB")
    return "\n".join(lines)


# ── Resim boyutlandır / format değiştir ───────────────────────────────── #
def resim_boyut(parameters: dict | None = None) -> str:
    p = parameters or {}
    yol = (p.get("path") or "").strip().strip('"')
    if not yol or not Path(yol).exists():
        return "Kullanım: 'resmi küçült C:\\yol\\foto.jpg' (yarıya indirir)"
    try:
        from PIL import Image  # type: ignore
        img = Image.open(yol)
        oran = float(p.get("oran", 0.5))
        hedef_fmt = p.get("format")
        src = Path(yol)
        if hedef_fmt:                       # format değiştir
            out = src.with_suffix("." + hedef_fmt.lower().replace("jpg", "jpeg"))
            img.convert("RGB").save(out)
            return f"🖼️ {src.name} → {out.name} ({hedef_fmt})."
        # küçült
        yeni = (int(img.width * oran), int(img.height * oran))
        out = src.with_name(src.stem + "_kucuk" + src.suffix)
        img.resize(yeni).save(out)
        return f"🖼️ {src.name} %{int(oran*100)} küçültüldü → {out.name}"
    except Exception as exc:
        return f"Resim işlenemedi: {exc}"


def _extract_resim_boyut(msg: str) -> dict:
    out = {}
    m = re.search(r"([A-Za-z]:\\[^\n]+\.(?:jpg|jpeg|png|bmp|webp))", msg, re.I)
    if m:
        out["path"] = m.group(1)
    for f in ("png", "jpg", "jpeg", "webp", "bmp"):
        if re.search(rf"\b{f}\b.*\b(yap|çevir|dönüştür)", msg, re.I):
            out["format"] = f
    o = re.search(r"%?\s*(\d{1,2})\s*(?:'?ye|ya)?\s*(?:küçült|indir)", msg, re.I)
    if o:
        out["oran"] = int(o.group(1)) / 100
    return out


# ── Resimleri PDF yap ─────────────────────────────────────────────────── #
def resim_pdf(parameters: dict | None = None) -> str:
    p = parameters or {}
    yol = (p.get("path") or "").strip().strip('"')
    src = Path(yol) if yol else None
    try:
        from PIL import Image  # type: ignore
        if src and src.is_dir():
            imgs = sorted([x for x in src.glob("*")
                           if x.suffix.lower() in (".jpg", ".jpeg", ".png", ".bmp", ".webp")])
            klasor = src
        elif src and src.is_file():
            imgs = [src]
            klasor = src.parent
        else:
            return "Kullanım: 'resimleri pdf yap C:\\klasör' (klasördeki resimler)"
        if not imgs:
            return "Klasörde resim bulunamadı."
        pages = [Image.open(i).convert("RGB") for i in imgs]
        out = klasor / "resimler.pdf"
        pages[0].save(out, save_all=True, append_images=pages[1:])
        return f"📄 {len(pages)} resim → {out}"
    except Exception as exc:
        return f"PDF yapılamadı: {exc}"


def _extract_path(msg: str) -> dict:
    m = re.search(r"([A-Za-z]:\\[^\n]+)", msg)
    return {"path": m.group(1).strip().strip('\"') if m else ""}


# ── Video → GIF (ffmpeg) ──────────────────────────────────────────────── #
def video_gif(parameters: dict | None = None) -> str:
    p = parameters or {}
    yol = (p.get("path") or "").strip().strip('"')
    if not yol or not Path(yol).exists():
        return "Kullanım: 'video gif yap C:\\yol\\video.mp4'"
    try:
        src = Path(yol)
        out = src.with_suffix(".gif")
        sure = int(p.get("sure", 6))
        # ilk N sn, 480px genişlik, 12 fps
        cmd = (f'ffmpeg -y -t {sure} -i "{src}" '
               f'-vf "fps=12,scale=480:-1:flags=lanczos" "{out}"')
        subprocess.run(cmd, shell=True, capture_output=True, timeout=120)
        if out.exists():
            return f"🎞️ GIF hazır: {out}"
        return "GIF yapılamadı (ffmpeg hatası)."
    except Exception as exc:
        return f"Hata: {exc}"


def _extract_video_gif(msg: str) -> dict:
    out = _extract_path(msg)
    s = re.search(r"(\d+)\s*(?:saniye|sn)", msg, re.I)
    if s:
        out["sure"] = int(s.group(1))
    return out
