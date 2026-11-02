"""CLI parser split keeps the public command surface."""

from __future__ import annotations

from pathlib import Path

from transcribe.cli.notebook import dispatch_notebook
from transcribe.cli.parser import build_parser
from transcribe.cli.runtime import runtime_paths
from transcribe.runtime_paths import PATHS
from transcribe.services.project import ProjectService, open_project_paths
from tests.conftest import FakeClock, SequentialIds


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


def test_runtime_paths_falls_back_without_main(monkeypatch) -> None:
    monkeypatch.delitem(__import__("sys").modules, "transcribe.__main__", raising=False)
    assert runtime_paths() is PATHS


def test_dispatch_notebook_returns_none_for_export_family() -> None:
    parser = build_parser()
    args = parser.parse_args(["export", "proj"])
    assert dispatch_notebook(args, clock=FakeClock(), ids=SequentialIds()) is None


def test_dispatch_init_and_status(tmp_path: Path, capsys) -> None:
    parser = build_parser()
    root = tmp_path / "nb"
    clock, ids = FakeClock(), SequentialIds()
    args = parser.parse_args(["init", str(root), "--title", "CLI notebook"])
    assert dispatch_notebook(args, clock=clock, ids=ids) == 0
    out = capsys.readouterr().out
    assert "Created project" in out
    project = ProjectService(open_project_paths(root), clock=clock, ids=ids).load(
        reconcile=False
    )
    assert project.title == "CLI notebook"
    status = parser.parse_args(["status", str(root)])
    assert dispatch_notebook(status, clock=clock, ids=ids) == 0
