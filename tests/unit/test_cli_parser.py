"""CLI parser split keeps the public command surface."""

from __future__ import annotations

from transcribe.cli.parser import build_parser


def test_build_parser_registers_core_commands() -> None:
    parser = build_parser()
    dests = set()

    def _walk(p) -> None:
        dests.add(getattr(p, "dest", None))
        for action in getattr(p, "_actions", ()):
            if getattr(action, "choices", None) and hasattr(action, "dest"):
                dests.add(action.dest)
            subs = getattr(action, "choices", None)
            if isinstance(subs, dict):
                dests.update(subs)
                for child in subs.values():
                    _walk(child)

    _walk(parser)
    for name in (
        "init",
        "import",
        "run",
        "multipass",
        "export",
        "bulk-import",
        "bulk-run",
        "bulk-analyse",
        "rag",
        "backup",
        "restore",
        "corpus-doctor",
        "detect",
    ):
        assert name in dests, name
