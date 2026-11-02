"""CLI for workspace search, collections, saved searches, and quality ratings."""

from __future__ import annotations

import argparse
import sys

from transcribe.cli.runtime import runtime_paths
from transcribe.services.archive import ArchiveFilters, ArchiveService
from transcribe.services.collections import NotebookCollectionsStore
from transcribe.services.quality import QualityRatingStore
from transcribe.services.saved_searches import SavedSearchStore


def _split(value: str | None) -> tuple[str, ...]:
    if not value:
        return ()
    return tuple(part.strip() for part in value.split(",") if part.strip())


def _cmd_search(args: argparse.Namespace) -> int:
    runtime = runtime_paths()
    filters = ArchiveFilters(
        query="",
        tags=_split(args.tags),
        people=_split(args.people),
        places=_split(args.places),
        include_archived=bool(args.include_archived),
        collection_id=str(args.collection or ""),
        bookmarked_only=bool(args.bookmarked),
    )
    if args.saved:
        saved = SavedSearchStore(runtime).get(args.saved)
        if saved is None:
            # Allow addressing a saved search by name.
            saved = next(
                (s for s in SavedSearchStore(runtime).list() if s.name == args.saved),
                None,
            )
        if saved is None:
            print(f"error: no saved search {args.saved!r}", file=sys.stderr)
            return 2
        filters = saved.filters
        if not args.query:
            args.query = saved.query
        args.order = saved.order
    result = ArchiveService(runtime).search(
        args.query or "",
        order=args.order,
        filters=filters,
        limit=args.limit,
        offset=args.offset,
    )
    print(f"{result.total_matched} matched ({result.total_indexed} indexed)")
    for hit in result.hits:
        date = hit.date.format_display() if hit.date else "Undated"
        print(
            f"{hit.project_title}\tp.{hit.page_index_in_notebook}/{hit.notebook_page_count}"
            f"\t{date}\t{hit.snippet}"
        )
    return 0


def _cmd_collections(args: argparse.Namespace, *, clock, ids) -> int:
    store = NotebookCollectionsStore(runtime_paths(), clock=clock, ids=ids)
    if args.collections_cmd == "list":
        state = store.load()
        for collection in state.collections:
            print(
                f"{collection.collection_id}\t{collection.name}\t"
                f"{len(collection.project_ids)} notebook(s)"
            )
        for project_id in state.archived_project_ids:
            print(f"archived\t{project_id}")
        return 0
    if args.collections_cmd == "create":
        created = store.create(args.name, description=args.description or "")
        print(created.collection_id)
        return 0
    if args.collections_cmd == "rename":
        updated = store.rename(args.collection_id, args.name)
        print(updated.name)
        return 0
    if args.collections_cmd == "delete":
        deleted = store.delete(args.collection_id)
        print("deleted" if deleted else "not found")
        return 0 if deleted else 1
    if args.collections_cmd == "assign":
        updated = store.assign(args.collection_id, args.project_id, member=True)
        print(f"{updated.name}: {len(updated.project_ids)} notebook(s)")
        return 0
    if args.collections_cmd == "unassign":
        updated = store.assign(args.collection_id, args.project_id, member=False)
        print(f"{updated.name}: {len(updated.project_ids)} notebook(s)")
        return 0
    if args.collections_cmd == "archive":
        store.set_archived(args.project_id, archived=True)
        print(f"archived {args.project_id}")
        return 0
    if args.collections_cmd == "unarchive":
        store.set_archived(args.project_id, archived=False)
        print(f"unarchived {args.project_id}")
        return 0
    return 2


def _cmd_saved_search(args: argparse.Namespace, *, clock, ids) -> int:
    store = SavedSearchStore(runtime_paths(), clock=clock, ids=ids)
    if args.saved_cmd == "list":
        for saved in store.list():
            print(f"{saved.search_id}\t{saved.name}\t{saved.query!r}")
        return 0
    if args.saved_cmd == "save":
        filters = ArchiveFilters(
            tags=_split(args.tags),
            people=_split(args.people),
            places=_split(args.places),
            include_archived=bool(args.include_archived),
        )
        saved = store.upsert(
            args.name,
            query=args.query or "",
            order=args.order,
            filters=filters,
        )
        print(saved.search_id)
        return 0
    if args.saved_cmd == "delete":
        print("deleted" if store.delete(args.search_id) else "not found")
        return 0
    return 2


def _cmd_quality(args: argparse.Namespace, *, clock, ids) -> int:
    store = QualityRatingStore(runtime_paths(), clock=clock, ids=ids)
    if args.quality_cmd == "summary":
        summary = store.summary(project_id=args.project)
        print(f"total: {summary['total']}")
        print(f"ocr_samples: {summary['ocr_samples']}")
        print(f"mean_cer: {summary['mean_cer']}")
        print(f"cleanup_acceptance: {summary['cleanup_acceptance']}")
        print(f"analysis_up_ratio: {summary['analysis_up_ratio']}")
        for key, count in summary["by_kind_verdict"].items():
            print(f"{key}: {count}")
        return 0
    if args.quality_cmd == "rate":
        rating = store.record(
            args.kind,
            args.verdict,
            project_id=args.project or "",
            page_id=args.page,
            module_id=args.module,
            notes=args.notes or "",
        )
        print(rating.rating_id)
        return 0
    if args.quality_cmd == "scoreboard":
        from transcribe.services.quality import build_scoreboard

        rows = build_scoreboard(runtime_paths(), project_id=args.project)
        if not rows:
            print("scoreboard: no corrected pages")
            return 0
        for row in rows:
            cer = f"{row.mean_cer:.4f}" if row.mean_cer is not None else "—"
            print(
                f"{row.kind}\t{row.model_name}\t{row.model_digest}\t"
                f"verified={row.verified}\tpages={row.pages}\tcer={cer}"
            )
        return 0
    return 2


def _cmd_workspace_doctor(args: argparse.Namespace) -> int:
    from transcribe.services.workspace_doctor import run_workspace_doctor

    result = run_workspace_doctor(runtime_paths(), deep=bool(args.deep))
    for finding in result.corpus_findings:
        print(f"corpus {finding.severity}: [{finding.code}] {finding.message}")
    for root, report in sorted(result.notebook_reports.items()):
        status = "ok" if report.ok else "ERROR"
        print(f"{status}: {root}")
        for finding in report.findings:
            print(f"  {finding.severity}: [{finding.code}] {finding.message}")
    for root, error in sorted(result.failures.items()):
        print(f"ERROR: {root}: {error}")
    for finding in result.census_findings:
        print(f"census {finding.severity}: [{finding.code}] {finding.path}: {finding.message}")
    print(
        f"workspace-doctor: {'ok' if result.ok else 'FAILED'} "
        f"({result.notebook_count} notebook(s))"
    )
    return 0 if result.ok else 1


def _cmd_verify_export(args: argparse.Namespace) -> int:
    from transcribe.services.export_verify import verify_export_bundle

    result = verify_export_bundle(args.dest)
    for rel in result.checked_files:
        print(f"ok: {rel}")
    for problem in result.problems:
        print(f"error: {problem}", file=sys.stderr)
    if result.ok:
        print(f"export readable standalone (revision {result.content_revision})")
    return 0 if result.ok else 1


__all__ = [
    "_cmd_collections",
    "_cmd_quality",
    "_cmd_saved_search",
    "_cmd_search",
    "_cmd_verify_export",
    "_cmd_workspace_doctor",
]
