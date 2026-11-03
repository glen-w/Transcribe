"""Human verdict on a second-pass OCR cleanup proposal.

The quality store already records accept/reject. This module is the Review
writer that can also persist the proposal as ``edited_text``. It never
deletes the attempt ``cleanup`` object. Visual declutter is a different
control and must not call this.
"""

from __future__ import annotations

from dataclasses import dataclass

from transcribe.domain.models import EDIT_GATE_CHOICES, OCRAttempt, PageResult
from transcribe.errors import ProjectError
from transcribe.runtime_paths import RuntimePaths, build_runtime_paths
from transcribe.services.project import ProjectService
from transcribe.services.quality import QualityRatingStore


@dataclass(frozen=True)
class CleanupProposal:
    """User-facing pair when a cleanup model produced distinct text."""

    vision_text: str
    proposal_text: str
    execution_status: str
    acceptance_status: str


def cleanup_proposal(attempt: OCRAttempt | None) -> CleanupProposal | None:
    """Return a proposal when cleanup ran and stored distinct vision vs candidate.

    ``provider_ok`` plus ``pre_cleanup_text`` is the applied case: vision is
    the pre-cleanup text and the proposal is attempt ``raw_text``. Failed or
    rejected cleanup stores no candidate, so there is nothing to Accept.
    """
    if attempt is None or attempt.cleanup is None:
        return None
    record = attempt.cleanup
    if record.execution_status != "provider_ok":
        return None
    vision = (record.pre_cleanup_text or "").strip()
    proposal = (attempt.raw_text or "").strip()
    if not vision or not proposal or vision == proposal:
        return None
    return CleanupProposal(
        vision_text=record.pre_cleanup_text or "",
        proposal_text=attempt.raw_text or "",
        execution_status=record.execution_status,
        acceptance_status=record.acceptance_status,
    )


def can_accept_proposal(proposal: CleanupProposal | None) -> bool:
    return proposal is not None


def accept_cleanup_proposal(
    projects: ProjectService,
    page_id: str,
    *,
    edit_gate_choice: str | None = None,
    runtime: RuntimePaths | None = None,
    quality: QualityRatingStore | None = None,
) -> PageResult:
    """Write the proposal into ``edited_text`` unless the user keeps an existing edit.

    When no edit is present, Accept is the save. When ``edited_text`` is set,
    ``edit_gate_choice`` is required: ``keep_edit`` records the quality accept
    and leaves the edit; ``adopt_new`` replaces it with the proposal.
    """
    result = projects.load_page_result(page_id)
    if result is None:
        raise ProjectError(f"no page result for {page_id}")
    attempt = result.active_attempt()
    proposal = cleanup_proposal(attempt)
    if proposal is None:
        raise ProjectError("no cleanup proposal to accept")
    existing_edit = result.edited_text
    if existing_edit is not None:
        if edit_gate_choice not in EDIT_GATE_CHOICES:
            raise ProjectError(
                "edit_gate_choice required when edited_text is set (keep_edit|adopt_new)"
            )
        if edit_gate_choice == "keep_edit":
            _record_cleanup(projects, page_id, "accept", runtime=runtime, quality=quality)
            return result
    saved = projects.save_user_edit(
        page_id,
        proposal.proposal_text,
        origin="human_selected",
    )
    _record_cleanup(projects, page_id, "accept", runtime=runtime, quality=quality)
    return saved


def reject_cleanup_proposal(
    projects: ProjectService,
    page_id: str,
    *,
    runtime: RuntimePaths | None = None,
    quality: QualityRatingStore | None = None,
) -> PageResult:
    """Record a reject. Effective text and the cleanup object stay as they are."""
    result = projects.load_page_result(page_id)
    if result is None:
        raise ProjectError(f"no page result for {page_id}")
    if cleanup_proposal(result.active_attempt()) is None:
        raise ProjectError("no cleanup proposal to reject")
    _record_cleanup(projects, page_id, "reject", runtime=runtime, quality=quality)
    after = projects.load_page_result(page_id)
    assert after is not None
    return after


def _record_cleanup(
    projects: ProjectService,
    page_id: str,
    verdict: str,
    *,
    runtime: RuntimePaths | None,
    quality: QualityRatingStore | None,
) -> None:
    store = quality or QualityRatingStore(runtime or build_runtime_paths())
    project = projects.load(reconcile=False)
    store.record(
        "cleanup",
        verdict,  # type: ignore[arg-type]
        project_id=project.id,
        page_id=page_id,
        notes="review",
    )
