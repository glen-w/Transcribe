"""Rank skip when comparison/composite is current; per-page rank errors."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from tests.acceptance.ocr_lifecycle.test_multipass_lifecycle import RankCompositeClient
from tests.conftest import FakeClock, SequentialIds
from tests.fakes import FakeVisionOCRProvider
from tests.ingest.test_ingest import _png_bytes
from tests.unit.test_ocr_lifecycle import _attempt
from transcribe.domain.models import ComparisonRecord, PageResult
from transcribe.errors import ValidationError
from transcribe.ingest import IngestService
from transcribe.providers.base import ModelInfo
from transcribe.services.job import JobCoordinator
from transcribe.services.multipass import MultiPassCoordinator
from transcribe.services.ocr_composite_state import should_skip_rank
from transcribe.services.ocr_rank_merge import RankCompositeOutcome
from transcribe.services.project import ProjectService, open_project_paths


def _coord(tmp_path: Path, pages: int = 2) -> tuple[ProjectService, JobCoordinator, MultiPassCoordinator]:
    paths = open_project_paths(tmp_path / "proj")
    clock, ids = FakeClock(), SequentialIds()
    projects = ProjectService(paths, clock=clock, ids=ids)
    projects.create("RankSkip")
    ingest = IngestService(paths, clock=clock, ids=ids)
    png = _png_bytes()
    for i in range(pages):
        ingest.import_bytes(f"p{i}.png", png)
    project = projects.load()
    settings = project.settings
    settings.text_model_name = "text-rank"
    settings.cleanup_model_name = "text-rank"
    settings.auto_activate_composite = True
    projects.save_settings(project, settings)
    models = [
        ModelInfo(name="vision-a", digest="digest-a", capabilities=["vision"], capability_known=True),
        ModelInfo(name="vision-b", digest="digest-b", capabilities=["vision"], capability_known=True),
    ]
    provider = FakeVisionOCRProvider(
        default_text="alpha notebook weather metro",
        models=models,
        digest="digest-a",
        verified=True,
    )
    jobs = JobCoordinator(paths, projects, provider, clock=clock, ids=ids)
    multi = MultiPassCoordinator(
        jobs=jobs,
        projects=projects,
        clock=clock,
        ids=ids,
        text_client=RankCompositeClient(responses={"default": "fallback"}),
    )
    return projects, jobs, multi


def test_should_skip_rank_when_composite_current() -> None:
    a1 = _attempt("a1", text="one", model="m1")
    a2 = _attempt("a2", text="two", model="m2", started="2020-01-02T00:00:00+00:00")
    comp = _attempt(
        "c1",
        text="one two",
        model="merger",
        kind="composite",
        started="2020-01-03T00:00:00+00:00",
        sources=["a1", "a2"],
    )
    result = PageResult(
        page_id="p",
        active_attempt_id="c1",
        attempts=[a1, a2, comp],
        comparison=ComparisonRecord(
            pass_id="old-uuid",
            ranked_attempt_ids=["a2", "a1"],
            created_at="2020-01-03T00:00:00+00:00",
        ),
    )
    assert should_skip_rank(result) is True


def test_should_not_skip_rank_without_comparison_or_composite() -> None:
    a1 = _attempt("a1", text="one", model="m1")
    a2 = _attempt("a2", text="two", model="m2", started="2020-01-02T00:00:00+00:00")
    result = PageResult(page_id="p", attempts=[a1, a2])
    assert should_skip_rank(result) is False


def test_second_multipass_does_not_rerank(tmp_path: Path) -> None:
    _projects, _jobs, multi = _coord(tmp_path, pages=1)
    first = multi.run_blocking(model_names=["vision-a", "vision-b"], force=False)
    assert first.status == "completed"
    assert first.pages_ranked >= 1

    calls: list[str] = []

    def boom(**kwargs):
        calls.append(kwargs["page_id"])
        raise AssertionError("rank should have been skipped")

    with patch(
        "transcribe.services.multipass.rank_and_composite_page",
        side_effect=boom,
    ):
        second = multi.run_compare_existing_blocking()
    assert second.status == "completed"
    assert calls == []
    assert second.pages_ranked >= 1


def test_rank_validation_error_does_not_abort_later_pages(tmp_path: Path) -> None:
    projects, _jobs, multi = _coord(tmp_path, pages=2)
    page_ids = [p.page_id for p in projects.load().pages]
    n = {"calls": 0}

    def flaky(**kwargs):
        n["calls"] += 1
        if kwargs["page_id"] == page_ids[0] and n["calls"] <= 2:
            raise ValidationError(
                "composite attempt x references missing source attempt 'gone'"
            )
        return RankCompositeOutcome(ranked=True, composited=True)

    with patch(
        "transcribe.services.multipass.rank_and_composite_page",
        side_effect=flaky,
    ):
        progress = multi.run_blocking(model_names=["vision-a", "vision-b"], force=False)
    assert progress.status == "completed"
    assert progress.pages_rank_failed >= 1
    assert progress.pages_ranked >= 1
    assert n["calls"] >= 3
