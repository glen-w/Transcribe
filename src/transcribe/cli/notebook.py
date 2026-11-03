"""CLI notebook commands: init, import, models, run, multipass, detect, status, doctor."""

from __future__ import annotations

import argparse
import sys

from transcribe.providers.ollama import (
    OllamaVisionProvider,
    is_local_machine_host,
    normalize_base_url,
)
from transcribe.runtime_paths import default_ollama_base_url
from transcribe.services.job import build_coordinator, cli_run_exit_code
from transcribe.services.project import ProjectService, open_project_paths


def _cmd_pages_batch(args: argparse.Namespace, projects: ProjectService) -> int:
    from transcribe.runtime_paths import build_runtime_paths
    from transcribe.services.archive import ArchiveService
    from transcribe.services.batch_metadata import apply_batch_metadata, filters_are_empty
    from transcribe.services.saved_searches import SavedSearchStore

    page_ids = list(args.page_ids or [])
    runtime = build_runtime_paths()
    if args.saved:
        store = SavedSearchStore(runtime)
        saved = store.get(args.saved) or next(
            (row for row in store.list() if row.name == args.saved),
            None,
        )
        if saved is None:
            print(f"error: no saved search {args.saved!r}", file=sys.stderr)
            return 2
        if filters_are_empty(saved.filters):
            print("error: saved search has an empty filter", file=sys.stderr)
            return 2
        project = projects.load()
        hits = ArchiveService(runtime).search("", filters=saved.filters, limit=500)
        page_ids.extend(
            hit.page_id for hit in hits.hits if hit.project_id == project.id
        )
    if not page_ids:
        print("error: batch metadata refuses an empty page selection", file=sys.stderr)
        return 2
    result = apply_batch_metadata(
        projects,
        page_ids,
        args.action,
        tag=args.tag or "",
        role=getattr(args, "role", "") or "",
        certainty=getattr(args, "certainty", "") or "",
        dry_run=not bool(args.apply),
        runtime=runtime,
    )
    print(
        f"{'dry-run' if result.dry_run else 'applied'}: "
        f"action={result.action} selected={result.selected} changed={result.changed}"
    )
    return 0


def dispatch_notebook(args: argparse.Namespace, *, clock, ids) -> int | None:
    """Return an exit code for notebook commands, or None to fall through."""
    if args.cmd == "init":
        paths = open_project_paths(args.project)
        ProjectService(paths, clock=clock, ids=ids).create(title=args.title)
        print(f"Created project at {paths.root}")
        return 0

    if args.cmd == "pages":
        paths = open_project_paths(args.project)
        projects = ProjectService(paths, clock=clock, ids=ids)
        if args.pages_cmd == "reorder":
            project = projects.reorder_pages(args.page_ids)
        elif args.pages_cmd == "move-to-date-cluster":
            project = projects.move_page_to_date_cluster(args.page_id)
        elif args.pages_cmd in ("batch", "batch-meta"):
            return _cmd_pages_batch(args, projects)
        else:
            return None
        print(" ".join(page.page_id for page in project.pages))
        return 0

    if args.cmd == "models":
        url = normalize_base_url(args.base_url or default_ollama_base_url())
        if not is_local_machine_host(url):
            print(
                "WARNING: Ollama host is not on this machine; images would leave this machine.",
                file=sys.stderr,
            )
        provider = OllamaVisionProvider(url)
        all_models = provider.list_models(refresh=args.refresh)
        if args.all:
            result = all_models
        else:
            from transcribe.services.model_selection import suitable_ocr_vision_models

            result_models = suitable_ocr_vision_models(all_models.models)
            from transcribe.providers.base import DiscoveryResult

            result = DiscoveryResult(models=result_models, error=all_models.error)
        if result.error:
            print(f"Discovery warning: {result.error}", file=sys.stderr)
        if not result.models:
            print("No models found.")
            return 1
        prefs = None
        if getattr(args, "prefs", False):
            from transcribe.services.ocr_preference_stats import (
                effective_model_preference_hint_mode,
                preference_hint_for_model,
                rollup_preference_stats,
            )

            prefs = rollup_preference_stats()
            hint_mode = effective_model_preference_hint_mode()
        for m in result.models:
            caps = ",".join(m.capabilities) if m.capability_known else "unknown"
            line = f"{m.name}\tdigest={m.digest or '-'}\tcapabilities={caps}"
            if prefs is not None:
                hint = preference_hint_for_model(
                    m.name,
                    stats=prefs,
                    share_mode=hint_mode,
                )
                if hint:
                    line = f"{line}\t{hint}"
            print(line)
        return 0

    if args.cmd not in {"import", "status", "doctor", "run", "multipass", "detect"}:
        return None

    paths, projects, coord, ingest = build_coordinator(args.project, clock=clock, ids=ids)

    if args.cmd == "import":
        projects.load()
        project = ingest.import_path(args.source, render_dpi=args.dpi)
        print(
            f"Imported {args.source.name}: {project.pages[-1].page_index + 1 if project.pages else 0} page(s); total pages={len(project.pages)}"
        )
        return 0

    if args.cmd == "status":
        project = projects.load()
        for i, page in enumerate(project.pages):
            result = projects.load_page_result(page.page_id)
            status = result.status if result else "pending"
            edited = " edited" if result and result.edited_text is not None else ""
            print(f"{i:04d}  {page.page_id}  {status}{edited}")
        return 0

    if args.cmd == "doctor":
        from transcribe.services.doctor import DoctorService

        report = DoctorService(paths, projects).run(deep=args.deep)
        for finding in report.findings:
            print(f"{finding.severity}: [{finding.code}] {finding.message}")
        if report.ok and not report.findings:
            print("ok: project integrity checks passed")
        elif report.ok:
            print("ok: no errors (warnings above)")
        return 0 if report.ok else 1

    if args.cmd == "run":
        project = projects.load()
        settings = project.settings
        settings.model_name = args.model
        if args.base_url:
            settings.base_url = normalize_base_url(args.base_url)
        settings.max_workers = max(1, min(2, args.workers))
        url = normalize_base_url(settings.base_url)
        if not is_local_machine_host(url) and not args.allow_remote_ollama:
            print(
                "Refusing non-local Ollama host without --allow-remote-ollama "
                "(page images would leave this machine).",
                file=sys.stderr,
            )
            return 2
        settings.allow_non_loopback = bool(args.allow_remote_ollama)
        if args.cleanup:
            settings.cleanup_enabled = True
            if args.cleanup_mode:
                settings.cleanup_mode = args.cleanup_mode
            if args.cleanup_model:
                settings.cleanup_model_name = args.cleanup_model.strip()
        elif args.cleanup_mode or args.cleanup_model:
            print(
                "error: --cleanup-mode / --cleanup-model require --cleanup",
                file=sys.stderr,
            )
            return 2
        project = projects.save_settings(project, settings)
        coord.provider = OllamaVisionProvider(settings.base_url)

        if args.retry_failed:
            from transcribe.services.job_outcome import retry_failed_page_ids

            project = projects.load()
            page_ids = retry_failed_page_ids(project, projects)
            if not page_ids:
                print("no failed, interrupted, or empty_output pages to retry")
                return 0
            progress = coord.run_blocking(page_ids=page_ids, force=args.force)
        else:
            progress = coord.run_blocking(force=args.force)
        from transcribe.services.job_outcome import classify_job_outcome

        outcome = classify_job_outcome(
            status=progress.status,
            circuit_open=progress.circuit_open,
            failed_pages=progress.failed,
        )
        print(
            f"outcome={outcome.outcome} status={outcome.status} "
            f"failed={progress.failed} skipped={progress.skipped}"
        )
        return cli_run_exit_code(progress)

    if args.cmd == "multipass":
        from transcribe.services.multipass import MultiPassCoordinator

        project = projects.load()
        settings = project.settings
        if args.base_url:
            settings.base_url = normalize_base_url(args.base_url)
        url = normalize_base_url(settings.base_url)
        if not is_local_machine_host(url) and not args.allow_remote_ollama:
            print(
                "Refusing non-local Ollama host without --allow-remote-ollama "
                "(page images would leave this machine).",
                file=sys.stderr,
            )
            return 2
        settings.allow_non_loopback = bool(args.allow_remote_ollama)
        if args.text_model:
            settings.text_model_name = args.text_model.strip()
            if not settings.cleanup_model_name:
                settings.cleanup_model_name = settings.text_model_name
        project = projects.save_settings(project, settings)
        coord.provider = OllamaVisionProvider(settings.base_url)
        multi = MultiPassCoordinator(jobs=coord, projects=projects, clock=clock, ids=ids)
        if args.resume:
            progress = multi.resume_blocking(args.resume)
        else:
            models = list(args.models or [])
            if len(models) < 2:
                print(
                    "error: multipass requires at least two --model values "
                    "(or --resume PASS_ID)",
                    file=sys.stderr,
                )
                return 2
            progress = multi.run_blocking(
                model_names=models,
                force=args.force,
                auto_activate_composite=not args.no_auto_composite,
                cleanup_enabled=bool(args.cleanup),
            )
        return 0 if progress.status == "completed" else 1

    if args.cmd == "detect":
        from transcribe.detection.api import DetectionService

        if args.list:
            for info in DetectionService.list_detectors():
                print(f"{info.detector_id}\tv{info.version}\t{info.title}")
            return 0
        svc = DetectionService(projects)
        result = svc.run_detector(args.detector, force=args.force, auto_tag=args.auto_tag)
        findings = result.get("findings") or []
        page_counts = result.get("page_counts") or []
        if page_counts:
            from transcribe.detection.lexical import lexical_page_count_rows

            page_order = {p.page_id: i for i, p in enumerate(projects.load().pages)}
            rows = lexical_page_count_rows(
                page_order=page_order,
                page_counts=page_counts,
            )
            total = sum(int(r["count"]) for r in rows)
            print(
                f"detector={args.detector} outcome={result.get('outcome')} "
                f"pages={len(rows)} total={total}"
            )
            for row in rows:
                label = (
                    f"page {row['order']}"
                    if row.get("order") is not None
                    else str(row["page_id"])[:8]
                )
                print(f"  {label}\t{row['count']}")
        else:
            print(
                f"detector={args.detector} outcome={result.get('outcome')} "
                f"findings={len(findings)} windows={result.get('windows_scanned', 0)}"
            )
            for f in findings:
                print(
                    f"  {f.get('finding_type')} pages {f.get('start_page_id')}.."
                    f"{f.get('end_page_id')} confidence={f.get('confidence')}"
                )
        return (
            0
            if result.get("outcome")
            in ("success", "skipped_not_applicable", "insufficient_data")
            else 1
        )

    return None
