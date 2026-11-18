"""``transcribe ocr-queue`` — notebooks with schedulable vision OCR."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from transcribe.runtime_paths import PATHS
from transcribe.services.ocr_schedule import list_schedulable_notebooks, parse_models


def cmd_ocr_queue(args: argparse.Namespace) -> int:
    models = parse_models(list(args.models or []))
    if not models:
        print("error: at least one --model is required", file=sys.stderr)
        return 2
    projects_dir = Path(args.projects_dir) if args.projects_dir else PATHS.projects_dir
    limit = int(args.max or 0)
    try:
        paths = list_schedulable_notebooks(
            projects_dir,
            models,
            tier=args.tier,
            limit=limit,
        )
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    for path in paths:
        print(path)
    return 0