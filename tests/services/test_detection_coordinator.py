"""DetectionRunCoordinator cancel and sequential detector runs (offline)."""

from __future__ import annotations

from pathlib import Path

from tests.conftest import FakeClock, SequentialIds
from tests.ingest.test_ingest import _png_bytes
from transcribe.detection.coordinator import DetectionProgress, DetectionRunCoordinator, _RunState
from transcribe.ingest import IngestService
from transcribe.services.project import ProjectService, open_project_paths


def _notebook(tmp_path: Path) -> ProjectService:
    paths = open_project_paths(tmp_path / "nb")
    clock, ids = FakeClock(), SequentialIds("det")
    projects = ProjectService(paths, clock=clock, ids=ids)
    projects.create("detect-nb")
    ingest = IngestService(paths, clock=clock, ids=ids)
    ingest.import_bytes("a.png", _png_bytes())
    ingest.import_bytes("b.png", _png_bytes())
    project = projects.load()
    for page in project.pages:
        projects.save_user_edit(page.page_id, "I think I know what I mean.")
    return projects


def test_pre_cancelled_loop_does_not_start_detectors(tmp_path: Path) -> None:
    projects = _notebook(tmp_path)
    coord = DetectionRunCoordinator(projects)
    state = _RunState(progress=DetectionProgress(status="running", total=2, message="go"))
    state.cancel_event.set()
    coord._run_loop(state, ["first_person", "swear_words"], None, True, False)
    assert state.progress.status == "cancelled"
    assert state.progress.outcomes == {}
    assert state.results == []


def test_lexical_run_completes_and_stop_is_idempotent(tmp_path: Path) -> None:
    projects = _notebook(tmp_path)
    coord = DetectionRunCoordinator(projects)
    coord.request_cancel()
    assert coord.get_progress().status == "idle"
    coord.start(["first_person"], force=True, auto_tag=False)
    thread = coord._run.thread if coord._run else None
    assert thread is not None
    thread.join(timeout=15)
    assert thread.is_alive() is False
    progress = coord.get_progress()
    assert progress.status == "completed"
    assert progress.outcomes.get("first_person")
    coord.request_cancel()
    assert coord.get_progress().status == "completed"
