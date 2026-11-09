"""Defer OCR for chronic fingerprint-compatible token_repeat failures."""

from __future__ import annotations

from pathlib import Path

from transcribe.ingest import IngestService
from transcribe.services.job import (
    TOKEN_REPEAT_DEFER_THRESHOLD,
    JobCoordinator,
)
from transcribe.services.project import ProjectService, open_project_paths
from tests.conftest import FakeClock, SequentialIds
from tests.fakes import FakeVisionOCRProvider
from tests.ingest.test_ingest import _png_bytes


def _project_with_one_page(tmp_path: Path):
    paths = open_project_paths(tmp_path / "proj")
    clock, ids = FakeClock(), SequentialIds()
    projects = ProjectService(paths, clock=clock, ids=ids)
    projects.create("defer")
    ingest = IngestService(paths, clock=clock, ids=ids)
    ingest.import_bytes("p0.png", _png_bytes(color=(5, 15, 25)))
    project = projects.load()
    settings = project.settings
    settings.model_name = "fake-vision"
    projects.save_settings(project, settings)
    return paths, projects, clock, ids, project


def test_third_token_repeat_then_non_force_skips(tmp_path: Path):
    paths, projects, clock, ids, project = _project_with_one_page(tmp_path)
    page_id = project.pages[0].page_id
    for _ in range(TOKEN_REPEAT_DEFER_THRESHOLD):
        provider = FakeVisionOCRProvider(
            fail_codes=["token_repeat"],
            digest="digest-aaa",
            verified=True,
        )
        coord = JobCoordinator(paths, projects, provider, clock=clock, ids=ids)
        progress = coord.run_blocking(page_ids=[page_id], force=True)
        assert progress.failed == 1

    provider = FakeVisionOCRProvider(digest="digest-aaa", verified=True)
    coord = JobCoordinator(paths, projects, provider, clock=clock, ids=ids)
    progress = coord.run_blocking(page_ids=[page_id])
    assert provider.calls == 0
    assert progress.skipped == 1
    assert "deferred" in progress.message.lower()


def test_force_bypasses_defer(tmp_path: Path):
    paths, projects, clock, ids, project = _project_with_one_page(tmp_path)
    page_id = project.pages[0].page_id
    calls = 0
    for _ in range(TOKEN_REPEAT_DEFER_THRESHOLD):
        provider = FakeVisionOCRProvider(
            fail_codes=["token_repeat"],
            digest="digest-aaa",
            verified=True,
        )
        coord = JobCoordinator(paths, projects, provider, clock=clock, ids=ids)
        coord.run_blocking(page_ids=[page_id], force=True)
        calls += provider.calls

    provider = FakeVisionOCRProvider(digest="digest-aaa", verified=True)
    coord = JobCoordinator(paths, projects, provider, clock=clock, ids=ids)
    coord.run_blocking(page_ids=[page_id], force=True)
    assert provider.calls == 1
    assert calls == TOKEN_REPEAT_DEFER_THRESHOLD


def test_prompt_change_after_three_repeats_reruns(tmp_path: Path):
    paths, projects, clock, ids, project = _project_with_one_page(tmp_path)
    page_id = project.pages[0].page_id
    for _ in range(TOKEN_REPEAT_DEFER_THRESHOLD):
        provider = FakeVisionOCRProvider(
            fail_codes=["token_repeat"],
            digest="digest-aaa",
            verified=True,
        )
        coord = JobCoordinator(paths, projects, provider, clock=clock, ids=ids)
        coord.run_blocking(page_ids=[page_id], force=True)

    settings = projects.load().settings
    settings.custom_prompt = "Different prompt for defer break."
    projects.save_settings(projects.load(), settings)

    provider = FakeVisionOCRProvider(digest="digest-aaa", verified=True)
    coord = JobCoordinator(paths, projects, provider, clock=clock, ids=ids)
    progress = coord.run_blocking(page_ids=[page_id])
    assert provider.calls == 1
    assert progress.skipped == 0


def test_compatible_success_still_skips_not_defers(tmp_path: Path):
    paths, projects, clock, ids, project = _project_with_one_page(tmp_path)
    page_id = project.pages[0].page_id
    provider = FakeVisionOCRProvider(digest="digest-aaa", verified=True)
    coord = JobCoordinator(paths, projects, provider, clock=clock, ids=ids)
    coord.run_blocking(page_ids=[page_id])
    assert provider.calls == 1
    progress = coord.run_blocking(page_ids=[page_id])
    assert provider.calls == 1
    assert progress.skipped == 1
