"""Argparse surface for ``python -m transcribe``."""

from __future__ import annotations

import argparse
from pathlib import Path

from transcribe.services.export_options import BODY_FONT_CHOICES


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="transcribe", description="Local notebook OCR")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_init = sub.add_parser("init", help="Create a new project directory")
    p_init.add_argument("project", type=Path)
    p_init.add_argument("--title", default="Untitled notebook")

    p_import = sub.add_parser("import", help="Import an image or PDF into a project")
    p_import.add_argument("project", type=Path)
    p_import.add_argument("source", type=Path)
    p_import.add_argument("--dpi", type=int, default=200)

    p_models = sub.add_parser("models", help="List vision-capable Ollama models")
    p_models.add_argument("--base-url", default=None)
    p_models.add_argument("--all", action="store_true", help="List all models")
    p_models.add_argument("--refresh", action="store_true")

    p_run = sub.add_parser("run", help="Run OCR on project pages")
    p_run.add_argument("project", type=Path)
    p_run.add_argument("--model", required=True)
    p_run.add_argument("--base-url", default=None)
    p_run.add_argument("--force", action="store_true")
    p_run.add_argument("--workers", type=int, default=1)
    p_run.add_argument("--allow-remote-ollama", action="store_true")
    p_run.add_argument(
        "--cleanup",
        action="store_true",
        help="Enable optional post-OCR text-model cleanup",
    )
    p_run.add_argument(
        "--cleanup-mode",
        choices=["strip_leak", "sanitize_light", "rewrite"],
        default=None,
        help="Cleanup mode (requires --cleanup)",
    )
    p_run.add_argument(
        "--cleanup-model",
        default=None,
        help="Text model for cleanup (defaults to project text analysis model)",
    )

    p_multi = sub.add_parser(
        "multipass",
        help="Run multiple vision OCR models then rank/composite",
    )
    p_multi.add_argument("project", type=Path)
    p_multi.add_argument(
        "--model",
        action="append",
        dest="models",
        required=False,
        help="Vision model (repeat; at least two). Not required with --resume",
    )
    p_multi.add_argument("--base-url", default=None)
    p_multi.add_argument("--force", action="store_true")
    p_multi.add_argument("--allow-remote-ollama", action="store_true")
    p_multi.add_argument(
        "--no-auto-composite",
        action="store_true",
        help="Do not auto-activate composite candidates",
    )
    p_multi.add_argument(
        "--text-model",
        default=None,
        help="Text model for rank/composite (defaults to project cleanup/text model)",
    )
    p_multi.add_argument(
        "--resume",
        default=None,
        metavar="PASS_ID",
        help="Resume an incomplete multipass job by pass_id",
    )
    p_multi.add_argument(
        "--cleanup",
        action="store_true",
        help="Run post-OCR text-model cleanup on vision phases (off by default)",
    )

    p_ft = sub.add_parser(
        "export-finetune",
        help="Export preferred/active OCR + images for external fine-tuning",
    )
    p_ft.add_argument("project", type=Path)
    p_ft.add_argument("dest", type=Path, nargs="?", default=None)
    p_ft.add_argument("--require-preferred", action="store_true")
    p_ft.add_argument("--include-rejected", action="store_true")
    p_ft.add_argument("--no-edited", action="store_true", help="Skip pages with human edits")
    p_ft.add_argument("--hardlink-images", action="store_true")

    p_dft = sub.add_parser(
        "export-detection-finetune",
        help="Export approved/rejected detection findings for external fine-tuning",
    )
    p_dft.add_argument("project", type=Path)
    p_dft.add_argument("dest", type=Path, nargs="?", default=None)
    p_dft.add_argument(
        "--include-unreviewed",
        action="store_true",
        help="Include unreviewed findings (default: approved/rejected only)",
    )
    p_dft.add_argument(
        "--detector",
        action="append",
        default=[],
        help="Filter by detector_id (repeatable)",
    )
    p_dft.add_argument(
        "--finding-type",
        action="append",
        default=[],
        help="Filter by finding_type (repeatable)",
    )
    p_dft.add_argument("--hardlink-images", action="store_true")

    p_models.add_argument(
        "--prefs",
        action="store_true",
        help="Show preference stats beside each model",
    )

    p_export = sub.add_parser(
        "export",
        help="Export notebook formats (json/markdown/text/html/epub/pdf)",
    )
    p_export.add_argument(
        "project",
        type=Path,
        nargs="?",
        default=None,
        help="Primary project path (optional when --notebooks is used)",
    )
    p_export.add_argument("dest", type=Path, nargs="?", default=None)
    p_export.add_argument(
        "--notebooks",
        type=Path,
        nargs="+",
        default=None,
        help="One or more notebook roots (anthology export when multiple)",
    )
    p_export.add_argument(
        "--format",
        dest="formats",
        action="append",
        default=None,
        help="Format to include (repeatable): json, markdown, text, html, epub, pdf",
    )
    p_export.add_argument(
        "--profile",
        default=None,
        help="Export profile name (default/readable/compact/large_print or user)",
    )
    p_export.add_argument("--body-font", choices=list(BODY_FONT_CHOICES), default=None)
    p_export.add_argument("--body-size", type=float, default=None)
    p_export.add_argument("--line-height", type=float, default=None)
    p_export.add_argument("--margin", type=float, default=None)
    p_export.add_argument(
        "--page-breaks",
        choices=["per_page", "continuous"],
        default=None,
    )
    p_export.add_argument("--title", default=None, help="Override anthology title")

    p_status = sub.add_parser("status", help="Show project page statuses")
    p_status.add_argument("project", type=Path)

    p_doctor = sub.add_parser("doctor", help="Validate project integrity")
    p_doctor.add_argument("project", type=Path)
    p_doctor.add_argument(
        "--deep",
        action="store_true",
        help="Hash source/render files and verify against the manifest",
    )

    p_detect = sub.add_parser("detect", help="Run a notebook content detector")
    p_detect.add_argument("project", type=Path)
    p_detect.add_argument(
        "--detector",
        default="poetry",
        help="Detector id (default: poetry)",
    )
    p_detect.add_argument("--force", action="store_true")
    p_detect.add_argument(
        "--auto-tag",
        action="store_true",
        help="After publish, tag pages from findings (finding type, or person names for names)",
    )
    p_detect.add_argument(
        "--list",
        action="store_true",
        help="List available detectors and exit",
    )

    p_bulk = sub.add_parser(
        "bulk-import",
        help="Plan/commit a folder into the notebook corpus (ImportRun)",
    )
    bulk_sub = p_bulk.add_subparsers(dest="bulk_cmd", required=True)
    p_bulk_plan = bulk_sub.add_parser(
        "folder",
        help="Scan a folder, create an ImportRun, and commit it",
    )
    p_bulk_plan.add_argument("folder", type=Path, help="Folder of JPEG/PNG/PDF files")
    p_bulk_plan.add_argument(
        "--title",
        default=None,
        help="Notebook title (default: folder name)",
    )
    p_bulk_plan.add_argument(
        "--policy",
        choices=["skip_existing_v1", "create_duplicate_v1"],
        default="skip_existing_v1",
    )
    p_bulk_plan.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the plan and exit without committing",
    )
    p_bulk_folders = bulk_sub.add_parser(
        "folders",
        help="Scan a parent directory; each child folder becomes a notebook",
    )
    p_bulk_folders.add_argument(
        "parent",
        type=Path,
        help="Parent directory whose immediate child folders become notebooks",
    )
    p_bulk_folders.add_argument(
        "--policy",
        choices=["skip_existing_v1", "create_duplicate_v1"],
        default="skip_existing_v1",
    )
    p_bulk_folders.add_argument(
        "--on-existing",
        choices=["skip", "overwrite"],
        default="skip",
        help="When a child folder name already maps to a managed notebook",
    )
    p_bulk_folders.add_argument(
        "--confirm-overwrite",
        default=None,
        help="Required for --on-existing overwrite; must be exactly 'OVERWRITE ALL'",
    )
    p_bulk_folders.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the scan/plan and exit without committing or deleting",
    )
    p_bulk_status = bulk_sub.add_parser("status", help="Show ImportRun outcomes")
    p_bulk_status.add_argument("import_run_id")
    p_bulk_resume = bulk_sub.add_parser("resume", help="Resume a non-terminal ImportRun")
    p_bulk_resume.add_argument("import_run_id")
    p_corpus_doctor = sub.add_parser(
        "corpus-doctor",
        help="Validate workspace corpus index integrity",
    )
    p_corpus_doctor.add_argument(
        "--deep",
        action="store_true",
        help="Also deep-doctor each registered notebook",
    )

    p_backup = sub.add_parser(
        "backup",
        help="Create or verify a full-workspace backup ZIP",
    )
    backup_sub = p_backup.add_subparsers(dest="backup_cmd", required=True)
    p_backup_create = backup_sub.add_parser(
        "create",
        help="Write a workspace backup ZIP (notebooks + corpus + config)",
    )
    p_backup_create.add_argument(
        "--dest",
        type=Path,
        default=None,
        help="Destination .zip (default: {EXPORT}/backups/transcribe-workspace-<stamp>.zip)",
    )
    p_backup_create.add_argument(
        "--include-inbox",
        action="store_true",
        help="Also pack TRANSCRIBE_INBOX_DIR",
    )
    p_backup_create.add_argument(
        "--include-exports",
        action="store_true",
        help="Also pack TRANSCRIBE_EXPORT_DIR (skips the destination zip itself)",
    )
    p_backup_create.add_argument(
        "--force",
        action="store_true",
        help="Overwrite destination if the .zip already exists",
    )
    p_backup_verify = backup_sub.add_parser(
        "verify",
        help="Verify a workspace backup ZIP without changing the workspace",
    )
    p_backup_verify.add_argument("archive", type=Path)

    p_restore = sub.add_parser(
        "restore",
        help="Replace the current workspace from a backup ZIP",
    )
    p_restore.add_argument("archive", type=Path)
    p_restore.add_argument(
        "--yes",
        action="store_true",
        help="Confirm replace (required to write)",
    )
    p_restore.add_argument(
        "--no-safety-backup",
        action="store_true",
        help="Skip automatic pre-restore safety ZIP",
    )
    p_restore.add_argument(
        "--dry-run",
        action="store_true",
        help="Verify and describe replace plan without writing",
    )

    p_bulk_run = sub.add_parser(
        "bulk-run",
        help="Run OCR across many notebooks (OcrBatchRun)",
    )
    bulk_run_sub = p_bulk_run.add_subparsers(dest="bulk_run_cmd", required=True)

    def _add_bulk_run_ocr_flags(parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "--model",
            action="append",
            required=True,
            help=("Vision model (repeat for multipass compare; " "one value = single-model batch)"),
        )
        parser.add_argument("--base-url", default=None)
        parser.add_argument("--force", action="store_true")
        parser.add_argument("--workers", type=int, default=1)
        parser.add_argument("--allow-remote-ollama", action="store_true")
        parser.add_argument(
            "--cleanup",
            action="store_true",
            help=(
                "Single-model: enable post-OCR text cleanup. "
                "Multipass (≥2 --model): opt in vision-phase cleanup during compare"
            ),
        )
        parser.add_argument(
            "--cleanup-mode",
            choices=["strip_leak", "sanitize_light", "rewrite"],
            default=None,
        )
        parser.add_argument("--cleanup-model", default=None)
        parser.add_argument(
            "--text-model",
            default=None,
            help="Text model for multipass rank/composite (and cleanup when unset)",
        )
        parser.add_argument(
            "--no-auto-composite",
            action="store_true",
            help="Multipass: do not auto-activate composite candidates",
        )

    p_br_pending = bulk_run_sub.add_parser(
        "pending",
        help="OCR corpus notebooks that still have untranscribed or failed pages",
    )
    _add_bulk_run_ocr_flags(p_br_pending)
    p_br_import = bulk_run_sub.add_parser(
        "import-run",
        help="OCR notebooks committed by an ImportRun",
    )
    p_br_import.add_argument("import_run_id")
    _add_bulk_run_ocr_flags(p_br_import)
    p_br_nbs = bulk_run_sub.add_parser(
        "notebooks",
        help="OCR explicit notebook ids or project paths",
    )
    p_br_nbs.add_argument(
        "notebooks",
        nargs="+",
        help="Notebook id or project root (repeatable)",
    )
    _add_bulk_run_ocr_flags(p_br_nbs)
    p_br_status = bulk_run_sub.add_parser("status", help="Show OcrBatchRun outcomes")
    p_br_status.add_argument("ocr_run_id")
    p_br_resume = bulk_run_sub.add_parser("resume", help="Resume a non-terminal OcrBatchRun")
    p_br_resume.add_argument("ocr_run_id")

    p_bulk_ax = sub.add_parser(
        "bulk-analyse",
        help="Run Analyse across many notebooks (AnalysisBatchRun)",
    )
    bulk_ax_sub = p_bulk_ax.add_subparsers(dest="bulk_analyse_cmd", required=True)

    def _add_bulk_analyse_flags(parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "--preset",
            choices=["quick", "balanced", "thorough", "custom"],
            default="balanced",
            help="Analysis preset (default: balanced)",
        )
        parser.add_argument(
            "--module",
            action="append",
            default=[],
            help="Module id (repeatable; required when --preset custom without --detector)",
        )
        parser.add_argument(
            "--detector",
            action="append",
            default=[],
            help="Detector id (repeatable; included in the Analyse plan)",
        )
        parser.add_argument(
            "--question",
            default=None,
            help="Optional Ask-notebook question (adds llm_custom_qa)",
        )
        parser.add_argument(
            "--text-model",
            default=None,
            help=(
                "Text Ollama model for LLM modules (frozen for the whole batch; "
                "defaults to notebook/workspace preference)"
            ),
        )

    p_ba_pending = bulk_ax_sub.add_parser(
        "pending",
        help="Analyse notebooks that need analysis (text + non-healthy)",
    )
    _add_bulk_analyse_flags(p_ba_pending)
    p_ba_import = bulk_ax_sub.add_parser(
        "import-run",
        help="Analyse notebooks committed by an ImportRun",
    )
    p_ba_import.add_argument("import_run_id")
    _add_bulk_analyse_flags(p_ba_import)
    p_ba_nbs = bulk_ax_sub.add_parser(
        "notebooks",
        help="Analyse explicit notebook ids or project paths",
    )
    p_ba_nbs.add_argument(
        "notebooks",
        nargs="+",
        help="Notebook id or project root (repeatable)",
    )
    _add_bulk_analyse_flags(p_ba_nbs)
    p_ba_status = bulk_ax_sub.add_parser("status", help="Show AnalysisBatchRun outcomes")
    p_ba_status.add_argument("analysis_batch_id")
    p_ba_resume = bulk_ax_sub.add_parser("resume", help="Resume a non-terminal AnalysisBatchRun")
    p_ba_resume.add_argument("analysis_batch_id")

    p_rag = sub.add_parser("rag", help="Ask RAG index (embed only; no Ask LLM)")
    rag_sub = p_rag.add_subparsers(dest="rag_cmd", required=True)
    p_rag_ingest = rag_sub.add_parser(
        "ingest",
        help="Build or refresh per-notebook RAG indexes from effective text",
    )
    p_rag_ingest.add_argument(
        "notebooks",
        nargs="*",
        help="Notebook id or project root (repeatable)",
    )
    p_rag_ingest.add_argument(
        "--library",
        action="store_true",
        help="Index every managed notebook in the workspace",
    )
    p_rag_ingest.add_argument(
        "--force",
        action="store_true",
        help="Re-index even when nothing changed",
    )
    p_rag_ingest.add_argument(
        "--retry-failed",
        action="store_true",
        help="Retry notebooks that failed on an earlier ingest",
    )
    p_rag_ingest.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be indexed; writes nothing",
    )
    p_rag_ingest.add_argument(
        "--limit",
        "-n",
        type=int,
        default=None,
        help="Index at most this many notebooks that need work",
    )
    p_rag_ingest.add_argument("--base-url", default=None)

    return parser
