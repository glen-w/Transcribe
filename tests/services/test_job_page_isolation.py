"""JobCoordinator per-page failure isolation and mid-run cancel (offline)."""

from __future__ import annotations

from pathlib import Path

from transcribe.ingest import IngestService
from transcribe.services.job import JobCoordinator
from transcribe.services.project import ProjectService, open_project_paths
from tests.conftest import FakeClock, SequentialIds
from tests.fakes import FakeVisionOCRProvider
from tests.ingest.test_ingest import _png_bytes


def _project_with_pages(tmp_path: Path, n: int):
    paths = open_project_paths(tmp_path / "proj")
    clock, ids = FakeClock(), SequentialIds()
    projects = ProjectService(paths, clock=clock, ids=ids)
    projects.create("isolation")
    ingest = IngestService(paths, clock=clock, ids=ids)
    for i in range(n):
        ingest.import_bytes(f"p{i}.png", _png_bytes(color=(i * 20, 10, 5)))
    project = projects.load()
    settings = project.settings
    settings.model_name = "fake-vision"
    projects.save_settings(project, settings)
    return paths, projects, clock, ids


def test_one_page_failure_does_not_block_later_pages(tmp_path: Path) -> None:
    paths, projects, clock, ids = _project_with_pages(tmp_path, 3)
    # First call fails (non-circuit), remaining succeed.
    provider = FakeVisionOCRProvider(
        fail_codes=["http_error", "", ""],
        digest="digest-aaa",
        verified=True,
    )
    coord = JobCoordinator(paths, projects, provider, clock=clock, ids=ids)
    progress = coord.run_blocking(force=True)
    assert progress.status == "completed"
    assert progress.failed == 1
    assert progress.completed == 2
    assert provider.calls == 3
    statuses = []
    for page in projects.load().pages:
        result = projects.load_page_result(page.page_id)
        assert result is not None
        statuses.append(result.status)
    assert statuses.count("failed") == 1
    assert statuses.count("succeeded") == 2


def test_cancel_stops_after_current_page(tmp_path: Path) -> None:
    paths, projects, clock, ids = _project_with_pages(tmp_path, 4)
    coord = JobCoordinator(
        paths, projects, FakeVisionOCRProvider(), clock=clock, ids=ids
    )

    class CancelAfterFirst(FakeVisionOCRProvider):
        def transcribe_image(self, **kwargs):
            result = super().transcribe_image(**kwargs)
            if self.calls == 1:
                coord.request_cancel()
            return result

    provider = CancelAfterFirst(digest="digest-aaa", verified=True)
    coord.provider = provider
    progress = coord.run_blocking(force=True)
    assert progress.status == "cancelled"
    assert provider.calls == 1
    assert progress.completed == 1
    succeeded = 0
    for page in projects.load().pages:
        result = projects.load_page_result(page.page_id)
        if result is not None and result.status == "succeeded":
            succeeded += 1
    assert succeeded == 1
