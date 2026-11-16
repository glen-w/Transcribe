"""U2.2 sample notebook install."""

from __future__ import annotations

from pathlib import Path

from tests.conftest import FakeClock, SequentialIds
from transcribe.runtime_paths import RuntimePaths
from transcribe.services.project import ProjectService, open_project_paths
from transcribe.services.sample_notebook import SAMPLE_SLUG, install_sample_notebook


def _runtime(tmp_path: Path) -> RuntimePaths:
    data = tmp_path / "data"
    projects = tmp_path / "projects"
    for path in (data, projects, tmp_path / "inbox", tmp_path / "exports", data / "config"):
        path.mkdir(parents=True, exist_ok=True)
    return RuntimePaths(
        repo_root=tmp_path,
        data_dir=data,
        projects_dir=projects,
        inbox_dir=tmp_path / "inbox",
        export_dir=tmp_path / "exports",
    )


def test_sample_manifest_is_package_data() -> None:
    """The wheel must carry the fixture: Docker installs the wheel, not the repo."""
    from importlib import resources

    from transcribe.services.sample_notebook import load_sample_manifest

    root = Path(__file__).resolve().parents[2]
    pyproject = (root / "pyproject.toml").read_text(encoding="utf-8")
    assert '"transcribe.samples" = ["demo-notebook/*"]' in pyproject
    packaged = resources.files("transcribe.samples").joinpath("demo-notebook", "manifest.json")
    assert packaged.is_file()
    assert len(load_sample_manifest()["pages"]) == 3
    source = (root / "src/transcribe/services/sample_notebook.py").read_text(encoding="utf-8")
    assert "parents[3]" not in source  # no source-tree lookups


def test_install_sample_notebook_seeds_text(tmp_path: Path, monkeypatch):
    runtime = _runtime(tmp_path)
    monkeypatch.setenv("TRANSCRIBE_DATA_DIR", str(runtime.data_dir))
    monkeypatch.setenv("TRANSCRIBE_PROJECTS_DIR", str(runtime.projects_dir))
    root = install_sample_notebook(
        runtime,
        clock=FakeClock(),
        ids=SequentialIds("smp"),
    )
    assert root.name == SAMPLE_SLUG
    assert root.is_dir()
    projects = ProjectService(open_project_paths(root), clock=FakeClock(), ids=SequentialIds("x"))
    project = projects.load()
    assert len(project.pages) == 3
    texts = [projects.load_page_result(p.page_id).effective_text() for p in project.pages]
    assert any("Anna" in (t or "") for t in texts)
    assert any("Paris" in (t or "") for t in texts)


def test_install_sample_idempotent_without_force(tmp_path: Path, monkeypatch):
    runtime = _runtime(tmp_path)
    monkeypatch.setenv("TRANSCRIBE_DATA_DIR", str(runtime.data_dir))
    monkeypatch.setenv("TRANSCRIBE_PROJECTS_DIR", str(runtime.projects_dir))
    clock, ids = FakeClock(), SequentialIds("smp")
    root1 = install_sample_notebook(runtime, clock=clock, ids=ids)
    marker = root1 / "project.json"
    mtime = marker.stat().st_mtime_ns
    root2 = install_sample_notebook(runtime, clock=clock, ids=ids, force=False)
    assert root2 == root1
    assert marker.stat().st_mtime_ns == mtime


def test_install_sample_writes_nothing_into_the_package(tmp_path: Path) -> None:
    """A wheel install may be read-only (Docker runs as a non-root user)."""
    import transcribe.samples as samples_pkg

    pkg_dir = Path(samples_pkg.__file__).parent
    before = sorted(p.relative_to(pkg_dir) for p in pkg_dir.rglob("*") if "__pycache__" not in p.parts)
    install_sample_notebook(_runtime(tmp_path), clock=FakeClock(), ids=SequentialIds("ro"))
    after = sorted(p.relative_to(pkg_dir) for p in pkg_dir.rglob("*") if "__pycache__" not in p.parts)
    assert after == before


def test_install_sample_missing_manifest_is_a_readable_error(tmp_path: Path, monkeypatch) -> None:
    import pytest

    from transcribe.errors import ProjectError
    from transcribe.services import sample_notebook

    def boom(_package):
        raise ModuleNotFoundError("transcribe.samples")

    monkeypatch.setattr(sample_notebook.resources, "files", boom)
    runtime = _runtime(tmp_path)
    with pytest.raises(ProjectError, match="import your own pages"):
        install_sample_notebook(runtime, clock=FakeClock(), ids=SequentialIds("m"))
    assert list(runtime.projects_dir.iterdir()) == []


def test_install_sample_failure_leaves_no_partial_notebook(tmp_path: Path, monkeypatch) -> None:
    import pytest

    from transcribe.services import sample_notebook

    def boom(self, *_args, **_kwargs):
        raise RuntimeError("disk full")

    monkeypatch.setattr(sample_notebook.IngestService, "import_bytes", boom)
    runtime = _runtime(tmp_path)
    with pytest.raises(RuntimeError):
        install_sample_notebook(runtime, clock=FakeClock(), ids=SequentialIds("f"))
    assert list(runtime.projects_dir.iterdir()) == []


def test_install_sample_refuses_non_notebook_folder(tmp_path: Path) -> None:
    import pytest

    from transcribe.errors import ProjectError

    runtime = _runtime(tmp_path)
    squatter = runtime.projects_dir / SAMPLE_SLUG
    squatter.mkdir()
    (squatter / "keep.txt").write_text("mine", encoding="utf-8")
    with pytest.raises(ProjectError, match="not a notebook"):
        install_sample_notebook(runtime, clock=FakeClock(), ids=SequentialIds("s"))
    assert (squatter / "keep.txt").read_text(encoding="utf-8") == "mine"


def test_install_sample_force_replaces(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    clock, ids = FakeClock(), SequentialIds("fr")
    root = install_sample_notebook(runtime, clock=clock, ids=ids)
    (root / "stray.txt").write_text("x", encoding="utf-8")
    again = install_sample_notebook(runtime, clock=clock, ids=ids, force=True)
    assert again == root
    assert not (root / "stray.txt").exists()
    assert [p.name for p in runtime.projects_dir.iterdir()] == [SAMPLE_SLUG]
