"""CLI workspace backup / restore commands."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

def _cmd_backup(args: argparse.Namespace) -> int:
    from transcribe.errors import BackupError
    from transcribe.runtime_paths import build_runtime_paths
    from transcribe.services.workspace_backup import (
        BackupOptions,
        WorkspaceBackupService,
        default_backup_dest,
    )

    runtime = build_runtime_paths()
    service = WorkspaceBackupService()
    try:
        if args.backup_cmd == "create":
            dest = Path(args.dest) if args.dest else default_backup_dest(runtime)
            result = service.create_backup(
                runtime,
                dest,
                BackupOptions(
                    include_inbox=bool(args.include_inbox),
                    include_exports=bool(args.include_exports),
                ),
                force=bool(args.force),
            )
            print(f"wrote {result.archive_path}")
            print(
                f"notebooks={result.notebook_count} files={result.file_count} "
                f"uncompressed_bytes={result.uncompressed_bytes}"
            )
            includes = result.manifest.get("includes") or {}
            print(
                "includes: "
                + ", ".join(f"{key}={value}" for key, value in sorted(includes.items()))
            )
            return 0
        if args.backup_cmd == "verify":
            result = service.verify_backup(Path(args.archive))
            for message in result.messages:
                print(f"note: {message}")
            counts = (result.manifest.get("counts") or {}) if result.manifest else {}
            includes = (result.manifest.get("includes") or {}) if result.manifest else {}
            print(
                "ok: backup verified "
                f"(notebooks={counts.get('notebooks')} files={counts.get('files')} "
                f"uncompressed_bytes={counts.get('uncompressed_bytes')})"
            )
            if includes:
                print(
                    "includes: "
                    + ", ".join(f"{key}={value}" for key, value in sorted(includes.items()))
                )
            created = (result.manifest or {}).get("created_at")
            version = (result.manifest or {}).get("transcribe_version")
            if created or version:
                print(f"created_at={created} transcribe_version={version}")
            return 0
    except BackupError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"error: unknown backup subcommand {args.backup_cmd!r}", file=sys.stderr)
    return 2


def _cmd_restore(args: argparse.Namespace) -> int:
    from transcribe.errors import BackupError
    from transcribe.runtime_paths import build_runtime_paths
    from transcribe.services.workspace_backup import WorkspaceBackupService

    runtime = build_runtime_paths()
    service = WorkspaceBackupService()
    archive = Path(args.archive)
    dry_run = bool(args.dry_run)
    if not dry_run and not args.yes:
        print(
            "Restore replaces notebooks, corpus, and config from the archive.\n"
            f"  archive: {archive}\n"
            f"  projects: {runtime.projects_dir}\n"
            f"  data: {runtime.data_dir}\n"
            "Re-run with --yes to confirm, or --dry-run to preview.",
            file=sys.stderr,
        )
        return 2
    try:
        result = service.restore_backup(
            runtime,
            archive,
            safety=not bool(args.no_safety_backup),
            dry_run=dry_run,
        )
    except BackupError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    for message in result.messages:
        print(message)
    if result.safety_archive is not None:
        print(f"safety_archive={result.safety_archive}")
    if result.doctor is not None:
        for finding in result.doctor.findings:
            print(f"{finding.severity}: [{finding.code}] {finding.message}")
        for nb_id, nb_report in result.doctor.notebook_reports.items():
            for finding in nb_report.findings:
                print(f"{finding.severity}: [{nb_id}/{finding.code}] {finding.message}")
    if dry_run:
        print("ok: dry-run complete (no changes)")
        return 0
    return 0 if result.ok else 1
