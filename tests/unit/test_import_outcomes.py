"""ImportRun product outcome buckets (no Streamlit)."""

from __future__ import annotations

from transcribe.corpus.duplicates import (
    CLASS_SAME_BYTES_OTHER_NOTEBOOK,
    CLASS_SAME_BYTES_SAME_NOTEBOOK,
    CLASS_SAME_FILENAME_DIFFERENT_BYTES,
)
from transcribe.corpus.import_outcomes import (
    BUCKET_DUPLICATED,
    BUCKET_FAILED,
    BUCKET_IMPORTED,
    BUCKET_NEEDS_REVIEW,
    bucket_import_item,
    format_outcome_summary,
    summarize_import_run,
)
from transcribe.corpus.import_run import ImportRun, ImportRunItemOutcome


def _item(item_id: str, state: str, classification: str | None = None) -> ImportRunItemOutcome:
    return ImportRunItemOutcome(
        item_id=item_id,
        state=state,
        skip_classification=classification,
    )


def _run(*items: ImportRunItemOutcome, status: str = "complete") -> ImportRun:
    return ImportRun(
        import_run_id="run-1",
        plan_id="plan-1",
        plan_fingerprint="fp",
        import_policy_id="skip_existing_v1",
        created_at="t0",
        updated_at="t1",
        status=status,
        items=list(items),
    )


def test_bucket_imported_failed_duplicated_needs_review() -> None:
    assert bucket_import_item(_item("a", "committed")) == BUCKET_IMPORTED
    assert bucket_import_item(_item("b", "failed")) == BUCKET_FAILED
    assert (
        bucket_import_item(_item("c", "skipped", CLASS_SAME_BYTES_SAME_NOTEBOOK))
        == BUCKET_DUPLICATED
    )
    assert (
        bucket_import_item(_item("d", "skipped", CLASS_SAME_FILENAME_DIFFERENT_BYTES))
        == BUCKET_NEEDS_REVIEW
    )
    assert (
        bucket_import_item(_item("e", "committed", CLASS_SAME_BYTES_OTHER_NOTEBOOK))
        == BUCKET_NEEDS_REVIEW
    )
    assert bucket_import_item(_item("f", "pending")) == BUCKET_NEEDS_REVIEW


def test_summarize_partial_run_flags_needs_review() -> None:
    run = _run(_item("a", "committed"), status="partial")
    counts = summarize_import_run(run)
    assert counts[BUCKET_IMPORTED] == 1
    assert counts[BUCKET_NEEDS_REVIEW] == 1
    text = format_outcome_summary(counts)
    assert "imported" in text
    assert "needs-review" in text
