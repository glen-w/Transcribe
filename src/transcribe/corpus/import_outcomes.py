"""Product outcome buckets over ImportRun item state + skip_classification."""

from __future__ import annotations

from collections import Counter
from typing import Iterable

from transcribe.corpus.duplicates import (
    CLASS_SAME_BYTES_OTHER_NOTEBOOK,
    CLASS_SAME_BYTES_SAME_NOTEBOOK,
    CLASS_SAME_FILENAME_DIFFERENT_BYTES,
)
from transcribe.corpus.import_run import ImportRun, ImportRunItemOutcome

BUCKET_IMPORTED = "imported"
BUCKET_FAILED = "failed"
BUCKET_DUPLICATED = "duplicated"
BUCKET_NEEDS_REVIEW = "needs_review"
BUCKET_OTHER = "other"

BUCKET_LABELS = {
    BUCKET_IMPORTED: "imported",
    BUCKET_FAILED: "failed",
    BUCKET_DUPLICATED: "duplicated",
    BUCKET_NEEDS_REVIEW: "needs-review",
    BUCKET_OTHER: "other",
}


def bucket_import_item(item: ImportRunItemOutcome) -> str:
    """Map one ImportRun item onto a product outcome bucket."""
    classification = item.skip_classification
    if item.state == "committed":
        if classification == CLASS_SAME_BYTES_OTHER_NOTEBOOK:
            return BUCKET_NEEDS_REVIEW
        return BUCKET_IMPORTED
    if item.state == "failed":
        return BUCKET_FAILED
    if item.state == "skipped":
        if classification == CLASS_SAME_BYTES_SAME_NOTEBOOK:
            return BUCKET_DUPLICATED
        if classification in {
            CLASS_SAME_FILENAME_DIFFERENT_BYTES,
            CLASS_SAME_BYTES_OTHER_NOTEBOOK,
        }:
            return BUCKET_NEEDS_REVIEW
        return BUCKET_DUPLICATED
    if item.state in {"pending", "cancelled_pending"}:
        return BUCKET_NEEDS_REVIEW
    return BUCKET_OTHER


def summarize_import_run(run: ImportRun) -> dict[str, int]:
    """Count product buckets for a run. Partial runs always flag needs-review."""
    counts: Counter[str] = Counter(bucket_import_item(item) for item in run.items)
    if run.status == "partial" and counts[BUCKET_NEEDS_REVIEW] == 0:
        counts[BUCKET_NEEDS_REVIEW] = 1
    return {
        BUCKET_IMPORTED: int(counts.get(BUCKET_IMPORTED, 0)),
        BUCKET_FAILED: int(counts.get(BUCKET_FAILED, 0)),
        BUCKET_DUPLICATED: int(counts.get(BUCKET_DUPLICATED, 0)),
        BUCKET_NEEDS_REVIEW: int(counts.get(BUCKET_NEEDS_REVIEW, 0)),
        BUCKET_OTHER: int(counts.get(BUCKET_OTHER, 0)),
    }


def format_outcome_summary(counts: dict[str, int]) -> str:
    parts = [
        f"{counts[key]} {BUCKET_LABELS[key]}"
        for key in (
            BUCKET_IMPORTED,
            BUCKET_FAILED,
            BUCKET_DUPLICATED,
            BUCKET_NEEDS_REVIEW,
        )
        if counts.get(key)
    ]
    return " · ".join(parts) if parts else "no items"


def iter_bucketed_items(
    items: Iterable[ImportRunItemOutcome],
) -> list[tuple[str, ImportRunItemOutcome]]:
    return [(bucket_import_item(item), item) for item in items]
