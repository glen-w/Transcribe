"""Domain PageResult / OCRSettings / provider-metadata unit coverage."""

from __future__ import annotations

from transcribe.domain.models import (
    DEFAULT_VISION_NUM_PREDICT,
    AttemptProvenance,
    ComparisonEntry,
    ComparisonRecord,
    OCRAttempt,
    OCRSettings,
    PageResult,
    filter_provider_metadata,
    prune_attempts,
)


def _attempt(
    attempt_id: str,
    *,
    raw: str | None = "raw",
    status: str = "succeeded",
    meta: dict | None = None,
) -> OCRAttempt:
    return OCRAttempt(
        attempt_id=attempt_id,
        status=status,
        input_fingerprint="fp",
        fingerprint_payload={},
        raw_text=raw,
        provenance=None,
        provider_metadata=meta or {},
        started_at="t0",
        completed_at="t1",
    )


def test_effective_text_prefers_edited_over_raw() -> None:
    result = PageResult(
        page_id="p1",
        active_attempt_id="a1",
        edited_text="edited",
        attempts=[_attempt("a1", raw="vision")],
    )
    assert result.effective_text() == "edited"


def test_effective_text_empty_edit_is_still_authoritative() -> None:
    """Empty string edit is intentional content, not 'no edit'."""
    result = PageResult(
        page_id="p1",
        active_attempt_id="a1",
        edited_text="",
        attempts=[_attempt("a1", raw="vision")],
    )
    assert result.edited_text is not None
    assert result.effective_text() == ""


def test_effective_text_falls_back_to_active_raw() -> None:
    result = PageResult(
        page_id="p1",
        active_attempt_id="a1",
        edited_text=None,
        attempts=[_attempt("a1", raw="vision")],
    )
    assert result.effective_text() == "vision"


def test_effective_text_none_without_active_attempt() -> None:
    result = PageResult(page_id="p1", attempts=[_attempt("a1")])
    assert result.effective_text() is None
    assert result.status == "pending"


def test_preferred_and_attempt_by_id_lookups() -> None:
    a1 = _attempt("a1", raw="one")
    a2 = _attempt("a2", raw="two")
    result = PageResult(
        page_id="p1",
        active_attempt_id="a1",
        preferred_attempt_id="a2",
        attempts=[a1, a2],
    )
    assert result.active_attempt() is a1
    assert result.preferred_attempt() is a2
    assert result.attempt_by_id("a2") is a2
    assert result.attempt_by_id("missing") is None
    assert result.preferred_attempt_id == "a2"


def test_preferred_attempt_none_when_id_missing() -> None:
    result = PageResult(
        page_id="p1",
        preferred_attempt_id="ghost",
        attempts=[_attempt("a1")],
    )
    assert result.preferred_attempt() is None


def test_filter_provider_metadata_allowlist_and_nan() -> None:
    assert filter_provider_metadata(None) == {}
    assert filter_provider_metadata({}) == {}
    cleaned = filter_provider_metadata(
        {
            "total_duration": 12,
            "retry_count": 1,
            "eval_count": 3,
            "truncated": True,
            "secret_header": "drop-me",
            "nested": {"x": 1},
            "bad_float": float("nan"),
            "load_duration": 0.5,
            "path": "pipeline",
            "pipeline_error": "RuntimeError: boom",
        }
    )
    assert cleaned == {
        "total_duration": 12,
        "retry_count": 1,
        "eval_count": 3,
        "truncated": True,
        "load_duration": 0.5,
        "path": "pipeline",
    }
    assert filter_provider_metadata({"path": "mlx_chat"}) == {"path": "mlx_chat"}
    assert filter_provider_metadata({"path": "/tmp/paddleocr-abc.png"}) == {}
    assert filter_provider_metadata({"path": "PIPELINE"}) == {}


def test_ocr_attempt_as_dict_filters_provider_metadata() -> None:
    attempt = _attempt("a1", meta={"total_duration": 9, "leak": "nope"})
    payload = attempt.as_dict()
    assert payload["provider_metadata"] == {"total_duration": 9}


def _num_predict(payload: dict) -> int:
    return OCRSettings.from_dict(payload).generation_options.num_predict


def test_ocr_settings_num_predict_clamps_and_defaults() -> None:
    assert _num_predict({}) == DEFAULT_VISION_NUM_PREDICT
    assert _num_predict({"generation_options": {"num_predict": "bad"}}) == DEFAULT_VISION_NUM_PREDICT
    assert _num_predict({"generation_options": {"num_predict": 10}}) == DEFAULT_VISION_NUM_PREDICT
    assert _num_predict({"generation_options": {"num_predict": 9000}}) == DEFAULT_VISION_NUM_PREDICT
    assert _num_predict({"generation_options": {"num_predict": 512}}) == 512


def test_ocr_settings_invalid_cleanup_and_prefer_modes_fall_back() -> None:
    settings = OCRSettings.from_dict(
        {"cleanup_mode": "nope", "prefer_mode": "also-nope"}
    )
    assert settings.cleanup_mode == "strip_leak"
    assert settings.prefer_mode == "prefer_is_promote"


def test_page_result_round_trip_preserves_schema_and_edit() -> None:
    original = PageResult(
        page_id="p1",
        active_attempt_id="a1",
        preferred_attempt_id="a1",
        edited_text="keep",
        attempts=[_attempt("a1", raw="vision")],
        schema_version=1,
        effective_text_origin="human_corrected",
    )
    loaded = PageResult.from_dict(original.as_dict())
    assert loaded.schema_version == 1
    assert loaded.edited_text == "keep"
    assert loaded.effective_text() == "keep"
    assert loaded.effective_text_origin == "human_corrected"
    assert loaded.as_dict()["status"] == "succeeded"


def test_page_result_round_trip_preserves_comparison_and_review_fields() -> None:
    comparison = ComparisonRecord(
        pass_id="pass-1",
        ranked_attempt_ids=["a2", "a1"],
        created_at="t0",
        entries=[
            ComparisonEntry(attempt_id="a2", score=0.9, rationale="clearer"),
            ComparisonEntry(attempt_id="a1", score=0.4, rationale=None),
        ],
        ranker_model_name="ranker",
        ranker_prompt_id="rank_v1",
        note="manual note",
    )
    original = PageResult(
        page_id="p1",
        active_attempt_id="a2",
        preferred_attempt_id="a2",
        edited_text=None,
        attempts=[_attempt("a1", raw="one"), _attempt("a2", raw="two")],
        comparison=comparison,
        schema_version=1,
        reviewed_text_fingerprint="text-fp",
        reviewed_evidence_fingerprint="ev-fp",
        source_disagreement_count=2,
        agreement_ratio=0.5,
    )
    loaded = PageResult.from_dict(original.as_dict())
    assert loaded.comparison is not None
    assert loaded.comparison.pass_id == "pass-1"
    assert loaded.comparison.ranked_attempt_ids == ["a2", "a1"]
    assert loaded.comparison.entries[0].score == 0.9
    assert loaded.comparison.ranker_model_name == "ranker"
    assert loaded.reviewed_text_fingerprint == "text-fp"
    assert loaded.reviewed_evidence_fingerprint == "ev-fp"
    assert loaded.source_disagreement_count == 2
    assert loaded.agreement_ratio == 0.5
    assert ComparisonRecord.from_dict(None) is None


def test_active_attempt_none_when_id_missing_from_list() -> None:
    result = PageResult(
        page_id="p1",
        active_attempt_id="ghost",
        attempts=[_attempt("a1")],
    )
    assert result.active_attempt() is None
    assert result.status == "pending"


def test_ocr_attempt_unknown_kind_falls_back_to_vision() -> None:
    payload = _attempt("a1").as_dict()
    payload["attempt_kind"] = "not-a-kind"
    loaded = OCRAttempt.from_dict(payload)
    assert loaded.attempt_kind == "vision"


def test_prune_attempts_when_protected_exceeds_max_retained() -> None:
    """Protected active/preferred/latest-per-model can exceed max_retained."""

    def _prov(model: str) -> AttemptProvenance:
        return AttemptProvenance(
            model_name=model,
            model_digest="d" * 64,
            model_identity_verified=True,
            prompt_id="faithful_markdown",
            prompt_version="1",
            prompt_sha256="a" * 64,
            prompt_text="p",
            input_sha256="b" * 64,
            preprocess_profile="none",
            preprocess_version=1,
            generation_options={},
            application_version="0",
            ollama_host="http://localhost:11434",
            request_id=model,
            render_id="r1",
        )

    attempts = [
        OCRAttempt(
            attempt_id=f"a{i}",
            status="succeeded",
            input_fingerprint=f"fp{i}",
            fingerprint_payload={},
            raw_text=f"t{i}",
            provenance=_prov(f"m{i}"),
            provider_metadata={},
            started_at=f"2020-01-{i + 1:02d}T00:00:00+00:00",
            completed_at=f"2020-01-{i + 1:02d}T00:00:00+00:00",
        )
        for i in range(6)
    ]
    kept = prune_attempts(
        attempts,
        active_attempt_id="a0",
        preferred_attempt_id="a1",
        max_retained=3,
    )
    ids = {a.attempt_id for a in kept}
    assert "a0" in ids
    assert "a1" in ids
    assert len(kept) == 3
    assert [a.started_at for a in kept] == sorted(a.started_at for a in kept)
