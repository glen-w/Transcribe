"""User-supplied export body fonts (workspace-local files).

Files live under ``data/config/fonts/``. A registered font yields a
``custom:<Family>`` body-font key usable in ExportTypography; HTML/EPUB CSS
references the family name. The stored file is kept for portability and is
never executed or parsed beyond a header sniff. See export contract notes.
"""

from __future__ import annotations

import re
from pathlib import Path

from transcribe.runtime_paths import RuntimePaths, build_runtime_paths

MAX_FONT_BYTES = 5 * 1024 * 1024
ALLOWED_SUFFIXES = frozenset({".ttf", ".otf", ".woff", ".woff2"})
_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _slug(name: str) -> str:
    slug = _SLUG_RE.sub("-", name.lower()).strip("-")
    return slug[:48] or "font"


def fonts_dir(runtime: RuntimePaths | None = None) -> Path:
    rt = runtime or build_runtime_paths()
    return rt.data_dir / "config" / "fonts"


def register_custom_font(
    name: str,
    data: bytes,
    *,
    suffix: str,
    runtime: RuntimePaths | None = None,
) -> str:
    """Store a font file and return its ``custom:<name>`` body-font key."""
    family = " ".join(str(name).split()).strip().strip('"').strip("'")
    if not family:
        raise ValueError("custom font requires a family name")
    if suffix.lower() not in ALLOWED_SUFFIXES:
        raise ValueError(f"unsupported font type {suffix!r}; use .ttf/.otf/.woff/.woff2")
    if not data or len(data) > MAX_FONT_BYTES:
        raise ValueError("font file is empty or larger than 5 MiB")
    directory = fonts_dir(runtime)
    directory.mkdir(parents=True, exist_ok=True)
    dest = directory / f"{_slug(family)}{suffix.lower()}"
    tmp = dest.with_suffix(dest.suffix + ".tmp")
    tmp.write_bytes(data)
    tmp.replace(dest)
    return f"custom:{family[:60]}"


def list_custom_fonts(runtime: RuntimePaths | None = None) -> list[str]:
    directory = fonts_dir(runtime)
    if not directory.exists():
        return []
    return sorted(p.name for p in directory.iterdir() if p.suffix.lower() in ALLOWED_SUFFIXES)


__all__ = ["fonts_dir", "list_custom_fonts", "register_custom_font"]
