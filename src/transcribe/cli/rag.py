"""CLI Ask RAG ingest command."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from transcribe.cli.runtime import runtime_paths
from transcribe.providers.ollama import normalize_base_url

def _cmd_rag(args: argparse.Namespace) -> int:
    if args.rag_cmd != "ingest":
        print(f"error: unknown rag subcommand {args.rag_cmd!r}", file=sys.stderr)
        return 2
    return _cmd_rag_ingest(args)


def _cmd_rag_ingest(args: argparse.Namespace) -> int:
    from transcribe.analysis.rag.exceptions import RagUnavailable
    from transcribe.analysis.rag.ingest import ingest_notebooks
    from transcribe.config.facade import get_config
    from transcribe.corpus.paths import CorpusPaths
    from transcribe.errors import CorpusError, ValidationError
    from transcribe.runtime_paths import default_ollama_base_url
    from transcribe.services.batch_notebooks import list_candidates, resolve_notebook_ref

    notebooks = list(args.notebooks or [])
    library = bool(args.library)
    if not notebooks and not library:
        print("error: give a notebook path/id and/or --library", file=sys.stderr)
        return 2
    rag = get_config().effective.analysis.rag
    corpus = CorpusPaths.from_runtime(runtime_paths())
    roots: list[Path] = []
    seen: set[str] = set()
    if library:
        for cand in list_candidates(corpus, include_page_stats=False):
            key = str(cand.root.resolve())
            if key not in seen:
                seen.add(key)
                roots.append(cand.root)
    for ref in notebooks:
        try:
            _nid, root = resolve_notebook_ref(corpus, ref)
        except (CorpusError, ValidationError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        key = str(root.resolve())
        if key not in seen:
            seen.add(key)
            roots.append(root)
    if not roots:
        print("No notebooks selected.")
        return 1
    url = normalize_base_url(args.base_url or default_ollama_base_url())
    try:
        batch = ingest_notebooks(
            roots,
            rag=rag,
            force=bool(args.force),
            retry_failed=bool(args.retry_failed),
            dry_run=bool(args.dry_run),
            limit=args.limit,
            ollama_base_url=url,
        )
    except RagUnavailable as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    for row in batch.rows:
        extra = f"\t{row.chunks}" if row.chunks else ""
        why = f"\t{row.reason}" if row.reason else ""
        print(f"{row.notebook_id}\t{row.status}{extra}{why}")
    summary = batch.summary()
    print(
        f"indexed={summary['indexed']} unchanged={summary['unchanged']} "
        f"empty={summary['empty']} failed={summary['failed']} chunks={summary['chunks']}"
        + (" dry-run" if batch.dry_run else "")
    )
    return 1 if summary["failed"] else 0
