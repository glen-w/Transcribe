"""CLI bulk-import / bulk-run / bulk-analyse / corpus-doctor commands."""

from __future__ import annotations

import argparse
import sys

from transcribe.cli.runtime import runtime_paths
from transcribe.errors import ValidationError
from transcribe.runtime_paths import default_ollama_base_url

def _cmd_bulk_import(args: argparse.Namespace, *, clock, ids) -> int:
    from transcribe.corpus.adapters import plan_from_folder, plan_from_folders
    from transcribe.corpus.folder_overwrite import prepare_folder_overwrite
    from transcribe.corpus.import_run import ImportRunStore
    from transcribe.corpus.orchestrator import ImportOrchestrator
    from transcribe.corpus.paths import CorpusPaths
    from transcribe.corpus.plan import (
        POLICY_CREATE_DUPLICATE_V1,
        POLICY_SKIP_EXISTING_V1,
    )

    corpus = CorpusPaths.from_runtime(runtime_paths())
    orchestrator = ImportOrchestrator(corpus, clock=clock, ids=ids)
    if args.bulk_cmd == "folder":
        policy = (
            POLICY_CREATE_DUPLICATE_V1
            if args.policy == "create_duplicate_v1"
            else POLICY_SKIP_EXISTING_V1
        )
        plan = plan_from_folder(
            args.folder,
            ids=ids,
            title=args.title,
            import_policy_id=policy,
        )
        print(
            f"plan_id={plan.plan_id} items={len(plan.items)} "
            f"policy={plan.import_policy_id} fingerprint={plan.fingerprint()[:12]}…"
        )
        for item in plan.items:
            print(
                f"  {item.op} {item.original_filename or item.item_id} "
                f"pages={len(item.page_indexes)} notebook={item.notebook_id}"
            )
        if args.dry_run:
            return 0
        run = orchestrator.create_run_from_plan(plan)
        completed = orchestrator.commit_run(run.import_run_id)
        print(f"import_run_id={completed.import_run_id} status={completed.status}")
        for item in completed.items:
            skip = f" skip={item.skip_classification}" if item.skip_classification else ""
            err = f" error={item.error_message}" if item.error_message else ""
            print(f"  {item.item_id} {item.state}{skip}{err}")
        return 0 if completed.status in {"complete", "partial"} else 1

    if args.bulk_cmd == "folders":
        policy = (
            POLICY_CREATE_DUPLICATE_V1
            if args.policy == "create_duplicate_v1"
            else POLICY_SKIP_EXISTING_V1
        )
        on_existing = args.on_existing
        plan, scan = plan_from_folders(
            args.parent,
            ids=ids,
            corpus_paths=corpus,
            import_policy_id=policy,
            on_existing=on_existing,
        )
        print(
            f"scan parent={scan.parent} new={len(scan.new_folders)} "
            f"already_imported={len(scan.already_imported)} "
            f"empty_skipped={len(scan.empty_skipped)} on_existing={on_existing}"
        )
        for conflict in scan.already_imported:
            print(
                f"  already_imported {conflict.managed_relpath} "
                f"notebook_id={conflict.notebook_id} title={conflict.title!r}"
            )
        for empty in scan.empty_skipped:
            print(f"  empty_skipped {empty.name}")
        print(
            f"plan_id={plan.plan_id} items={len(plan.items)} "
            f"policy={plan.import_policy_id} fingerprint={plan.fingerprint()[:12]}…"
        )
        notebooks: dict[str, list] = {}
        for item in plan.items:
            notebooks.setdefault(item.notebook_id, []).append(item)
        for nb_id, items in notebooks.items():
            title = (items[0].provenance or {}).get("title") or nb_id
            print(
                f"  notebook {title!r} id={nb_id} "
                f"sources={len(items)} pages={sum(len(i.page_indexes) for i in items)}"
            )
        if args.dry_run:
            return 0
        if on_existing == "overwrite" and scan.already_imported:
            prepare_folder_overwrite(
                scan.already_imported,
                corpus,
                confirm=args.confirm_overwrite or "",
                clock=clock,
            )
            print(f"overwrite wiped={len(scan.already_imported)} " f"managed notebook(s)")
        run = orchestrator.create_run_from_plan(plan)
        completed = orchestrator.commit_run(run.import_run_id)
        print(f"import_run_id={completed.import_run_id} status={completed.status}")
        for item in completed.items:
            skip = f" skip={item.skip_classification}" if item.skip_classification else ""
            err = f" error={item.error_message}" if item.error_message else ""
            print(f"  {item.item_id} {item.state}{skip}{err}")
        return 0 if completed.status in {"complete", "partial"} else 1

    if args.bulk_cmd == "status":
        run = ImportRunStore(corpus).load(args.import_run_id)
        print(
            f"import_run_id={run.import_run_id} status={run.status} "
            f"plan_id={run.plan_id} policy={run.import_policy_id}"
        )
        for item in run.items:
            skip = f" skip={item.skip_classification}" if item.skip_classification else ""
            err = f" error={item.error_message}" if item.error_message else ""
            print(f"  {item.item_id} {item.state}{skip}{err}")
        return 0

    if args.bulk_cmd == "resume":
        completed = orchestrator.commit_run(args.import_run_id)
        print(f"import_run_id={completed.import_run_id} status={completed.status}")
        for item in completed.items:
            print(f"  {item.item_id} {item.state}")
        return 0 if completed.status in {"complete", "partial"} else 1

    print(f"error: unknown bulk-import subcommand {args.bulk_cmd}", file=sys.stderr)
    return 2


def _cmd_bulk_run(args: argparse.Namespace, *, clock, ids) -> int:
    from transcribe.corpus.ocr_run import OcrBatchRunStore
    from transcribe.corpus.paths import CorpusPaths
    from transcribe.domain.models import OCRSettings
    from transcribe.providers.factory import build_vision_provider, normalize_provider_id
    from transcribe.providers.ollama import (
        is_local_machine_host,
        normalize_base_url,
    )
    from transcribe.services.batch_ocr import (
        BatchOcrCoordinator,
        list_candidates,
        resolve_notebook_ref,
        select_by_ids,
        select_from_import_run,
        select_pending,
    )

    corpus = CorpusPaths.from_runtime(runtime_paths())
    coord = BatchOcrCoordinator(corpus, clock=clock, ids=ids)
    store = OcrBatchRunStore(corpus)

    if args.bulk_run_cmd == "status":
        run = store.load(args.ocr_run_id)
        models = (
            ",".join(run.vision_model_names)
            if run.mode == "multipass" and run.vision_model_names
            else (run.settings or {}).get("model_name", "")
        )
        print(
            f"ocr_run_id={run.ocr_run_id} status={run.status} mode={run.mode} "
            f"models={models} force={run.force} items={len(run.items)}"
        )
        if run.import_run_id:
            print(f"import_run_id={run.import_run_id}")
        for item in run.items:
            err = f" error={item.error_message}" if item.error_message else ""
            pass_bit = f" pass_id={item.pass_id}" if item.pass_id else ""
            print(
                f"  {item.notebook_id} {item.state} "
                f"pages={item.pages_completed}/{item.pages_total} "
                f"failed={item.pages_failed} skipped={item.pages_skipped}"
                f"{pass_bit}{err}"
            )
        return 0

    if args.bulk_run_cmd == "resume":
        progress = coord.resume(args.ocr_run_id, blocking=True)
        run = store.load(progress.ocr_run_id)
        print(f"ocr_run_id={run.ocr_run_id} status={run.status} mode={run.mode}")
        for item in run.items:
            print(f"  {item.notebook_id} {item.state}")
        return 0 if run.status in {"completed", "partial"} else 1

    url = normalize_base_url(args.base_url or default_ollama_base_url())
    provider_id = normalize_provider_id(getattr(args, "provider", None))
    if provider_id == "paddleocr":
        if not is_local_machine_host(url):
            print(
                "Refusing non-local paddleocr sidecar "
                "(page images would leave this machine).",
                file=sys.stderr,
            )
            return 2
        if not args.base_url:
            url = normalize_base_url("http://127.0.0.1:8112")
    elif not is_local_machine_host(url) and not args.allow_remote_ollama:
        print(
            "Refusing non-local Ollama host without --allow-remote-ollama "
            "(page images would leave this machine).",
            file=sys.stderr,
        )
        return 2
    models = [m.strip() for m in (args.model or []) if m and str(m).strip()]
    if not models:
        print("error: at least one --model is required", file=sys.stderr)
        return 2
    is_multipass = len(models) >= 2
    if (args.cleanup_mode or args.cleanup_model) and not args.cleanup:
        print(
            "error: --cleanup-mode / --cleanup-model require --cleanup",
            file=sys.stderr,
        )
        return 2

    text_model = (args.text_model or "").strip()
    cleanup_model = (args.cleanup_model or "").strip() or text_model
    settings = OCRSettings(
        model_name=models[0],
        base_url=url,
        max_workers=max(1, min(2, args.workers)),
        allow_non_loopback=bool(args.allow_remote_ollama),
        cleanup_enabled=bool(args.cleanup) and not is_multipass,
        cleanup_mode=args.cleanup_mode or "strip_leak",
        cleanup_model_name=cleanup_model,
        text_model_name=text_model or cleanup_model,
        auto_activate_composite=not bool(getattr(args, "no_auto_composite", False)),
    )
    coord.provider = build_vision_provider(provider_id, url)
    candidates = list_candidates(corpus, clock=clock, ids=ids)
    import_run_id = None
    if args.bulk_run_cmd == "pending":
        selected = select_pending(candidates)
    elif args.bulk_run_cmd == "import-run":
        import_run_id = args.import_run_id
        selected = select_from_import_run(corpus, import_run_id, candidates)
    elif args.bulk_run_cmd == "notebooks":
        nids: list[str] = []
        for ref in args.notebooks:
            nid, _root = resolve_notebook_ref(corpus, ref)
            nids.append(nid)
        selected = select_by_ids(candidates, nids)
    else:
        print(
            f"error: unknown bulk-run subcommand {args.bulk_run_cmd}",
            file=sys.stderr,
        )
        return 2

    if not selected:
        print("No notebooks selected.")
        return 1
    try:
        run = coord.create_run(
            selected,
            settings=settings,
            force=bool(args.force),
            import_run_id=import_run_id,
            mode="multipass" if is_multipass else "single",
            vision_model_names=models if is_multipass else None,
            multipass_cleanup_enabled=bool(args.cleanup) if is_multipass else False,
        )
    except ValidationError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    model_label = ",".join(models) if is_multipass else models[0]
    print(
        f"ocr_run_id={run.ocr_run_id} notebooks={len(run.items)} "
        f"mode={run.mode} models={model_label} force={run.force}"
    )
    progress = coord.run_blocking(run.ocr_run_id)
    finished = store.load(progress.ocr_run_id)
    print(f"status={finished.status}")
    for item in finished.items:
        err = f" error={item.error_message}" if item.error_message else ""
        print(f"  {item.notebook_id} {item.state}{err}")
    return 0 if finished.status in {"completed", "partial"} else 1


def _cmd_bulk_analyse(args: argparse.Namespace, *, clock, ids) -> int:
    from transcribe.analysis.presets import resolve_analysis_preset
    from transcribe.corpus.analysis_batch_run import AnalysisBatchRunStore
    from transcribe.corpus.paths import CorpusPaths
    from transcribe.services.batch_analysis import (
        BatchAnalysisCoordinator,
        list_analysis_candidates,
        select_by_ids,
        select_from_import_run,
        select_needing_analysis,
    )
    from transcribe.services.batch_notebooks import resolve_notebook_ref

    corpus = CorpusPaths.from_runtime(runtime_paths())
    coord = BatchAnalysisCoordinator(corpus, clock=clock, ids=ids)
    store = AnalysisBatchRunStore(corpus)

    if args.bulk_analyse_cmd == "status":
        run = store.load(args.analysis_batch_id)
        print(
            f"analysis_batch_id={run.analysis_batch_id} status={run.status} "
            f"preset={run.preset_key or '-'} modules={len(run.module_ids)} "
            f"detectors={len(run.detector_ids)} items={len(run.items)}"
        )
        if run.import_run_id:
            print(f"import_run_id={run.import_run_id}")
        for item in run.items:
            err = f" error={item.error_message}" if item.error_message else ""
            print(
                f"  {item.notebook_id} {item.state} "
                f"modules={item.modules_completed}/{item.modules_total} "
                f"failed={item.modules_failed} skipped={item.modules_skipped}{err}"
            )
        return 0

    if args.bulk_analyse_cmd == "resume":
        progress = coord.resume(args.analysis_batch_id, blocking=True)
        run = store.load(progress.analysis_batch_id)
        print(f"analysis_batch_id={run.analysis_batch_id} status={run.status}")
        for item in run.items:
            print(f"  {item.notebook_id} {item.state}")
        return 0 if run.status in {"completed", "partial"} else 1

    preset = str(args.preset or "balanced")
    custom = [m.strip() for m in (args.module or []) if m and str(m).strip()]
    custom_dets = [
        d.strip() for d in (getattr(args, "detector", None) or []) if d and str(d).strip()
    ]
    if preset == "custom" and not custom and not custom_dets:
        print(
            "error: --preset custom requires at least one --module or --detector",
            file=sys.stderr,
        )
        return 2
    resolved = resolve_analysis_preset(
        preset, custom_modules=custom, custom_detectors=custom_dets
    )
    question = (args.question or "").strip() or None
    module_ids = list(resolved.module_ids)
    detector_ids = list(resolved.detector_ids)
    if question:
        from transcribe.analysis.presets import ask_execution_flags
        from transcribe.config.facade import get_config

        rag = get_config().effective.analysis.rag
        custom_qa, rag_qa = ask_execution_flags(
            rag.ask_mode, has_question=True, rag_enabled=rag.enabled
        )
        if custom_qa and "llm_custom_qa" not in module_ids:
            module_ids.append("llm_custom_qa")
        if rag_qa and "llm_rag_qa" not in module_ids:
            module_ids.append("llm_rag_qa")

    candidates = list_analysis_candidates(corpus, clock=clock, ids=ids)
    import_run_id = None
    if args.bulk_analyse_cmd == "pending":
        selected = select_needing_analysis(candidates)
    elif args.bulk_analyse_cmd == "import-run":
        import_run_id = args.import_run_id
        selected = select_from_import_run(corpus, import_run_id, candidates, purpose="analyse")
    elif args.bulk_analyse_cmd == "notebooks":
        nids: list[str] = []
        for ref in args.notebooks:
            nid, _root = resolve_notebook_ref(corpus, ref)
            nids.append(nid)
        selected = select_by_ids(candidates, nids)
    else:
        print(
            f"error: unknown bulk-analyse subcommand {args.bulk_analyse_cmd}",
            file=sys.stderr,
        )
        return 2

    if not selected:
        print("error: no notebooks selected", file=sys.stderr)
        return 2

    run = coord.create_run(
        selected,
        module_ids=module_ids,
        detector_ids=detector_ids,
        question_text=question,
        preset_label=preset.title(),
        preset_key=resolved.preset,
        preset_content_version=resolved.content_version,
        preset_policy_fingerprint=resolved.policy_fingerprint,
        import_run_id=import_run_id,
        text_model_name=(args.text_model or "").strip() or None,
    )
    print(
        f"analysis_batch_id={run.analysis_batch_id} notebooks={len(run.items)} "
        f"preset={run.preset_key} modules={len(run.module_ids)} "
        f"detectors={len(run.detector_ids)}"
    )
    progress = coord.run_blocking(run.analysis_batch_id)
    finished = store.load(progress.analysis_batch_id)
    print(f"status={finished.status}")
    for item in finished.items:
        err = f" error={item.error_message}" if item.error_message else ""
        print(f"  {item.notebook_id} {item.state}{err}")
    return 0 if finished.status in {"completed", "partial"} else 1


def _cmd_corpus_doctor(args: argparse.Namespace) -> int:
    from transcribe.corpus.paths import CorpusPaths
    from transcribe.services.corpus_doctor import CorpusDoctorService

    report = CorpusDoctorService(CorpusPaths.from_runtime(runtime_paths())).run(deep=args.deep)
    for finding in report.findings:
        print(f"{finding.severity}: [{finding.code}] {finding.message}")
    if report.ok and not report.findings:
        print("ok: corpus integrity checks passed")
    elif report.ok:
        print("ok: no errors (warnings above)")
    return 0 if report.ok else 1
