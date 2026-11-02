"""CLI export / fine-tune export commands."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from transcribe.cli.runtime import runtime_paths
from transcribe.services.export import ExportService
from transcribe.services.project import ProjectService, open_project_paths

def _cmd_export_finetune(args: argparse.Namespace, *, clock, ids) -> int:
    from transcribe.services.finetune_export import (
        FinetuneExportOptions,
        FinetuneExportService,
    )

    paths = open_project_paths(args.project)
    projects = ProjectService(paths, clock=clock, ids=ids)
    projects.load()
    opts = FinetuneExportOptions(
        include_edited_pages=not args.no_edited,
        require_preferred=bool(args.require_preferred),
        include_rejected_candidates=bool(args.include_rejected),
        image_mode="hardlink" if args.hardlink_images else "copy",
    )
    out = FinetuneExportService(paths, projects).export(args.dest, options=opts)
    print(f"Fine-tune export written to {out}")
    return 0


def _cmd_export_detection_finetune(args: argparse.Namespace, *, clock, ids) -> int:
    from transcribe.services.detection_finetune_export import (
        DetectionFinetuneExportOptions,
        DetectionFinetuneExportService,
    )

    paths = open_project_paths(args.project)
    projects = ProjectService(paths, clock=clock, ids=ids)
    projects.load()
    opts = DetectionFinetuneExportOptions(
        include_unreviewed=bool(args.include_unreviewed),
        detector_ids=tuple(args.detector or ()),
        finding_types=tuple(args.finding_type or ()),
        image_mode="hardlink" if args.hardlink_images else "copy",
    )
    out = DetectionFinetuneExportService(projects).export(args.dest, options=opts)
    print(f"Detection fine-tune export written to {out}")
    return 0


def _cmd_export(args: argparse.Namespace, *, clock, ids) -> int:
    from transcribe.config.defaults import builtin_profile_config
    from transcribe.config.profiles import load_profile_overlay
    from transcribe.services.export_options import ExportOptions, ExportTypography

    roots: list[Path] = []
    if args.notebooks:
        roots.extend(args.notebooks)
    if args.project is not None:
        if args.project not in roots:
            roots.insert(0, args.project)
    if not roots:
        print("error: provide a project path and/or --notebooks", file=sys.stderr)
        return 2

    base = ExportOptions()
    if args.profile:
        try:
            overlay = load_profile_overlay("export", args.profile)
        except Exception:
            overlay = builtin_profile_config("export", args.profile) or {}
        if overlay.get("export"):
            base = ExportOptions.from_dict(overlay["export"])

    formats = base.formats
    if args.formats:
        formats = frozenset(str(f).lower() for f in args.formats)  # type: ignore[arg-type]

    typo = base.typography
    typo = ExportTypography(
        body_font=args.body_font or typo.body_font,  # type: ignore[arg-type]
        body_size_pt=float(args.body_size if args.body_size is not None else typo.body_size_pt),
        line_height=float(args.line_height if args.line_height is not None else typo.line_height),
        paragraph_spacing_em=typo.paragraph_spacing_em,
        margin_in=float(args.margin if args.margin is not None else typo.margin_in),
        heading_scale=typo.heading_scale,
    )
    opts = ExportOptions(
        formats=formats,
        page_breaks=args.page_breaks or base.page_breaks,  # type: ignore[arg-type]
        include_dates=base.include_dates,
        include_blank_pages=base.include_blank_pages,
        title_page=base.title_page,
        typography=typo,
    )

    snapshots = []
    primary_paths = None
    primary_projects = None
    for root in roots:
        nb_paths = open_project_paths(root)
        nb_projects = ProjectService(nb_paths, clock=clock, ids=ids)
        if primary_paths is None:
            primary_paths = nb_paths
            primary_projects = nb_projects
        snapshots.append(ExportService.capture_snapshot_at(nb_paths, nb_projects))

    assert primary_paths is not None and primary_projects is not None
    if args.dest is not None:
        dest = args.dest
    elif os.getenv("TRANSCRIBE_EXPORT_DIR"):
        dest = runtime_paths().export_dir / primary_paths.root.name
    else:
        dest = primary_paths.exports_dir

    written = ExportService(primary_paths, primary_projects).export_snapshots(
        snapshots,
        dest_dir=dest,
        options=opts,
        title=args.title,
    )
    for kind, path in written.items():
        print(f"{kind}: {path}")
    return 0

