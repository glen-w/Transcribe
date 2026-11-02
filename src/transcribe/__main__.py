"""CLI entry point: python -m transcribe …"""

from __future__ import annotations

import sys

from transcribe.cli.backup_cmd import _cmd_backup, _cmd_restore
from transcribe.cli.bulk import (
    _cmd_bulk_analyse,
    _cmd_bulk_import,
    _cmd_bulk_run,
    _cmd_corpus_doctor,
)
from transcribe.cli.export_cmd import (
    _cmd_export,
    _cmd_export_detection_finetune,
    _cmd_export_finetune,
)
from transcribe.cli.notebook import dispatch_notebook
from transcribe.cli.parser import build_parser
from transcribe.cli.rag import _cmd_rag
from transcribe.cli.workspace_cmd import (
    _cmd_collections,
    _cmd_quality,
    _cmd_saved_search,
    _cmd_search,
    _cmd_verify_export,
    _cmd_workspace_doctor,
)
from transcribe.errors import (
    JobConflictError,
    ProviderError,
    TranscribeError,
)
from transcribe.ports import SystemClock, UuidGenerator
from transcribe.runtime_paths import PATHS

__all__ = ["PATHS", "main"]


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    clock = SystemClock()
    ids = UuidGenerator()

    try:
        if args.cmd == "bulk-import":
            return _cmd_bulk_import(args, clock=clock, ids=ids)
        if args.cmd == "bulk-run":
            return _cmd_bulk_run(args, clock=clock, ids=ids)
        if args.cmd == "bulk-analyse":
            return _cmd_bulk_analyse(args, clock=clock, ids=ids)
        if args.cmd == "rag":
            return _cmd_rag(args)
        if args.cmd == "corpus-doctor":
            return _cmd_corpus_doctor(args)
        if args.cmd == "backup":
            return _cmd_backup(args)
        if args.cmd == "restore":
            return _cmd_restore(args)
        if args.cmd == "workspace-doctor":
            return _cmd_workspace_doctor(args)
        if args.cmd == "verify-export":
            return _cmd_verify_export(args)
        if args.cmd == "search":
            return _cmd_search(args)
        if args.cmd == "collections":
            return _cmd_collections(args, clock=clock, ids=ids)
        if args.cmd == "saved-search":
            return _cmd_saved_search(args, clock=clock, ids=ids)
        if args.cmd == "quality":
            return _cmd_quality(args, clock=clock, ids=ids)
        if args.cmd == "export":
            return _cmd_export(args, clock=clock, ids=ids)
        if args.cmd == "export-finetune":
            return _cmd_export_finetune(args, clock=clock, ids=ids)
        if args.cmd == "export-detection-finetune":
            return _cmd_export_detection_finetune(args, clock=clock, ids=ids)

        code = dispatch_notebook(args, clock=clock, ids=ids)
        if code is not None:
            return code

        parser.error(f"unknown command {args.cmd}")
        return 2
    except (TranscribeError, JobConflictError, ProviderError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
