"""Argparse surface for ``python -m transcribe``."""

from __future__ import annotations

import argparse
from pathlib import Path

from transcribe.services.export_options import BODY_FONT_CHOICES


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="transcribe", description="Transcribe — local notebook OCR")
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
    p_run.add_argument(
        "--retry-failed",
        action="store_true",
        help="Only pages whose latest attempt failed, was interrupted, or returned no text",
    )
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
    p_export.add_argument(
        "--include-tag",
        dest="include_tags",
        action="append",
        default=[],
        help="Reading formats only: require this page tag (repeatable, AND)",
    )
    p_export.add_argument(
        "--exclude-tag",
        dest="exclude_tags",
        action="append",
        default=[],
        help="Reading formats only: skip pages with this tag (repeatable)",
    )
    p_export.add_argument(
        "--collection",
        default=None,
        help="Export the notebooks in this collection id (anthology)",
    )
    p_export.add_argument(
        "--custom-font",
        default=None,
        help="Custom body font family name (overrides --body-font)",
    )

    p_pages = sub.add_parser("pages", help="Reorder notebook pages (pages array only)")
    pages_sub = p_pages.add_subparsers(dest="pages_cmd", required=True)
    p_pages_reorder = pages_sub.add_parser(
        "reorder",
        help="Set notebook order from a permutation of page ids",
    )
    p_pages_reorder.add_argument("project", type=Path)
    p_pages_reorder.add_argument(
        "page_ids",
        nargs="+",
        help="Every page_id exactly once; does not rename render directories",
    )
    p_pages_move = pages_sub.add_parser(
        "move-to-date-cluster",
        help="Insert a page after the confirmed cluster for its date",
    )
    p_pages_move.add_argument("project", type=Path)
    p_pages_move.add_argument("page_id")
    p_pages_batch = pages_sub.add_parser(
        "batch",
        help="Apply one metadata change to selected pages (dry-run unless --apply)",
    )
    p_pages_batch.add_argument("project", type=Path)
    p_pages_batch.add_argument(
        "--page",
        dest="page_ids",
        action="append",
        default=[],
        help="Page id (repeatable). Or pass --saved.",
    )
    p_pages_batch.add_argument("--saved", default=None, help="Saved search id or name")
    p_pages_batch.add_argument(
        "--action",
        required=True,
        choices=[
            "approve_dates",
            "ignore_dates",
            "ignore",
            "unignore",
            "add_tag",
            "remove_tag",
            "set_page_role",
            "set_page_certainty",
        ],
    )
    p_pages_batch.add_argument("--tag", default="")
    p_pages_batch.add_argument(
        "--role",
        default="",
        choices=["", "text", "scan"],
        help="For set_page_role",
    )
    p_pages_batch.add_argument(
        "--certainty",
        default="",
        choices=["", "sure", "unsure"],
        help="For set_page_certainty",
    )
    p_pages_batch.add_argument(
        "--apply",
        action="store_true",
        help="Write the change. Without this flag the command is a dry run.",
    )

    p_pages_batch_meta = pages_sub.add_parser(
        "batch-meta",
        help="Alias of pages batch (durable-notebook metadata)",
        parents=[],
    )
    # Parents=[] still needs the same flags; copy from batch via a shared helper
    # by registering identical arguments.
    p_pages_batch_meta.add_argument("project", type=Path)
    p_pages_batch_meta.add_argument(
        "--page",
        dest="page_ids",
        action="append",
        default=[],
        help="Page id (repeatable). Or pass --saved.",
    )
    p_pages_batch_meta.add_argument("--saved", default=None, help="Saved search id or name")
    p_pages_batch_meta.add_argument(
        "--action",
        required=True,
        choices=[
            "approve_dates",
            "ignore_dates",
            "ignore",
            "unignore",
            "add_tag",
            "remove_tag",
            "set_page_role",
            "set_page_certainty",
        ],
    )
    p_pages_batch_meta.add_argument("--tag", default="")
    p_pages_batch_meta.add_argument(
        "--role",
        default="",
        choices=["", "text", "scan"],
    )
    p_pages_batch_meta.add_argument(
        "--certainty",
        default="",
        choices=["", "sure", "unsure"],
    )
    p_pages_batch_meta.add_argument(
        "--apply",
        action="store_true",
        help="Write the change. Without this flag the command is a dry run.",
    )

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
    p_backup_one = backup_sub.add_parser(
        "restore-notebook",
        help="Extract one notebook from a workspace ZIP (does not replace the workspace)",
    )
    p_backup_one.add_argument("archive", type=Path)
    p_backup_one.add_argument("notebook_id")
    p_backup_one.add_argument(
        "--force",
        action="store_true",
        help="Replace the live folder for that notebook id only",
    )
    p_backup_one.add_argument(
        "--dry-run",
        action="store_true",
        help="Verify and describe the extract without writing",
    )

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

    p_ws_doctor = sub.add_parser(
        "workspace-doctor",
        help="Corpus doctor plus a doctor pass over every notebook",
    )
    p_ws_doctor.add_argument("--deep", action="store_true", help="Deep hashing (slower)")

    p_verify_export = sub.add_parser(
        "verify-export",
        help="Verify an export directory is readable without Transcribe",
    )
    p_verify_export.add_argument("dest", type=Path, help="Export directory with export.manifest.json")

    p_search = sub.add_parser("search", help="Search page text across notebooks")
    p_search.add_argument("query", nargs="?", default="")
    p_search.add_argument("--tags", default=None, help="Comma-separated page tags (AND)")
    p_search.add_argument("--people", default=None, help="Comma-separated published-NER people")
    p_search.add_argument("--places", default=None, help="Comma-separated published-NER places")
    p_search.add_argument("--include-archived", action="store_true")
    p_search.add_argument(
        "--bookmarked",
        action="store_true",
        help="Only pages bookmarked in reading-marks.json",
    )
    p_search.add_argument("--collection", default=None, help="Collection id to search within")
    p_search.add_argument("--saved", default=None, help="Saved search id or name")
    p_search.add_argument("--order", choices=["oldest", "newest"], default="oldest")
    p_search.add_argument("--limit", type=int, default=50)
    p_search.add_argument("--offset", type=int, default=0)

    p_collections = sub.add_parser(
        "collections", help="Manage notebook collections and archived state"
    )
    col_sub = p_collections.add_subparsers(dest="collections_cmd", required=True)
    col_sub.add_parser("list", help="List collections and archived notebooks")
    p_col_create = col_sub.add_parser("create", help="Create a collection")
    p_col_create.add_argument("name")
    p_col_create.add_argument("--description", default="")
    p_col_rename = col_sub.add_parser("rename", help="Rename a collection")
    p_col_rename.add_argument("collection_id")
    p_col_rename.add_argument("name")
    p_col_delete = col_sub.add_parser("delete", help="Delete a collection")
    p_col_delete.add_argument("collection_id")
    p_col_assign = col_sub.add_parser("assign", help="Add a notebook to a collection")
    p_col_assign.add_argument("collection_id")
    p_col_assign.add_argument("project_id")
    p_col_unassign = col_sub.add_parser("unassign", help="Remove a notebook from a collection")
    p_col_unassign.add_argument("collection_id")
    p_col_unassign.add_argument("project_id")
    p_col_archive = col_sub.add_parser("archive", help="Archive a notebook (hide by default)")
    p_col_archive.add_argument("project_id")
    p_col_unarchive = col_sub.add_parser("unarchive", help="Unarchive a notebook")
    p_col_unarchive.add_argument("project_id")

    p_saved = sub.add_parser("saved-search", help="Manage saved searches")
    saved_sub = p_saved.add_subparsers(dest="saved_cmd", required=True)
    saved_sub.add_parser("list", help="List saved searches")
    p_saved_save = saved_sub.add_parser("save", help="Save (or update) a search by name")
    p_saved_save.add_argument("name")
    p_saved_save.add_argument("--query", default="")
    p_saved_save.add_argument("--tags", default=None)
    p_saved_save.add_argument("--people", default=None)
    p_saved_save.add_argument("--places", default=None)
    p_saved_save.add_argument("--include-archived", action="store_true")
    p_saved_save.add_argument("--order", choices=["oldest", "newest"], default="oldest")
    p_saved_delete = saved_sub.add_parser("delete", help="Delete a saved search")
    p_saved_delete.add_argument("search_id")

    p_quality = sub.add_parser(
        "quality", help="Local quality ratings (collect-only; no telemetry)"
    )
    quality_sub = p_quality.add_subparsers(dest="quality_cmd", required=True)
    p_quality_summary = quality_sub.add_parser("summary", help="Summarise local ratings")
    p_quality_summary.add_argument("--project", default=None, help="Filter by project id")
    p_quality_board = quality_sub.add_parser(
        "scoreboard",
        help="CER of succeeded OCR against human corrections (local, read-only)",
    )
    p_quality_board.add_argument("--project", default=None, help="Filter by project id")
    p_quality_rate = quality_sub.add_parser("rate", help="Record a local rating")
    p_quality_rate.add_argument(
        "kind", choices=["ocr_sample", "cleanup", "analysis"]
    )
    p_quality_rate.add_argument(
        "verdict",
        choices=["accept", "edit", "reject", "up", "down"],
        help="ocr_sample: accept/edit/reject; cleanup: accept/reject; analysis: up/down",
    )
    p_quality_rate.add_argument("--project", default=None)
    p_quality_rate.add_argument("--page", default=None)
    p_quality_rate.add_argument("--module", default=None)
    p_quality_rate.add_argument("--notes", default="")

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
