"""Domain PageResult / OCRSettings / provider-metadata unit coverage."""

from __future__ import annotations

from transcribe.domain.models import (
    DEFAULT_VISION_NUM_PREDICT,
    OCRAttempt,
    OCRSettings,
    PageResult,
    filter_provider_metadata,
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
        }
    )
    assert cleaned == {
        "total_duration": 12,
        "retry_count": 1,
        "eval_count": 3,
        "truncated": True,
        "load_duration": 0.5,
    }


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
