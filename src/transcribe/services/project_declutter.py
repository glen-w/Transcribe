"""Visual declutter re-apply on active page renders."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from transcribe.domain.models import Project, page_label
from transcribe.domain.validation import validate_project
from transcribe.errors import JobConflictError, ProjectError
from transcribe.persistence.atomic import read_json, write_json_atomic
from transcribe.persistence.locks import job_lock_held, mutation_lock
from transcribe.persistence.schema import require_format
from transcribe.ports import to_iso


@dataclass
class DeclutterReapplyStats:
    pages_total: int = 0
    pages_cropped: int = 0
    pages_noop: int = 0
    pages_unchanged: int = 0
    pages_error: int = 0



class ProjectDeclutter:
    """Collaborator: visual declutter. Public API remains on ``ProjectService``."""

    def __init__(self, svc: Any) -> None:
        self._svc = svc

    def reapply_visual_declutter(
        self,
        *,
        enabled: bool = True,
        on_progress: Callable[[int, int, str], None] | None = None,
        page_ids: Sequence[str] | None = None,
    ) -> DeclutterReapplyStats:
        """Re-run visual declutter on active renders; replace cropped pages.

        ``page_ids`` limits the run to those pages (notebook order of the given
        ids). ``None`` means every page. Creates a new ``render_id`` when pixels
        change. Provenance-only updates keep the existing render when bytes are
        unchanged. Refuses while an OCR job lock is held. Never restores
        already-cropped margins when ``enabled`` is False — that only records
        ``disabled`` provenance on current pixels.
        """
        from transcribe.declutter import apply_declutter
        from transcribe.domain.fingerprint import sha256_bytes
        from transcribe.domain.models import RenderProvenance
        from transcribe.persistence.atomic import write_bytes_atomic

        if job_lock_held(self._svc.paths.job_lock):
            raise JobConflictError("cannot re-apply visual declutter while an OCR job is running")

        stats = DeclutterReapplyStats()
        with mutation_lock(self._svc.paths.mutation_lock):
            payload = require_format(read_json(self._svc.paths.manifest), "transcribe.project")
            current = Project.from_dict(payload)
            if page_ids is None:
                targets = list(current.pages)
            else:
                wanted = list(dict.fromkeys(page_ids))
                if not wanted:
                    raise ProjectError("page_ids must not be empty")
                by_id = {p.page_id: p for p in current.pages}
                missing = next((pid for pid in wanted if pid not in by_id), None)
                if missing is not None:
                    raise ProjectError(f"unknown page_id: {missing}")
                targets = [by_id[pid] for pid in wanted]
            stats.pages_total = len(targets)
            old_files: list[Path] = []
            thumb_files: list[Path] = []

            for index, page in enumerate(targets):
                if on_progress is not None:
                    on_progress(
                        index,
                        stats.pages_total,
                        f"Decluttering {page_label(current, page.page_id)}…",
                    )
                old = current.renders.get(page.active_render_id)
                if old is None:
                    stats.pages_error += 1
                    continue
                try:
                    img_path = self._svc.paths.resolve_contained(old.image_relpath)
                    png = img_path.read_bytes()
                    result = apply_declutter(png, enabled=enabled)
                except Exception:  # noqa: BLE001 — keep going; count as error
                    stats.pages_error += 1
                    continue

                if result.state == "enabled_cropped":
                    stats.pages_cropped += 1
                elif result.state == "enabled_noop":
                    stats.pages_noop += 1
                elif result.state == "error_fallback":
                    stats.pages_error += 1
                else:
                    stats.pages_noop += 1

                pixels_changed = result.image_bytes != png
                if not pixels_changed:
                    stats.pages_unchanged += 1
                    updated = RenderProvenance(
                        render_id=old.render_id,
                        source_sha256=old.source_sha256,
                        pdf_page_index=old.pdf_page_index,
                        render_dpi=old.render_dpi,
                        renderer=old.renderer,
                        renderer_version=old.renderer_version,
                        rendered_image_sha256=old.rendered_image_sha256,
                        width=old.width,
                        height=old.height,
                        image_relpath=old.image_relpath,
                        **result.provenance_dict(),
                    )
                    current.renders[old.render_id] = updated
                    continue

                new_rid = self._svc.ids.new_id()
                new_path = self._svc.paths.page_render_path(page.source_id, page.page_index, new_rid)
                write_bytes_atomic(new_path, result.image_bytes)
                new_rel = self._svc.paths.relativize(new_path)
                new_render = RenderProvenance(
                    render_id=new_rid,
                    source_sha256=old.source_sha256,
                    pdf_page_index=old.pdf_page_index,
                    render_dpi=old.render_dpi,
                    renderer=old.renderer,
                    renderer_version=old.renderer_version,
                    rendered_image_sha256=sha256_bytes(result.image_bytes),
                    width=result.width,
                    height=result.height,
                    image_relpath=new_rel,
                    **result.provenance_dict(),
                )
                current.renders[new_rid] = new_render
                del current.renders[old.render_id]
                page.active_render_id = new_rid
                page.width = result.width
                page.height = result.height
                old_files.append(img_path)
                thumb = self._svc.paths.thumb_path(page.page_id)
                if thumb.exists():
                    thumb_files.append(thumb)
                grid_thumb = self._svc.paths.grid_thumb_path(page.page_id)
                if grid_thumb.exists():
                    thumb_files.append(grid_thumb)

            current.updated_at = to_iso(self._svc.clock.now())
            validate_project(current)
            write_json_atomic(self._svc.paths.manifest, current.as_dict())

            for path in old_files:
                try:
                    path.unlink(missing_ok=True)
                except OSError:
                    pass
            for path in thumb_files:
                try:
                    path.unlink(missing_ok=True)
                except OSError:
                    pass
            # Active renders changed — rebuild disposable cover + grid thumbs.
            try:
                from transcribe.services.thumbnails import ThumbnailService

                ThumbnailService(self._svc.paths).ensure_thumbs_for_pages(current)
            except Exception:  # noqa: BLE001
                pass
            if on_progress is not None:
                on_progress(
                    stats.pages_total,
                    stats.pages_total,
                    f"Finished → cropped {stats.pages_cropped}, unchanged {stats.pages_unchanged}",
                )
            return stats
