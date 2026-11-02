"""Offline CLI and branch coverage for the 1.3 surfaces.

These call ``main`` with a temporary workspace. They do not open a live
Ollama connection.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from transcribe.domain.models import AttemptError, OCRAttempt, PageResult
from transcribe.errors import JobConflictError, ProjectError
from transcribe.persistence.atomic import write_json_atomic
from transcribe.persistence.locks import JobLock
from transcribe.persistence.schema import SUPPORTED
from transcribe.services.batch_metadata import apply_batch_metadata, filters_are_empty
from transcribe.services.format_census import run_format_census
from transcribe.services.job_outcome import count_page_attempts, outcome_from_record
from transcribe.services.reading_marks import ReadingMarksStore
from transcribe.services.archive import ArchiveFilters
from transcribe.services.workspace_backup import WorkspaceBackupService
from tests.services.test_archive import _make_notebook, _runtime


def _bind(monkeypatch, runtime) -> None:
    import transcribe.__main__ as main_mod

    monkeypatch.setattr(main_mod, "PATHS", runtime)
    monkeypatch.setenv("TRANSCRIBE_DATA_DIR", str(runtime.data_dir))
    monkeypatch.setenv("TRANSCRIBE_PROJECTS_DIR", str(runtime.projects_dir))
    monkeypatch.setenv("TRANSCRIBE_INBOX_DIR", str(runtime.inbox_dir))
    monkeypatch.setenv("TRANSCRIBE_EXPORT_DIR", str(runtime.export_dir))


def test_cli_backup_verify_restore_and_one_notebook(tmp_path: Path, monkeypatch) -> None:
    from transcribe.__main__ import main

    runtime = _runtime(tmp_path)
    root, projects = _make_notebook(
        runtime, "nb", title="Diary", page_specs=[{"text": "kept line"}]
    )
    notebook_id = projects.load().id
    _bind(monkeypatch, runtime)
    dest = runtime.export_dir / "backups" / "ws.zip"
    assert main(["backup", "create", "--dest", str(dest)]) == 0
    assert main(["backup", "verify", str(dest)]) == 0
    assert main(["backup", "restore-notebook", str(dest), "missing-id"]) == 1
    assert main(["backup", "restore-notebook", str(dest), notebook_id]) == 1
    assert (
        main(["backup", "restore-notebook", str(dest), notebook_id, "--dry-run", "--force"])
        == 0
    )
    assert main(["restore", str(dest)]) == 2
    assert main(["restore", str(dest), "--dry-run"]) == 0
    with pytest.raises(Exception):
        WorkspaceBackupService().restore_notebook(runtime, dest, "  ")


def test_cli_workspace_search_collections_quality_and_doctor(
    tmp_path: Path, monkeypatch
) -> None:
    from transcribe.__main__ import main

    runtime = _runtime(tmp_path)
    root, projects = _make_notebook(
        runtime, "nb", title="Diary", page_specs=[{"text": "alpha in paris"}]
    )
    project = projects.load()
    ReadingMarksStore(projects.paths).set_mark(project.pages[0].page_id, bookmarked=True)
    _bind(monkeypatch, runtime)

    assert main(["search", "alpha", "--bookmarked"]) == 0
    assert main(["search", "--saved", "no-such-search"]) == 2
    assert main(["saved-search", "save", "paris", "--query", "alpha", "--tags", "ink"]) == 0
    assert main(["saved-search", "list"]) == 0
    assert main(["search", "--saved", "paris"]) == 0
    assert main(["saved-search", "delete", "missing"]) == 0

    assert main(["collections", "create", "Shelf", "--description", "daily"]) == 0
    assert main(["collections", "list"]) == 0
    # create printed an id; assign using the store's only collection via a second create name
    from transcribe.services.collections import NotebookCollectionsStore

    collection_id = NotebookCollectionsStore(runtime).load().collections[0].collection_id
    assert main(["collections", "rename", collection_id, "Shelf two"]) == 0
    assert main(["collections", "assign", collection_id, project.id]) == 0
    assert main(["collections", "unassign", collection_id, project.id]) == 0
    assert main(["collections", "archive", project.id]) == 0
    assert main(["collections", "unarchive", project.id]) == 0
    assert main(["collections", "delete", collection_id]) == 0
    assert main(["collections", "delete", "missing"]) == 1

    assert main(["quality", "summary"]) == 0
    assert main(["quality", "rate", "cleanup", "accept", "--project", project.id]) == 0
    assert main(["quality", "scoreboard", "--project", project.id]) == 0
    assert main(["workspace-doctor"]) == 0

    from transcribe.services.export import ExportService
    from transcribe.services.project import open_project_paths

    out = tmp_path / "export-out"
    ExportService(open_project_paths(root), projects).export_all(dest_dir=out)
    assert main(["verify-export", str(out)]) == 0
    assert main(["verify-export", str(tmp_path / "missing-export")]) == 1


def test_cli_status_doctor_batch_and_run_guards(tmp_path: Path, monkeypatch) -> None:
    from transcribe.__main__ import main

    runtime = _runtime(tmp_path)
    root, projects = _make_notebook(
        runtime, "nb", title="Diary", page_specs=[{"text": "page"}]
    )
    page_id = projects.load().pages[0].page_id
    _bind(monkeypatch, runtime)

    assert main(["status", str(root)]) == 0
    assert main(["doctor", str(root), "--deep"]) == 0
    assert main(["detect", str(root), "--list"]) == 0
    assert (
        main(
            [
                "run",
                str(root),
                "--model",
                "glm-ocr",
                "--base-url",
                "http://example.com:11434",
            ]
        )
        == 2
    )
    assert main(["run", str(root), "--model", "glm-ocr", "--cleanup-mode", "strip_leak"]) == 2
    assert main(["run", str(root), "--model", "glm-ocr", "--retry-failed", "--base-url", "http://127.0.0.1:11434"]) == 0

    assert main(["pages", "batch", str(root), "--action", "ignore"]) == 2
    assert (
        main(
            [
                "pages",
                "batch",
                str(root),
                "--page",
                page_id,
                "--action",
                "add_tag",
                "--tag",
                "ink",
                "--apply",
            ]
        )
        == 0
    )
    assert "ink" in projects.load().pages[0].tags


def test_job_outcome_counts_skip_pending_and_interrupted(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    root, projects = _make_notebook(
        runtime,
        "nb",
        title="Diary",
        page_specs=[{"text": "a"}, {"text": "b"}, {"text": "c"}, {"text": "d"}],
    )
    project = projects.load()
    projects.set_ocr_policy(project.pages[0].page_id, "skip")
    paths = projects.paths

    def _write(page_id: str, status: str, code: str | None = None) -> None:
        error = AttemptError(code=code, message="x", retriable=False) if code else None
        write_json_atomic(
            paths.result_path(page_id),
            PageResult(
                page_id=page_id,
                active_attempt_id="a",
                attempts=[
                    OCRAttempt(
                        attempt_id="a",
                        status=status,
                        input_fingerprint="fp",
                        fingerprint_payload={},
                        raw_text=None,
                        provenance=None,
                        provider_metadata={},
                        started_at="2026-01-01T00:00:00.000Z",
                        error=error,
                    )
                ],
            ).as_dict(),
        )

    _write(project.pages[1].page_id, "interrupted")
    _write(project.pages[2].page_id, "running")
    # page 3 has no result file → pending. The helper wrote text, so delete it.
    paths.result_path(project.pages[3].page_id).unlink()
    failed, interrupted, pending = count_page_attempts(projects.load(), projects)
    assert interrupted == 1
    assert pending == 2
    assert failed == 0
    record = outcome_from_record({"status": "completed", "circuit_open": True, "failed": "2"})
    assert record.outcome == "completed_with_gaps"
    assert record.failed_pages == 2


def test_reading_marks_corrupt_file_and_clear(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    _root, projects = _make_notebook(runtime, "nb", title="Diary", page_specs=[{"text": "a"}])
    store = ReadingMarksStore(projects.paths)
    page_id = projects.load().pages[0].page_id
    store.set_mark(page_id, bookmarked=True, note="x" * 800)
    assert len(store.load()[page_id].note) == 500
    store.set_mark(page_id, bookmarked=False, note="")
    assert store.load() == {}

    store.path.write_text("{not json", encoding="utf-8")
    assert store.load() == {}
    write_json_atomic(
        store.path,
        {"format": "transcribe.reading-marks", "schema_version": 1, "pages": ["nope"]},
    )
    assert store.load() == {}
    write_json_atomic(
        store.path,
        {
            "format": "transcribe.reading-marks",
            "schema_version": 1,
            "pages": {"p": "nope", "q": {}},
        },
    )
    assert store.load() == {}


def test_batch_metadata_branches(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    _root, projects = _make_notebook(
        runtime, "nb", title="Diary", page_specs=[{"text": "a", "date": None}]
    )
    page = projects.load().pages[0]
    with pytest.raises(ProjectError):
        apply_batch_metadata(projects, [page.page_id], "nope")
    with pytest.raises(ProjectError):
        apply_batch_metadata(projects, [page.page_id], "add_tag", tag="")
    with pytest.raises(ProjectError):
        apply_batch_metadata(projects, ["missing"], "ignore")

    from transcribe.domain.dates import ApproximateDate

    projects.approve_page_date(page.page_id, ApproximateDate(2018, 1, 2))
    # Force the date back to unapproved so approve_dates has work to do.
    project = projects.load()
    project.pages[0].set_date_state(
        ApproximateDate(2018, 1, 2), approved=False, source="extracted"
    )
    from transcribe.persistence.atomic import write_json_atomic as write_json

    write_json(projects.paths.manifest, project.as_dict())
    approved = apply_batch_metadata(
        projects, [page.page_id], "approve_dates", dry_run=False, runtime=runtime
    )
    assert approved.changed == 1
    assert projects.load().pages[0].date_approved is True

    apply_batch_metadata(
        projects, [page.page_id], "add_tag", tag="Ink", dry_run=False, runtime=runtime
    )
    apply_batch_metadata(
        projects, [page.page_id], "remove_tag", tag="ink", dry_run=False, runtime=runtime
    )
    assert "ink" not in projects.load().pages[0].tags
    assert filters_are_empty(ArchiveFilters()) is True
    assert filters_are_empty(ArchiveFilters(query="x")) is False

    held = JobLock(projects.paths.analysis_lock)
    assert held.acquire()
    try:
        with pytest.raises(JobConflictError):
            apply_batch_metadata(projects, [page.page_id], "ignore", dry_run=False)
    finally:
        held.release()


def test_format_census_skips_junk_and_rejects_unknown_version(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    assert run_format_census(runtime).ok
    junk = runtime.data_dir / "config" / "junk.json"
    junk.write_text("not-json", encoding="utf-8")
    cache = runtime.data_dir / "cache" / "skip.json"
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text("{}", encoding="utf-8")
    bad = runtime.data_dir / "config" / "settings-bad.json"
    bad.write_text(
        json.dumps({"format": "transcribe.settings", "schema_version": 99}),
        encoding="utf-8",
    )
    census = run_format_census(runtime)
    assert any(item.code == "unsupported_schema_version" for item in census.findings)
    assert census.ok is False
    assert SUPPORTED["transcribe.settings"] == 1
    assert "not-json" in junk.read_text(encoding="utf-8")
