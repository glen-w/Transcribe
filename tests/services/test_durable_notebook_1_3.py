"""Durable-notebook waves 1–7 (offline)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.conftest import FakeClock, SequentialIds
from tests.fakes import FakeVisionOCRProvider
from tests.services.test_archive import _make_notebook, _runtime
from transcribe.domain.fingerprint import sha256_text
from transcribe.domain.models import (
    AttemptError,
    CleanupRecord,
    OCRAttempt,
    PageResult,
)
from transcribe.errors import JobConflictError, ProjectError
from transcribe.persistence.atomic import read_json, write_json_atomic
from transcribe.persistence.locks import JobLock
from transcribe.persistence.schema import SUPPORTED
from transcribe.services.batch_metadata import apply_batch_metadata
from transcribe.services.cleanup_prompts import render_cleanup_prompt
from transcribe.services.cleanup_verdict import (
    accept_cleanup_proposal,
    can_accept_proposal,
    cleanup_proposal,
    reject_cleanup_proposal,
)
from transcribe.services.edit_divergence import edit_diverges, result_edit_diverges
from transcribe.services.export import ExportService
from transcribe.services.export_options import ExportOptions
from transcribe.services.hand_spellings import (
    PAIR_CAP,
    HandSpellingsStore,
    SpellingPair,
    apply_spelling_occurrence,
)
from transcribe.services.job import build_coordinator
from transcribe.services.miss_desk import classify_miss_code, group_failed_ocr, miss_desk_page_ids
from transcribe.services.project import open_project_paths
from transcribe.services.quality import QualityRatingStore


def _attach_cleanup(
    paths,
    page_id: str,
    *,
    execution: str = "provider_ok",
    vision: str = "teh cat",
    proposal: str = "the cat",
    edited: str | None = None,
) -> PageResult:
    result = PageResult.from_dict(read_json(paths.result_path(page_id)))
    attempt = result.attempts[0]
    attempt.raw_text = proposal if execution == "provider_ok" else vision
    attempt.cleanup = CleanupRecord(
        execution_status=execution,
        acceptance_status="applied" if execution == "provider_ok" else "not_applicable",
        pre_cleanup_text=vision if execution == "provider_ok" else None,
    )
    result.edited_text = edited
    write_json_atomic(paths.result_path(page_id), result.as_dict())
    return result


def test_wave1_accept_writes_edited_text_reject_does_not(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    root, projects = _make_notebook(runtime, "nb", title="D", page_specs=[{"text": "teh cat"}])
    page_id = projects.load().pages[0].page_id
    paths = open_project_paths(root)
    _attach_cleanup(paths, page_id)
    store = QualityRatingStore(runtime)

    accepted = accept_cleanup_proposal(projects, page_id, runtime=runtime, quality=store)
    assert accepted.edited_text == "the cat"
    assert accepted.attempts[0].cleanup is not None
    assert store.summary()["cleanup_acceptance"] == 1.0

    _attach_cleanup(paths, page_id, vision="raw", proposal="clean", edited=None)
    before = projects.load_page_result(page_id)
    assert before is not None
    assert before.edited_text is None
    rejected = reject_cleanup_proposal(projects, page_id, runtime=runtime, quality=store)
    assert rejected.edited_text is None
    assert rejected.effective_text() == "clean"
    assert rejected.attempts[0].cleanup is not None


def test_wave1_existing_edit_defaults_keep_and_failed_hides_accept(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    root, projects = _make_notebook(runtime, "nb", title="D", page_specs=[{"text": "x"}])
    page_id = projects.load().pages[0].page_id
    paths = open_project_paths(root)
    _attach_cleanup(paths, page_id, edited="my careful edit")
    store = QualityRatingStore(runtime)
    kept = accept_cleanup_proposal(
        projects, page_id, edit_gate_choice="keep_edit", runtime=runtime, quality=store
    )
    assert kept.edited_text == "my careful edit"

    _attach_cleanup(paths, page_id, edited="my careful edit")
    adopted = accept_cleanup_proposal(
        projects, page_id, edit_gate_choice="adopt_new", runtime=runtime, quality=store
    )
    assert adopted.edited_text == "the cat"

    _attach_cleanup(paths, page_id, execution="provider_failed")
    result = projects.load_page_result(page_id)
    assert result is not None
    proposal = cleanup_proposal(result.active_attempt())
    assert proposal is None
    assert can_accept_proposal(proposal) is False


def test_wave2_divergence_banner_helper() -> None:
    assert edit_diverges(edited_text="hello", raw_text="hello", threshold=0.15) is False
    assert edit_diverges(edited_text="hello", raw_text="xxxxx", threshold=0.15) is True
    below = PageResult(
        page_id="p",
        edited_text="hello",
        active_attempt_id="a",
        attempts=[
            OCRAttempt(
                attempt_id="a",
                status="succeeded",
                input_fingerprint="x",
                fingerprint_payload={},
                raw_text="hallo",
                provenance=None,
                provider_metadata={},
                started_at="t",
            )
        ],
        updated_at="t",
    )
    assert result_edit_diverges(below, threshold=0.9) is False
    assert result_edit_diverges(below, threshold=0.1) is True
    source = Path("src/transcribe/services/edit_divergence.py").read_text(encoding="utf-8")
    assert "adopt_raw_as_edit" not in source


def test_wave3_miss_desk_plan_only_empty_output(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    root, projects = _make_notebook(
        runtime, "nb", title="D", page_specs=[{"text": "a"}, {"text": "b"}, {"text": "ok"}]
    )
    project = projects.load()
    p0, p1, p2 = [p.page_id for p in project.pages]
    paths = open_project_paths(root)

    def _fail(page_id: str, code: str) -> None:
        write_json_atomic(
            paths.result_path(page_id),
            PageResult(
                page_id=page_id,
                active_attempt_id="a",
                attempts=[
                    OCRAttempt(
                        attempt_id="a",
                        status="failed",
                        input_fingerprint="x",
                        fingerprint_payload={},
                        raw_text=None,
                        provenance=None,
                        provider_metadata={},
                        started_at="t",
                        completed_at="t",
                        error=AttemptError(code=code, message="x", retriable=False),
                    )
                ],
                updated_at="t",
            ).as_dict(),
        )

    _fail(p0, "empty_output")
    _fail(p1, "empty_output")
    grouped = group_failed_ocr(projects.load(), projects.load_page_result)
    assert grouped["empty_output"] == [p0, p1]
    assert p2 not in grouped["empty_output"]
    assert classify_miss_code("weird_new_code") == "other"
    ids = miss_desk_page_ids(projects.load(), projects.load_page_result, group="empty_output")
    _paths, _projects, coord, _ingest = build_coordinator(
        root, clock=FakeClock(), ids=SequentialIds("job"), provider=FakeVisionOCRProvider(),
        archive_runtime=runtime,
    )
    plan = coord._build_plan(
        _projects.load(),
        job_id="job",
        page_ids=ids,
        force=True,
        provider=coord.provider,
        model_name="glm-ocr",
    )
    assert list(plan.page_ids) == [p0, p1]


def test_wave4_kept_scan_skipped_and_legacy_loads(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    root, projects = _make_notebook(
        runtime, "nb", title="D", page_specs=[{"text": "draw"}, {"text": "keep"}]
    )
    project = projects.load()
    scan_id, text_id = project.pages[0].page_id, project.pages[1].page_id
    projects.set_page_role(scan_id, "scan")
    _paths, _projects, coord, _ingest = build_coordinator(
        root, clock=FakeClock(), ids=SequentialIds("job"), provider=FakeVisionOCRProvider(),
        archive_runtime=runtime,
    )
    plan = coord._build_plan(
        _projects.load(),
        job_id="job",
        page_ids=None,
        force=True,
        provider=coord.provider,
        model_name="glm-ocr",
    )
    assert scan_id not in plan.page_ids
    assert text_id in plan.page_ids

    payload = read_json(open_project_paths(root).manifest)
    for page in payload["pages"]:
        page.pop("page_role", None)
        page.pop("page_certainty", None)
        page.pop("page_gloss", None)
    write_json_atomic(open_project_paths(root).manifest, payload)
    loaded = _projects.load()
    assert all(p.page_role == "text" for p in loaded.pages)
    assert all(not p.page_gloss for p in loaded.pages)


def test_wave5_gloss_and_unsure(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    root, projects = _make_notebook(runtime, "nb", title="D", page_specs=[{"text": "diary line"}])
    page = projects.load().pages[0]
    with pytest.raises(ProjectError):
        projects.set_page_gloss(page.page_id, "x" * 501)
    projects.set_page_gloss(page.page_id, "a short gloss")
    projects.set_page_certainty(page.page_id, "unsure")
    loaded = projects.load()
    assert loaded.pages[0].page_certainty == "unsure"
    assert loaded.pages[0].review_status == "unreviewed"
    result = projects.load_page_result(page.page_id)
    assert result is not None
    assert result.effective_text() == "diary line"
    assert "gloss" not in (result.effective_text() or "")

    markdown = (
        ExportService(open_project_paths(root), projects)
        .export_all(dest_dir=tmp_path / "out")["markdown"]
        .read_text(encoding="utf-8")
    )
    assert "a short gloss" not in markdown
    noted = (
        ExportService(open_project_paths(root), projects)
        .export_all(
            dest_dir=tmp_path / "noted",
            options=ExportOptions(include_page_notes=True),
        )["markdown"]
        .read_text(encoding="utf-8")
    )
    assert "a short gloss" in noted


def test_wave6_spellings_apply_cap_and_fingerprint(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    store = HandSpellingsStore(runtime)
    store.add("teh", "the")
    assert apply_spelling_occurrence("teh cat teh", "teh", "the", 0) == "the cat teh"
    assert apply_spelling_occurrence("teh cat teh", "teh", "the", 1) == "teh cat the"
    with pytest.raises(ProjectError):
        store.replace([SpellingPair("a", "b")] * (PAIR_CAP + 1))
    off = render_cleanup_prompt(mode="strip_leak", ocr_text="{ocr_text}")
    on = render_cleanup_prompt(
        mode="strip_leak", ocr_text="{ocr_text}", spelling_pairs=(("teh", "the"),)
    )
    assert sha256_text(off[2]) != sha256_text(on[2])
    again = render_cleanup_prompt(mode="strip_leak", ocr_text="{ocr_text}")
    assert sha256_text(off[2]) == sha256_text(again[2])
    assert "transcribe.hand-spellings" in SUPPORTED


def test_wave7_batch_lock_and_untouched_third_page(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    _root, projects = _make_notebook(
        runtime, "nb", title="D", page_specs=[{"text": "a"}, {"text": "b"}, {"text": "c"}]
    )
    p0, p1, p2 = [p.page_id for p in projects.load().pages]
    apply_batch_metadata(
        projects, [p0, p1], "set_page_role", role="scan", dry_run=False, runtime=runtime
    )
    loaded = projects.load()
    by_id = {p.page_id: p for p in loaded.pages}
    assert by_id[p0].page_role == "scan"
    assert by_id[p1].page_role == "scan"
    assert by_id[p2].page_role == "text"
    third_before = json.dumps(by_id[p2].as_dict(), sort_keys=True)

    held = JobLock(projects.paths.job_lock)
    held.acquire()
    try:
        with pytest.raises(JobConflictError):
            apply_batch_metadata(
                projects, [p0], "set_page_certainty", certainty="unsure", dry_run=False
            )
    finally:
        held.release()
    after = {p.page_id: p for p in projects.load().pages}
    assert json.dumps(after[p2].as_dict(), sort_keys=True) == third_before
    assert after[p0].page_certainty == "sure"
    from transcribe.services.batch_metadata import ACTIONS

    assert "gloss" not in ACTIONS and "set_page_gloss" not in ACTIONS


def test_wave1_edit_proposal_is_buffer_only() -> None:
    source = Path("src/transcribe/ui/review_workbench.py").read_text(encoding="utf-8")
    assert 'button("Edit proposal"' in source
    assert "_set_buffer(page_id, proposal.proposal_text" in source
    assert "Visual Cleanup" not in source or "declutter" in source
    cleanup_tab = source[source.index("def _render_cleanup_tab") :]
    assert "Accept proposal" not in cleanup_tab.split("def ")[0]


def test_wave4_scan_skipped_by_analyse_and_finetune(tmp_path: Path) -> None:
    from transcribe.analysis.adapter import build_page_v1_document
    from transcribe.services.finetune_export import FinetuneExportService

    runtime = _runtime(tmp_path)
    root, projects = _make_notebook(
        runtime, "nb", title="D", page_specs=[{"text": "drawing ink"}, {"text": "keep this line"}]
    )
    scan_id, text_id = [p.page_id for p in projects.load().pages]
    projects.set_page_role(scan_id, "scan")
    doc = build_page_v1_document(projects.load(), projects)
    unit_ids = {u.unit_id for u in doc.units}
    assert scan_id not in unit_ids
    assert text_id in unit_ids
    assert "drawing ink" not in doc.text

    out = FinetuneExportService(open_project_paths(root), projects).export(tmp_path / "ft")
    rows = (out / "samples.jsonl").read_text(encoding="utf-8").strip().splitlines()
    page_ids = {json.loads(row)["source"]["page_id"] for row in rows if row}
    assert scan_id not in page_ids
    assert text_id in page_ids
    viewer = Path("src/transcribe/ui/page_viewer.py").read_text(encoding="utf-8")
    assert "Kept scan — image only" in viewer


def test_wave5_gloss_is_not_fts_indexed(tmp_path: Path) -> None:
    from transcribe.services.archive import ArchiveService

    runtime = _runtime(tmp_path)
    root, projects = _make_notebook(
        runtime, "nb", title="D", page_specs=[{"text": "diary line uniqueocr"}]
    )
    page_id = projects.load().pages[0].page_id
    projects.set_page_gloss(page_id, "zzglossneedle")
    archive = ArchiveService(runtime)
    archive.ensure_index(force=True)
    assert archive.search("zzglossneedle").showing == 0
    assert archive.search("uniqueocr").showing >= 1
    manifest = read_json(open_project_paths(root).manifest)
    assert manifest["schema_version"] == 1
    assert manifest["format"] == "transcribe.project"


def test_wave6_apply_does_not_write_edited_text(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    _root, projects = _make_notebook(runtime, "nb", title="D", page_specs=[{"text": "teh cat"}])
    page_id = projects.load().pages[0].page_id
    before = projects.load_page_result(page_id)
    assert before is not None
    buffer = apply_spelling_occurrence(before.effective_text() or "", "teh", "the", 0)
    assert buffer == "the cat"
    after = projects.load_page_result(page_id)
    assert after is not None
    assert after.edited_text is None
    assert after.effective_text() == "teh cat"


def test_wave6_spellings_roundtrip_in_workspace_backup(tmp_path: Path) -> None:
    from transcribe.services.workspace_backup import BackupOptions, WorkspaceBackupService

    runtime = _runtime(tmp_path)
    _make_notebook(runtime, "nb", title="D", page_specs=[{"text": "x"}])
    HandSpellingsStore(runtime).add("teh", "the")
    archive = tmp_path / "ws.zip"
    WorkspaceBackupService().create_backup(runtime, archive, BackupOptions())
    fresh = _runtime(tmp_path / "restored")
    WorkspaceBackupService().restore_backup(fresh, archive, safety=False)
    pairs = HandSpellingsStore(fresh).list()
    assert [(p.source, p.target) for p in pairs] == [("teh", "the")]


def test_wave3_miss_desk_copy_and_no_finetune_hold() -> None:
    from transcribe.services import miss_desk
    from transcribe.services.miss_desk import MISS_DESK_COPY

    assert "not a fine-tune target" in MISS_DESK_COPY.lower()
    assert not hasattr(miss_desk, "finetune_hold")
