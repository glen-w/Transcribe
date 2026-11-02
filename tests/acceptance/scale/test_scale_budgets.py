"""Synthetic scale budgets (nightly `scale` lane; excluded from default suite).

Builds a 25-notebook / 500-page workspace with stub text (no Ollama, no GPU)
and asserts Archive search/listing stay inside generous wall-clock budgets.
Budgets are regression guards, not benchmarks: they are set well above a
healthy run so only real blow-ups fail.
"""

from __future__ import annotations

import time
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image

from transcribe.ingest import IngestService
from transcribe.runtime_paths import RuntimePaths
from transcribe.services.archive import ArchiveFilters, ArchiveService
from transcribe.services.project import ProjectService, open_project_paths
from tests.conftest import FakeClock, SequentialIds

pytestmark = pytest.mark.scale

NOTEBOOKS = 25
PAGES_PER_NOTEBOOK = 20
SEARCH_BUDGET_S = 20.0
LIST_BUDGET_S = 20.0


def _png_bytes() -> bytes:
    img = Image.new("RGB", (24, 24), (200, 200, 200))
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _runtime(tmp_path: Path) -> RuntimePaths:
    runtime = RuntimePaths(
        repo_root=tmp_path,
        data_dir=tmp_path / "data",
        projects_dir=tmp_path / "projects",
        inbox_dir=tmp_path / "inbox",
        export_dir=tmp_path / "exports",
    )
    runtime.ensure_layout()
    return runtime


def test_archive_search_and_listing_at_scale(tmp_path: Path, monkeypatch):
    _assert_archive_budget(tmp_path, monkeypatch, notebooks=NOTEBOOKS, pages=PAGES_PER_NOTEBOOK)


@pytest.mark.slow
@pytest.mark.timeout(300)
def test_archive_search_and_listing_at_nightly_scale(tmp_path: Path, monkeypatch):
    """100 notebooks x 40 pages. Nightly only (`slow` keeps it out of the PR suite)."""
    _assert_archive_budget(tmp_path, monkeypatch, notebooks=100, pages=40)


def _assert_archive_budget(tmp_path: Path, monkeypatch, *, notebooks: int, pages: int) -> None:
    runtime = _runtime(tmp_path)
    monkeypatch.setenv("TRANSCRIBE_DATA_DIR", str(runtime.data_dir))
    monkeypatch.setenv("TRANSCRIBE_PROJECTS_DIR", str(runtime.projects_dir))
    clock, ids = FakeClock(), SequentialIds("scale")
    png = _png_bytes()
    for nb in range(notebooks):
        root = runtime.projects_dir / f"nb{nb:02d}"
        paths = open_project_paths(root)
        projects = ProjectService(paths, clock=clock, ids=ids)
        projects.create(f"Notebook {nb}")
        ingest = IngestService(paths, clock=clock, ids=ids)
        for _ in range(pages):
            ingest.import_bytes("p.png", png)
        project = projects.load()
        for i, page in enumerate(project.pages):
            projects.save_user_edit(
                page.page_id,
                f"Notebook {nb} page {i} common diary text about travel and Anna in Paris.",
            )

    service = ArchiveService(runtime)
    start = time.monotonic()
    result = service.search("Anna", filters=ArchiveFilters(people=("Anna",)))
    search_s = time.monotonic() - start
    # No published NER at scale-fixture level: entity prefilter matches nothing,
    # but the plain text search must find every page mentioning Anna.
    assert result.total_matched == 0
    plain = service.search("Anna")
    assert plain.total_matched == notebooks * pages
    assert search_s < SEARCH_BUDGET_S

    start = time.monotonic()
    listed = service.list_notebooks()
    list_s = time.monotonic() - start
    assert len(listed) == notebooks
    assert all(item.page_count == pages for item in listed)
    assert list_s < LIST_BUDGET_S
