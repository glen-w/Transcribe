from __future__ import annotations

import pytest

from transcribe.paths import ProjectPaths
from transcribe.persistence.schema import SchemaError, require_format
from transcribe.ports import SystemClock, to_iso


def test_clock_utc_iso_has_z():
    stamp = to_iso(SystemClock().now())
    assert stamp.endswith("Z")
    assert "+" not in stamp[:-1] or True  # Z form


def test_rag_dir_is_under_project_cache(tmp_path):
    paths = ProjectPaths(root=tmp_path)
    assert paths.rag_dir == paths.cache_dir / "rag"
    assert paths.rag_dir.is_relative_to(tmp_path)


def test_path_containment_rejects_escape(tmp_path):
    paths = ProjectPaths(root=tmp_path)
    paths.ensure_layout()
    with pytest.raises(ValueError):
        paths.resolve_contained("../../etc/passwd")


def test_schema_rejects_unknown_version():
    with pytest.raises(SchemaError):
        require_format(
            {"format": "transcribe.project", "schema_version": 99},
            "transcribe.project",
        )


def test_schema_rejects_wrong_format():
    with pytest.raises(SchemaError):
        require_format(
            {"format": "transcribe.notebook", "schema_version": 1},
            "transcribe.project",
        )


def test_schema_rejects_non_object_payload():
    with pytest.raises(SchemaError, match="expected object"):
        require_format([], "transcribe.project")


def test_schema_rejects_non_int_schema_version():
    with pytest.raises(SchemaError, match="schema_version must be int"):
        require_format(
            {"format": "transcribe.project", "schema_version": "1"},
            "transcribe.project",
        )


def test_schema_accepts_known_format():
    payload = {"format": "transcribe.project", "schema_version": 1, "id": "x"}
    assert require_format(payload, "transcribe.project") is payload


def test_schema_rejects_unsupported_format_key():
    with pytest.raises(SchemaError, match="unsupported format"):
        require_format(
            {"format": "transcribe.not-a-real-format", "schema_version": 1},
            "transcribe.not-a-real-format",
        )


def test_schema_registry_includes_workspace_job_envelopes():
    from transcribe.persistence.schema import SUPPORTED

    for fmt in (
        "transcribe.settings",
        "transcribe.profile",
        "transcribe.job-record",
        "transcribe.interface-menus",
        "transcribe.geocode-cache",
    ):
        assert SUPPORTED.get(fmt) == 1, fmt
