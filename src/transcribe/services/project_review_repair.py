"""Review-status repair for empty / looping OCR successes."""

from __future__ import annotations

from typing import Any

from transcribe.domain.models import (
    AttemptError,
    EMPTY_OUTPUT_CODE,
    EMPTY_OUTPUT_MESSAGE,
    TOKEN_REPEAT_CODE,
    TRUNCATED_REPEAT_MESSAGE,
    PageResult,
    Project,
)
from transcribe.domain.validation import validate_page_result, validate_project
from transcribe.persistence.atomic import read_json, write_json_atomic
from transcribe.persistence.locks import mutation_lock
from transcribe.persistence.schema import require_format
from transcribe.ports import to_iso


def _review_fingerprints_match(result: PageResult | None) -> bool:
    from transcribe.services.ocr_composite_state import (
        evidence_fingerprint,
        reviewed_text_fingerprint,
    )

    if result is None:
        return False
    if not result.reviewed_text_fingerprint or not result.reviewed_evidence_fingerprint:
        return False
    text = result.effective_text() or ""
    return result.reviewed_text_fingerprint == reviewed_text_fingerprint(
        text
    ) and result.reviewed_evidence_fingerprint == evidence_fingerprint(result)


def _review_should_invalidate(before: PageResult | None, after: PageResult) -> bool:
    from transcribe.services.ocr_composite_state import evidence_fingerprint

    if before is None:
        return True
    if (before.effective_text() or "") != (after.effective_text() or ""):
        return True
    if before.active_attempt_id != after.active_attempt_id:
        return True
    return evidence_fingerprint(before) != evidence_fingerprint(after)


class ProjectReviewRepair:
    """Collaborator: review validity repairs. Public API remains on ``ProjectService``."""

    def __init__(self, svc: Any) -> None:
        self._svc = svc

    def repair_empty_successes(self, page_id: str) -> PageResult | None:
        """Demote succeeded-but-empty vision attempts and restore a good active.

        Historical empty ``succeeded`` writes (e.g. DeepSeek-OCR + faithful prompt)
        become ``failed`` / ``empty_output``. If the active attempt has no text and
        another succeeded-with-text exists, that reading becomes current.
        """
        from transcribe.services.project import _latest_succeeded_with_text, _origin_from_active

        with mutation_lock(self._svc.paths.mutation_lock):
            existing = self._svc._load_page_result_unlocked(page_id)
            if existing is None:
                return None
            before = PageResult.from_dict(existing.as_dict())
            changed = False
            for i, attempt in enumerate(existing.attempts):
                if (attempt.attempt_kind or "vision") != "vision":
                    continue
                if attempt.status != "succeeded":
                    continue
                if (attempt.raw_text or "").strip():
                    continue
                attempt.status = "failed"
                attempt.error = AttemptError(
                    code=EMPTY_OUTPUT_CODE,
                    message=EMPTY_OUTPUT_MESSAGE,
                    retriable=False,
                )
                existing.attempts[i] = attempt
                changed = True
            active = existing.active_attempt()
            prior = _latest_succeeded_with_text(existing.attempts)
            if prior is not None and (
                active is None
                or active.status != "succeeded"
                or not (active.raw_text or "").strip()
            ):
                existing.active_attempt_id = prior.attempt_id
                if existing.edited_text is None:
                    existing.effective_text_origin = _origin_from_active(existing)
                changed = True
            if not changed:
                return existing
            existing.updated_at = to_iso(self._svc.clock.now())
            validate_page_result(existing, expected_page_id=page_id)
            write_json_atomic(self._svc.paths.result_path(page_id), existing.as_dict())
            self._invalidate_review_unlocked(page_id, before=before, after=existing)
            return existing

    def repair_truncated_repetition_successes(self, page_id: str) -> PageResult | None:
        """Demote truncated+looping vision successes so they do not skip forever.

        Pre-hardening attempts could hit ``num_predict`` with repeated text and
        still store ``succeeded``. Those fingerprints would skip on the next job.
        Demote to ``failed`` / ``token_repeat`` (same code as live truncated+rep
        fails). If the active reading was one of them, restore another succeeded
        vision attempt with text when available.
        """
        from transcribe.services.project import _latest_succeeded_with_text, _origin_from_active
        from transcribe.services.review_signals import (
            text_echoes_prompt,
            text_has_long_repetition,
            text_has_repetition,
        )

        with mutation_lock(self._svc.paths.mutation_lock):
            existing = self._svc._load_page_result_unlocked(page_id)
            if existing is None:
                return None
            before = PageResult.from_dict(existing.as_dict())
            changed = False
            for i, attempt in enumerate(existing.attempts):
                if (attempt.attempt_kind or "vision") != "vision":
                    continue
                if attempt.status != "succeeded":
                    continue
                meta = attempt.provider_metadata or {}
                if not bool(meta.get("truncated")):
                    continue
                raw = attempt.raw_text or ""
                prompt = ""
                if attempt.provenance is not None:
                    prompt = attempt.provenance.prompt_text or ""
                looping = text_has_repetition(raw) or text_has_long_repetition(raw)
                leaked = text_echoes_prompt(raw, prompt)
                if not (looping or leaked):
                    continue
                attempt.status = "failed"
                attempt.error = AttemptError(
                    code=TOKEN_REPEAT_CODE,
                    message=TRUNCATED_REPEAT_MESSAGE,
                    retriable=False,
                )
                existing.attempts[i] = attempt
                changed = True
            active = existing.active_attempt()
            prior = _latest_succeeded_with_text(existing.attempts)
            if prior is not None and (
                active is None
                or active.status != "succeeded"
                or not (active.raw_text or "").strip()
            ):
                existing.active_attempt_id = prior.attempt_id
                if existing.edited_text is None:
                    existing.effective_text_origin = _origin_from_active(existing)
                changed = True
            if not changed:
                return existing
            existing.updated_at = to_iso(self._svc.clock.now())
            validate_page_result(existing, expected_page_id=page_id)
            write_json_atomic(self._svc.paths.result_path(page_id), existing.as_dict())
            self._invalidate_review_unlocked(page_id, before=before, after=existing)
            return existing

    def repair_review_validity(self, page_id: str) -> str:
        """If status is reviewed but fingerprints mismatch, move to needs_attention."""
        with mutation_lock(self._svc.paths.mutation_lock):
            project = Project.from_dict(
                require_format(read_json(self._svc.paths.manifest), "transcribe.project")
            )
            page = self._svc._require_page(project, page_id)
            status = page.review_status or "unreviewed"
            result = self._svc._load_page_result_unlocked(page_id)
            if status == "reviewed" and not _review_fingerprints_match(result):
                self._write_review_status_unlocked(page_id, "needs_attention")
                return "needs_attention"
            return status

    def _invalidate_review_unlocked(
        self,
        page_id: str,
        *,
        before: PageResult | None,
        after: PageResult,
    ) -> None:
        if not after.reviewed_text_fingerprint and not (
            before and before.reviewed_text_fingerprint
        ):
            return
        payload = require_format(read_json(self._svc.paths.manifest), "transcribe.project")
        project = Project.from_dict(payload)
        page = next((p for p in project.pages if p.page_id == page_id), None)
        if page is None or (page.review_status or "unreviewed") != "reviewed":
            return
        if _review_should_invalidate(before, after):
            self._write_review_status_unlocked(page_id, "needs_attention")

    def _write_review_status_unlocked(self, page_id: str, status: str) -> Project:
        payload = require_format(read_json(self._svc.paths.manifest), "transcribe.project")
        current = Project.from_dict(payload)
        page = self._svc._require_page(current, page_id)
        page.review_status = status
        current.updated_at = to_iso(self._svc.clock.now())
        validate_project(current)
        write_json_atomic(self._svc.paths.manifest, current.as_dict())
        return current
