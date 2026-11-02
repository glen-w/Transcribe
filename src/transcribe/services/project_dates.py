"""Date suggestion, approval, and inheritance for a notebook."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from transcribe.domain.dates import (
    ApproximateDate,
    DATE_SOURCE_EXTRACTED,
    DATE_SOURCE_INHERITED,
    DateRegression,
    extract_page_date,
    find_date_regressions,
    looks_like_unparsed_date_stamp,
)
from transcribe.domain.models import PageIndex, Project
from transcribe.domain.validation import validate_project
from transcribe.errors import ProjectError
from transcribe.persistence.atomic import read_json, write_json_atomic
from transcribe.persistence.locks import mutation_lock
from transcribe.persistence.schema import require_format
from transcribe.ports import to_iso


def splice_page_after_date_cluster(pages: Sequence[PageIndex], page_id: str) -> list[PageIndex]:
    """Return a new ``pages`` order with ``page_id`` placed by date cluster.

    Confirmed (``date_approved``) pages sharing date ``D`` form a contiguous
    cluster; the moved page is inserted after that cluster's last page. When no
    such cluster exists, insert after the last page whose approved date is not
    clearly after ``D`` (chronological). Does not mutate on-disk ``page_index``.
    """
    idx = next((i for i, page in enumerate(pages) if page.page_id == page_id), None)
    if idx is None:
        raise ProjectError(f"unknown page_id: {page_id}")
    page = pages[idx]
    if page.date is None:
        raise ProjectError("cannot move an undated page to a date cluster")
    target = page.date
    remaining = [p for p in pages if p.page_id != page_id]

    def _is_confirmed_cluster_member(other: PageIndex) -> bool:
        return bool(other.date_approved and other.date is not None and other.date == target)

    cluster_end: int | None = None
    i = 0
    while i < len(remaining):
        if _is_confirmed_cluster_member(remaining[i]):
            j = i
            while j + 1 < len(remaining) and _is_confirmed_cluster_member(remaining[j + 1]):
                j += 1
            cluster_end = j
            break
        i += 1

    if cluster_end is not None:
        insert_at = cluster_end + 1
    else:
        insert_at = 0
        for i, other in enumerate(remaining):
            if other.date is None or not other.date_approved:
                continue
            if not target.clearly_before(other.date):
                insert_at = i + 1

    return remaining[:insert_at] + [page] + remaining[insert_at:]


class ProjectDateOps:
    """Collaborator: page dates. Public API remains on ``ProjectService``."""

    def __init__(self, svc: Any) -> None:
        self._svc = svc

    def approve_page_date(
        self,
        page_id: str,
        date: ApproximateDate | None,
    ) -> tuple[Project, bool]:
        """Atomically set human-approved date (approved=True, source=None).

        When the date **value** changes, re-infers unapproved downstream pages
        (and the cover page when applicable) so inherited suggestions stay aligned
        with the new upstream date.

        Returns (project, date_value_changed) for the approved page only.
        """
        with mutation_lock(self._svc.paths.mutation_lock):
            payload = require_format(read_json(self._svc.paths.manifest), "transcribe.project")
            current = Project.from_dict(payload)
            page = self._svc._require_page(current, page_id)
            idx = next(i for i, p in enumerate(current.pages) if p.page_id == page_id)
            old = page.date
            page.set_date_state(date, approved=True, source=None)
            date_value_changed = old != page.date
            if date_value_changed:
                self._reinfer_unapproved_page_dates(
                    current.pages,
                    cover_page_id=current.cover_page_id,
                    start_idx=idx + 1,
                    cover_look_ahead=False,
                    skip_cover_post_pass_for_idx=idx,
                )
            current.updated_at = to_iso(self._svc.clock.now())
            validate_project(current)
            write_json_atomic(self._svc.paths.manifest, current.as_dict())
            return current, date_value_changed

    def list_date_regressions(self, project: Project | None = None) -> list[DateRegression]:
        """Notebook-order date regressions for bulk-approve honesty."""
        current = project if project is not None else self._svc.load(reconcile=False)
        return find_date_regressions([(page.page_id, page.date) for page in current.pages])

    def approve_all_suggested_dates(
        self,
        *,
        confirm_regressions: bool = False,
    ) -> tuple[Project, int, list[DateRegression]]:
        """Approve every unapproved suggested date in notebook order.

        Returns ``(project, approved_count, regressions)``. When regressions
        exist and ``confirm_regressions`` is false, writes nothing and returns
        count 0 so the UI can confirm.
        """
        with mutation_lock(self._svc.paths.mutation_lock):
            payload = require_format(read_json(self._svc.paths.manifest), "transcribe.project")
            current = Project.from_dict(payload)
            regressions = find_date_regressions(
                [(page.page_id, page.date) for page in current.pages]
            )
            if regressions and not confirm_regressions:
                return current, 0, regressions
            changed = 0
            for page in current.pages:
                if page.date is None or page.date_approved:
                    continue
                page.set_date_state(page.date, approved=True, source=None)
                changed += 1
            if changed:
                current.updated_at = to_iso(self._svc.clock.now())
                validate_project(current)
                write_json_atomic(self._svc.paths.manifest, current.as_dict())
            return current, changed, regressions

    def ignore_all_suggested_dates(self) -> tuple[Project, int]:
        """Clear every unapproved suggested date (human ignore)."""
        with mutation_lock(self._svc.paths.mutation_lock):
            payload = require_format(read_json(self._svc.paths.manifest), "transcribe.project")
            current = Project.from_dict(payload)
            changed = 0
            for page in current.pages:
                if page.date is None or page.date_approved:
                    continue
                page.set_date_state(None, approved=True, source=None)
                changed += 1
            if changed:
                current.updated_at = to_iso(self._svc.clock.now())
                validate_project(current)
                write_json_atomic(self._svc.paths.manifest, current.as_dict())
            return current, changed

    def suggest_page_date(self, page_id: str) -> bool:
        """Suggest date from effective_text or previous page. Returns True if date value changed.

        Reloads on-disk project under the mutation lock (never a job-start snapshot).
        Never overwrites an approved date.
        """
        with mutation_lock(self._svc.paths.mutation_lock):
            payload = require_format(read_json(self._svc.paths.manifest), "transcribe.project")
            current = Project.from_dict(payload)
            page = self._svc._require_page(current, page_id)
            if page.date is not None and page.date_approved:
                return False
            idx = next(i for i, p in enumerate(current.pages) if p.page_id == page_id)
            old_date = page.date
            old_approved = page.date_approved
            old_source = page.date_source
            result = self._svc._load_page_result_unlocked(page_id)
            text = result.effective_text() if result else None
            self._apply_suggestion(current.pages, idx, text, cover_page_id=current.cover_page_id)
            page = current.pages[idx]
            value_changed = old_date != page.date
            state_changed = (
                value_changed
                or old_approved != page.date_approved
                or old_source != page.date_source
            )
            if state_changed:
                current.updated_at = to_iso(self._svc.clock.now())
                validate_project(current)
                write_json_atomic(self._svc.paths.manifest, current.as_dict())
            return value_changed

    def fill_page_dates_ordered(self) -> int:
        """Walk pages in order; apply extract→inherit; one manifest write.

        Cover page (explicit ``cover_page_id``, else first page) inherits from the
        first dated page when it has no extractable stamp — done in a post-pass
        so later pages can donate a date.

        Returns number of pages whose date **value** changed.
        """
        with mutation_lock(self._svc.paths.mutation_lock):
            payload = require_format(read_json(self._svc.paths.manifest), "transcribe.project")
            current = Project.from_dict(payload)
            value_changed, any_change = self._reinfer_unapproved_page_dates(
                current.pages,
                cover_page_id=current.cover_page_id,
                start_idx=0,
            )
            if any_change:
                current.updated_at = to_iso(self._svc.clock.now())
                validate_project(current)
                write_json_atomic(self._svc.paths.manifest, current.as_dict())
            return value_changed

    def _reinfer_unapproved_page_dates(
        self,
        pages: list[PageIndex],
        *,
        cover_page_id: str | None,
        start_idx: int = 0,
        cover_look_ahead: bool = True,
        skip_cover_post_pass_for_idx: int | None = None,
    ) -> tuple[int, bool]:
        """Re-run extract→inherit for unapproved pages from ``start_idx`` (+ cover post-pass).

        ``cover_look_ahead`` (default true) lets undated approved cover pages inherit
        from the first dated page during a full ordered fill. Partial cascades after
        human date edits disable this so explicitly undated covers stay undated.

        Returns (date_value_changed_count, any_state_changed).
        """
        value_changed = 0
        any_change = False
        cascade_mode = not cover_look_ahead

        def _note(page: PageIndex, old_date, old_approved, old_source) -> None:
            nonlocal value_changed, any_change
            if old_date != page.date:
                value_changed += 1
            if (
                old_date != page.date
                or old_approved != page.date_approved
                or old_source != page.date_source
            ):
                any_change = True

        for idx in range(start_idx, len(pages)):
            page = pages[idx]
            if page.date_approved and (cascade_mode or page.date is not None):
                continue
            old_date = page.date
            old_approved = page.date_approved
            old_source = page.date_source
            result = self._svc._load_page_result_unlocked(page.page_id)
            text = result.effective_text() if result else None
            self._apply_suggestion(
                pages,
                idx,
                text,
                cover_page_id=cover_page_id,
            )
            _note(pages[idx], old_date, old_approved, old_source)

        cover_idx = self._cover_page_index(pages, cover_page_id)
        if cover_idx is not None and cover_idx != skip_cover_post_pass_for_idx:
            cover = pages[cover_idx]
            should_refresh = not cover.date_approved
            if cover_look_ahead and cover.date is None and cover.date_approved:
                should_refresh = True
            if should_refresh:
                old_date = cover.date
                old_approved = cover.date_approved
                old_source = cover.date_source
                result = self._svc._load_page_result_unlocked(cover.page_id)
                text = result.effective_text() if result else None
                self._apply_suggestion(
                    pages,
                    cover_idx,
                    text,
                    cover_page_id=cover_page_id,
                )
                _note(pages[cover_idx], old_date, old_approved, old_source)

        return value_changed, any_change

    @staticmethod
    def _cover_page_index(pages: list[PageIndex], cover_page_id: str | None) -> int | None:
        if not pages:
            return None
        if cover_page_id:
            for i, page in enumerate(pages):
                if page.page_id == cover_page_id:
                    return i
        return 0

    def _apply_suggestion(
        self,
        pages: list[PageIndex],
        idx: int,
        text: str | None,
        *,
        cover_page_id: str | None = None,
    ) -> None:
        page = pages[idx]
        if page.date is not None and page.date_approved:
            return
        extracted = extract_page_date(text)
        if extracted is not None:
            page.set_date_state(extracted, approved=False, source=DATE_SOURCE_EXTRACTED)
            return
        # Failed-looking stamp: stay undated for Review (do not inherit).
        if looks_like_unparsed_date_stamp(text):
            page.set_date_state(None, approved=True, source=None)
            return
        for prev in reversed(pages[:idx]):
            if prev.date is not None:
                page.set_date_state(prev.date, approved=False, source=DATE_SOURCE_INHERITED)
                return
        # Cover pages rarely carry a diary stamp; inherit the first dated page.
        cover_idx = self._cover_page_index(pages, cover_page_id)
        if cover_idx == idx:
            for other in pages:
                if other.page_id == page.page_id or other.date is None:
                    continue
                page.set_date_state(other.date, approved=False, source=DATE_SOURCE_INHERITED)
                return
        page.set_date_state(None, approved=True, source=None)
