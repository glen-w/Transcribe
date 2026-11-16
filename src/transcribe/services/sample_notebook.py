"""Install the bundled sample notebook into the projects directory (U2.2)."""

from __future__ import annotations

import io
import json
import shutil
import tempfile
from importlib import resources
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

from transcribe.errors import ProjectError
from transcribe.ingest import IngestService
from transcribe.ports import Clock, IdGenerator, SystemClock, UuidGenerator
from transcribe.runtime_paths import RuntimePaths
from transcribe.services.project import ProjectService, open_project_paths

SAMPLE_SLUG = "sample-notebook"
SAMPLE_TITLE = "Sample notebook"


def load_sample_manifest() -> dict[str, Any]:
    """Read the packaged sample manifest (works from a wheel and a checkout)."""
    try:
        raw = (
            resources.files("transcribe.samples")
            .joinpath("demo-notebook", "manifest.json")
            .read_text(encoding="utf-8")
        )
        manifest = json.loads(raw)
    except (OSError, ModuleNotFoundError, ValueError) as exc:
        raise ProjectError(
            "The bundled sample notebook is missing or unreadable in this install. "
            "Create a notebook and import your own pages instead."
        ) from exc
    if not isinstance(manifest, dict) or not isinstance(manifest.get("pages"), list):
        raise ProjectError("The bundled sample notebook manifest is not valid.")
    return manifest


def _placeholder_png(label: str, *, size: tuple[int, int] = (640, 480)) -> bytes:
    img = Image.new("RGB", size, (245, 242, 235))
    draw = ImageDraw.Draw(img)
    draw.rectangle([24, 24, size[0] - 24, size[1] - 24], outline=(60, 60, 60), width=2)
    draw.text((40, 40), label, fill=(30, 30, 30))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def install_sample_notebook(
    runtime: RuntimePaths,
    *,
    clock: Clock | None = None,
    ids: IdGenerator | None = None,
    force: bool = False,
) -> Path:
    """Create the sample in ``runtime.projects_dir`` and return the project root.

    Uses existing ``ProjectService.create`` + ``IngestService.import_bytes`` and
    seeds ``edited_text`` so deterministic Analyse modules run without OCR.
    Placeholder pages are generated in memory, so nothing is written into the
    install. The notebook is built in a hidden sibling folder and renamed into
    place, so an interrupted install never leaves a half-built notebook.
    """
    clock = clock or SystemClock()
    ids = ids or UuidGenerator()
    manifest = load_sample_manifest()
    dest = runtime.projects_dir / SAMPLE_SLUG
    if dest.exists() and not force:
        if not (dest / "project.json").is_file():
            raise ProjectError(
                f"A folder named {SAMPLE_SLUG!r} already exists in your notebooks "
                "folder but is not a notebook. Rename or remove it, then open the "
                "sample again."
            )
        # Already installed — return existing root.
        return dest

    runtime.projects_dir.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{SAMPLE_SLUG}-", dir=runtime.projects_dir))
    try:
        paths = open_project_paths(staging)
        projects = ProjectService(paths, clock=clock, ids=ids)
        projects.create(str(manifest.get("title") or SAMPLE_TITLE))
        ingest = IngestService(paths, clock=clock, ids=ids)
        rows = [row for row in manifest["pages"] if isinstance(row, dict)]
        for i, row in enumerate(rows, start=1):
            name = Path(str(row.get("file") or f"page_{i:02d}.png")).name
            ingest.import_bytes(name, _placeholder_png(f"Sample page {i}"))
        project = projects.load()
        for page, row in zip(project.pages, rows, strict=False):
            text = str(row.get("text") or "").strip()
            if text:
                projects.save_user_edit(page.page_id, text)
        if dest.exists():
            shutil.rmtree(dest)
        staging.chmod(0o755)  # mkdtemp is 0700; match ordinary notebook folders
        staging.replace(dest)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return dest
