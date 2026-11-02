"""Per-notebook job timeline (Diagnostics read-model).

Aggregates durable run records — OCR job records, analysis run records, and
the latest detection attempt per detector — into one chronological list.
Every record is validated against the schema registry on read; malformed
records surface as ``valid=False`` entries instead of being silently
trusted or crashing Diagnostics. The record's own id serves as its
correlation id (OCR job_id / analysis run_id / detection attempt id).
This is a read-model only: it writes nothing and invents no status values.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from transcribe.paths import ProjectPaths
from transcribe.persistence.atomic import read_json
from transcribe.persistence.schema import SchemaError, require_format

MAX_ENTRIES = 100


@dataclass(frozen=True)
class TimelineEntry:
    correlation_id: str
    kind: str  # "ocr" | "analysis" | "detection"
    status: str
    started_at: str | None = None
    ended_at: str | None = None
    total: int = 0
    completed: int = 0
    failed: int = 0
    skipped: int = 0
    message: str = ""
    detail: str = ""  # model / modules / detector label
    valid: bool = True
    error: str = ""
    outcome: str = ""


def _int(payload: dict[str, Any], key: str) -> int:
    try:
        return int(payload.get(key) or 0)
    except (TypeError, ValueError):
        return 0


def _ocr_entries(paths: ProjectPaths) -> list[TimelineEntry]:
    entries: list[TimelineEntry] = []
    jobs_dir = paths.jobs_dir
    if not jobs_dir.exists():
        return entries
    for path in sorted(jobs_dir.glob("*.json")):
        try:
            payload = require_format(read_json(path), "transcribe.job-record")
        except (SchemaError, OSError, ValueError, TypeError) as exc:
            entries.append(
                TimelineEntry(
                    correlation_id=path.stem,
                    kind="ocr",
                    status="unknown",
                    valid=False,
                    error=str(exc)[:200],
                )
            )
            continue
        from transcribe.services.job_outcome import outcome_from_record

        outcome = outcome_from_record(payload)
        entries.append(
            TimelineEntry(
                correlation_id=str(payload.get("job_id") or path.stem),
                kind="ocr",
                status=str(payload.get("status") or "unknown"),
                started_at=payload.get("started_at"),
                ended_at=payload.get("ended_at"),
                total=_int(payload, "total"),
                completed=_int(payload, "completed"),
                failed=_int(payload, "failed"),
                skipped=_int(payload, "skipped"),
                message=str(payload.get("message") or ""),
                detail=str(payload.get("model_name") or ""),
                outcome=outcome.outcome,
            )
        )
    return entries


def _analysis_entries(paths: ProjectPaths) -> list[TimelineEntry]:
    entries: list[TimelineEntry] = []
    runs_dir = paths.analysis_runs_dir
    if not runs_dir.exists():
        return entries
    for path in sorted(runs_dir.glob("*.json")):
        try:
            payload = read_json(path)
            if not isinstance(payload, dict):
                raise SchemaError("analysis run record is not an object")
            fmt = payload.get("format")
            if fmt:
                require_format(payload, str(fmt))
        except (SchemaError, OSError, ValueError, TypeError) as exc:
            entries.append(
                TimelineEntry(
                    correlation_id=path.stem,
                    kind="analysis",
                    status="unknown",
                    valid=False,
                    error=str(exc)[:200],
                )
            )
            continue
        modules = payload.get("module_ids") or []
        entries.append(
            TimelineEntry(
                correlation_id=str(payload.get("run_id") or path.stem),
                kind="analysis",
                status=str(payload.get("status") or "unknown"),
                started_at=payload.get("started_at"),
                ended_at=payload.get("ended_at"),
                total=len(modules) if isinstance(modules, list) else 0,
                completed=_int(payload, "completed"),
                failed=_int(payload, "failed"),
                skipped=_int(payload, "skipped"),
                message=str(payload.get("message") or ""),
                detail=", ".join(str(m) for m in modules) if isinstance(modules, list) else "",
            )
        )
    return entries


def _detection_entries(paths: ProjectPaths) -> list[TimelineEntry]:
    entries: list[TimelineEntry] = []
    detection_dir = paths.detection_dir
    if not detection_dir.exists():
        return entries
    for detector_dir in sorted(p for p in detection_dir.iterdir() if p.is_dir()):
        attempts = detector_dir / "attempts"
        if not attempts.exists():
            continue
        files = sorted(attempts.glob("*.json"))
        if not files:
            continue
        path = files[-1]
        try:
            payload = read_json(path)
            if not isinstance(payload, dict):
                raise SchemaError("detection attempt is not an object")
        except (SchemaError, OSError, ValueError, TypeError) as exc:
            entries.append(
                TimelineEntry(
                    correlation_id=path.stem,
                    kind="detection",
                    status="unknown",
                    detail=detector_dir.name,
                    valid=False,
                    error=str(exc)[:200],
                )
            )
            continue
        entries.append(
            TimelineEntry(
                correlation_id=str(payload.get("attempt_id") or path.stem),
                kind="detection",
                status=str(
                    payload.get("attempt_state") or payload.get("outcome") or "unknown"
                ),
                started_at=payload.get("started_at") or payload.get("created_at"),
                ended_at=payload.get("ended_at") or payload.get("updated_at"),
                message=str(payload.get("outcome") or ""),
                detail=detector_dir.name,
            )
        )
    return entries


def build_job_timeline(paths: ProjectPaths, *, limit: int = MAX_ENTRIES) -> list[TimelineEntry]:
    """Newest-first timeline across OCR / analysis / detection records."""
    entries = [
        *_ocr_entries(paths),
        *_analysis_entries(paths),
        *_detection_entries(paths),
    ]
    entries.sort(key=lambda e: (e.started_at or e.ended_at or "", e.correlation_id), reverse=True)
    return entries[: max(1, limit)]


__all__ = ["TimelineEntry", "build_job_timeline"]
