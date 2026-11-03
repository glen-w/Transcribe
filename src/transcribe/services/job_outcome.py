"""Read-model over OCR job records and page attempts.

On-disk job status stays ``completed`` when a circuit opens. This module
classifies that case as ``completed_with_gaps`` for CLI, Diagnostics, and
doctor. It does not invent a ``completed_partial`` status.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from transcribe.domain.models import EMPTY_OUTPUT_CODE, Project
from transcribe.services.project import ProjectService


@dataclass(frozen=True)
class JobOutcome:
    """Classification of one job record plus optional page-attempt counts."""

    status: str
    outcome: str
    circuit_open: bool = False
    failed_pages: int = 0
    interrupted_pages: int = 0
    pending_pages: int = 0

    @property
    def completed_with_gaps(self) -> bool:
        return self.outcome == "completed_with_gaps"


def classify_job_outcome(
    *,
    status: str,
    circuit_open: bool = False,
    failed_pages: int = 0,
    interrupted_pages: int = 0,
    pending_pages: int = 0,
) -> JobOutcome:
    """Map a stored status to an operator-facing outcome.

    ``completed`` plus ``circuit_open`` is ``completed_with_gaps``. The stored
    status string is unchanged.
    """
    stored = str(status or "unknown")
    outcome = "completed_with_gaps" if stored == "completed" and circuit_open else stored
    return JobOutcome(
        status=stored,
        outcome=outcome,
        circuit_open=bool(circuit_open),
        failed_pages=int(failed_pages),
        interrupted_pages=int(interrupted_pages),
        pending_pages=int(pending_pages),
    )


def outcome_from_record(payload: dict[str, Any]) -> JobOutcome:
    return classify_job_outcome(
        status=str(payload.get("status") or "unknown"),
        circuit_open=bool(payload.get("circuit_open")),
        failed_pages=int(payload.get("failed") or 0),
    )


def count_page_attempts(project: Project, projects: ProjectService) -> tuple[int, int, int]:
    """Return ``(failed, interrupted, pending)`` over the latest attempt per page.

    Pages with ``ocr_policy=skip`` or ``page_role=scan`` are not OCR work.
    """
    failed = interrupted = pending = 0
    for page in project.pages:
        if page.skip_ocr():
            continue
        result = projects.load_page_result(page.page_id)
        if result is None or not result.attempts:
            pending += 1
            continue
        latest = result.attempts[-1]
        if latest.status == "failed" or (
            latest.error is not None and latest.error.code == EMPTY_OUTPUT_CODE
        ):
            failed += 1
        elif latest.status == "interrupted":
            interrupted += 1
        elif latest.status in ("running", "cancelled"):
            pending += 1
    return failed, interrupted, pending


def retry_failed_page_ids(project: Project, projects: ProjectService) -> list[str]:
    """Pages whose latest attempt failed, was interrupted, or returned no text.

    Skip-OCR and kept-scan pages are omitted. Verified successes stay out of
    this list so the normal fingerprint skip still applies to them.
    """
    chosen: list[str] = []
    for page in project.pages:
        if page.skip_ocr():
            continue
        result = projects.load_page_result(page.page_id)
        if result is None or not result.attempts:
            continue
        latest = result.attempts[-1]
        code = latest.error.code if latest.error is not None else ""
        if latest.status in ("failed", "interrupted") or code == EMPTY_OUTPUT_CODE:
            chosen.append(page.page_id)
    return chosen
