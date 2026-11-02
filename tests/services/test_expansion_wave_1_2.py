"""1.2 wave integration: archive entities/org, export tags, timeline, guards."""

from __future__ import annotations

from pathlib import Path

import pytest

from transcribe.net_guard import (
    bind_warning,
    check_bind_allowed,
    is_loopback_bind,
    redact_sensitive,
)
from transcribe.persistence.atomic import write_json_atomic
from transcribe.persistence.disk import ensure_disk_budget
from transcribe.errors import DiskFullError
from transcribe.services.archive import ArchiveFilters, ArchiveService
from transcribe.services.collections import NotebookCollectionsStore
from transcribe.services.export import ExportService
from transcribe.services.export_options import ExportOptions
from transcribe.services.job_timeline import build_job_timeline
from tests.conftest import FakeClock, SequentialIds
from tests.services.test_archive import _make_notebook, _runtime


def test_archive_entity_filters_from_published_ner(tmp_path: Path):
    runtime = _runtime(tmp_path)
    root, projects = _make_notebook(
        runtime,
        "nb1",
        title="Diary",
        page_specs=[{"text": "Anna went to Paris with Ben."}],
    )
    # Published NER envelope (payload entities grouped by unit/page id).
    page_id = projects.load().pages[0].page_id
    ner_dir = root / "analysis" / "ner"
    ner_dir.mkdir(parents=True, exist_ok=True)
    write_json_atomic(
        ner_dir / "published.json",
        {
            "format": "transcribe.analysis-result",
            "schema_version": 1,
            "attempt_id": "ner1",
            "attempt_state": "succeeded",
            "outcome": "success",
            "payload": {
                "entities": [
                    {"surface": "Anna", "label": "PERSON", "unit_id": page_id},
                    {"surface": "Paris", "label": "GPE", "unit_id": page_id},
                    {"surface": "Ben", "label": "PERSON", "unit_id": page_id},
                ]
            },
        },
    )
    service = ArchiveService(runtime)
    assert service.search("Anna", filters=ArchiveFilters(people=("Anna",))).total_matched == 1
    assert service.search("", filters=ArchiveFilters(people=("Ben",))).total_matched == 1
    assert service.search("", filters=ArchiveFilters(places=("Paris",))).total_matched == 1
    # A PERSON surface must not satisfy a place filter (and vice versa).
    assert service.search("", filters=ArchiveFilters(places=("Anna",))).total_matched == 0
    assert service.search("", filters=ArchiveFilters(people=("Paris",))).total_matched == 0
    assert service.search("", filters=ArchiveFilters(people=("Nobody",))).total_matched == 0


def test_archive_archived_and_collection_filters(tmp_path: Path):
    runtime = _runtime(tmp_path)
    root, projects = _make_notebook(
        runtime,
        "nb1",
        title="Diary",
        page_specs=[{"text": "archivable notebook text"}],
    )
    project_id = projects.load().id
    store = NotebookCollectionsStore(runtime, clock=FakeClock(), ids=SequentialIds("c"))
    collection = store.create("Shelf", project_ids=(project_id,))
    store.set_archived(project_id, archived=True)

    service = ArchiveService(runtime)
    assert service.list_notebooks() == []
    assert service.search("archivable").total_matched == 0
    included = service.list_notebooks(filters=ArchiveFilters(include_archived=True))
    assert len(included) == 1
    assert included[0].archived is True
    assert included[0].collection_ids == [collection.collection_id]
    assert (
        service.search(
            "archivable",
            filters=ArchiveFilters(
                include_archived=True, collection_id=collection.collection_id
            ),
        ).total_matched
        == 1
    )
    assert (
        service.search(
            "archivable",
            filters=ArchiveFilters(include_archived=True, collection_id="missing"),
        ).total_matched
        == 0
    )


def test_export_tag_filters_reading_formats_only(tmp_path: Path):
    runtime = _runtime(tmp_path)
    root, projects = _make_notebook(
        runtime,
        "nb1",
        title="Diary",
        page_specs=[
            {"text": "keep this page", "tags": ["keep"]},
            {"text": "drop this page", "tags": ["drop"]},
            {"text": "plain page here"},
        ],
    )
    from transcribe.services.project import open_project_paths

    service = ExportService(open_project_paths(root), projects)
    opts = ExportOptions(
        formats=frozenset({"markdown", "json"}),
        include_tags=("keep",),
    )
    written = service.export_all(dest_dir=tmp_path / "out1", options=opts)
    md = written["markdown"].read_text(encoding="utf-8")
    assert "keep this page" in md
    assert "drop this page" not in md
    assert "plain page here" not in md
    # JSON keeps the full notebook regardless of reading-format filters.
    import json

    notebook = json.loads(written["notebook"].read_text(encoding="utf-8"))
    assert len(notebook["pages"]) == 3

    opts2 = ExportOptions(formats=frozenset({"markdown"}), exclude_tags=("drop",))
    written2 = service.export_all(dest_dir=tmp_path / "out2", options=opts2)
    md2 = written2["markdown"].read_text(encoding="utf-8")
    assert "keep this page" in md2
    assert "drop this page" not in md2
    assert "plain page here" in md2


def test_job_timeline_validates_records(tmp_path: Path):
    runtime = _runtime(tmp_path)
    root, projects = _make_notebook(
        runtime,
        "nb1",
        title="Diary",
        page_specs=[{"text": "timeline text"}],
    )
    from transcribe.services.project import open_project_paths

    paths = open_project_paths(root)
    paths.jobs_dir.mkdir(parents=True, exist_ok=True)
    write_json_atomic(
        paths.jobs_dir / "job1.json",
        {
            "format": "transcribe.job-record",
            "schema_version": 1,
            "job_id": "job1",
            "status": "completed",
            "started_at": "2026-01-01T00:00:00Z",
            "ended_at": "2026-01-01T00:01:00Z",
            "total": 1,
            "completed": 1,
            "model_name": "fake-vision",
        },
    )
    write_json_atomic(paths.jobs_dir / "bad.json", {"format": "nope", "schema_version": 1})
    entries = build_job_timeline(paths)
    assert len(entries) == 2
    good = next(e for e in entries if e.correlation_id == "job1")
    assert good.valid is True
    assert good.kind == "ocr"
    assert good.detail == "fake-vision"
    bad = next(e for e in entries if e.correlation_id == "bad")
    assert bad.valid is False
    assert bad.error


def test_disk_budget_guard(tmp_path: Path):
    ensure_disk_budget(tmp_path, additional=0, min_free_bytes=0)
    with pytest.raises(DiskFullError):
        ensure_disk_budget(tmp_path, additional=10**15, min_free_bytes=0)


def test_bind_guard_and_redaction():
    assert is_loopback_bind("127.0.0.1") is True
    assert is_loopback_bind("0.0.0.0") is False
    assert bind_warning("127.0.0.1") is None
    assert bind_warning("0.0.0.0") is not None
    assert check_bind_allowed("0.0.0.0", env={}) is not None
    assert check_bind_allowed("0.0.0.0", env={"TRANSCRIBE_ALLOW_LAN": "1"}) is None
    assert check_bind_allowed("0.0.0.0", env={"TRANSCRIBE_CONTAINER": "1"}) is None
    assert check_bind_allowed("192.168.1.5", env={"TRANSCRIBE_ALLOW_LAN": "1"}) is None
    home = str(Path.home())
    redacted = redact_sensitive(
        f"see http://user:secret@example.com/x?api_key=abc and {home}/data/file",
    )
    assert "secret" not in redacted
    assert "abc" not in redacted
    assert home not in redacted


def test_cli_export_collection_single_positional_is_dest(tmp_path: Path, monkeypatch):
    """`export --collection <id> <dest>`: the lone positional is the dest."""
    from transcribe.__main__ import main
    from transcribe.runtime_paths import RuntimePaths as _RP
    import transcribe.__main__ as main_mod

    runtime = _runtime(tmp_path)
    root, projects = _make_notebook(
        runtime,
        "nb1",
        title="Diary",
        page_specs=[{"text": "collection export text"}],
    )
    project_id = projects.load().id
    store = NotebookCollectionsStore(runtime, clock=FakeClock(), ids=SequentialIds("c"))
    collection = store.create("Shelf", project_ids=(project_id,))
    monkeypatch.setattr(main_mod, "PATHS", runtime)
    dest = tmp_path / "col-out"
    rc = main(["export", "--collection", collection.collection_id, str(dest), "--format", "markdown"])
    assert rc == 0
    assert (dest / "notebook.md").exists()
    from transcribe.services.export_verify import verify_export_bundle

    assert verify_export_bundle(dest).ok
