"""Dry-run-first batch page metadata mutations.

One project write per notebook. Refuses an empty selection and refuses while
that notebook's OCR or analysis lock is held. Does not delete pages.
"""

from __future__ import annotations

from dataclasses import dataclass

from transcribe.domain.dates import normalize_tags
from transcribe.errors import JobConflictError, ProjectError
from transcribe.persistence.atomic import read_json, write_json_atomic
from transcribe.persistence.locks import analysis_lock_held, job_lock_held, mutation_lock
from transcribe.persistence.schema import require_format
from transcribe.ports import to_iso
from transcribe.runtime_paths import RuntimePaths
from transcribe.services.archive import ArchiveFilters, bump_archive_generation
from transcribe.services.project import ProjectService

ACTIONS = frozenset({"approve_dates", "ignore", "unignore", "add_tag", "remove_tag"})


def filters_are_empty(filters: ArchiveFilters) -> bool:
    """True when a saved search would match the whole corpus."""
    return not any(
        (
            filters.query.strip(),
            filters.tags,
            filters.people,
            filters.places,
            filters.collection_id.strip(),
            filters.notebook_ids,
            filters.project_tags,
            filters.media_types,
            filters.period != "all",
            filters.bookmarked_only,
            not filters.include_undated,
        )
    )


@dataclass(frozen=True)
class BatchMetadataResult:
    action: str
    selected: int
    changed: int
    dry_run: bool


def apply_batch_metadata(
    projects: ProjectService,
    page_ids: list[str],
    action: str,
    *,
    tag: str = "",
    dry_run: bool = True,
    runtime: RuntimePaths | None = None,
) -> BatchMetadataResult:
    if action not in ACTIONS:
        raise ProjectError(f"unknown batch action {action!r}")
    if not page_ids:
        raise ProjectError("batch metadata refuses an empty page selection")
    if action in ("add_tag", "remove_tag") and not normalize_tags([tag]):
        raise ProjectError("add_tag and remove_tag require a tag slug")
    if job_lock_held(projects.paths.job_lock):
        raise JobConflictError("cannot edit page metadata while an OCR job is running")
    if analysis_lock_held(projects.paths.analysis_lock):
        raise JobConflictError("cannot edit page metadata while an analysis job is running")

    wanted = list(dict.fromkeys(page_ids))
    slug = normalize_tags([tag])[0] if action in ("add_tag", "remove_tag") else ""

    with mutation_lock(projects.paths.mutation_lock):
        payload = require_format(read_json(projects.paths.manifest), "transcribe.project")
        from transcribe.domain.models import Project
        from transcribe.domain.validation import validate_project

        current = Project.from_dict(payload)
        known = {page.page_id for page in current.pages}
        missing = [page_id for page_id in wanted if page_id not in known]
        if missing:
            raise ProjectError(f"unknown page_id: {missing[0]}")
        changed = 0
        selected = 0
        for page in current.pages:
            if page.page_id not in known or page.page_id not in set(wanted):
                continue
            selected += 1
            if action == "approve_dates":
                if page.date is not None and not page.date_approved:
                    page.set_date_state(page.date, approved=True, source=None)
                    changed += 1
            elif action == "ignore" and not page.ignored:
                page.ignored = True
                changed += 1
            elif action == "unignore" and page.ignored:
                page.ignored = False
                changed += 1
            elif action == "add_tag" and slug not in page.tags:
                page.tags = normalize_tags([*page.tags, slug])
                page.suppressed_auto_tags = [
                    item for item in page.suppressed_auto_tags if item != slug
                ]
                changed += 1
            elif action == "remove_tag" and slug in page.tags:
                page.tags = [item for item in page.tags if item != slug]
                if slug not in page.suppressed_auto_tags:
                    page.suppressed_auto_tags = normalize_tags([*page.suppressed_auto_tags, slug])
                changed += 1
        if changed and not dry_run:
            current.updated_at = to_iso(projects.clock.now())
            validate_project(current)
            write_json_atomic(projects.paths.manifest, current.as_dict())

    if changed and not dry_run and runtime is not None:
        bump_archive_generation(runtime)
    return BatchMetadataResult(
        action=action,
        selected=selected,
        changed=changed,
        dry_run=dry_run,
    )
