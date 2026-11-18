"""Schedulable OCR vs deferred error tails (stdlib + on-disk page results).

A page×model slot is:

- ``succeeded`` — vision attempt with text for that model
- ``deferred`` — ≥N fingerprint-compatible durable failures (until ``--force``)
- ``open`` — still worth a night-queue attempt

Notebooks with no ``open`` slots drop off ``ocr-queue``. Rollup / glance still
count only succeeded runs, so deferred holes stay visible.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any, Literal

from transcribe.domain.fingerprint import (
    digest_from_fingerprint_payload,
    fingerprints_compatible_for_skip,
)
from transcribe.domain.models import EMPTY_OUTPUT_CODE, TOKEN_REPEAT_CODE

PageModelState = Literal["succeeded", "deferred", "open"]

TIERS = ("recent", "from_2023", "rest")
OCR_FAIL_DEFER_THRESHOLD = 3
DURABLE_FAIL_CODES = frozenset(
    {
        TOKEN_REPEAT_CODE,
        EMPTY_OUTPUT_CODE,
        "validate",
        "rank_failed",
    }
)
RANK_FAIL_DEFER_THRESHOLD = 2
RANK_FAIL_CODES = frozenset({"validate", "rank_failed"})


def normalize_ocr_model_name(name: str) -> str:
    n = (name or "").strip().lower()
    n = n.removesuffix(":latest")
    return n


def parse_models(names: list[str] | tuple[str, ...] | set[str]) -> set[str]:
    return {normalize_ocr_model_name(n) for n in names if str(n).strip()}


def notebook_max_date(pages: list) -> tuple[int, int, int] | None:
    best: tuple[int, int, int] | None = None
    for page in pages:
        if not isinstance(page, dict):
            continue
        date = page.get("date")
        if not isinstance(date, dict):
            continue
        year = date.get("y")
        if not isinstance(year, int) or year <= 0:
            continue
        month = date.get("m") if isinstance(date.get("m"), int) else 0
        day = date.get("d") if isinstance(date.get("d"), int) else 0
        key = (year, month, day)
        if best is None or key > best:
            best = key
    return best


def tier_for(max_date: tuple[int, int, int] | None) -> str:
    if max_date is None:
        return "rest"
    year = max_date[0]
    if year >= 2025:
        return "recent"
    if year >= 2023:
        return "from_2023"
    return "rest"


def _attempt_model(attempt: dict) -> str:
    provenance = attempt.get("provenance") or {}
    name = ""
    if isinstance(provenance, dict):
        name = provenance.get("model_name") or ""
    if not name:
        payload = attempt.get("fingerprint_payload") or {}
        if isinstance(payload, dict):
            name = payload.get("model_name") or ""
    return normalize_ocr_model_name(str(name))


def _attempt_text(attempt: dict) -> str:
    return (attempt.get("raw_text") or attempt.get("text") or "").strip()


def _error_code(attempt: dict) -> str:
    err = attempt.get("error")
    if isinstance(err, dict):
        return str(err.get("code") or "")
    return ""


def _fingerprint_key(attempt: dict) -> str:
    digest = str(attempt.get("input_fingerprint") or "")
    payload = attempt.get("fingerprint_payload")
    if isinstance(payload, dict) and payload:
        try:
            return digest_from_fingerprint_payload(payload)
        except (TypeError, ValueError, OverflowError):
            return digest
    return digest


def succeeded_vision_models(result: dict) -> set[str]:
    found: set[str] = set()
    for attempt in result.get("attempts") or []:
        if not isinstance(attempt, dict):
            continue
        if attempt.get("status") != "succeeded":
            continue
        kind = attempt.get("attempt_kind") or "vision"
        if kind != "vision":
            continue
        if not _attempt_text(attempt):
            continue
        model = _attempt_model(attempt)
        if model:
            found.add(model)
    return found


def count_durable_failures(
    result: dict,
    *,
    model_name: str,
    current_digest: str | None = None,
) -> int:
    """Fingerprint-compatible durable vision failures for ``model_name``."""
    target = normalize_ocr_model_name(model_name)
    groups: Counter[str] = Counter()
    matched = 0
    for attempt in result.get("attempts") or []:
        if not isinstance(attempt, dict):
            continue
        if attempt.get("status") != "failed":
            continue
        kind = attempt.get("attempt_kind") or "vision"
        if kind != "vision":
            continue
        if _attempt_model(attempt) != target:
            continue
        if _error_code(attempt) not in DURABLE_FAIL_CODES:
            continue
        stored = str(attempt.get("input_fingerprint") or "")
        payload = attempt.get("fingerprint_payload")
        payload_dict = payload if isinstance(payload, dict) else None
        if current_digest:
            if not fingerprints_compatible_for_skip(
                current_digest,
                stored_digest=stored,
                fingerprint_payload=payload_dict,
            ):
                continue
            matched += 1
        else:
            groups[_fingerprint_key(attempt)] += 1
    if current_digest:
        return matched
    return max(groups.values(), default=0)


def page_model_state(
    result: dict | None,
    model: str,
    *,
    current_digest: str | None = None,
    defer_threshold: int = OCR_FAIL_DEFER_THRESHOLD,
) -> PageModelState:
    target = normalize_ocr_model_name(model)
    if not target:
        return "open"
    if result is None:
        return "open"
    if target in succeeded_vision_models(result):
        return "succeeded"
    n = count_durable_failures(
        result, model_name=target, current_digest=current_digest
    )
    if n >= defer_threshold:
        return "deferred"
    return "open"


def page_has_schedulable_ocr(
    result: dict | None,
    models: set[str],
    *,
    current_digests: dict[str, str] | None = None,
) -> bool:
    for model in models:
        digest = None
        if current_digests:
            digest = current_digests.get(model) or current_digests.get(
                normalize_ocr_model_name(model)
            )
        if page_model_state(result, model, current_digest=digest) == "open":
            return True
    return False


def load_page_result_dict(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def notebook_has_schedulable_ocr(
    root: Path,
    models: set[str],
    pages: list | None = None,
) -> bool:
    """True if any page still has an open (not succeeded, not deferred) model."""
    if not models:
        return False
    if pages is None:
        project_path = root / "project.json"
        if not project_path.is_file():
            return False
        try:
            data = json.loads(project_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return False
        pages = data.get("pages") or []
    results_dir = root / "results"
    for page in pages:
        if not isinstance(page, dict):
            return True
        page_id = page.get("page_id")
        if not page_id:
            return True
        result = load_page_result_dict(results_dir / f"{page_id}.json")
        if page_has_schedulable_ocr(result, models):
            return True
    return False


def list_schedulable_notebooks(
    projects_dir: Path,
    models: set[str],
    *,
    tier: str | None = None,
    limit: int = 0,
) -> list[Path]:
    """Notebook roots with schedulable OCR, newest diary date first, then title."""
    if tier is not None and tier not in TIERS:
        raise ValueError(f"unknown tier {tier!r}")
    if not models or not projects_dir.is_dir():
        return []
    rows: list[tuple[tuple[int, int, int], str, Path]] = []
    for child in projects_dir.iterdir():
        if not child.is_dir():
            continue
        project_path = child / "project.json"
        if not project_path.is_file():
            continue
        try:
            data = json.loads(project_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        pages = data.get("pages") or []
        if not pages:
            continue
        max_date = notebook_max_date(pages)
        if tier is not None and tier_for(max_date) != tier:
            continue
        if not notebook_has_schedulable_ocr(child, models, pages=pages):
            continue
        title = (data.get("title") or child.name).strip() or child.name
        rows.append((max_date or (0, 0, 0), title.lower(), child))
    rows.sort(key=lambda row: (-row[0][0], -row[0][1], -row[0][2], row[1]))
    if limit > 0:
        rows = rows[:limit]
    return [path for _date, _title, path in rows]
