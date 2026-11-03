"""Failed-OCR grouping by attempt error code.

Review Failed OCR stays the queue. This read-model counts misses so Retry
these can build an ordinary OCR plan for one group. Uncorrected misses are
not fine-tune targets. No ``finetune_hold`` flag.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

from transcribe.domain.models import EMPTY_OUTPUT_CODE, TOKEN_REPEAT_CODE, PageResult, Project
from transcribe.persistence.atomic import read_json
from transcribe.services.project import ProjectService

MISS_GROUPS: tuple[str, ...] = (
    "empty_output",
    "token_repeat",
    "model_load",
    "timeout",
    "circuit_open",
    "other",
)

_KNOWN = frozenset(MISS_GROUPS)

MISS_DESK_COPY = (
    "An uncorrected miss is not a fine-tune target. Retry these pages with a "
    "vision model; do not export unread pages as training data."
)


def classify_miss_code(code: str | None) -> str:
    raw = str(code or "").strip() or "other"
    if raw in ("empty_output", EMPTY_OUTPUT_CODE):
        return "empty_output"
    if raw in ("token_repeat", TOKEN_REPEAT_CODE):
        return "token_repeat"
    if raw == "model_load":
        return "model_load"
    if raw in {"timeout", "circuit_open"}:
        return raw
    if raw in _KNOWN:
        return raw
    return "other"


def group_failed_ocr(
    project: Project,
    load_page_result: Callable[[str], PageResult | None],
    *,
    circuit_skipped_ids: Sequence[str] = (),
) -> dict[str, list[str]]:
    """Map miss-desk group → page ids. Unknown codes land in ``other``."""
    buckets: dict[str, list[str]] = {key: [] for key in MISS_GROUPS}
    skipped = set(circuit_skipped_ids)
    for page in project.pages:
        if page.skip_ocr():
            continue
        result = load_page_result(page.page_id)
        if result is not None and result.status == "failed":
            attempt = result.active_attempt()
            code = attempt.error.code if attempt is not None and attempt.error else "other"
            buckets[classify_miss_code(code)].append(page.page_id)
        elif page.page_id in skipped:
            buckets["circuit_open"].append(page.page_id)
    for page_id in circuit_skipped_ids:
        if page_id not in buckets["circuit_open"] and any(
            p.page_id == page_id for p in project.pages
        ):
            already = {pid for group in buckets.values() for pid in group}
            if page_id not in already:
                buckets["circuit_open"].append(page_id)
    return buckets


def circuit_skipped_page_ids(projects: ProjectService) -> list[str]:
    """Pages listed on the latest circuit-open job that still have no later attempt."""
    jobs_dir = projects.paths.jobs_dir
    if not jobs_dir.is_dir():
        return []
    records: list[dict[str, Any]] = []
    for path in jobs_dir.glob("*.json"):
        try:
            payload = read_json(path)
        except (OSError, ValueError, TypeError):
            continue
        if isinstance(payload, dict) and payload.get("circuit_open"):
            records.append(payload)
    if not records:
        return []
    records.sort(key=lambda row: str(row.get("started_at") or ""), reverse=True)
    latest = records[0]
    started = str(latest.get("started_at") or "")
    targets = [str(pid) for pid in (latest.get("target_page_ids") or []) if str(pid)]
    out: list[str] = []
    for page_id in targets:
        result = projects.load_page_result(page_id)
        if result is None or not result.attempts:
            out.append(page_id)
            continue
        latest_attempt = result.attempts[-1]
        completed = latest_attempt.completed_at or latest_attempt.started_at or ""
        if started and completed and completed >= started:
            continue
        out.append(page_id)
    return out


def miss_desk_page_ids(
    project: Project,
    load_page_result: Callable[[str], PageResult | None],
    *,
    group: str | None = None,
    page_ids: Sequence[str] | None = None,
    circuit_skipped_ids: Sequence[str] = (),
) -> list[str]:
    """Page ids for Retry these: one group, or an explicit subset of misses."""
    grouped = group_failed_ocr(
        project,
        load_page_result,
        circuit_skipped_ids=circuit_skipped_ids,
    )
    if page_ids is not None:
        allowed = {pid for ids in grouped.values() for pid in ids}
        return [pid for pid in page_ids if pid in allowed]
    key = classify_miss_code(group)
    return list(grouped.get(key, ()))
