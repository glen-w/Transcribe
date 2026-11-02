"""H4 longevity: standalone exports, workspace sweep, migration rehearsal."""

from __future__ import annotations

import json
from pathlib import Path

from transcribe.persistence.atomic import read_json, write_json_atomic
from transcribe.services.export import ExportService
from transcribe.services.export_verify import verify_export_bundle
from transcribe.services.project import ProjectService, open_project_paths
from transcribe.services.workspace_doctor import run_workspace_doctor
from tests.services.test_archive import _make_notebook, _runtime


def test_export_bundle_readable_without_transcribe(tmp_path: Path):
    runtime = _runtime(tmp_path)
    root, projects = _make_notebook(
        runtime,
        "nb1",
        title="Diary",
        page_specs=[{"text": "standalone export text"}],
    )
    service = ExportService(open_project_paths(root), projects)
    written = service.export_all(dest_dir=tmp_path / "out")
    result = verify_export_bundle(tmp_path / "out")
    assert result.ok, result.problems
    assert result.content_revision
    assert any(name.endswith(".md") for name in result.checked_files)

    # Corrupting a reading format is detected via the manifest checksum.
    md_path = written["markdown"]
    md_path.write_text(md_path.read_text(encoding="utf-8") + "tampered\n", encoding="utf-8")
    bad = verify_export_bundle(tmp_path / "out")
    assert bad.ok is False
    assert any("checksum" in p for p in bad.problems)


def test_verify_export_missing_manifest(tmp_path: Path):
    result = verify_export_bundle(tmp_path / "nope")
    assert result.ok is False
    assert result.problems


def test_workspace_doctor_sweep(tmp_path: Path):
    runtime = _runtime(tmp_path)
    _make_notebook(
        runtime,
        "nb1",
        title="Diary",
        page_specs=[{"text": "healthy notebook"}],
    )
    result = run_workspace_doctor(runtime)
    assert result.notebook_count == 1
    assert result.ok, (result.corpus_findings, result.failures)


def test_migration_rehearsal_legacy_notebook_loads_and_exports(tmp_path: Path):
    """A 1.0.1-shaped notebook (no 1.2 fields anywhere) loads, mutates, exports."""
    runtime = _runtime(tmp_path)
    root, projects = _make_notebook(
        runtime,
        "nb1",
        title="Legacy",
        page_specs=[{"text": "legacy page text"}],
    )
    paths = open_project_paths(root)
    manifest = read_json(paths.manifest)
    # Strip any additive fields a newer build might write, to pin the old shape.
    for page in manifest.get("pages", []):
        page.pop("suppressed_auto_tags", None)
        page.pop("review_status", None)
        page.pop("ignored", None)
    write_json_atomic(paths.manifest, manifest)

    reopened = ProjectService(paths, clock=projects.clock, ids=projects.ids)
    project = reopened.load()  # default read (L2)
    assert project.title == "Legacy"
    assert len(project.pages) == 1
    # Absence of 1.2 workspace files is a valid workspace.
    assert not (runtime.data_dir / "config" / "notebook-collections.json").exists()
    assert not (runtime.data_dir / "config" / "saved-searches.json").exists()

    service = ExportService(paths, reopened)
    service.export_all(dest_dir=tmp_path / "out")
    assert verify_export_bundle(tmp_path / "out").ok

    # The loaded manifest round-trips through json (no lost identity).
    assert json.loads(json.dumps(project.as_dict()))["id"] == project.id
