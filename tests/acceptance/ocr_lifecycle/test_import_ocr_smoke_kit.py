"""Import -> OCR smoke kit (design: docs/dev/smoke_kit_import_ocr.md).

Offline stub vision only — no Ollama, no GPU. Proves the kit's acceptance:
human corrections survive re-OCR, and whitespace output is a miss on the
Review Failed OCR queue (``empty_output``), never a successful read.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from transcribe.ingest import IngestService
from transcribe.services.job import JobCoordinator
from transcribe.services.project import ProjectService, open_project_paths
from tests.conftest import FakeClock, SequentialIds
from tests.fakes import FakeVisionOCRProvider
from tests.ingest.test_ingest import _png_bytes

pytestmark = pytest.mark.smoke


def _kit(tmp_path: Path, provider: FakeVisionOCRProvider):
    paths = open_project_paths(tmp_path / "proj")
    clock, ids = FakeClock(), SequentialIds("kit")
    projects = ProjectService(paths, clock=clock, ids=ids)
    projects.create("smoke-kit")
    ingest = IngestService(paths, clock=clock, ids=ids)
    ingest.import_bytes("page.png", _png_bytes())
    project = projects.load()
    settings = project.settings
    settings.model_name = "fake-vision"
    projects.save_settings(project, settings)
    coord = JobCoordinator(paths, projects, provider, clock=clock, ids=ids)
    return paths, projects, coord


def test_correction_survives_reocr(tmp_path: Path):
    provider = FakeVisionOCRProvider(
        text_by_call=["stub reading one", "stub reading two"],
        digest="digest-aaa",
        verified=True,
    )
    _paths, projects, coord = _kit(tmp_path, provider)
    progress = coord.run_blocking(force=True)
    assert progress.status == "completed"
    page = projects.load().pages[0]
    result = projects.load_page_result(page.page_id)
    assert result is not None
    assert result.effective_text() == "stub reading one"

    projects.save_user_edit(page.page_id, "human corrected text")
    progress = coord.run_blocking(force=True)
    assert progress.status == "completed"
    result = projects.load_page_result(page.page_id)
    assert result is not None
    # Raw OCR may update its own attempt; the human correction still wins.
    assert result.edited_text == "human corrected text"
    assert result.effective_text() == "human corrected text"
    assert provider.calls == 2


def test_whitespace_output_is_a_miss_not_a_success(tmp_path: Path):
    provider = FakeVisionOCRProvider(
        text_by_call=["   "],
        digest="digest-aaa",
        verified=True,
    )
    _paths, projects, coord = _kit(tmp_path, provider)
    coord.run_blocking(force=True)
    page = projects.load().pages[0]
    result = projects.load_page_result(page.page_id)
    assert result is not None
    assert result.status == "failed"
    assert result.attempts
    assert result.attempts[-1].error is not None
    assert result.attempts[-1].error.code == "empty_output"
