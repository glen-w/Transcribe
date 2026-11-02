#!/usr/bin/env python3
"""Seed a throwaway workspace with a synthetic diary notebook for documentation media.

Everything here is invented: page images are rendered text on lined paper, the two
"OCR models" are canned strings (no Ollama), and dates/tags are fixed. Safe to publish.

Usage:
    python scripts/docs/seed_demo_workspace.py /tmp/transcribe-docs-ws
"""

from __future__ import annotations

import random
import sys
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from transcribe.domain.dates import ApproximateDate
from transcribe.domain.models import AttemptProvenance, OCRAttempt
from transcribe.ingest import IngestService
from transcribe.ports import SystemClock, UuidGenerator
from transcribe.services.project import ProjectService, open_project_paths

TITLE = "Field notebook 2026"

# (date, tags, text as written, model-b variant with a couple of plausible misreads)
PAGES: list[tuple[ApproximateDate, list[str], str, str]] = [
    (
        ApproximateDate(2026, 3, 2),
        ["garden"],
        "Monday 2 March. Frost on the beds again.\nSowed leeks under glass and\nlabelled every tray twice.\nBlackbird singing by half six.",
        "Monday 2 March. Frost on the beds again.\nSowed leeks under glass and\nlabelled every tray twice.\nBlackbird singing by half six.",
    ),
    (
        ApproximateDate(2026, 3, 3),
        ["garden", "weather"],
        "Tuesday. Rain all morning.\nRepaired the cold frame hinge.\nList: twine, canes, seed compost,\nsomething for the slugs.",
        "Tuesday. Rain all morning.\nRepaired the cold frame hinge.\nList: twine, canes, seed compost,\nsomething for the slugs.",
    ),
    (
        ApproximateDate(2026, 3, 5),
        ["walks"],
        "Thursday. Long walk to the canal.\nHeron on the lock gate, very still.\nCame home by the allotments and\ntalked beans with Mr Okafor.",
        "Thursday. Long walk to the canal.\nHeron on the lock gate, very still.\nCame home by the allotments and\ntalked beans with Mr Okafor.",
    ),
    (
        ApproximateDate(2026, 3, 9),
        ["garden", "weather"],
        "Monday 9 March. First warm day.\nPotted on the tomatoes and moved\nthe cold frame south.\nBees on the crocus at last.",
        "Monday 9 March. First warm day.\nPolled on the tomatoes and moved\nthe cold frame south.\nBees on the crocns at last.",
    ),
    (
        # Out of order on purpose: dated before its neighbours (shows date repair).
        ApproximateDate(2026, 3, 4),
        ["weather"],
        "Wednesday. Wrote this one late.\nSleet at dusk, then a clear sky.\nTurned the compost and found\nthree sleepy toads.",
        "Wednesday. Wrote this one late.\nSleet at dusk, then a clear sky.\nTurned the compost and found\nthree sleepy toads.",
    ),
    (
        ApproximateDate(2026, 3, 12),
        ["walks", "todo"],
        "Thursday 12th. Bus into town.\nTo do: library books, stamps,\nbirthday card for Aunt Mira,\nbuy a new notebook (this is nearly full).",
        "Thursday 12th. Bus into town.\nTo do: library books, stamps,\nbirthday card for Aunt Mina,\nbuy a new notebook (this is nearly full).",
    ),
]

_FONT_CANDIDATES = [
    "/System/Library/Fonts/Noteworthy.ttc",
    "/System/Library/Fonts/Supplemental/SnellRoundhand.ttc",
    "/System/Library/Fonts/MarkerFelt.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]


def _font(size: int) -> ImageFont.ImageFont:
    for cand in _FONT_CANDIDATES:
        if Path(cand).is_file():
            try:
                return ImageFont.truetype(cand, size)
            except OSError:
                continue
    return ImageFont.load_default()


def render_page(text: str, seed: int) -> bytes:
    """Render a lined notebook page with handwriting-ish text."""
    rng = random.Random(seed)
    w, h = 900, 1200
    img = Image.new("RGB", (w, h), (247, 243, 232))
    draw = ImageDraw.Draw(img)
    # Margin rule + ruled lines.
    draw.line([(110, 0), (110, h)], fill=(214, 120, 120), width=2)
    for y in range(150, h - 60, 64):
        draw.line([(40, y), (w - 40, y)], fill=(186, 200, 214), width=2)
    font = _font(46)
    y = 96
    for line in text.splitlines():
        x = 132 + rng.randint(-4, 6)
        draw.text((x, y + rng.randint(-3, 3)), line, font=font, fill=(32, 36, 78))
        y += 64
    # Light scan noise so the page reads as a photograph rather than a render.
    pixels = img.load()
    for _ in range(9000):
        px, py = rng.randrange(w), rng.randrange(h)
        v = rng.randint(-10, 6)
        r, g, b = pixels[px, py]
        pixels[px, py] = (max(0, r + v), max(0, g + v), max(0, b + v))
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _attempt(aid: str, text: str, model: str, started: str, page_n: int) -> OCRAttempt:
    return OCRAttempt(
        attempt_id=aid,
        status="succeeded",
        input_fingerprint=f"fp-{aid}",
        fingerprint_payload={},
        raw_text=text,
        provenance=AttemptProvenance(
            model_name=model,
            model_digest="d" * 64,
            model_identity_verified=True,
            prompt_id="faithful_markdown",
            prompt_version="1",
            prompt_sha256="a" * 64,
            prompt_text="Transcribe faithfully.",
            input_sha256="b" * 64,
            preprocess_profile="none",
            preprocess_version=1,
            generation_options={},
            application_version="1.1.0",
            ollama_host="http://localhost:11434",
            request_id=aid,
            render_id=f"r{page_n}",
        ),
        provider_metadata={},
        started_at=started,
        completed_at=started,
        attempt_kind="vision",
    )


def seed(workspace: Path) -> Path:
    projects_dir = workspace / "projects"
    projects_dir.mkdir(parents=True, exist_ok=True)
    root = projects_dir / "field-notebook-2026"
    if root.exists():
        raise SystemExit(f"refusing to overwrite existing notebook: {root}")
    paths = open_project_paths(root)
    clock, ids = SystemClock(), UuidGenerator()
    svc = ProjectService(paths, clock=clock, ids=ids)
    svc.create(TITLE)
    ingest = IngestService(paths, clock=clock, ids=ids, visual_declutter_enabled=False)
    for i, (_date, _tags, text, _alt) in enumerate(PAGES, start=1):
        ingest.import_bytes(f"page_{i:02d}.png", render_page(text, seed=i))
    project = svc.load(reconcile=False)
    for i, (page, (date, tags, text, alt)) in enumerate(zip(project.pages, PAGES, strict=True), 1):
        svc.record_generation(
            page.page_id,
            _attempt(f"a{i}-glm", text, "glm-ocr:latest", f"2026-03-20T10:0{i}:00+00:00", i),
            activate=True,
        )
        svc.record_generation(
            page.page_id,
            _attempt(
                f"a{i}-granite", alt, "granite3.2-vision:latest", f"2026-03-20T11:0{i}:00+00:00", i
            ),
            activate=False,
        )
        svc.approve_page_date(page.page_id, date)
        svc.update_page_metadata(page.page_id, tags=tags)
    # Mark the first three reviewed (via a saved edit); leave the rest in the queue.
    for page, (_d, _g, text, _a) in list(zip(project.pages, PAGES, strict=True))[:3]:
        svc.save_user_edit(page.page_id, text, mark_reviewed=True)
    svc.set_page_review_status(project.pages[4].page_id, "needs_attention")
    return root


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    root = seed(Path(argv[1]).expanduser().resolve())
    print(root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
