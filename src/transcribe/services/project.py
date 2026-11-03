"""Project load/save, reconciliation, merge-safe result writes."""

from __future__ import annotations

import re
import shutil
from collections.abc import Callable, Sequence
from pathlib import Path

from transcribe.domain.dates import (
    ApproximateDate,
    DateRegression,
    normalize_tags,
)
from transcribe.domain.models import (
    ComparisonRecord,
    DEFAULT_PREFER_MODE,
    EDIT_GATE_CHOICES,
    EFFECTIVE_TEXT_ORIGINS,
    MAX_ATTEMPTS_RETAINED,
    OCRAttempt,
    OCRSettings,
    PREFER_MODES,
    REVIEW_STATUSES,
    PageIndex,
    PageResult,
    Project,
    prune_attempts,
)
from transcribe.domain.validation import validate_page_result, validate_project
from transcribe.errors import JobConflictError, ProjectError
from transcribe.corpus.paths import CorpusPaths
from transcribe.paths import ProjectPaths
from transcribe.persistence.atomic import read_json, write_json_atomic
from transcribe.persistence.locks import analysis_lock_held, job_lock_held, mutation_lock
from transcribe.persistence.schema import require_format
from transcribe.ports import Clock, IdGenerator, to_iso
from transcribe.runtime_paths import default_ollama_base_url
from transcribe.services.project_dates import ProjectDateOps, splice_page_after_date_cluster
from transcribe.services.project_declutter import DeclutterReapplyStats, ProjectDeclutter
from transcribe.services.project_review_repair import ProjectReviewRepair


def _seed_ocr_settings() -> OCRSettings:
    """Seed new-project OCR from workspace defaults (one-shot; then project-owned)."""
    from transcribe.config.facade import get_config

    view = get_config()
    ocr = view.effective.ocr
    llm = view.effective.llm
    base = (ocr.base_url or "").strip() or default_ollama_base_url()
    text_model = (ocr.text_model_name or "").strip() or (llm.text_model_preference or "").strip()
    data = {
        "base_url": base,
        "prompt_id": ocr.prompt_id,
        "language": ocr.language,
        "preprocess_profile": ocr.preprocess_profile,
        "max_workers": ocr.max_workers,
        "cleanup_enabled": ocr.cleanup_enabled,
        "cleanup_mode": ocr.cleanup_mode,
        "cleanup_model_name": ocr.cleanup_model_name,
        "text_model_name": text_model,
        "prefer_mode": getattr(ocr, "prefer_mode", "prefer_is_promote"),
        "auto_activate_composite": getattr(ocr, "auto_activate_composite", True),
    }
    return OCRSettings.from_dict(data)


_UNSET = object()


def _origin_from_active(result: PageResult) -> str | None:
    from transcribe.services.ocr_composite_state import current_composite_attempt

    if result.edited_text is not None:
        return result.effective_text_origin
    active = result.active_attempt()
    if active is None:
        return None
    current = current_composite_attempt(result)
    if current is not None and active.attempt_id == current.attempt_id:
        return "composite"
    if (active.attempt_kind or "vision") == "composite":
        return "composite"
    return "ocr_attempt"


def _latest_succeeded_with_text(
    attempts: list[OCRAttempt],
    *,
    exclude_id: str | None = None,
) -> OCRAttempt | None:
    found: OCRAttempt | None = None
    for attempt in attempts:
        if exclude_id and attempt.attempt_id == exclude_id:
            continue
        if attempt.status != "succeeded":
            continue
        if not (attempt.raw_text or "").strip():
            continue
        if found is None or attempt.started_at >= found.started_at:
            found = attempt
    return found


def _active_after_generation(
    existing: PageResult,
    attempt: OCRAttempt,
    *,
    activate: bool,
) -> str | None:
    """Choose active_attempt_id after appending/updating ``attempt``.

    Succeeded-with-text may become active when ``activate`` is true. Failed,
    running, and empty writes keep a prior good reading. First-ever attempt
    (no prior succeeded-with-text) may still become active when ``activate``.
    """
    prior_good = _latest_succeeded_with_text(existing.attempts, exclude_id=attempt.attempt_id)
    current = existing.active_attempt_id
    if not activate:
        if current:
            return current
        return prior_good.attempt_id if prior_good else current
    if attempt.status == "succeeded" and (attempt.raw_text or "").strip():
        return attempt.attempt_id
    if current and current != attempt.attempt_id:
        return current
    if prior_good:
        return prior_good.attempt_id
    return attempt.attempt_id


class ProjectService:
    def __init__(
        self,
        paths: ProjectPaths,
        *,
        clock: Clock,
        ids: IdGenerator,
        corpus_paths: CorpusPaths | None = None,
    ) -> None:
        self.paths = paths
        self.clock = clock
        self.ids = ids
        self.corpus_paths = corpus_paths
        self._dates = ProjectDateOps(self)
        self._review = ProjectReviewRepair(self)
        self._declutter = ProjectDeclutter(self)

    def create(self, title: str = "Untitled notebook") -> Project:
        self.paths.ensure_layout()
        if self.paths.manifest.exists():
            raise ProjectError(f"project already exists at {self.paths.root}")
        now = to_iso(self.clock.now())
        project = Project(
            id=self.ids.new_id(),
            title=title,
            created_at=now,
            updated_at=now,
            settings=_seed_ocr_settings(),
        )
        validate_project(project)
        with mutation_lock(self.paths.mutation_lock):
            write_json_atomic(self.paths.manifest, project.as_dict())
        if self.corpus_paths is not None:
            from transcribe.services.corpus_registry import ensure_registered

            ensure_registered(
                self.corpus_paths,
                project_root=self.paths.root,
                project_id=project.id,
                clock=self.clock,
            )
        return project

    def _load_unlocked(self, *, reconcile: bool = False) -> Project:
        if not self.paths.manifest.exists():
            raise ProjectError(f"no project.json at {self.paths.root}")
        payload = require_format(read_json(self.paths.manifest), "transcribe.project")
        project = Project.from_dict(payload)
        validate_project(project, paths=self.paths, deep=False)
        if reconcile:
            self._reconcile_interrupted_locked()
        return project

    def load(self, *, reconcile: bool = False) -> Project:
        """Load the on-disk notebook. Public read API; reconcile is explicit.

        ``reconcile=False`` (default, 1.2 L2) is a pure read aside from
        crash-interrupted ingest recovery: it never marks running attempts
        interrupted. ``reconcile=True`` is a **write** used only on explicit
        notebook (re)open: recover incomplete ingest, then mark orphaned
        running OCR attempts interrupted when the job lock is free, then
        reconcile analysis/detection storage. Notebook-open callers use
        :meth:`reconcile_interrupted` or pass ``reconcile=True`` deliberately;
        mid-run UI, jobs, and nested analysis/detection loads use the default.

        Does not change ``effective_text()`` semantics, fingerprints, or lock
        order (mutation lock, then job-lock check inside OCR reconcile).
        """
        # Finish or roll back a crash-interrupted ingest before trusting the manifest.
        if self.paths.ingest_journal.exists():
            from transcribe.ingest import IngestService

            declutter = True
            try:
                from transcribe.config.facade import get_config

                declutter = bool(get_config().effective.ingest.visual_declutter_enabled)
            except Exception:
                pass
            IngestService(
                self.paths,
                clock=self.clock,
                ids=self.ids,
                visual_declutter_enabled=declutter,
            ).recover_incomplete_ingest()
        with mutation_lock(self.paths.mutation_lock):
            project = self._load_unlocked(reconcile=reconcile)
        if reconcile:
            from transcribe.analysis.storage import AnalysisStorage
            from transcribe.detection.storage import DetectionStorage

            AnalysisStorage(self.paths).reconcile_interrupted()
            DetectionStorage(self.paths).reconcile_interrupted()
        return project

    def reconcile_interrupted(self) -> None:
        """Explicit reopen path: interrupt orphaned OCR/analysis/detection runs.

        ``load(reconcile=True)`` already performs this. Callers that loaded with
        ``reconcile=False`` can invoke this when the notebook is opened and
        long-running locks are free. No-ops while the OCR job lock is held.
        """
        with mutation_lock(self.paths.mutation_lock):
            self._reconcile_interrupted_locked()
        from transcribe.analysis.storage import AnalysisStorage
        from transcribe.detection.storage import DetectionStorage

        AnalysisStorage(self.paths).reconcile_interrupted()
        DetectionStorage(self.paths).reconcile_interrupted()

    def content_revision(self, project: Project | None = None) -> str:
        """Compute notebook content_revision from a coherent on-disk snapshot."""
        from transcribe.domain.content_revision import content_revision_hex

        with mutation_lock(self.paths.mutation_lock):
            snap = self._load_unlocked(reconcile=False) if project is None else project
            # When caller passes project, still re-read page results under lock for coherence.
            if project is not None:
                snap = project
            results: dict[str, PageResult | None] = {}
            for page in snap.pages:
                results[page.page_id] = self._load_page_result_unlocked(page.page_id)
            return content_revision_hex(snap, results)

    def save_settings(self, project: Project, settings: OCRSettings) -> Project:
        with mutation_lock(self.paths.mutation_lock):
            payload = require_format(read_json(self.paths.manifest), "transcribe.project")
            current = Project.from_dict(payload)
            current.settings = settings
            current.updated_at = to_iso(self.clock.now())
            validate_project(current)
            write_json_atomic(self.paths.manifest, current.as_dict())
            return current

    def update_page_metadata(
        self,
        page_id: str,
        *,
        tags: list[str] | object = _UNSET,
        ignored: bool | object = _UNSET,
    ) -> Project:
        """Merge-safe page metadata updates (tags, ignored). Date changes use approve_page_date."""
        with mutation_lock(self.paths.mutation_lock):
            payload = require_format(read_json(self.paths.manifest), "transcribe.project")
            current = Project.from_dict(payload)
            found = False
            for page in current.pages:
                if page.page_id != page_id:
                    continue
                found = True
                if tags is not _UNSET:
                    new_tags = normalize_tags(tags)  # type: ignore[arg-type]
                    old_set = set(page.tags)
                    new_set = set(new_tags)
                    removed = [slug for slug in page.tags if slug not in new_set]
                    added = new_set - old_set
                    page.tags = new_tags
                    suppressed = [slug for slug in page.suppressed_auto_tags if slug not in added]
                    for slug in removed:
                        if slug not in suppressed:
                            suppressed.append(slug)
                    page.suppressed_auto_tags = normalize_tags(suppressed)
                if ignored is not _UNSET:
                    page.ignored = bool(ignored)
                break
            if not found:
                raise ProjectError(f"unknown page_id: {page_id}")
            current.updated_at = to_iso(self.clock.now())
            validate_project(current)
            write_json_atomic(self.paths.manifest, current.as_dict())
            return current

    def set_page_role(self, page_id: str, role: str) -> Project:
        """Set ``page_role`` to ``text`` or ``scan``.

        ``scan`` pages stay in Reading as images, leave the OCR schedule, and
        are not fine-tune positives. Orthogonal to Ignore in Reader. Refuses
        while an OCR job lock is held. In-flight jobs are not rewritten.
        """
        from transcribe.domain.models import PAGE_ROLES

        if role not in PAGE_ROLES:
            raise ProjectError(f"page_role must be text or scan, got {role!r}")
        if job_lock_held(self.paths.job_lock):
            raise JobConflictError("cannot change page role while an OCR job is running")
        with mutation_lock(self.paths.mutation_lock):
            payload = require_format(read_json(self.paths.manifest), "transcribe.project")
            current = Project.from_dict(payload)
            page = self._require_page(current, page_id)
            page.page_role = role
            current.updated_at = to_iso(self.clock.now())
            validate_project(current)
            write_json_atomic(self.paths.manifest, current.as_dict())
            return current

    def set_page_certainty(self, page_id: str, certainty: str) -> Project:
        """Set ``page_certainty`` to ``sure`` or ``unsure``. Does not change review_status."""
        from transcribe.domain.models import PAGE_CERTAINTIES

        if certainty not in PAGE_CERTAINTIES:
            raise ProjectError(f"page_certainty must be sure or unsure, got {certainty!r}")
        with mutation_lock(self.paths.mutation_lock):
            payload = require_format(read_json(self.paths.manifest), "transcribe.project")
            current = Project.from_dict(payload)
            page = self._require_page(current, page_id)
            page.page_certainty = certainty
            current.updated_at = to_iso(self.clock.now())
            validate_project(current)
            write_json_atomic(self.paths.manifest, current.as_dict())
            return current

    def set_page_gloss(self, page_id: str, gloss: str) -> Project:
        """Set the page gloss (one plain note). Empty clears. Max 500 characters."""
        from transcribe.domain.models import PAGE_GLOSS_MAX

        text = str(gloss or "")
        if len(text) > PAGE_GLOSS_MAX:
            raise ProjectError(f"page gloss is at most {PAGE_GLOSS_MAX} characters")
        with mutation_lock(self.paths.mutation_lock):
            payload = require_format(read_json(self.paths.manifest), "transcribe.project")
            current = Project.from_dict(payload)
            page = self._require_page(current, page_id)
            page.page_gloss = text
            current.updated_at = to_iso(self.clock.now())
            validate_project(current)
            write_json_atomic(self.paths.manifest, current.as_dict())
            return current

    def set_ocr_policy(self, page_id: str, policy: str) -> Project:
        """Set ``ocr_policy`` to ``transcribe`` or ``skip``.

        ``skip`` pages are not scheduled for OCR. This does not delete text
        and does not change ``effective_text()``. Refuses while an OCR job
        lock is held.
        """
        if policy not in ("transcribe", "skip"):
            raise ProjectError(f"ocr_policy must be transcribe or skip, got {policy!r}")
        if job_lock_held(self.paths.job_lock):
            raise JobConflictError("cannot change OCR policy while an OCR job is running")
        with mutation_lock(self.paths.mutation_lock):
            payload = require_format(read_json(self.paths.manifest), "transcribe.project")
            current = Project.from_dict(payload)
            page = self._require_page(current, page_id)
            page.ocr_policy = policy
            current.updated_at = to_iso(self.clock.now())
            validate_project(current)
            write_json_atomic(self.paths.manifest, current.as_dict())
            return current

    def set_page_ignored(self, page_id: str, ignored: bool) -> Project:
        """Mark or clear ``Page.ignored`` (Reader omits ignored pages by default).

        Refuses while an OCR job lock is held. Does not delete page artifacts.
        """
        if job_lock_held(self.paths.job_lock):
            raise JobConflictError("cannot change ignored while an OCR job is running")
        with mutation_lock(self.paths.mutation_lock):
            payload = require_format(read_json(self.paths.manifest), "transcribe.project")
            current = Project.from_dict(payload)
            page = self._require_page(current, page_id)
            page.ignored = bool(ignored)
            current.updated_at = to_iso(self.clock.now())
            validate_project(current)
            write_json_atomic(self.paths.manifest, current.as_dict())
            return current

    def delete_page(self, page_id: str) -> Project:
        """Remove a page from the notebook (manifest + on-disk artifacts).

        Reindexes later pages in the same source so ``page_index`` stays
        contiguous. Removes the source when it has no remaining pages. Refuses
        when the notebook would become empty (delete the notebook instead) or
        while an OCR job lock is held.
        """
        if job_lock_held(self.paths.job_lock):
            raise JobConflictError("cannot delete page while an OCR job is running")

        with mutation_lock(self.paths.mutation_lock):
            payload = require_format(read_json(self.paths.manifest), "transcribe.project")
            current = Project.from_dict(payload)
            if len(current.pages) <= 1:
                raise ProjectError("cannot delete the last page; delete the notebook instead")
            page = self._require_page(current, page_id)
            source_id = page.source_id
            deleted_index = page.page_index
            render_id = page.active_render_id

            current.renders.pop(render_id, None)
            current.pages = [p for p in current.pages if p.page_id != page_id]
            if current.cover_page_id == page_id:
                current.cover_page_id = None

            # Remove this page's artifacts before reindex can reuse its directory.
            page_dir = self.paths.pages_dir / source_id / f"{deleted_index:04d}"
            if page_dir.is_dir():
                shutil.rmtree(page_dir, ignore_errors=True)
            try:
                self.paths.result_path(page_id).unlink(missing_ok=True)
            except OSError:
                pass
            try:
                self.paths.thumb_path(page_id).unlink(missing_ok=True)
            except OSError:
                pass
            try:
                self.paths.grid_thumb_path(page_id).unlink(missing_ok=True)
            except OSError:
                pass

            # Reindex later pages in this source via a staging dir to avoid collisions.
            siblings = [
                p
                for p in current.pages
                if p.source_id == source_id and p.page_index > deleted_index
            ]
            siblings.sort(key=lambda p: p.page_index)
            if siblings:
                staging_root = self.paths.pages_dir / source_id / f".reindex-{page_id}"
                if staging_root.exists():
                    shutil.rmtree(staging_root, ignore_errors=True)
                staging_root.mkdir(parents=True, exist_ok=True)
                for sibling in siblings:
                    old_index = sibling.page_index
                    old_dir = self.paths.pages_dir / source_id / f"{old_index:04d}"
                    if old_dir.is_dir():
                        old_dir.rename(staging_root / f"{old_index:04d}")
                for sibling in siblings:
                    old_index = sibling.page_index
                    new_index = old_index - 1
                    staged = staging_root / f"{old_index:04d}"
                    new_dir = self.paths.pages_dir / source_id / f"{new_index:04d}"
                    if staged.is_dir():
                        if new_dir.exists():
                            raise ProjectError(
                                f"cannot reindex page directory: {new_dir} already exists"
                            )
                        staged.rename(new_dir)
                    sibling.page_index = new_index
                    sib_render = current.renders.get(sibling.active_render_id)
                    if sib_render is not None:
                        old_rel = sib_render.image_relpath
                        prefix = f"pages/{source_id}/{old_index:04d}/"
                        new_prefix = f"pages/{source_id}/{new_index:04d}/"
                        if old_rel.startswith(prefix):
                            sib_render.image_relpath = new_prefix + old_rel[len(prefix) :]
                        if sib_render.pdf_page_index == old_index:
                            sib_render.pdf_page_index = new_index
                try:
                    staging_root.rmdir()
                except OSError:
                    shutil.rmtree(staging_root, ignore_errors=True)

            remaining_in_source = [p for p in current.pages if p.source_id == source_id]
            source_file: Path | None = None
            if remaining_in_source:
                for source in current.sources:
                    if source.source_id == source_id:
                        source.page_count = len(remaining_in_source)
                        break
            else:
                source_obj = next(
                    (s for s in current.sources if s.source_id == source_id),
                    None,
                )
                current.sources = [s for s in current.sources if s.source_id != source_id]
                if source_obj is not None:
                    try:
                        source_file = self.paths.resolve_contained(source_obj.stored_relpath)
                    except ValueError:
                        source_file = None
                source_pages_root = self.paths.pages_dir / source_id
                if source_pages_root.is_dir():
                    shutil.rmtree(source_pages_root, ignore_errors=True)

            current.updated_at = to_iso(self.clock.now())
            validate_project(current, paths=self.paths)
            write_json_atomic(self.paths.manifest, current.as_dict())

            if source_file is not None:
                try:
                    source_file.unlink(missing_ok=True)
                except OSError:
                    pass
            return current

    def _refuse_reorder_if_busy(self) -> None:
        if job_lock_held(self.paths.job_lock):
            raise JobConflictError("cannot reorder pages while an OCR job is running")
        if analysis_lock_held(self.paths.analysis_lock):
            raise JobConflictError("cannot reorder pages while an analysis job is running")

    def reorder_pages(self, page_ids: Sequence[str]) -> Project:
        """Permute notebook order (the ``pages`` array) without touching ``page_index``.

        ``page_ids`` must be a permutation of every current page id. Refuses
        duplicate/missing ids, an empty list, and OCR/analysis locks. On-disk
        render directories stay at ``pages/<source_id>/<page_index>/``.
        """
        self._refuse_reorder_if_busy()
        ordered = list(page_ids)
        if not ordered:
            raise ProjectError("empty page permutation")
        if len(ordered) != len(set(ordered)):
            raise ProjectError("duplicate page_id in permutation")

        with mutation_lock(self.paths.mutation_lock):
            payload = require_format(read_json(self.paths.manifest), "transcribe.project")
            current = Project.from_dict(payload)
            existing = [page.page_id for page in current.pages]
            if len(ordered) != len(existing) or set(ordered) != set(existing):
                raise ProjectError("permutation must list every page_id exactly once")
            if ordered == existing:
                return current
            index_by_id = {page.page_id: page.page_index for page in current.pages}
            by_id = {page.page_id: page for page in current.pages}
            current.pages = [by_id[page_id] for page_id in ordered]
            for page in current.pages:
                if page.page_index != index_by_id[page.page_id]:
                    raise ProjectError("reorder must not change page_index")
            self._dates._reinfer_unapproved_page_dates(
                current.pages,
                cover_page_id=current.cover_page_id,
                start_idx=0,
                cover_look_ahead=False,
            )
            current.updated_at = to_iso(self.clock.now())
            validate_project(current)
            write_json_atomic(self.paths.manifest, current.as_dict())
            return current

    def move_page_to_date_cluster(self, page_id: str) -> Project:
        """Insert ``page_id`` after the confirmed cluster for its date.

        Undated pages are refused. No on-disk ``page_index`` rename.
        """
        self._refuse_reorder_if_busy()
        with mutation_lock(self.paths.mutation_lock):
            payload = require_format(read_json(self.paths.manifest), "transcribe.project")
            current = Project.from_dict(payload)
            self._require_page(current, page_id)
            new_order = splice_page_after_date_cluster(current.pages, page_id)
            if [page.page_id for page in new_order] == [page.page_id for page in current.pages]:
                return current
            index_by_id = {page.page_id: page.page_index for page in current.pages}
            current.pages = new_order
            for page in current.pages:
                if page.page_index != index_by_id[page.page_id]:
                    raise ProjectError("reorder must not change page_index")
            self._dates._reinfer_unapproved_page_dates(
                current.pages,
                cover_page_id=current.cover_page_id,
                start_idx=0,
                cover_look_ahead=False,
            )
            current.updated_at = to_iso(self.clock.now())
            validate_project(current)
            write_json_atomic(self.paths.manifest, current.as_dict())
            return current

    def approve_page_date(
        self,
        page_id: str,
        date: ApproximateDate | None,
    ) -> tuple[Project, bool]:
        return self._dates.approve_page_date(page_id, date)

    def list_date_regressions(self, project: Project | None = None) -> list[DateRegression]:
        return self._dates.list_date_regressions(project)

    def approve_all_suggested_dates(
        self,
        *,
        confirm_regressions: bool = False,
    ) -> tuple[Project, int, list[DateRegression]]:
        return self._dates.approve_all_suggested_dates(confirm_regressions=confirm_regressions)

    def ignore_all_suggested_dates(self) -> tuple[Project, int]:
        return self._dates.ignore_all_suggested_dates()

    def suggest_page_date(self, page_id: str) -> bool:
        return self._dates.suggest_page_date(page_id)

    def fill_page_dates_ordered(self) -> int:
        return self._dates.fill_page_dates_ordered()

    @staticmethod
    def _require_page(project: Project, page_id: str) -> PageIndex:
        for page in project.pages:
            if page.page_id == page_id:
                return page
        raise ProjectError(f"unknown page_id: {page_id}")

    def update_notebook_metadata(
        self,
        *,
        title: str | object = _UNSET,
        tags: list[str] | object = _UNSET,
        cover_page_id: str | None | object = _UNSET,
        date_start: ApproximateDate | None | object = _UNSET,
        date_end: ApproximateDate | None | object = _UNSET,
    ) -> Project:
        """Update notebook-level user metadata. Omit kwargs to leave fields unchanged."""
        with mutation_lock(self.paths.mutation_lock):
            payload = require_format(read_json(self.paths.manifest), "transcribe.project")
            current = Project.from_dict(payload)
            if title is not _UNSET:
                current.title = str(title)
            if tags is not _UNSET:
                current.tags = normalize_tags(tags)  # type: ignore[arg-type]
            if cover_page_id is not _UNSET:
                if cover_page_id is not None and not any(
                    p.page_id == cover_page_id for p in current.pages
                ):
                    raise ProjectError(f"unknown cover_page_id: {cover_page_id}")
                current.cover_page_id = cover_page_id  # type: ignore[assignment]
            if date_start is not _UNSET:
                current.date_start = date_start  # type: ignore[assignment]
            if date_end is not _UNSET:
                current.date_end = date_end  # type: ignore[assignment]
            current.updated_at = to_iso(self.clock.now())
            validate_project(current)
            write_json_atomic(self.paths.manifest, current.as_dict())
            return current

    def _load_page_result_unlocked(self, page_id: str) -> PageResult | None:
        path = self.paths.result_path(page_id)
        if not path.exists():
            return None
        payload = require_format(read_json(path), "transcribe.page-result")
        result = PageResult.from_dict(payload)
        validate_page_result(result, expected_page_id=page_id)
        return result

    def load_page_result(self, page_id: str) -> PageResult | None:
        return self._load_page_result_unlocked(page_id)

    def record_generation(
        self,
        page_id: str,
        attempt: OCRAttempt,
        *,
        activate: bool = True,
    ) -> PageResult:
        with mutation_lock(self.paths.mutation_lock):
            existing = self._load_page_result_unlocked(page_id) or PageResult(page_id=page_id)
            before = PageResult.from_dict(existing.as_dict())
            # Replace same attempt_id if updating running→terminal; else append.
            replaced = False
            for i, old in enumerate(existing.attempts):
                if old.attempt_id == attempt.attempt_id:
                    existing.attempts[i] = attempt
                    replaced = True
                    break
            if not replaced:
                existing.attempts.append(attempt)
            existing.active_attempt_id = _active_after_generation(
                existing, attempt, activate=activate
            )
            if len(existing.attempts) > MAX_ATTEMPTS_RETAINED:
                existing.attempts = prune_attempts(
                    existing.attempts,
                    active_attempt_id=existing.active_attempt_id,
                    preferred_attempt_id=existing.preferred_attempt_id,
                )
            existing.updated_at = to_iso(self.clock.now())
            if attempt.status == "succeeded" and existing.edited_text is None:
                existing.effective_text_origin = _origin_from_active(existing)
            validate_page_result(existing, expected_page_id=page_id)
            write_json_atomic(self.paths.result_path(page_id), existing.as_dict())
            self._invalidate_review_unlocked(page_id, before=before, after=existing)
            return existing

    def set_active_attempt(
        self, page_id: str, attempt_id: str, *, record_ledger: bool = True
    ) -> PageResult:
        """Promote a succeeded attempt to active without clearing edited_text."""
        with mutation_lock(self.paths.mutation_lock):
            existing = self._load_page_result_unlocked(page_id)
            if existing is None:
                raise ProjectError(f"no page result for {page_id}")
            attempt = existing.attempt_by_id(attempt_id)
            if attempt is None:
                raise ProjectError(f"attempt {attempt_id!r} not found on {page_id}")
            if attempt.status != "succeeded":
                raise ProjectError(
                    f"only succeeded attempts can be activated (status={attempt.status})"
                )
            before = PageResult.from_dict(existing.as_dict())
            existing.active_attempt_id = attempt_id
            if existing.edited_text is None:
                existing.effective_text_origin = _origin_from_active(existing)
            existing.updated_at = to_iso(self.clock.now())
            validate_page_result(existing, expected_page_id=page_id)
            write_json_atomic(self.paths.result_path(page_id), existing.as_dict())
            self._invalidate_review_unlocked(page_id, before=before, after=existing)
            result = existing
            attempt_snap = attempt
        if record_ledger:
            self._append_preference_event(
                page_id=page_id,
                attempt=attempt_snap,
                action="promote",
            )
        return result

    def set_preferred_attempt(
        self,
        page_id: str,
        attempt_id: str,
        *,
        mode: str | None = None,
        edit_gate_choice: str | None = None,
        record_ledger: bool = True,
        action_override: str | None = None,
    ) -> PageResult:
        """Mark preferred; optionally promote per prefer_mode (A/B/C)."""
        resolved_mode = mode or self._resolved_prefer_mode()
        if resolved_mode not in PREFER_MODES:
            raise ProjectError(f"unsupported prefer_mode: {resolved_mode!r}")
        with mutation_lock(self.paths.mutation_lock):
            existing = self._load_page_result_unlocked(page_id)
            if existing is None:
                raise ProjectError(f"no page result for {page_id}")
            attempt = existing.attempt_by_id(attempt_id)
            if attempt is None:
                raise ProjectError(f"attempt {attempt_id!r} not found on {page_id}")
            if attempt.status != "succeeded":
                raise ProjectError(
                    f"only succeeded attempts can be preferred (status={attempt.status})"
                )
            existing.preferred_attempt_id = attempt_id
            promote = False
            if resolved_mode == "prefer_is_promote":
                promote = True
            elif resolved_mode == "prefer_only":
                promote = False
            elif resolved_mode == "prefer_promote_with_edit_gate":
                if existing.edited_text is not None:
                    if edit_gate_choice not in EDIT_GATE_CHOICES:
                        raise ProjectError(
                            "edit_gate_choice required when edited_text is set "
                            "(keep_edit|adopt_new)"
                        )
                    if edit_gate_choice == "adopt_new":
                        existing.edited_text = None
                    promote = True
                else:
                    promote = True
            before = PageResult.from_dict(existing.as_dict())
            if promote:
                existing.active_attempt_id = attempt_id
            if existing.edited_text is None:
                existing.effective_text_origin = _origin_from_active(existing)
            existing.updated_at = to_iso(self.clock.now())
            validate_page_result(existing, expected_page_id=page_id)
            write_json_atomic(self.paths.result_path(page_id), existing.as_dict())
            self._invalidate_review_unlocked(page_id, before=before, after=existing)
            result = existing
        if record_ledger:
            self._append_preference_event(
                page_id=page_id,
                attempt=attempt,
                action=action_override or ("prefer" if not promote else "prefer"),
            )
        return result

    def save_comparison(self, page_id: str, comparison: ComparisonRecord | None) -> PageResult:
        with mutation_lock(self.paths.mutation_lock):
            existing = self._load_page_result_unlocked(page_id)
            if existing is None:
                raise ProjectError(f"no page result for {page_id}")
            existing.comparison = comparison
            existing.updated_at = to_iso(self.clock.now())
            validate_page_result(existing, expected_page_id=page_id)
            write_json_atomic(self.paths.result_path(page_id), existing.as_dict())
            return existing

    def _resolved_prefer_mode(self) -> str:
        project = self.load()
        mode = getattr(project.settings, "prefer_mode", None) or DEFAULT_PREFER_MODE
        if mode in PREFER_MODES:
            return mode
        return DEFAULT_PREFER_MODE

    def _append_preference_event(
        self,
        *,
        page_id: str,
        attempt: OCRAttempt,
        action: str,
    ) -> None:
        try:
            from transcribe.services.ocr_preference_stats import append_preference_event

            project = self.load()
            append_preference_event(
                notebook_id=project.id,
                page_id=page_id,
                attempt_id=attempt.attempt_id,
                model_name=(attempt.provenance.model_name if attempt.provenance else ""),
                model_digest=(attempt.provenance.model_digest if attempt.provenance else None),
                attempt_kind=attempt.attempt_kind or "vision",
                action=action,
                pass_id=attempt.pass_id,
                clock=self.clock,
            )
        except Exception:
            # Ledger is best-effort; page mutation already committed.
            return

    def save_user_edit(
        self,
        page_id: str,
        edited_text: str | None,
        *,
        origin: str | None = None,
        mark_reviewed: bool = False,
    ) -> PageResult:
        if origin is not None and origin not in EFFECTIVE_TEXT_ORIGINS:
            raise ProjectError(f"unsupported effective_text_origin: {origin!r}")
        with mutation_lock(self.paths.mutation_lock):
            existing = self._load_page_result_unlocked(page_id)
            if existing is None:
                existing = PageResult(page_id=page_id)
            before = PageResult.from_dict(existing.as_dict())
            existing.edited_text = edited_text
            if origin is not None:
                existing.effective_text_origin = origin
            elif edited_text is None:
                existing.effective_text_origin = _origin_from_active(existing)
            existing.updated_at = to_iso(self.clock.now())
            if mark_reviewed:
                from transcribe.services.ocr_composite_state import (
                    evidence_fingerprint,
                    reviewed_text_fingerprint,
                )

                text = existing.effective_text() or ""
                existing.reviewed_text_fingerprint = reviewed_text_fingerprint(text)
                existing.reviewed_evidence_fingerprint = evidence_fingerprint(existing)
            validate_page_result(existing, expected_page_id=page_id)
            write_json_atomic(self.paths.result_path(page_id), existing.as_dict())
            if mark_reviewed:
                self._write_review_status_unlocked(page_id, "reviewed")
            else:
                self._invalidate_review_unlocked(page_id, before=before, after=existing)
            return existing

    def adopt_raw_as_edit(self, page_id: str) -> PageResult:
        """Clear edited_text so effective text becomes active raw."""
        return self.save_user_edit(page_id, None)

    def set_page_review_status(self, page_id: str, status: str) -> Project:
        """Set PageIndex.review_status. ``reviewed`` must go through save_user_edit."""
        if status not in REVIEW_STATUSES:
            raise ProjectError(f"unsupported review_status: {status!r}")
        if status == "reviewed":
            raise ProjectError("mark reviewed via save_user_edit(..., mark_reviewed=True)")
        with mutation_lock(self.paths.mutation_lock):
            return self._write_review_status_unlocked(page_id, status)

    def repair_empty_successes(self, page_id: str) -> PageResult | None:
        return self._review.repair_empty_successes(page_id)

    def repair_truncated_repetition_successes(self, page_id: str) -> PageResult | None:
        return self._review.repair_truncated_repetition_successes(page_id)

    def repair_review_validity(self, page_id: str) -> str:
        return self._review.repair_review_validity(page_id)

    def _invalidate_review_unlocked(
        self,
        page_id: str,
        *,
        before: PageResult | None,
        after: PageResult,
    ) -> None:
        self._review._invalidate_review_unlocked(page_id, before=before, after=after)

    def _write_review_status_unlocked(self, page_id: str, status: str) -> Project:
        return self._review._write_review_status_unlocked(page_id, status)

    def cache_alignment_signals(
        self,
        page_id: str,
        *,
        source_disagreement_count: int,
        agreement_ratio: float,
    ) -> PageResult:
        with mutation_lock(self.paths.mutation_lock):
            existing = self._load_page_result_unlocked(page_id)
            if existing is None:
                existing = PageResult(page_id=page_id)
            existing.source_disagreement_count = int(source_disagreement_count)
            existing.agreement_ratio = float(agreement_ratio)
            existing.updated_at = to_iso(self.clock.now())
            validate_page_result(existing, expected_page_id=page_id)
            write_json_atomic(self.paths.result_path(page_id), existing.as_dict())
            return existing

    def reapply_visual_declutter(
        self,
        *,
        enabled: bool = True,
        on_progress: Callable[[int, int, str], None] | None = None,
        page_ids: Sequence[str] | None = None,
    ) -> DeclutterReapplyStats:
        return self._declutter.reapply_visual_declutter(
            enabled=enabled,
            on_progress=on_progress,
            page_ids=page_ids,
        )

    def _reconcile_interrupted_locked(self) -> None:
        if job_lock_held(self.paths.job_lock):
            return
        for path in self.paths.results_dir.glob("*.json"):
            try:
                payload = require_format(read_json(path), "transcribe.page-result")
                result = PageResult.from_dict(payload)
                validate_page_result(result, expected_page_id=path.stem)
            except Exception:
                continue
            changed = False
            for attempt in result.attempts:
                if attempt.status == "running":
                    attempt.status = "interrupted"
                    if attempt.error is None:
                        from transcribe.domain.models import AttemptError

                        attempt.error = AttemptError(
                            code="interrupted",
                            message="OCR attempt interrupted by process exit",
                            retriable=True,
                        )
                    attempt.completed_at = to_iso(self.clock.now())
                    changed = True
            if changed:
                result.updated_at = to_iso(self.clock.now())
                write_json_atomic(path, result.as_dict())


def open_project_paths(root: Path) -> ProjectPaths:
    paths = ProjectPaths(root=Path(root).expanduser().resolve())
    paths.ensure_layout()
    return paths


def notebook_dir_slug(title: str) -> str:
    """Filesystem-safe folder name derived from a notebook display title."""
    raw = (title or "").strip() or "Untitled notebook"
    slug = re.sub(r"[^\w.\-()+ ]+", "_", raw, flags=re.UNICODE).strip(" .")
    slug = re.sub(r"\s+", "-", slug)
    return slug or "notebook"


def allocate_notebook_root(projects_dir: Path | str, title: str) -> Path:
    """Pick an unused directory under ``projects_dir`` for a new notebook."""
    projects = Path(projects_dir).expanduser().resolve()
    base = notebook_dir_slug(title)
    candidate = projects / base
    if not candidate.exists():
        return candidate
    n = 2
    while True:
        alt = projects / f"{base}-{n}"
        if not alt.exists():
            return alt
        n += 1


def delete_managed_notebook(
    project_root: Path | str,
    *,
    projects_dir: Path | str,
) -> Path:
    """Delete a managed notebook directory (imported copies only).

    External originals outside the project tree are never touched. The root must
    resolve under ``projects_dir``, be a real directory, and contain
    ``project.json``.
    """
    projects = Path(projects_dir).expanduser().resolve()
    try:
        root = Path(project_root).expanduser().resolve()
    except OSError as exc:
        raise ProjectError(f"unresolvable project root: {exc}") from exc

    try:
        root.relative_to(projects)
    except ValueError as exc:
        raise ProjectError(f"project root escapes projects directory: {root}") from exc

    if root == projects:
        raise ProjectError("refusing to delete projects directory itself; pass a notebook root")
    if not root.is_dir():
        raise ProjectError(f"project root is not a directory: {root}")
    if not (root / "project.json").is_file():
        raise ProjectError(f"missing project.json under {root}")

    job_lock = root / ".transcribe.job.lock"
    if job_lock_held(job_lock):
        raise JobConflictError("cannot delete notebook while an OCR job is running")

    # Brief exclusive section so concurrent mutators fail closed before removal.
    mutation = root / ".transcribe.lock"
    with mutation_lock(mutation):
        pass

    shutil.rmtree(root)
    return root
