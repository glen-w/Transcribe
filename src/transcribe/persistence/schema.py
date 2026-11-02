"""Persisted format/schema recognition."""

from __future__ import annotations

from typing import Any

SUPPORTED: dict[str, int] = {
    "transcribe.project": 1,
    "transcribe.page-result": 1,
    "transcribe.notebook": 1,
    "transcribe.export-manifest": 1,
    "transcribe.export-bundle": 1,
    "transcribe.analysis-document": 1,
    "transcribe.analysis-result": 1,
    "transcribe.detection-result": 1,
    "transcribe.prompt-definition": 1,
    "transcribe.page-metrics": 1,
    # Bulk-import generation (runtime-normative; workspace may omit index)
    "transcribe.corpus-index": 1,
    "transcribe.import-run": 1,
    "transcribe.ocr-batch-run": 1,
    "transcribe.analysis-batch-run": 1,
    "transcribe.ingest-journal": 1,
    "transcribe.ocr-preference-ledger": 1,
    "transcribe.ocr-multipass-job": 1,
    "transcribe.finetune-export-manifest": 1,
    "transcribe.detection-finetune-export-manifest": 1,
    "transcribe.workspace-backup": 1,
    "personal_corpus.tag-catalog": 1,
    "transcribe.detection-auto-tag": 1,
    "transcribe.ocr-model-recipes": 1,
    # Workspace / job envelopes (L4 registry completeness). Settings and
    # profiles keep their own ConfigError codes on load; job-record and
    # geocode-cache are write-side today. Interface-menus identity is this
    # format even though on-disk files currently omit the ``format`` key.
    "transcribe.settings": 1,
    "transcribe.profile": 1,
    "transcribe.job-record": 1,
    "transcribe.interface-menus": 1,
    "transcribe.geocode-cache": 1,
    # 1.2 expansion wave: workspace organisation / saved filters / quality.
    "transcribe.saved-searches": 1,
    "transcribe.notebook-collections": 1,
    "transcribe.quality-ratings": 1,
    # 1.3: per-notebook bookmarks and marginal notes. Absent file is valid.
    "transcribe.reading-marks": 1,
}


class SchemaError(ValueError):
    pass


def require_format(payload: Any, expected_format: str) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise SchemaError(f"expected object for {expected_format}")
    fmt = payload.get("format")
    version = payload.get("schema_version")
    if fmt != expected_format:
        raise SchemaError(f"expected format {expected_format!r}, got {fmt!r}")
    expected_version = SUPPORTED.get(expected_format)
    if expected_version is None:
        raise SchemaError(f"unsupported format: {expected_format!r}")
    if not isinstance(version, int):
        raise SchemaError(f"schema_version must be int for {expected_format}")
    if version != expected_version:
        raise SchemaError(
            f"unsupported schema_version {version} for {expected_format}; "
            f"this build supports {expected_version}"
        )
    return payload
