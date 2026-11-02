"""1.3 durability and OCR-truth gates (offline)."""

from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image

from transcribe.declutter import apply_declutter
from transcribe.domain.models import (
    AttemptError,
    AttemptProvenance,
    CleanupRecord,
    OCRAttempt,
    PageResult,
)
from transcribe.errors import BackupError
from transcribe.persistence.atomic import read_json, write_json_atomic
from transcribe.services.archive import ArchiveFilters, ArchiveService
from transcribe.services.batch_metadata import apply_batch_metadata
from transcribe.services.export import ExportService
from transcribe.services.format_census import run_format_census
from transcribe.services.job import build_coordinator
from transcribe.services.job_outcome import classify_job_outcome, retry_failed_page_ids
from transcribe.services.project import ProjectService, open_project_paths
from transcribe.services.quality import build_scoreboard
from transcribe.services.reading_marks import ReadingMarksStore
from transcribe.services.workspace_backup import BackupOptions, WorkspaceBackupService
from tests.conftest import FakeClock, SequentialIds
from tests.fakes import FakeVisionOCRProvider
from tests.services.test_archive import _make_notebook, _runtime


def _provenance(name: str = "glm-ocr", digest: str = "abc") -> AttemptProvenance:
    return AttemptProvenance(
        model_name=name,
        model_digest=digest,
        model_identity_verified=True,
        prompt_id="p",
        prompt_version="1",
        prompt_sha256="s",
        prompt_text="read",
        input_sha256="i",
        preprocess_profile="none",
        preprocess_version=1,
        generation_options={},
        application_version="1.3.0",
        ollama_host="http://127.0.0.1:11434",
        request_id="r",
        render_id="render",
    )


def test_scoreboard_scores_corrections_not_the_quality_file(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    root, projects = _make_notebook(
        runtime, "nb", title="Diary", page_specs=[{"text": "helo"}]
    )
    project = projects.load()
    page_id = project.pages[0].page_id
    paths = open_project_paths(root)
    result = projects.load_page_result(page_id)
    assert result is not None
    result.edited_text = "hello"
    result.attempts[0].provenance = _provenance()
    result.attempts[0].cleanup = CleanupRecord(
        execution_status="provider_ok",
        acceptance_status="applied",
        model_name="cleanup-model",
        model_digest="clean",
        pre_cleanup_text="helo",
    )
    result.attempts[0].raw_text = "hello"
    write_json_atomic(paths.result_path(page_id), result.as_dict())

    rows = build_scoreboard(runtime, project_id=project.id)
    by_kind = {row.kind: row for row in rows}
    assert by_kind["raw"].model_name == "glm-ocr"
    assert by_kind["raw"].mean_cer == pytest.approx(1 / 5)
    assert by_kind["cleanup"].mean_cer == 0
    assert result.effective_text() == "hello"
    assert not (runtime.data_dir / "config" / "quality-ratings.json").exists()


def test_reading_marks_do_not_enter_effective_text_or_default_export(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    root, projects = _make_notebook(
        runtime, "nb", title="Diary", page_specs=[{"text": "the diary line"}]
    )
    project = projects.load()
    page_id = project.pages[0].page_id
    paths = open_project_paths(root)
    ReadingMarksStore(paths).set_mark(page_id, bookmarked=True, note="margin only")
    result = projects.load_page_result(page_id)
    assert result is not None
    assert result.effective_text() == "the diary line"
    assert "margin only" not in (result.effective_text() or "")

    written = ExportService(paths, projects).export_all(dest_dir=tmp_path / "out")
    markdown = written["markdown"].read_text(encoding="utf-8")
    assert "the diary line" in markdown
    assert "margin only" not in markdown

    from transcribe.services.export_options import ExportOptions

    noted = ExportService(paths, projects).export_all(
        dest_dir=tmp_path / "noted",
        options=ExportOptions(include_reading_notes=True),
    )
    assert "margin only" in noted["markdown"].read_text(encoding="utf-8")


def test_skip_ocr_is_not_scheduled_and_export_omits_ocr_text(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    root, projects = _make_notebook(
        runtime, "nb", title="Diary", page_specs=[{"text": "should not export"}, {"text": "keep"}]
    )
    project = projects.load()
    skipped = project.pages[0].page_id
    kept = project.pages[1].page_id
    projects.set_ocr_policy(skipped, "skip")
    ReadingMarksStore(open_project_paths(root)).set_mark(skipped, note="photo of a ticket")

    clock, ids = FakeClock(), SequentialIds("job")
    _paths, _projects, coord, _ingest = build_coordinator(
        root, clock=clock, ids=ids, provider=FakeVisionOCRProvider(), archive_runtime=runtime
    )
    project = _projects.load()
    plan = coord._build_plan(
        project,
        job_id="job",
        page_ids=None,
        force=True,
        provider=coord.provider,
        model_name="glm-ocr",
    )
    assert skipped not in plan.page_ids
    assert kept in plan.page_ids

    markdown = (
        ExportService(open_project_paths(root), projects)
        .export_all(dest_dir=tmp_path / "out")["markdown"]
        .read_text(encoding="utf-8")
    )
    assert "should not export" not in markdown
    assert "photo of a ticket" in markdown
    assert "keep" in markdown
    assert "image only" in markdown


def test_restore_notebook_replaces_one_folder_and_crash_leaves_it(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    root, projects = _make_notebook(
        runtime, "keep-me", title="Keep", page_specs=[{"text": "stay"}]
    )
    other, _other_projects = _make_notebook(
        runtime, "other", title="Other", page_specs=[{"text": "other page"}]
    )
    project = projects.load()
    archive = tmp_path / "ws.zip"
    service = WorkspaceBackupService()
    service.create_backup(runtime, archive, BackupOptions())

    manifest = read_json(open_project_paths(root).manifest)
    manifest["title"] = "Changed live"
    write_json_atomic(open_project_paths(root).manifest, manifest)

    def _kill(_tmp: Path) -> None:
        raise RuntimeError("killed after temp tree")

    with pytest.raises(BackupError):
        service.restore_notebook(
            runtime,
            archive,
            project.id,
            force=True,
            before_commit=_kill,
        )
    live = read_json(open_project_paths(root).manifest)
    assert live["title"] == "Changed live"

    result = service.restore_notebook(runtime, archive, project.id, force=True)
    assert result.replaced
    restored = read_json(open_project_paths(root).manifest)
    assert restored["title"] == "Keep"
    assert read_json(open_project_paths(other).manifest)["title"] == "Other"

    fresh = _runtime(tmp_path / "empty")
    preview = service.restore_notebook(fresh, archive, project.id, dry_run=True)
    assert preview.dry_run
    assert not (fresh.projects_dir / "keep-me" / "project.json").exists()


def test_archive_ttl_skips_load_until_cheap_stat_changes(tmp_path: Path, monkeypatch) -> None:
    runtime = _runtime(tmp_path)
    _make_notebook(runtime, "a", title="A", page_specs=[{"text": "alpha"}])
    _make_notebook(runtime, "b", title="B", page_specs=[{"text": "beta"}])
    archive = ArchiveService(runtime)
    archive.ensure_index()
    archive._validated_at = 0.0

    calls = {"n": 0}
    original = ProjectService.load

    def _counting(self, *args, **kwargs):
        calls["n"] += 1
        return original(self, *args, **kwargs)

    monkeypatch.setattr(ProjectService, "load", _counting)
    archive.ensure_index()
    assert calls["n"] == 0

    target = runtime.projects_dir / "a" / "project.json"
    payload = json.loads(target.read_text(encoding="utf-8"))
    payload["title"] = "A2"
    target.write_text(json.dumps(payload), encoding="utf-8")
    archive._validated_at = 0.0
    archive.ensure_index()
    assert calls["n"] == 1
    assert archive.search("alpha", filters=ArchiveFilters()).total_matched == 1


def test_bookmarked_search_uses_the_cache_flag(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    root, projects = _make_notebook(
        runtime, "nb", title="Diary", page_specs=[{"text": "alpha page"}, {"text": "beta page"}]
    )
    project = projects.load()
    ReadingMarksStore(open_project_paths(root)).set_mark(project.pages[0].page_id, bookmarked=True)
    archive = ArchiveService(runtime)
    archive.ensure_index(force=True)
    hits = archive.search("", filters=ArchiveFilters(bookmarked_only=True))
    assert [hit.page_id for hit in hits.hits] == [project.pages[0].page_id]


def test_batch_metadata_refuses_a_held_ocr_lock(tmp_path: Path) -> None:
    from transcribe.errors import JobConflictError
    from transcribe.persistence.locks import JobLock

    runtime = _runtime(tmp_path)
    _root, projects = _make_notebook(runtime, "nb", title="Diary", page_specs=[{"text": "page"}])
    page_id = projects.load().pages[0].page_id
    held = JobLock(projects.paths.job_lock)
    held.acquire()
    try:
        with pytest.raises(JobConflictError):
            apply_batch_metadata(projects, [page_id], "ignore", dry_run=False, runtime=runtime)
    finally:
        held.release()
    assert projects.load().pages[0].ignored is False


def test_batch_metadata_dry_run_does_not_write(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    root, projects = _make_notebook(
        runtime, "nb", title="Diary", page_specs=[{"text": "page"}]
    )
    page_id = projects.load().pages[0].page_id
    preview = apply_batch_metadata(projects, [page_id], "ignore", dry_run=True, runtime=runtime)
    assert preview.dry_run and preview.changed == 1
    assert projects.load().pages[0].ignored is False
    applied = apply_batch_metadata(projects, [page_id], "ignore", dry_run=False, runtime=runtime)
    assert applied.changed == 1
    assert projects.load().pages[0].ignored is True
    with pytest.raises(Exception):
        apply_batch_metadata(projects, [], "ignore", dry_run=True)


def test_format_census_leaves_unknown_files(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    path = runtime.data_dir / "config" / "odd.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"format": "transcribe.not-a-format", "schema_version": 9}),
        encoding="utf-8",
    )
    census = run_format_census(runtime)
    assert any(item.code == "unknown_format" for item in census.findings)
    assert "transcribe.not-a-format" in path.read_text(encoding="utf-8")


def test_completed_with_gaps_does_not_change_stored_status() -> None:
    outcome = classify_job_outcome(status="completed", circuit_open=True, failed_pages=2)
    assert outcome.status == "completed"
    assert outcome.outcome == "completed_with_gaps"
    assert classify_job_outcome(status="completed").outcome == "completed"


def test_retry_failed_selects_failed_pages_only(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    root, projects = _make_notebook(
        runtime, "nb", title="Diary", page_specs=[{"text": "ok"}, {"text": "bad"}]
    )
    project = projects.load()
    paths = open_project_paths(root)
    bad = project.pages[1].page_id
    failed = PageResult(
        page_id=bad,
        active_attempt_id="f1",
        attempts=[
            OCRAttempt(
                attempt_id="f1",
                status="failed",
                input_fingerprint="x",
                fingerprint_payload={},
                raw_text=None,
                provenance=None,
                provider_metadata={},
                started_at="2026-01-01T00:00:00.000Z",
                error=AttemptError(code="empty_output", message="none", retriable=False),
            )
        ],
    )
    write_json_atomic(paths.result_path(bad), failed.as_dict())
    chosen = retry_failed_page_ids(projects.load(), projects)
    assert chosen == [bad]


def test_declutter_v6_crops_punch_hole_and_calibration_stripe() -> None:
    image = Image.new("L", (180, 220), 230)
    for y in range(80, 100):
        for x in range(6, 16):
            image.putpixel((x, y), 10)
    striped = image.copy()
    for x in range(180):
        color = 0 if (x // 8) % 2 == 0 else 255
        for y in range(12):
            striped.putpixel((x, y), color)
    buf = BytesIO()
    striped.save(buf, format="PNG")
    result = apply_declutter(buf.getvalue(), enabled=True)
    assert result.state == "enabled_cropped"
    assert result.inset_left >= 14
    assert result.inset_top >= 8
    assert "remove_punch_hole_margins" in result.ops
    assert "remove_calibration_stripes" in result.ops

    interior = Image.new("L", (180, 220), 230)
    for x in range(40, 140):
        for y in range(100, 112):
            interior.putpixel((x, y), 0 if (x // 8) % 2 == 0 else 255)
    buf = BytesIO()
    interior.save(buf, format="PNG")
    left_alone = apply_declutter(buf.getvalue(), enabled=True)
    assert left_alone.inset_top == 0
    assert left_alone.inset_bottom == 0
