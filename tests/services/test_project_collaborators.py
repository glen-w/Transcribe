"""ProjectService collaborators and explicit load vs reconcile."""

from __future__ import annotations

from pathlib import Path

from transcribe.domain.models import OCRAttempt
from transcribe.ingest import IngestService
from transcribe.services.project import ProjectService, open_project_paths
from transcribe.services.project_dates import ProjectDateOps
from transcribe.services.project_declutter import ProjectDeclutter
from transcribe.services.project_review_repair import ProjectReviewRepair
from tests.conftest import FakeClock, SequentialIds
from tests.ingest.test_ingest import _png_bytes


def _svc(tmp_path: Path) -> ProjectService:
    paths = open_project_paths(tmp_path / "projects" / "nb")
    return ProjectService(paths, clock=FakeClock(), ids=SequentialIds())


def test_project_service_delegates_to_collaborators() -> None:
    src = Path("src/transcribe/services/project.py").read_text(encoding="utf-8")
    assert "class ProjectService" in src
    assert "self._dates = ProjectDateOps(self)" in src
    assert "self._review = ProjectReviewRepair(self)" in src
    assert "self._declutter = ProjectDeclutter(self)" in src
    assert "return self._dates.approve_page_date" in src
    assert "return self._review.repair_empty_successes" in src
    assert "return self._declutter.reapply_visual_declutter" in src


def test_load_documents_reconcile_as_explicit_write() -> None:
    doc = ProjectService.load.__doc__ or ""
    assert "reconcile=False" in doc
    assert "write" in doc.lower()
    assert "effective_text()" in doc
    assert ProjectService.reconcile_interrupted.__doc__


def test_load_without_reconcile_leaves_running_attempt(tmp_path: Path) -> None:
    projects = _svc(tmp_path)
    project = projects.create("Run")
    ingest = IngestService(projects.paths, clock=projects.clock, ids=projects.ids)
    project = ingest.import_bytes("a.png", _png_bytes())
    page_id = project.pages[0].page_id
    projects.record_generation(
        page_id,
        OCRAttempt(
            attempt_id="live",
            status="running",
            input_fingerprint="fp",
            fingerprint_payload={},
            raw_text=None,
            provenance=None,
            provider_metadata={},
            started_at="2026-01-01T00:00:00.000Z",
        ),
    )
    projects.load(reconcile=False)
    running = projects.load_page_result(page_id)
    assert running is not None
    assert running.active_attempt() is not None
    assert running.active_attempt().status == "running"

    projects.reconcile_interrupted()
    after = projects.load_page_result(page_id)
    assert after is not None
    assert after.active_attempt() is not None
    assert after.active_attempt().status == "interrupted"


def test_collaborator_types_bind_to_service(tmp_path: Path) -> None:
    projects = _svc(tmp_path)
    assert isinstance(projects._dates, ProjectDateOps)
    assert isinstance(projects._review, ProjectReviewRepair)
    assert isinstance(projects._declutter, ProjectDeclutter)
