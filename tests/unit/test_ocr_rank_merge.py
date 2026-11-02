"""Offline unit coverage for rank/composite helpers."""

from __future__ import annotations

from transcribe.domain.models import AttemptProvenance, OCRAttempt, PageResult
from transcribe.services.ocr_rank_merge import (
    RankCompositeOutcome,
    comparable_attempts,
    rank_and_composite_page,
)


def _vision(attempt_id: str, *, text: str, model: str = "m") -> OCRAttempt:
    return OCRAttempt(
        attempt_id=attempt_id,
        status="succeeded",
        input_fingerprint=f"fp-{attempt_id}",
        fingerprint_payload={},
        raw_text=text,
        provenance=AttemptProvenance(
            model_name=model,
            model_digest="d",
            model_identity_verified=True,
            prompt_id="p",
            prompt_version="1",
            prompt_sha256="",
            prompt_text="",
            input_sha256="",
            preprocess_profile="none",
            preprocess_version=0,
            generation_options={},
            application_version="0",
            ollama_host="http://127.0.0.1:11434",
            request_id=attempt_id,
            render_id="r1",
        ),
        provider_metadata={},
        started_at="t0",
        completed_at="t1",
        attempt_kind="vision",
    )


def test_comparable_attempts_none_and_empty() -> None:
    assert comparable_attempts(None) == []
    assert comparable_attempts(PageResult(page_id="p1", attempts=[])) == []


def test_comparable_attempts_keeps_latest_per_model() -> None:
    older = _vision("a1", text="one", model="m1")
    older.started_at = "2020-01-01T00:00:00Z"
    newer = _vision("a2", text="two", model="m1")
    newer.started_at = "2020-01-02T00:00:00Z"
    other = _vision("a3", text="three", model="m2")
    result = PageResult(page_id="p1", attempts=[older, newer, other])
    ids = {a.attempt_id for a in comparable_attempts(result)}
    assert ids == {"a2", "a3"}


def test_rank_and_composite_requires_two_vision_attempts(tmp_path) -> None:
    from tests.conftest import FakeClock, SequentialIds
    from transcribe.services.project import ProjectService, open_project_paths

    paths = open_project_paths(tmp_path / "proj")
    clock, ids = FakeClock(), SequentialIds()
    projects = ProjectService(paths, clock=clock, ids=ids)
    projects.create("rank")
    outcome = rank_and_composite_page(
        projects=projects,
        page_id="missing",
        pass_id="pass-1",
        ranker_model_name="ranker",
        base_url="http://127.0.0.1:11434",
        ids=ids,
        clock=clock,
        auto_activate_composite=False,
        prefer_mode="prefer_is_promote",
        prior_active_id=None,
        attempts=[_vision("only", text="solo")],
        text_client=None,
    )
    assert outcome == RankCompositeOutcome(ranked=False, composited=False)
