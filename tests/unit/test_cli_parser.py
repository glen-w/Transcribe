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
        "pages",
        "reorder",
        "move-to-date-cluster",
    ):
        assert name in dests, name


def test_runtime_paths_falls_back_without_main(monkeypatch) -> None:
    monkeypatch.delitem(__import__("sys").modules, "transcribe.__main__", raising=False)
    assert runtime_paths() is PATHS


def test_dispatch_notebook_returns_none_for_export_family() -> None:
    parser = build_parser()
    args = parser.parse_args(["export", "proj"])
    assert dispatch_notebook(args, clock=FakeClock(), ids=SequentialIds()) is None


def test_run_paddleocr_refuses_remote_host(tmp_path) -> None:
    from transcribe.__main__ import main
    from transcribe.services.project import ProjectService, open_project_paths

    paths = open_project_paths(tmp_path / "nb")
    ProjectService(paths, clock=FakeClock(), ids=SequentialIds()).create("nb")
    rc = main(
        [
            "run",
            str(tmp_path / "nb"),
            "--model",
            "PaddleOCR-VL-1.6",
            "--provider",
            "paddleocr",
            "--base-url",
            "http://example.com:8112",
        ]
    )
    assert rc == 2


def test_bulk_run_paddleocr_refuses_remote_host() -> None:
    from transcribe.__main__ import main

    rc = main(
        [
            "bulk-run",
            "notebooks",
            "proj",
            "--model",
            "PaddleOCR-VL-1.6",
            "--provider",
            "paddleocr",
            "--base-url",
            "http://example.com:8112",
        ]
    )
    assert rc == 2


def test_parser_provider_flag_defaults_ollama() -> None:
    parser = build_parser()
    run_args = parser.parse_args(["run", "proj", "--model", "qwen2.5vl:7b"])
    assert run_args.provider == "ollama"
    bulk = parser.parse_args(
        ["bulk-run", "notebooks", "proj", "--model", "PaddleOCR-VL-1.6", "--provider", "paddleocr"]
    )
    assert bulk.provider == "paddleocr"


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


def test_bulk_run_paddleocr_ignores_remote_ollama_default(monkeypatch, capsys) -> None:
    """The sidecar default is local even when the Ollama default is remote (M3).

    Reaching the health pre-flight proves the locality check passed.
    """
    from transcribe.__main__ import main
    from transcribe.errors import ProviderError
    from transcribe.providers.paddleocr import PaddleocrVisionProvider

    seen: list[str] = []

    def down(self) -> None:
        seen.append(self.base_url)
        raise ProviderError("sidecar down", code="connection")

    monkeypatch.setattr(PaddleocrVisionProvider, "healthcheck", down)
    monkeypatch.setenv("TRANSCRIBE_OLLAMA_BASE_URL", "http://203.0.113.9:11434")
    rc = main(["bulk-run", "pending", "--model", "PaddleOCR-VL-1.6", "--provider", "paddleocr"])
    err = capsys.readouterr().err
    assert "Refusing" not in err
    assert seen == ["http://127.0.0.1:8112"]
    assert rc == 1 and "sidecar down" in err


def test_run_paddleocr_fails_fast_when_sidecar_is_down(tmp_path, monkeypatch, capsys) -> None:
    from transcribe.__main__ import main
    from transcribe.errors import ProviderError
    from transcribe.providers.paddleocr import PaddleocrVisionProvider
    from transcribe.services.project import ProjectService, open_project_paths

    def down(self) -> None:
        raise ProviderError("Cannot reach PaddleOCR sidecar", code="connection")

    monkeypatch.setattr(PaddleocrVisionProvider, "healthcheck", down)
    paths = open_project_paths(tmp_path / "nb")
    ProjectService(paths, clock=FakeClock(), ids=SequentialIds()).create("nb")
    rc = main(["run", str(tmp_path / "nb"), "--model", "PaddleOCR-VL-1.6", "--provider", "paddleocr"])
    assert rc == 1
    assert "Cannot reach PaddleOCR sidecar" in capsys.readouterr().err


def test_paddleocr_rejects_allow_remote_flag(tmp_path, capsys) -> None:
    from transcribe.__main__ import main
    from transcribe.services.project import ProjectService, open_project_paths

    paths = open_project_paths(tmp_path / "nb")
    ProjectService(paths, clock=FakeClock(), ids=SequentialIds()).create("nb")
    common = ["--model", "PaddleOCR-VL-1.6", "--provider", "paddleocr", "--allow-remote-ollama"]
    assert main(["run", str(tmp_path / "nb"), *common]) == 2
    assert "does not apply" in capsys.readouterr().err
    assert main(["bulk-run", "notebooks", "proj", *common]) == 2
    assert "does not apply" in capsys.readouterr().err


def test_run_paddleocr_restores_notebook_settings(tmp_path, monkeypatch) -> None:
    """`run --provider paddleocr` must not leave the sidecar URL in notebook settings."""
    from tests.fakes import FakeVisionOCRProvider
    from tests.ingest.test_ingest import _png_bytes
    from transcribe.__main__ import main
    from transcribe.ingest import IngestService
    from transcribe.services.project import ProjectService, open_project_paths

    paths = open_project_paths(tmp_path / "nb")
    projects = ProjectService(paths, clock=FakeClock(), ids=SequentialIds())
    project = projects.create("nb")
    IngestService(paths, clock=FakeClock(), ids=SequentialIds("i")).import_bytes(
        "p.png", _png_bytes(color=(1, 20, 30))
    )
    settings = project.settings
    settings.model_name = "my-ollama-vision"
    projects.save_settings(projects.load(), settings)
    ollama_url = projects.load().settings.base_url

    fake = FakeVisionOCRProvider(provider_id="paddleocr")
    fake.base_url = "http://127.0.0.1:8112"  # matches the plan, so the job keeps this fake
    monkeypatch.setattr(
        "transcribe.cli.notebook.build_vision_provider", lambda _pid, _url, **_kw: fake
    )
    rc = main(["run", str(tmp_path / "nb"), "--model", "PaddleOCR-VL-1.6", "--provider", "paddleocr"])
    assert rc == 0 and fake.calls == 1
    after = projects.load().settings
    assert (after.base_url, after.model_name) == (ollama_url, "my-ollama-vision")
