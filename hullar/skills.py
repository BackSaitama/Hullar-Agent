"""
HULLAR — Skill indeksleyici.

Birden çok klasördeki SKILL.md / *.md dosyalarını tarar, her birinden
SADECE isim + tek satır açıklama çıkarır. Tüm içeriği değil — böylece
AI'a verilen sistem promptu küçük kalır (token tasarrufu).

Taranan yerler:
  - rat/skills              (31 otomasyon skill'i)
  - kök kuralları           (FOCUS.md, AGENT.md)
  - Hermes skills           (AppData/Local/hermes/skills)
  - hermes-skill-factory    (Desktop/hermes-skill-factory-master/skills)

Sonuç bir kez taranır ve bellekte tutulur.
"""

from __future__ import annotations

import re
from pathlib import Path

# ── Taranacak skill kökleri ───────────────────────────────────────────── #
_HOME = Path.home()
_DESKTOP = _HOME / "Desktop"

SKILL_DIRS = [
    _DESKTOP / "rat" / "skills",
    _HOME / "AppData" / "Local" / "hermes" / "skills",
    _DESKTOP / "hermes-skill-factory-master" / "skills",
]

# Kök kural dosyaları (kısa, tam yüklenir ama kırpılır)
RULE_FILES = [
    _DESKTOP / "rat" / "FOCUS.md",
    _DESKTOP / "rat" / "AGENT.md",
]

_MAX_RULE_CHARS = 1200   # her kural dosyasından en çok bu kadar karakter


def _parse_skill_md(path: Path) -> tuple[str, str] | None:
    """Bir SKILL.md/*.md dosyasından (isim, açıklama) çıkarır."""
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return None

    name = ""
    desc = ""

    # YAML frontmatter (--- name: ... description: ... ---)
    fm = re.match(r"^---\s*\n(.*?)\n---", text, re.S)
    if fm:
        block = fm.group(1)
        n = re.search(r"^name:\s*(.+)$", block, re.M)
        d = re.search(r"^description:\s*(.+)$", block, re.M)
        if n:
            name = n.group(1).strip().strip("\"'")
        if d:
            desc = d.group(1).strip().strip("\"'")

    # Frontmatter yoksa: ilk başlık + ilk anlamlı satır
    if not name:
        h = re.search(r"^#\s+(.+)$", text, re.M)
        name = h.group(1).strip() if h else path.parent.name

    if not desc:
        # İlk başlık olmayan, boş olmayan satır
        for line in text.splitlines():
            s = line.strip()
            if s and not s.startswith("#") and not s.startswith("---"):
                desc = s
                break

    # Açıklamayı tek satıra indir, kısalt
    desc = re.sub(r"\s+", " ", desc)[:120]
    return (name or path.parent.name, desc)


def _scan_dir(root: Path) -> list[tuple[str, str]]:
    """Bir kök altındaki tüm SKILL.md ve doğrudan *.md dosyalarını bulur."""
    found: list[tuple[str, str]] = []
    if not root.exists():
        return found

    # Alt klasörlerdeki SKILL.md
    for md in root.glob("*/SKILL.md"):
        parsed = _parse_skill_md(md)
        if parsed:
            found.append(parsed)

    # İki kademe alt (skill-factory/skill-factory/SKILL.md gibi)
    for md in root.glob("*/*/SKILL.md"):
        parsed = _parse_skill_md(md)
        if parsed:
            found.append(parsed)

    # Doğrudan klasör altında numaralı skill klasörleri (rat/skills/01-...)
    for sub in root.iterdir():
        if sub.is_dir():
            md = sub / "SKILL.md"
            if md.exists():
                continue  # zaten yukarıda yakalandı
            # SKILL.md yoksa klasördeki ilk .md'yi dene
            mds = list(sub.glob("*.md"))
            if mds:
                parsed = _parse_skill_md(mds[0])
                if parsed:
                    found.append(parsed)
    return found


_CACHE: str | None = None


def build_index() -> str:
    """Tüm skill'leri tarayıp kompakt bir metin indeksi döndürür."""
    global _CACHE
    if _CACHE is not None:
        return _CACHE

    seen: set[str] = set()
    lines: list[str] = []

    for root in SKILL_DIRS:
        items = _scan_dir(root)
        for name, desc in items:
            key = name.lower()
            if key in seen:
                continue
            seen.add(key)
            if desc:
                lines.append(f"- {name}: {desc}")
            else:
                lines.append(f"- {name}")

    index = "\n".join(sorted(lines))
    _CACHE = index
    return index


def load_rules() -> str:
    """Kök kural dosyalarını (FOCUS, AGENT) kısaltarak yükler."""
    chunks: list[str] = []
    for rf in RULE_FILES:
        if rf.exists():
            try:
                txt = rf.read_text(encoding="utf-8", errors="ignore").strip()
                if txt:
                    chunks.append(f"### {rf.name}\n{txt[:_MAX_RULE_CHARS]}")
            except Exception:
                pass
    return "\n\n".join(chunks)


def count() -> int:
    return len([l for l in build_index().splitlines() if l.strip()])


if __name__ == "__main__":
    idx = build_index()
    print(idx)
    print(f"\n--- Toplam {count()} skill indekslendi ---")
