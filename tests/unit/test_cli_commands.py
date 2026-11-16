"""CLI command bodies, end to end through ``main`` (offline).

Parser shape is covered in ``test_cli_parser.py``. These tests run the command
functions against a temporary workspace with a fake vision provider, so exit
codes and printed outcomes are pinned without a live Ollama or sidecar.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.fakes import FakeVisionOCRProvider
from tests.ingest.test_ingest import _png_bytes
from tests.services.test_archive import _make_notebook, _runtime
from transcribe.__main__ import main
from transcribe.providers.base import DiscoveryResult, ModelInfo
from transcribe.services.project import ProjectService, open_project_paths

REMOTE = "http://203.0.113.9:11434"


@pytest.fixture
def workspace(tmp_path: Path, monkeypatch):
    import transcribe.__main__ as main_mod

    runtime = _runtime(tmp_path)
    monkeypatch.setattr(main_mod, "PATHS", runtime)
    monkeypatch.setenv("TRANSCRIBE_DATA_DIR", str(runtime.data_dir))
    monkeypatch.setenv("TRANSCRIBE_PROJECTS_DIR", str(runtime.projects_dir))
    monkeypatch.setenv("TRANSCRIBE_INBOX_DIR", str(runtime.inbox_dir))
    monkeypatch.setenv("TRANSCRIBE_EXPORT_DIR", str(runtime.export_dir))
    monkeypatch.delenv("TRANSCRIBE_OLLAMA_BASE_URL", raising=False)
    return runtime


@pytest.fixture
def fake_vision(monkeypatch) -> FakeVisionOCRProvider:
    """Route every CLI-built vision provider to one in-memory fake."""
    fake = FakeVisionOCRProvider()
    fake.base_url = "http://127.0.0.1:11434"

    def build(_provider_id, _url, **_kwargs):
        return fake

    monkeypatch.setattr("transcribe.cli.notebook.build_vision_provider", build)
    monkeypatch.setattr("transcribe.providers.factory.build_vision_provider", build)
    return fake


def _scan_folder(root: Path, name: str, pages: int = 2) -> Path:
    folder = root / name
    folder.mkdir(parents=True)
    for i in range(pages):
        (folder / f"scan-{i}.png").write_bytes(_png_bytes(color=(10 * (i + 1), 40, 90)))
    return folder


def _projects(root: Path) -> ProjectService:
    from tests.conftest import FakeClock, SequentialIds

    return ProjectService(open_project_paths(root), clock=FakeClock(), ids=SequentialIds("t"))


# --- notebook commands -------------------------------------------------------


def test_init_import_status_doctor(workspace, tmp_path: Path, capsys) -> None:
    nb = workspace.projects_dir / "diary"
    assert main(["init", str(nb), "--title", "Diary"]) == 0
    assert "Created project" in capsys.readouterr().out

    scan = tmp_path / "one.png"
    scan.write_bytes(_png_bytes(color=(5, 6, 7)))
    assert main(["import", str(nb), str(scan)]) == 0
    assert "total pages=1" in capsys.readouterr().out

    assert main(["status", str(nb)]) == 0
    out = capsys.readouterr().out
    assert out.startswith("0000") and "pending" in out

    assert main(["doctor", str(nb)]) == 0
    assert "ok:" in capsys.readouterr().out


def test_import_missing_project_is_a_clean_error(workspace, tmp_path: Path, capsys) -> None:
    scan = tmp_path / "one.png"
    scan.write_bytes(_png_bytes())
    assert main(["import", str(workspace.projects_dir / "nope"), str(scan)]) == 1
    assert capsys.readouterr().err.startswith("error:")


def test_status_marks_edited_pages(workspace, capsys) -> None:
    root, projects = _make_notebook(
        workspace, "nb", title="Diary", page_specs=[{"text": "raw"}, {}]
    )
    first = projects.load().pages[0].page_id
    projects.save_user_edit(first, "corrected")
    assert main(["status", str(root)]) == 0
    lines = capsys.readouterr().out.strip().splitlines()
    assert lines[0].endswith("succeeded edited")
    assert lines[1].endswith("pending")


def test_pages_reorder_and_batch(workspace, capsys) -> None:
    root, projects = _make_notebook(
        workspace, "nb", title="Diary", page_specs=[{"text": "a"}, {"text": "b"}]
    )
    first, second = (p.page_id for p in projects.load().pages)

    assert main(["pages", "reorder", str(root), second, first]) == 0
    assert capsys.readouterr().out.split() == [second, first]
    assert [p.page_id for p in projects.load().pages] == [second, first]

    # Empty selection is refused.
    assert main(["pages", "batch", str(root), "--action", "ignore"]) == 2
    assert "empty page selection" in capsys.readouterr().err

    # Unknown saved search is refused before anything is touched.
    assert main(["pages", "batch", str(root), "--saved", "nope", "--action", "ignore"]) == 2
    assert "no saved search" in capsys.readouterr().err

    # Dry run changes nothing; --apply writes.
    args = ["pages", "batch", str(root), "--page", first, "--action", "add_tag", "--tag", "trip"]
    assert main(args) == 0
    assert capsys.readouterr().out.startswith("dry-run:")
    assert "trip" not in (projects.load().pages[1].tags or [])
    assert main([*args, "--apply"]) == 0
    assert capsys.readouterr().out.startswith("applied:")
    tagged = {p.page_id: list(p.tags or []) for p in projects.load().pages}
    assert tagged[first] == ["trip"] and tagged[second] == []

    # The batch-meta alias reaches the same code.
    assert (
        main(
            ["pages", "batch-meta", str(root), "--page", second]
            + ["--action", "set_page_certainty", "--certainty", "unsure", "--apply"]
        )
        == 0
    )
    assert "changed=1" in capsys.readouterr().out


def test_models_lists_filters_and_warns(workspace, monkeypatch, capsys) -> None:
    from transcribe.providers.ollama import OllamaVisionProvider

    listed = DiscoveryResult(
        models=[
            ModelInfo(name="glm-ocr", digest="d1", capabilities=["vision"], capability_known=True),
            ModelInfo(
                name="qwen3:8b", digest=None, capabilities=["completion"], capability_known=True
            ),
        ],
        error=None,
    )
    monkeypatch.setattr(OllamaVisionProvider, "list_models", lambda self, refresh=False: listed)

    assert main(["models"]) == 0
    out = capsys.readouterr().out
    assert "glm-ocr\tdigest=d1\tcapabilities=vision" in out
    assert "qwen3:8b" not in out  # text-only models are not OCR candidates

    assert main(["models", "--all", "--prefs"]) == 0
    assert "qwen3:8b\tdigest=-" in capsys.readouterr().out

    assert main(["models", "--base-url", REMOTE]) == 0
    assert "images would leave this machine" in capsys.readouterr().err

    empty = DiscoveryResult(models=[], error="connection refused")
    monkeypatch.setattr(OllamaVisionProvider, "list_models", lambda self, refresh=False: empty)
    assert main(["models"]) == 1
    captured = capsys.readouterr()
    assert "No models found." in captured.out
    assert "Discovery warning: connection refused" in captured.err


def test_run_refusals_leave_settings_alone(workspace, capsys) -> None:
    root, projects = _make_notebook(workspace, "nb", title="Diary", page_specs=[{}])
    before = projects.load().settings.as_dict()

    assert main(["run", str(root), "--model", "glm-ocr", "--base-url", REMOTE]) == 2
    assert "--allow-remote-ollama" in capsys.readouterr().err

    assert main(["run", str(root), "--model", "glm-ocr", "--cleanup-mode", "rewrite"]) == 2
    assert "require --cleanup" in capsys.readouterr().err

    assert projects.load().settings.as_dict() == before


def test_run_transcribes_and_retry_failed(workspace, fake_vision, capsys) -> None:
    root, projects = _make_notebook(workspace, "nb", title="Diary", page_specs=[{}, {}])

    assert main(["run", str(root), "--model", "fake-vision"]) == 0
    assert "outcome=completed status=completed failed=0" in capsys.readouterr().out
    assert fake_vision.calls == 2
    pages = projects.load().pages
    assert all(projects.load_page_result(p.page_id).status == "succeeded" for p in pages)
    assert projects.load().settings.model_name == "fake-vision"

    # Nothing failed, so --retry-failed has no work and makes no vision calls.
    assert main(["run", str(root), "--model", "fake-vision", "--retry-failed"]) == 0
    assert "no failed, interrupted, or empty_output pages" in capsys.readouterr().out
    assert fake_vision.calls == 2

    # A plain re-run skips on fingerprint.
    assert main(["run", str(root), "--model", "fake-vision"]) == 0
    assert "skipped=2" in capsys.readouterr().out
    assert fake_vision.calls == 2


def test_run_reports_failed_pages_and_retries_only_those(workspace, fake_vision, capsys) -> None:
    root, projects = _make_notebook(workspace, "nb", title="Diary", page_specs=[{}, {}])
    fake_vision.fail_codes = ["http_error"]  # first call fails, not retriable

    rc = main(["run", str(root), "--model", "fake-vision", "--workers", "1"])
    out = capsys.readouterr().out
    assert "failed=1" in out
    assert rc == 0  # documented: only a tripped circuit or non-completed job exits 1
    statuses = sorted(
        projects.load_page_result(p.page_id).status for p in projects.load().pages
    )
    assert statuses == ["failed", "succeeded"]

    calls = fake_vision.calls
    assert main(["run", str(root), "--model", "fake-vision", "--retry-failed"]) == 0
    assert fake_vision.calls == calls + 1  # only the failed page was sent again
    assert all(
        projects.load_page_result(p.page_id).status == "succeeded"
        for p in projects.load().pages
    )


def test_multipass_refusals(workspace, capsys) -> None:
    root, _projects_svc = _make_notebook(workspace, "nb", title="Diary", page_specs=[{}])

    assert main(["multipass", str(root), "--model", "a", "--model", "b", "--base-url", REMOTE]) == 2
    assert "--allow-remote-ollama" in capsys.readouterr().err

    assert main(["multipass", str(root), "--model", "only-one"]) == 2
    assert "at least two --model" in capsys.readouterr().err


def test_detect_list_and_lexical_run(workspace, capsys) -> None:
    root, _projects_svc = _make_notebook(
        workspace,
        "nb",
        title="Diary",
        page_specs=[{"text": "I walked home. I was tired and I slept."}, {"text": "Rain."}],
    )
    assert main(["detect", str(root), "--list"]) == 0
    listed = capsys.readouterr().out
    assert "first_person" in listed and "poetry" in listed

    assert main(["detect", str(root), "--detector", "first_person"]) == 0
    out = capsys.readouterr().out
    assert "detector=first_person outcome=success" in out
    assert "page 1\t" in out


def test_unknown_detector_is_a_clean_error(workspace, capsys) -> None:
    root, _projects_svc = _make_notebook(workspace, "nb", title="Diary", page_specs=[{"text": "x"}])
    assert main(["detect", str(root), "--detector", "no-such-detector"]) == 2
    err = capsys.readouterr().err
    assert err.startswith("error: unknown detector") and "--list" in err


# --- bulk-import -------------------------------------------------------------


def test_bulk_import_folder_dry_run_commit_status_resume(workspace, tmp_path, capsys) -> None:
    folder = _scan_folder(tmp_path / "inbox", "holiday", pages=2)

    assert main(["bulk-import", "folder", str(folder), "--dry-run"]) == 0
    assert "plan_id=" in capsys.readouterr().out
    assert list(workspace.projects_dir.iterdir()) == []  # dry run wrote no notebook

    assert main(["bulk-import", "folder", str(folder), "--title", "Holiday"]) == 0
    out = capsys.readouterr().out
    assert "status=complete" in out
    run_id = next(
        line.split("import_run_id=")[1].split()[0]
        for line in out.splitlines()
        if line.startswith("import_run_id=")
    )
    notebooks = [p for p in workspace.projects_dir.iterdir() if (p / "project.json").is_file()]
    assert len(notebooks) == 1
    assert len(_projects(notebooks[0]).load().pages) == 2

    assert main(["bulk-import", "status", run_id]) == 0
    assert f"import_run_id={run_id} status=complete" in capsys.readouterr().out
    assert main(["bulk-import", "resume", run_id]) == 0  # terminal run: idempotent
    capsys.readouterr()

    # Same folder again is refused up front with a readable reason, and no
    # failed ImportRun is recorded for it.
    runs_dir = workspace.data_dir / "corpus"
    before = sorted(p.name for p in runs_dir.rglob("*.json"))
    assert main(["bulk-import", "folder", str(folder)]) == 1
    err = capsys.readouterr().err
    assert "already exists" in err and "Rename the folder" in err
    assert sorted(p.name for p in runs_dir.rglob("*.json")) == before
    assert len(_projects(notebooks[0]).load().pages) == 2

    assert main(["bulk-import", "status", "no-such-run"]) == 1
    assert capsys.readouterr().err.startswith("error:")


def test_bulk_import_folders_scans_children(workspace, tmp_path, capsys) -> None:
    parent = tmp_path / "inbox"
    _scan_folder(parent, "alpha", pages=1)
    _scan_folder(parent, "beta", pages=2)
    (parent / "empty").mkdir()

    assert main(["bulk-import", "folders", str(parent), "--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "new=2" in out and "empty_skipped=1" in out
    assert list(workspace.projects_dir.iterdir()) == []

    assert main(["bulk-import", "folders", str(parent)]) == 0
    assert "status=complete" in capsys.readouterr().out
    # A second pass over the same parent has nothing new and says so.
    assert main(["bulk-import", "folders", str(parent), "--dry-run"]) == 1
    assert "already imported" in capsys.readouterr().err

    assert main(["corpus-doctor"]) == 0
    assert "ok:" in capsys.readouterr().out


# --- bulk-run ----------------------------------------------------------------


def test_bulk_run_argument_refusals(workspace, capsys) -> None:
    base = ["bulk-run", "pending", "--model", "glm-ocr"]

    assert main([*base, "--base-url", REMOTE]) == 2
    assert "--allow-remote-ollama" in capsys.readouterr().err

    assert main([*base, "--cleanup-model", "qwen3:8b"]) == 2
    assert "require --cleanup" in capsys.readouterr().err

    assert main(["bulk-run", "pending", "--model", "  "]) == 2
    assert "at least one --model" in capsys.readouterr().err


def test_bulk_run_with_nothing_to_do(workspace, fake_vision, capsys) -> None:
    assert main(["bulk-run", "pending", "--model", "fake-vision"]) == 1
    assert "No notebooks selected." in capsys.readouterr().out
    assert main(["bulk-run", "notebooks", "missing", "--model", "fake-vision"]) == 1
    assert "notebook not found" in capsys.readouterr().err
    assert fake_vision.calls == 0


def test_bulk_run_pending_then_status_and_resume(workspace, fake_vision, capsys) -> None:
    _make_notebook(workspace, "alpha", title="Alpha", page_specs=[{}, {}])
    beta_root, beta = _make_notebook(workspace, "beta", title="Beta", page_specs=[{}])

    assert main(["bulk-run", "pending", "--model", "fake-vision"]) == 0
    out = capsys.readouterr().out
    assert "notebooks=2 mode=single models=fake-vision" in out
    assert "status=completed" in out
    assert fake_vision.calls == 3
    run_id = out.split("ocr_run_id=")[1].split()[0]

    assert main(["bulk-run", "status", run_id]) == 0
    status = capsys.readouterr().out
    assert f"ocr_run_id={run_id} status=completed" in status
    assert "provider=" not in status  # Ollama is the unmarked default
    assert status.count(" completed pages=") == 2

    assert main(["bulk-run", "resume", run_id]) == 0
    capsys.readouterr()
    assert fake_vision.calls == 3  # fingerprint skip on resume

    # Everything is transcribed now, so `pending` selects nothing.
    assert main(["bulk-run", "pending", "--model", "fake-vision"]) == 1
    capsys.readouterr()

    # Explicit notebook by project path, forced.
    assert main(["bulk-run", "notebooks", str(beta_root), "--model", "fake-vision", "--force"]) == 0
    assert "notebooks=1" in capsys.readouterr().out
    assert fake_vision.calls == 4
    assert beta.load().settings.model_name == "fake-vision"


def test_bulk_run_import_run_selects_only_that_import(
    workspace, fake_vision, tmp_path, capsys
) -> None:
    _make_notebook(workspace, "older", title="Older", page_specs=[{}])
    folder = _scan_folder(tmp_path / "inbox", "fresh", pages=2)
    assert main(["bulk-import", "folder", str(folder)]) == 0
    import_run_id = capsys.readouterr().out.split("import_run_id=")[1].split()[0]

    assert main(["bulk-run", "import-run", import_run_id, "--model", "fake-vision"]) == 0
    out = capsys.readouterr().out
    assert "notebooks=1" in out
    assert fake_vision.calls == 2  # the older notebook was not touched
    run_id = out.split("ocr_run_id=")[1].split()[0]
    assert main(["bulk-run", "status", run_id]) == 0
    assert f"import_run_id={import_run_id}" in capsys.readouterr().out


def test_bulk_run_records_and_shows_sidecar_provider(workspace, monkeypatch, capsys) -> None:
    _root, projects = _make_notebook(workspace, "alpha", title="Alpha", page_specs=[{}])
    ollama_settings = projects.load().settings.as_dict()
    paddle = FakeVisionOCRProvider(provider_id="paddleocr")
    paddle.base_url = "http://127.0.0.1:8112"
    monkeypatch.setattr(
        "transcribe.providers.factory.build_vision_provider", lambda _p, _u, **_k: paddle
    )

    args = ["bulk-run", "pending", "--model", "PaddleOCR-VL-1.6", "--provider", "paddleocr"]
    assert main(args) == 0
    run_id = capsys.readouterr().out.split("ocr_run_id=")[1].split()[0]
    assert paddle.calls == 1

    assert main(["bulk-run", "status", run_id]) == 0
    assert "provider=paddleocr" in capsys.readouterr().out
    # The notebook's Ollama host and model survive the sidecar run.
    after = projects.load().settings.as_dict()
    assert (after["base_url"], after["model_name"]) == (
        ollama_settings["base_url"],
        ollama_settings["model_name"],
    )


# --- bulk-analyse ------------------------------------------------------------


def test_bulk_analyse_refusals_and_lookup_errors(workspace, capsys) -> None:
    assert main(["bulk-analyse", "pending", "--preset", "custom"]) == 2
    assert "requires at least one --module or --detector" in capsys.readouterr().err

    assert main(["bulk-analyse", "pending", "--preset", "quick"]) == 2
    assert "no notebooks selected" in capsys.readouterr().err

    for sub in ("status", "resume"):
        assert main(["bulk-analyse", sub, "no-such-batch"]) == 1
        assert capsys.readouterr().err.startswith("error:")


def test_bulk_analyse_quick_then_status(workspace, capsys) -> None:
    _make_notebook(
        workspace,
        "alpha",
        title="Alpha",
        page_specs=[{"text": "Monday. Walked to the market with Anna. Felt calm after rain."}],
    )
    assert main(["bulk-analyse", "pending", "--preset", "quick"]) == 0
    out = capsys.readouterr().out
    assert "notebooks=1 preset=quick" in out
    assert "status=completed" in out
    batch_id = out.split("analysis_batch_id=")[1].split()[0]

    assert main(["bulk-analyse", "status", batch_id]) == 0
    status = capsys.readouterr().out
    assert f"analysis_batch_id={batch_id} status=completed" in status
    assert " completed modules=" in status


# --- export ------------------------------------------------------------------


def test_export_writes_formats_and_refuses_bad_input(workspace, tmp_path, capsys) -> None:
    root, _projects_svc = _make_notebook(
        workspace, "nb", title="Diary", page_specs=[{"text": "kept line"}]
    )
    dest = tmp_path / "out"
    assert main(["export", str(root), str(dest), "--format", "markdown", "--format", "json"]) == 0
    capsys.readouterr()
    written = {p.suffix for p in dest.rglob("*") if p.is_file()}
    assert ".md" in written and ".json" in written
    assert any("kept line" in p.read_text(encoding="utf-8") for p in dest.rglob("*.md"))

    assert main(["export"]) == 2
    assert "provide a project path" in capsys.readouterr().err

    assert main(["export", "--collection", "no-such-collection"]) == 2
    assert "no collection" in capsys.readouterr().err

    assert main(["export", str(workspace.projects_dir / "nope"), str(tmp_path / "x")]) == 1
    assert capsys.readouterr().err.startswith("error:")


def test_export_defaults_to_the_export_dir_and_takes_typography(workspace, capsys) -> None:
    root, _projects_svc = _make_notebook(
        workspace, "nb", title="Diary", page_specs=[{"text": "kept line"}]
    )
    args = ["export", str(root), "--format", "html", "--profile", "readable"]
    assert main([*args, "--body-size", "13", "--line-height", "1.6", "--margin", "1"]) == 0
    capsys.readouterr()
    out_dir = workspace.export_dir / "nb"
    assert any(p.suffix == ".html" for p in out_dir.rglob("*"))


def test_export_anthology_takes_single_positional_as_destination(
    workspace, tmp_path, capsys
) -> None:
    a_root, _a = _make_notebook(workspace, "a", title="A", page_specs=[{"text": "first book"}])
    b_root, _b = _make_notebook(workspace, "b", title="B", page_specs=[{"text": "second book"}])
    dest = tmp_path / "anthology"
    rc = main(["export", str(dest), "--notebooks", str(a_root), str(b_root), "--format", "markdown"])
    assert rc == 0
    capsys.readouterr()
    text = "\n".join(p.read_text(encoding="utf-8") for p in dest.rglob("*.md"))
    assert "first book" in text and "second book" in text


def test_export_finetune_writes_a_dataset(workspace, tmp_path, capsys) -> None:
    root, projects = _make_notebook(
        workspace, "nb", title="Diary", page_specs=[{"text": "raw reading"}]
    )
    projects.save_user_edit(projects.load().pages[0].page_id, "corrected reading")
    dest = tmp_path / "ft"
    assert main(["export-finetune", str(root), str(dest)]) == 0
    assert "Fine-tune export written to" in capsys.readouterr().out
    jsonl = list(dest.rglob("*.jsonl"))
    assert jsonl and "corrected reading" in jsonl[0].read_text(encoding="utf-8")

    assert main(["export-detection-finetune", str(root), str(tmp_path / "dft")]) == 0
    assert "Detection fine-tune export written to" in capsys.readouterr().out
