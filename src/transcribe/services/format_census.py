"""Format census for workspace-doctor.

Walks workspace JSON that carries a ``format`` key and reports files whose
format or schema_version this build does not support. Files are never
modified. There is still no migrator: unknown versions fail closed at load.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from transcribe.persistence.schema import SUPPORTED
from transcribe.runtime_paths import RuntimePaths

_SKIP_DIR_NAMES = frozenset({".cache", "__pycache__", ".staging", "cache"})


@dataclass
class FormatFinding:
    severity: str
    code: str
    message: str
    path: str


@dataclass
class FormatCensus:
    counts: dict[str, int] = field(default_factory=dict)
    findings: list[FormatFinding] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not any(item.severity == "error" for item in self.findings)


def _iter_json(root: Path) -> list[Path]:
    if not root.is_dir():
        return []
    found: list[Path] = []
    for path in root.rglob("*.json"):
        if any(part in _SKIP_DIR_NAMES for part in path.parts):
            continue
        if path.is_file():
            found.append(path)
    return found


def run_format_census(runtime: RuntimePaths) -> FormatCensus:
    """Count recognised formats and flag unknown ones without rewriting them."""
    census = FormatCensus(counts={name: 0 for name in sorted(SUPPORTED)})
    roots = [
        runtime.projects_dir,
        runtime.data_dir / "config",
        runtime.data_dir / "corpus",
    ]
    for root in roots:
        for path in _iter_json(root):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError):
                continue
            if not isinstance(payload, dict) or "format" not in payload:
                continue
            fmt = payload.get("format")
            version = payload.get("schema_version")
            label = str(path)
            if not isinstance(fmt, str) or fmt not in SUPPORTED:
                census.findings.append(
                    FormatFinding(
                        severity="warning",
                        code="unknown_format",
                        message=f"unregistered format {fmt!r} left untouched",
                        path=label,
                    )
                )
                continue
            census.counts[fmt] = census.counts.get(fmt, 0) + 1
            if version != SUPPORTED[fmt]:
                census.findings.append(
                    FormatFinding(
                        severity="error",
                        code="unsupported_schema_version",
                        message=(
                            f"{fmt} schema_version {version!r} is not "
                            f"{SUPPORTED[fmt]} (file left untouched)"
                        ),
                        path=label,
                    )
                )
    return census
