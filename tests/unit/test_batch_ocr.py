"""Batch OCR selection, resume, and cancel (offline, fake provider)."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from transcribe.corpus.ocr_run import OcrBatchRunStore, finalize_ocr_batch_status
from transcribe.corpus.paths import CorpusPaths
from transcribe.domain.models import OCRSettings
from transcribe.errors import ValidationError
from transcribe.ingest import IngestService
from transcribe.services.batch_ocr import (
    BatchOcrCoordinator,
    list_candidates,
    select_by_ids,
    select_from_import_run,
    select_pending,
)
from transcribe.services.project import ProjectService, open_project_paths
from tests.conftest import FakeClock, SequentialIds
from tests.fakes import FakeVisionOCRProvider
from tests.ingest.test_ingest import _png_bytes


def _corpus(tmp_path: Path) -> CorpusPaths:
    paths = CorpusPaths(data_dir=tmp_path / "data", projects_dir=tmp_path / "projects")
    paths.projects_dir.mkdir(parents=True)
    paths.ensure_layout()
    return paths


def _make_notebook(
    corpus: CorpusPaths,
    name: str,
    *,
    clock: FakeClock,
    ids: SequentialIds,
    pages: int = 1,
) -> Path:
    root = corpus.projects_dir / name
    projects = ProjectService(open_project_paths(root), clock=clock, ids=ids)
    project = projects.create(name)
    ingest = IngestService(open_project_paths(root), clock=clock, ids=ids)
    for i in range(pages):
        ingest.import_bytes(f"{name}-{i}.png", _png_bytes(color=(i + 1, 20, 30)))
    settings = project.settings
    settings.model_name = "fake-vision"
    projects.save_settings(projects.load(), settings)
    return root


def test_select_pending_skips_fully_transcribed(tmp_path: Path) -> None:
    corpus = _corpus(tmp_path)
    clock, ids = FakeClock(), SequentialIds("sel")
    _make_notebook(corpus, "pending-nb", clock=clock, ids=ids)
    done_root = _make_notebook(corpus, "done-nb", clock=clock, ids=ids)
    provider = FakeVisionOCRProvider()
    paths = open_project_paths(done_root)
    projects = ProjectService(paths, clock=clock, ids=ids)
    from transcribe.services.job import JobCoordinator

    JobCoordinator(paths, projects, provider, clock=clock, ids=ids).run_blocking()

    candidates = list_candidates(corpus, clock=clock, ids=ids)
    pending = select_pending(candidates)
    assert {c.title for c in pending} == {"pending-nb"}
    by_id = select_by_ids(candidates, [c.notebook_id for c in candidates])
    assert len(by_id) == 2


def test_list_candidates_dedupes_shared_notebook_id(tmp_path: Path) -> None:
    corpus = _corpus(tmp_path)
    clock, ids = FakeClock(), SequentialIds("dup")
    root = _make_notebook(corpus, "original", clock=clock, ids=ids)
    shutil.copytree(root, corpus.projects_dir / "copy")

    candidates = list_candidates(corpus, clock=clock, ids=ids)
    assert len(candidates) == 1


def test_select_by_ids_dedupes_repeated_picks(tmp_path: Path) -> None:
    corpus = _corpus(tmp_path)
    clock, ids = FakeClock(), SequentialIds("pick")
    _make_notebook(corpus, "only", clock=clock, ids=ids)
    candidates = list_candidates(corpus, clock=clock, ids=ids)
    nid = candidates[0].notebook_id

    picked = select_by_ids(candidates, [nid, nid, nid])
    assert len(picked) == 1
    assert picked[0].notebook_id == nid


def test_batch_create_run_dedupes_duplicate_candidates(tmp_path: Path) -> None:
    from transcribe.services.batch_notebooks import NotebookCandidate

    corpus = _corpus(tmp_path)
    clock, ids = FakeClock(), SequentialIds("run")
    root = _make_notebook(corpus, "nb", clock=clock, ids=ids)
    project = ProjectService(open_project_paths(root), clock=clock, ids=ids).load(
        reconcile=False
    )
    dup = NotebookCandidate(
        notebook_id=project.id,
        title="nb",
        root=root,
        managed_relpath="nb",
    )
    coord = BatchOcrCoordinator(corpus, clock=clock, ids=ids)
    settings = OCRSettings.from_dict(project.settings.as_dict())
    settings.model_name = "fake-vision"
    run = coord.create_run([dup, dup], settings=settings)
    assert len(run.items) == 1


def test_select_from_import_run_uses_committed_notebooks_only(tmp_path: Path) -> None:
    from transcribe.corpus.import_run import (
        ImportRun,
        ImportRunItemOutcome,
        ImportRunStore,
    )
    from transcribe.corpus.plan import POLICY_SKIP_EXISTING_V1

    corpus = _corpus(tmp_path)
    clock, ids = FakeClock(), SequentialIds("imp")
    _make_notebook(corpus, "kept", clock=clock, ids=ids)
    _make_notebook(corpus, "skipped-nb", clock=clock, ids=ids)
    candidates = list_candidates(corpus, clock=clock, ids=ids)
    by_title = {c.title: c for c in candidates}
    run = ImportRun(
        import_run_id="imprun1",
        plan_id="plan1",
        plan_fingerprint="a" * 64,
        import_policy_id=POLICY_SKIP_EXISTING_V1,
        created_at="2026-01-01T00:00:00+00:00",
        updated_at="2026-01-01T00:00:00+00:00",
        status="complete",
        items=[
            ImportRunItemOutcome(
                item_id="i1",
                state="committed",
                resulting_ids={"notebook_id": by_title["kept"].notebook_id},
            ),
            ImportRunItemOutcome(
                item_id="i2",
                state="skipped",
                resulting_ids={"notebook_id": by_title["skipped-nb"].notebook_id},
            ),
        ],
    )
    ImportRunStore(corpus).save(run)
    selected = select_from_import_run(corpus, "imprun1", candidates)
    assert [c.title for c in selected] == ["kept"]


def test_batch_ocr_runs_two_notebooks_and_skips_on_resume(tmp_path: Path) -> None:
    corpus = _corpus(tmp_path)
    clock, ids = FakeClock(), SequentialIds("bat")
    _make_notebook(corpus, "alpha", clock=clock, ids=ids, pages=1)
    _make_notebook(corpus, "beta", clock=clock, ids=ids, pages=1)
    provider = FakeVisionOCRProvider()
    coord = BatchOcrCoordinator(corpus, clock=clock, ids=ids, provider=provider)
    selected = select_pending(list_candidates(corpus, clock=clock, ids=ids))
    settings = OCRSettings(model_name="fake-vision")
    run = coord.create_run(selected, settings=settings, force=False)
    progress = coord.run_blocking(run.ocr_run_id)
    assert progress.status == "completed"
    assert provider.calls == 2
    stored = OcrBatchRunStore(corpus).load(run.ocr_run_id)
    assert all(i.state == "completed" for i in stored.items)

    resumed = coord.resume(run.ocr_run_id, blocking=True)
    assert resumed.status == "completed"
    assert provider.calls == 2  # fingerprint skip; no new vision calls


def test_batch_ocr_resumes_multipage_partial_notebook(tmp_path: Path) -> None:
    """Batch OCR completes remaining pages after a partial single-notebook job."""
    from transcribe.services.job import JobCoordinator

    corpus = _corpus(tmp_path)
    clock, ids = FakeClock(), SequentialIds("mpart")
    root = corpus.projects_dir / "multi"
    projects = ProjectService(open_project_paths(root), clock=clock, ids=ids)
    projects.create("multi")
    ingest = IngestService(open_project_paths(root), clock=clock, ids=ids)
    fixture = Path(__file__).resolve().parents[1] / "fixtures" / "mini_multipage.pdf"
    ingest.import_path(fixture, render_dpi=72)
    paths = open_project_paths(root)
    projects = ProjectService(paths, clock=clock, ids=ids)
    settings = OCRSettings(model_name="fake-vision")
    projects.save_settings(projects.load(), settings)
    inner = JobCoordinator(paths, projects, FakeVisionOCRProvider(), clock=clock, ids=ids)

    class CancelAfterFirst(FakeVisionOCRProvider):
        def transcribe_image(self, **kwargs):
            result = super().transcribe_image(**kwargs)
            if self.calls == 1:
                inner.request_cancel()
            return result

    inner.provider = CancelAfterFirst()
    inner.run_blocking()
    project = projects.load()
    succeeded = sum(
        1
        for page in project.pages
        if (result := projects.load_page_result(page.page_id)) and result.status == "succeeded"
    )
    assert 1 <= succeeded < len(project.pages)

    batch_provider = FakeVisionOCRProvider()
    coord = BatchOcrCoordinator(corpus, clock=clock, ids=ids, provider=batch_provider)
    selected = select_by_ids(list_candidates(corpus, clock=clock, ids=ids), [project.id])
    run = coord.create_run(selected, settings=settings, force=False)
    progress = coord.run_blocking(run.ocr_run_id)
    assert progress.status == "completed"
    assert batch_provider.calls == len(project.pages) - succeeded
    for page in project.pages:
        result = projects.load_page_result(page.page_id)
        assert result is not None
        assert result.status == "succeeded"


def test_batch_ocr_model_load_circuits_within_notebook(tmp_path: Path) -> None:
    """Fatal vision load errors must skip remaining pages inside a batch notebook."""
    corpus = _corpus(tmp_path)
    clock, ids = FakeClock(), SequentialIds("mload")
    _make_notebook(corpus, "nb", clock=clock, ids=ids, pages=4)
    provider = FakeVisionOCRProvider(fail_codes=["model_load"] * 4)
    coord = BatchOcrCoordinator(corpus, clock=clock, ids=ids, provider=provider)
    selected = select_pending(list_candidates(corpus, clock=clock, ids=ids))
    run = coord.create_run(selected, settings=OCRSettings(model_name="fake-vision"), force=False)
    progress = coord.run_blocking(run.ocr_run_id)
    stored = OcrBatchRunStore(corpus).load(run.ocr_run_id)
    assert progress.status in {"completed", "partial"}
    assert provider.calls == 1
    assert stored.items[0].pages_failed == 1
    assert stored.items[0].pages_skipped == 3
    assert "cannot load this vision model" in (stored.items[0].error_message or "").lower()


def test_batch_ocr_cancel_does_not_start_next_notebook(tmp_path: Path) -> None:
    corpus = _corpus(tmp_path)
    clock, ids = FakeClock(), SequentialIds("can")
    _make_notebook(corpus, "first", clock=clock, ids=ids, pages=1)
    _make_notebook(corpus, "second", clock=clock, ids=ids, pages=1)

    coord = BatchOcrCoordinator(corpus, clock=clock, ids=ids)

    class CancelAfterFirst(FakeVisionOCRProvider):
        def transcribe_image(self, **kwargs):
            coord.request_cancel()
            return super().transcribe_image(**kwargs)

    provider = CancelAfterFirst()
    coord.provider = provider
    selected = select_pending(list_candidates(corpus, clock=clock, ids=ids))
    # Stable order by discover_project_roots (sorted folder names): first, second
    run = coord.create_run(selected, settings=OCRSettings(model_name="fake-vision"), force=False)
    progress = coord.run_blocking(run.ocr_run_id)
    stored = OcrBatchRunStore(corpus).load(run.ocr_run_id)
    states = [i.state for i in stored.items]
    assert "cancelled" in states
    assert states.count("completed") == 1
    assert progress.status in {"cancelled", "partial"}
    assert provider.calls == 1


def test_create_run_requires_model_and_notebooks(tmp_path: Path) -> None:
    corpus = _corpus(tmp_path)
    coord = BatchOcrCoordinator(corpus, clock=FakeClock(), ids=SequentialIds("req"))
    with pytest.raises(ValidationError, match="at least one"):
        coord.create_run([], settings=OCRSettings(model_name="fake-vision"))
    with pytest.raises(ValidationError, match="vision model"):
        clock, ids = FakeClock(), SequentialIds("req2")
        _make_notebook(corpus, "nb", clock=clock, ids=ids)
        selected = list_candidates(corpus, clock=clock, ids=ids)
        coord.create_run(selected, settings=OCRSettings(model_name=""))


def test_create_run_multipass_validation(tmp_path: Path) -> None:
    corpus = _corpus(tmp_path)
    clock, ids = FakeClock(), SequentialIds("mpv")
    _make_notebook(corpus, "nb", clock=clock, ids=ids)
    coord = BatchOcrCoordinator(corpus, clock=clock, ids=ids)
    selected = list_candidates(corpus, clock=clock, ids=ids)
    with pytest.raises(ValidationError, match="at least two"):
        coord.create_run(
            selected,
            settings=OCRSettings(
                model_name="a",
                text_model_name="text-rank",
                cleanup_model_name="text-rank",
            ),
            mode="multipass",
            vision_model_names=["only-one"],
        )
    with pytest.raises(ValidationError, match="text/cleanup"):
        coord.create_run(
            selected,
            settings=OCRSettings(model_name="a"),
            mode="multipass",
            vision_model_names=["a", "b"],
        )


def test_ocr_batch_run_multipass_round_trip(tmp_path: Path) -> None:
    from transcribe.corpus.ocr_run import OcrBatchItem, OcrBatchRun
    from transcribe.services.batch_ocr import settings_fingerprint

    corpus = _corpus(tmp_path)
    settings = OCRSettings(
        model_name="vision-a",
        text_model_name="text-rank",
        cleanup_model_name="text-rank",
    )
    fp = settings_fingerprint(
        settings,
        force=True,
        mode="multipass",
        vision_model_names=["vision-a", "vision-b"],
        multipass_cleanup_enabled=True,
    )
    run = OcrBatchRun(
        ocr_run_id="r-mp",
        created_at="t",
        updated_at="t",
        status="pending",
        force=True,
        settings=settings.as_dict(),
        settings_fingerprint=fp,
        mode="multipass",
        vision_model_names=["vision-a", "vision-b"],
        multipass_cleanup_enabled=True,
        items=[
            OcrBatchItem(notebook_id="a", state="pending", pass_id="pass-1"),
        ],
    )
    store = OcrBatchRunStore(corpus)
    store.save(run)
    loaded = store.load("r-mp")
    assert loaded.mode == "multipass"
    assert loaded.vision_model_names == ["vision-a", "vision-b"]
    assert loaded.multipass_cleanup_enabled is True
    assert loaded.items[0].pass_id == "pass-1"
    assert loaded.settings_fingerprint == fp
    legacy = {
        "format": "transcribe.ocr-batch-run",
        "schema_version": 1,
        "ocr_run_id": "legacy",
        "created_at": "t",
        "updated_at": "t",
        "status": "pending",
        "force": False,
        "settings": {"model_name": "x"},
        "settings_fingerprint": "abc",
        "items": [{"notebook_id": "n1", "state": "pending"}],
    }
    from transcribe.persistence.atomic import write_json_atomic

    write_json_atomic(corpus.ocr_run_path("legacy"), legacy)
    back = store.load("legacy")
    assert back.mode == "single"
    assert back.vision_model_names == []


def test_finalize_status_partial_when_cancelled_after_success() -> None:
    from transcribe.corpus.ocr_run import OcrBatchItem, OcrBatchRun

    run = OcrBatchRun(
        ocr_run_id="r1",
        created_at="t",
        updated_at="t",
        status="running",
        items=[
            OcrBatchItem(notebook_id="a", state="completed"),
            OcrBatchItem(notebook_id="b", state="cancelled"),
        ],
    )
    assert finalize_ocr_batch_status(run) == "partial"


def test_batch_run_records_provider_and_resume_rebuilds_it(tmp_path: Path, monkeypatch) -> None:
    """A resumed paddleocr run must not fall back to the Ollama client (M2)."""
    corpus = _corpus(tmp_path)
    clock, ids = FakeClock(), SequentialIds("prov")
    _make_notebook(corpus, "alpha", clock=clock, ids=ids)
    paddle = FakeVisionOCRProvider(provider_id="paddleocr")
    coord = BatchOcrCoordinator(corpus, clock=clock, ids=ids, provider=paddle)
    selected = select_pending(list_candidates(corpus, clock=clock, ids=ids))
    settings = OCRSettings(model_name="fake-vision", base_url="http://127.0.0.1:8112")
    run = coord.create_run(selected, settings=settings)
    assert run.provider_id == "paddleocr"
    stored = OcrBatchRunStore(corpus).load(run.ocr_run_id)
    assert stored.provider_id == "paddleocr"
    assert stored.as_dict()["provider_id"] == "paddleocr"

    built: list[tuple[str, str]] = []
    rebuilt = FakeVisionOCRProvider(provider_id="paddleocr")

    def fake_build(provider_id, base_url, **_kwargs):
        built.append((provider_id, base_url))
        return rebuilt

    monkeypatch.setattr("transcribe.providers.factory.build_vision_provider", fake_build)
    fresh = BatchOcrCoordinator(corpus, clock=clock, ids=ids)  # as `bulk-run resume` does
    progress = fresh.resume(run.ocr_run_id, blocking=True)
    assert progress.status == "completed"
    assert built and set(built) == {("paddleocr", "http://127.0.0.1:8112")}
    assert rebuilt.calls == 1


def test_batch_run_provider_defaults_to_ollama_and_is_omitted(tmp_path: Path) -> None:
    corpus = _corpus(tmp_path)
    clock, ids = FakeClock(), SequentialIds("dflt")
    _make_notebook(corpus, "alpha", clock=clock, ids=ids)
    coord = BatchOcrCoordinator(corpus, clock=clock, ids=ids, provider=FakeVisionOCRProvider())
    selected = select_pending(list_candidates(corpus, clock=clock, ids=ids))
    run = coord.create_run(selected, settings=OCRSettings(model_name="fake-vision"))
    assert run.provider_id == "ollama"  # unknown test ids are not persisted
    payload = run.as_dict()
    assert "provider_id" not in payload  # additive: pre-existing readers see no new key
    from transcribe.corpus.ocr_run import OcrBatchRun

    assert OcrBatchRun.from_dict(payload).provider_id == "ollama"


def test_batch_run_rejects_unknown_provider_id(tmp_path: Path) -> None:
    from transcribe.corpus.ocr_run import validate_ocr_batch_run

    corpus = _corpus(tmp_path)
    clock, ids = FakeClock(), SequentialIds("badp")
    _make_notebook(corpus, "alpha", clock=clock, ids=ids)
    coord = BatchOcrCoordinator(corpus, clock=clock, ids=ids, provider=FakeVisionOCRProvider())
    selected = select_pending(list_candidates(corpus, clock=clock, ids=ids))
    run = coord.create_run(selected, settings=OCRSettings(model_name="fake-vision"))
    run.provider_id = "cloud-thing"
    with pytest.raises(ValidationError):
        validate_ocr_batch_run(run)


def test_resumed_paddleocr_run_refuses_remote_sidecar(tmp_path: Path) -> None:
    """A hand-edited run record cannot send page images to a remote sidecar."""
    from transcribe.errors import ProviderError

    corpus = _corpus(tmp_path)
    clock, ids = FakeClock(), SequentialIds("rem")
    _make_notebook(corpus, "alpha", clock=clock, ids=ids)
    paddle = FakeVisionOCRProvider(provider_id="paddleocr")
    coord = BatchOcrCoordinator(corpus, clock=clock, ids=ids, provider=paddle)
    selected = select_pending(list_candidates(corpus, clock=clock, ids=ids))
    settings = OCRSettings(model_name="fake-vision", base_url="http://203.0.113.9:8112")
    run = coord.create_run(selected, settings=settings)
    fresh = BatchOcrCoordinator(corpus, clock=clock, ids=ids)
    with pytest.raises(ProviderError):
        fresh.resume(run.ocr_run_id, blocking=True)


def test_paddleocr_batch_restores_notebook_ollama_settings(tmp_path: Path) -> None:
    """A sidecar run must not leave the sidecar URL as the notebook's Ollama host."""
    corpus = _corpus(tmp_path)
    clock, ids = FakeClock(), SequentialIds("rst")
    root = _make_notebook(corpus, "alpha", clock=clock, ids=ids)
    projects = ProjectService(open_project_paths(root), clock=clock, ids=ids)
    before = projects.load().settings
    assert before.model_name == "fake-vision"

    paddle = FakeVisionOCRProvider(provider_id="paddleocr")
    paddle.base_url = "http://127.0.0.1:8112"  # matches the plan, so the job keeps this fake
    coord = BatchOcrCoordinator(corpus, clock=clock, ids=ids, provider=paddle)
    selected = select_pending(list_candidates(corpus, clock=clock, ids=ids))
    settings = OCRSettings(model_name="PaddleOCR-VL-1.6", base_url="http://127.0.0.1:8112")
    run = coord.create_run(selected, settings=settings)
    assert coord.run_blocking(run.ocr_run_id).status == "completed"
    assert paddle.calls == 1

    after = projects.load().settings
    assert after.base_url == before.base_url
    assert after.model_name == "fake-vision"
    page = projects.load().pages[0]
    assert projects.load_page_result(page.page_id).status == "succeeded"


def test_ollama_batch_still_persists_run_settings(tmp_path: Path) -> None:
    """Unchanged behaviour for the default backend: batch settings stay on the notebook."""
    corpus = _corpus(tmp_path)
    clock, ids = FakeClock(), SequentialIds("keep")
    root = _make_notebook(corpus, "alpha", clock=clock, ids=ids)
    coord = BatchOcrCoordinator(corpus, clock=clock, ids=ids, provider=FakeVisionOCRProvider())
    selected = select_pending(list_candidates(corpus, clock=clock, ids=ids))
    run = coord.create_run(selected, settings=OCRSettings(model_name="other-vision"))
    coord.run_blocking(run.ocr_run_id)
    projects = ProjectService(open_project_paths(root), clock=clock, ids=ids)
    assert projects.load().settings.model_name == "other-vision"
