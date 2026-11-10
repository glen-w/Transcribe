#!/usr/bin/env python3
"""Collect OCR model stats from transcribe-projects + Nightshift logs.

Stdlib only. Writes JSON under assessments/data/. Does not import Transcribe.
Semantics match Nightshift list_tier.py (normalize :latest, nonempty vision text).

Usage (from repo root)::

    python3 assessments/scripts/collect_model_stats.py
    python3 assessments/scripts/collect_model_stats.py --skip-job-log
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

TARGET_MODELS = ("qwen2.5vl:7b", "glm-ocr", "granite3.2-vision")
MISS_CODES = (
    "empty_output",
    "token_repeat",
    "model_load",
    "timeout",
    "circuit_open",
    "http_error",
    "interrupted",
    "other",
)
# Same windows as transcribe.services.review_signals
_REPEAT_RE = re.compile(r"(.{12,80}?)\1{2,}", re.DOTALL)
_LONG_REPEAT_RE = re.compile(r"(.{12,240}?)\1{2,}", re.DOTALL)

_TRANSCRIBE_NIGHT_HEADER = re.compile(r"^### `transcribe-night`\s*$")
_NIGHT_WHEN = re.compile(
    r"\*\*When:\*\*\s*([^\n]+)",
)
_NIGHT_DETAIL = re.compile(r"\*\*Detail:\*\*\s*(.+)")
_NIGHT_HEADLINE = re.compile(r"\*\*Headline:\*\*\s*(.+)")
_NIGHT_STATUS = re.compile(r"\*\*Status:\*\*\s*(.+)")
_PHASE_LINE = re.compile(r"^\s+- `([^`]+)`:\s*(.+)$")
_JOB_NIGHT_START = re.compile(
    r"^=== .+ nightshift transcribe-night \(window ([^)]+)\)"
)
_JOB_MODELS = re.compile(r"^transcribe-night: models (.+) · rank ")
_JOB_TOKEN_REPEAT = "token repeat"
_JOB_EMPTY = "returned no text"
_JOB_TRUNC_REP = "repeated text"

DEFAULT_PROJECTS = Path.home() / "Documents" / "transcribe-projects"
DEFAULT_NS_LOGS = Path.home() / "Documents" / "nightshift" / "logs"
DEFAULT_JOB_LOG = Path.home() / "Library" / "Logs" / "nightshift-transcribe-night.log"


def normalize_model(name: str) -> str:
    n = (name or "").strip().lower()
    if n.endswith(":latest"):
        n = n[: -len(":latest")]
    return n


def parse_iso(raw: str | None) -> datetime | None:
    if not raw or not isinstance(raw, str):
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def night_shift_key(local_dt: datetime) -> str | None:
    """Map a local timestamp to morning date of the overnight window (23:30–07:30)."""
    h, m = local_dt.hour, local_dt.minute
    d = local_dt.date()
    if h == 23 and m >= 30:
        return (d + timedelta(days=1)).isoformat()
    if h < 7 or (h == 7 and m < 30):
        return d.isoformat()
    return None


def window_kind(local_dt: datetime) -> str:
    if night_shift_key(local_dt):
        return "night"
    h = local_dt.hour
    if 10 <= h < 16:
        return "dayshift"
    return "other"


def attempt_model(attempt: dict) -> str:
    provenance = attempt.get("provenance") or {}
    name = ""
    if isinstance(provenance, dict):
        name = provenance.get("model_name") or ""
    if not name:
        payload = attempt.get("fingerprint_payload") or {}
        if isinstance(payload, dict):
            name = payload.get("model_name") or ""
    return normalize_model(str(name))


def attempt_text(attempt: dict) -> str:
    return (attempt.get("raw_text") or attempt.get("text") or "").strip()


def classify_error_code(code: str | None) -> str:
    raw = str(code or "").strip() or "other"
    if raw in ("empty_output", "token_repeat", "model_load", "timeout", "circuit_open"):
        return raw
    if raw == "http_error":
        return "http_error"
    if raw == "interrupted":
        return "interrupted"
    return "other"


def notebook_max_date(pages: list) -> tuple[int, int, int] | None:
    best: tuple[int, int, int] | None = None
    for page in pages:
        if not isinstance(page, dict):
            continue
        date = page.get("date")
        if not isinstance(date, dict):
            continue
        year = date.get("y")
        if not isinstance(year, int) or year <= 0:
            continue
        month = date.get("m") if isinstance(date.get("m"), int) else 0
        day = date.get("d") if isinstance(date.get("d"), int) else 0
        key = (year, month, day)
        if best is None or key > best:
            best = key
    return best


def tier_for(max_date: tuple[int, int, int] | None) -> str:
    if max_date is None:
        return "rest"
    year = max_date[0]
    if year >= 2025:
        return "recent"
    if year >= 2023:
        return "from_2023"
    return "rest"


def elapsed_seconds(attempt: dict) -> float | None:
    start = parse_iso(attempt.get("started_at"))
    end = parse_iso(attempt.get("completed_at"))
    if start and end:
        delta = (end - start).total_seconds()
        if delta >= 0:
            return delta
    meta = attempt.get("provider_metadata") or {}
    total_ns = meta.get("total_duration")
    if isinstance(total_ns, (int, float)) and total_ns > 0:
        return float(total_ns) / 1e9
    return None


def median_or_none(values: list[float]) -> float | None:
    if not values:
        return None
    return round(float(statistics.median(values)), 2)


def _new_model_bucket() -> dict[str, Any]:
    return {
        "attempts": 0,
        "succeeded": 0,
        "failed": 0,
        "interrupted": 0,
        "running": 0,
        "other_status": 0,
        "error_codes": {k: 0 for k in MISS_CODES},
        "truncated_successes": 0,
        "truncated_repetition_successes": 0,
        "eval_counts": [],
        "elapsed_s": [],
        "example_failures": [],
    }


def collect_corpus(
    projects_dir: Path,
    target_models: tuple[str, ...],
) -> tuple[dict[str, Any], dict[str, Any]]:
    targets = {normalize_model(m) for m in target_models}
    notebooks: list[dict[str, Any]] = []
    by_model: dict[str, dict[str, Any]] = {}
    by_tier = {
        t: {
            "notebooks": 0,
            "pages": 0,
            "pages_any_success": 0,
            "target_runs_done": 0,
            "target_runs_total": 0,
        }
        for t in ("recent", "from_2023", "rest")
    }
    pages_total = 0
    pages_any_success = 0
    pages_with_composite = 0
    pages_edited = 0
    target_runs_done = 0
    night_successes: Counter[str] = Counter()
    dayshift_successes: Counter[str] = Counter()

    for child in sorted(projects_dir.iterdir()):
        if not child.is_dir():
            continue
        project_path = child / "project.json"
        if not project_path.is_file():
            continue
        try:
            project = json.loads(project_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        page_list = project.get("pages") or []
        if not page_list:
            continue
        title = (project.get("title") or child.name).strip() or child.name
        max_date = notebook_max_date(page_list)
        tier = tier_for(max_date)
        results_dir = child / "results"
        n_pages = 0
        n_any = 0
        n_composite = 0
        n_edited = 0
        per_model_done = {m: 0 for m in targets}
        miss_active: Counter[str] = Counter()
        for page in page_list:
            if not isinstance(page, dict):
                continue
            page_id = page.get("page_id")
            if not page_id:
                continue
            n_pages += 1
            result_path = results_dir / f"{page_id}.json"
            result: dict[str, Any] = {}
            if result_path.is_file():
                try:
                    result = json.loads(result_path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    result = {}
            attempts = result.get("attempts") or []
            succeeded_models: set[str] = set()
            has_composite = False
            latest_fail_code = ""
            latest_fail_at = ""
            for attempt in attempts:
                if not isinstance(attempt, dict):
                    continue
                kind = attempt.get("attempt_kind") or "vision"
                if kind == "composite":
                    has_composite = True
                    continue
                if kind != "vision":
                    continue
                model = attempt_model(attempt) or "(unknown)"
                bucket = by_model.setdefault(model, _new_model_bucket())
                bucket["attempts"] += 1
                status = attempt.get("status") or "other"
                if status == "succeeded":
                    bucket["succeeded"] += 1
                elif status == "failed":
                    bucket["failed"] += 1
                elif status == "interrupted":
                    bucket["interrupted"] += 1
                elif status == "running":
                    bucket["running"] += 1
                else:
                    bucket["other_status"] += 1

                meta = attempt.get("provider_metadata") or {}
                eval_count = meta.get("eval_count")
                if isinstance(eval_count, (int, float)):
                    bucket["eval_counts"].append(float(eval_count))
                elapsed = elapsed_seconds(attempt)
                if elapsed is not None:
                    bucket["elapsed_s"].append(elapsed)
                truncated = bool(meta.get("truncated"))
                raw = attempt_text(attempt)
                if status == "succeeded" and truncated:
                    bucket["truncated_successes"] += 1
                    # Bound the scan: looping tails on dense pages can be huge.
                    sample = raw[-8000:] if len(raw) > 8000 else raw
                    if sample and (
                        _REPEAT_RE.search(sample) or _LONG_REPEAT_RE.search(sample)
                    ):
                        bucket["truncated_repetition_successes"] += 1

                if status == "succeeded" and raw:
                    succeeded_models.add(model)
                    completed = parse_iso(attempt.get("completed_at"))
                    if completed is not None:
                        local = completed.astimezone()
                        kind_w = window_kind(local)
                        if kind_w == "night":
                            night_successes[model] += 1
                        elif kind_w == "dayshift":
                            dayshift_successes[model] += 1
                elif status == "failed":
                    err = attempt.get("error") or {}
                    code = classify_error_code(
                        err.get("code") if isinstance(err, dict) else None
                    )
                    bucket["error_codes"][code] = bucket["error_codes"].get(code, 0) + 1
                    completed_raw = str(attempt.get("completed_at") or "")
                    if completed_raw >= latest_fail_at:
                        latest_fail_at = completed_raw
                        latest_fail_code = code
                    examples = bucket["example_failures"]
                    if len(examples) < 5:
                        examples.append(
                            {
                                "notebook": child.name,
                                "page_id": page_id,
                                "attempt_id": attempt.get("attempt_id"),
                                "code": code,
                                "message": (err.get("message") if isinstance(err, dict) else "")[
                                    :160
                                ],
                                "completed_at": attempt.get("completed_at"),
                            }
                        )

            if succeeded_models:
                n_any += 1
            if has_composite:
                n_composite += 1
            if (result.get("edited_text") or "").strip():
                n_edited += 1
            if latest_fail_code and not succeeded_models:
                miss_active[latest_fail_code] += 1
            for model in targets:
                if model in succeeded_models:
                    per_model_done[model] += 1

        pages_total += n_pages
        pages_any_success += n_any
        pages_with_composite += n_composite
        pages_edited += n_edited
        runs_done = sum(per_model_done.values())
        target_runs_done += runs_done
        runs_total = n_pages * len(targets)
        by_tier[tier]["notebooks"] += 1
        by_tier[tier]["pages"] += n_pages
        by_tier[tier]["pages_any_success"] += n_any
        by_tier[tier]["target_runs_done"] += runs_done
        by_tier[tier]["target_runs_total"] += runs_total
        pct = (runs_done / runs_total * 100.0) if runs_total else 0.0
        print(f"  {child.name}: {n_pages} pages {tier}", file=sys.stderr)
        notebooks.append(
            {
                "dir": child.name,
                "title": title,
                "tier": tier,
                "max_date": (
                    f"{max_date[0]:04d}-{max_date[1]:02d}-{max_date[2]:02d}"
                    if max_date
                    else None
                ),
                "pages": n_pages,
                "pages_any_success": n_any,
                "pages_with_composite": n_composite,
                "pages_edited": n_edited,
                "target_runs_done": runs_done,
                "target_runs_total": runs_total,
                "completion_pct": round(pct, 1),
                "by_model_done": per_model_done,
                "active_miss_codes": dict(miss_active),
            }
        )

    for bucket in by_model.values():
        bucket["median_eval_count"] = median_or_none(bucket.pop("eval_counts"))
        bucket["median_elapsed_s"] = median_or_none(bucket.pop("elapsed_s"))
        succ = bucket["succeeded"]
        fail = bucket["failed"]
        finished = succ + fail
        bucket["success_rate_finished"] = (
            round(succ / finished, 4) if finished else None
        )

    notebooks.sort(key=lambda row: (-row["pages"], row["dir"]))
    at_pct = {"100": 0, "95": 0, "90": 0, "80": 0}
    for row in notebooks:
        for floor in (100, 95, 90, 80):
            if row["completion_pct"] >= floor - 1e-9:
                at_pct[str(floor)] += 1

    target_runs_total = pages_total * len(targets)
    corpus = {
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "projects_dir": str(projects_dir),
        "target_models": list(target_models),
        "notebooks": len(notebooks),
        "pages": pages_total,
        "pages_any_succeeded_vision": pages_any_success,
        "pages_with_composite": pages_with_composite,
        "pages_with_edited_text": pages_edited,
        "target_runs_done": target_runs_done,
        "target_runs_total": target_runs_total,
        "target_runs_remaining": max(0, target_runs_total - target_runs_done),
        "target_completion_pct": round(
            (target_runs_done / target_runs_total * 100.0) if target_runs_total else 0.0,
            2,
        ),
        "notebooks_at_pct": at_pct,
        "by_tier": by_tier,
        "by_model_target_done": {
            m: sum(nb["by_model_done"].get(m, 0) for nb in notebooks) for m in targets
        },
        "night_window_successes_by_model": dict(night_successes),
        "dayshift_window_successes_by_model": dict(dayshift_successes),
        "notebooks_detail": notebooks,
    }
    error_report = {
        "collected_at": corpus["collected_at"],
        "notes": (
            "Per-attempt counts (not unique pages). Latest-fail miss codes on "
            "pages with no succeeded vision attempt are in notebooks_detail.active_miss_codes."
        ),
        "by_model": by_model,
    }
    return corpus, error_report


def parse_transcribe_night_md(path: Path) -> dict[str, Any] | None:
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    start = None
    for i, line in enumerate(lines):
        if _TRANSCRIBE_NIGHT_HEADER.match(line):
            start = i
            break
    if start is None:
        return None
    block: list[str] = []
    for line in lines[start + 1 :]:
        if line.startswith("### "):
            break
        block.append(line)
    blob = "\n".join(block)
    phases: dict[str, str] = {}
    for line in block:
        m = _PHASE_LINE.match(line)
        if m:
            phases[m.group(1)] = m.group(2).strip()
    when_m = _NIGHT_WHEN.search(blob)
    detail_m = _NIGHT_DETAIL.search(blob)
    headline_m = _NIGHT_HEADLINE.search(blob)
    status_m = _NIGHT_STATUS.search(blob)
    return {
        "night_date": path.stem,
        "status": (status_m.group(1).strip() if status_m else ""),
        "when": (when_m.group(1).strip() if when_m else ""),
        "headline": (headline_m.group(1).strip() if headline_m else ""),
        "detail": (detail_m.group(1).strip() if detail_m else ""),
        "phases": phases,
        "recent": phases.get("recent", ""),
        "from_2023": phases.get("from_2023", ""),
        "rest": phases.get("rest", ""),
        "ingest": phases.get("ingest", ""),
        "models": phases.get("models", ""),
        "outcome": phases.get("outcome", ""),
    }


def collect_nightshift_md(logs_dir: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not logs_dir.is_dir():
        return rows
    for path in sorted(logs_dir.glob("20*.md")):
        row = parse_transcribe_night_md(path)
        if row:
            rows.append(row)
    return rows


def collect_snapshots(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.is_file():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def snapshot_deltas(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ordered = sorted(rows, key=lambda r: str(r.get("night_date") or ""))
    out: list[dict[str, Any]] = []
    for prev, cur in zip(ordered, ordered[1:]):
        try:
            delta = int(cur["runs_done"]) - int(prev["runs_done"])
        except (KeyError, TypeError, ValueError):
            continue
        out.append(
            {
                "from": prev.get("night_date"),
                "to": cur.get("night_date"),
                "delta_runs_done": delta,
            }
        )
    return out


def collect_job_log(path: Path) -> dict[str, Any]:
    empty: dict[str, Any] = {
        "path": str(path),
        "present": False,
        "nights_started": 0,
        "models_seen": [],
        "page_outcomes": {"succeeded": 0, "failed": 0, "skipped": 0},
        "fail_reasons": {},
        "last_night_start": None,
        "last_night_models": None,
        "last_night_outcomes": {},
        "last_night_fail_reasons": {},
    }
    if not path.is_file():
        return empty
    nights_started = 0
    models_seen: Counter[str] = Counter()
    outcomes: Counter[str] = Counter()
    fail_reasons: Counter[str] = Counter()
    last_start = None
    last_models = None
    last_outcomes: Counter[str] = Counter()
    last_fails: Counter[str] = Counter()
    current_outcomes: Counter[str] = Counter()
    current_fails: Counter[str] = Counter()
    current_models = ""

    def classify_fail(msg: str) -> str:
        lower = msg.lower()
        if _JOB_TOKEN_REPEAT in lower:
            return "token_repeat"
        if _JOB_EMPTY in lower:
            return "empty_output"
        if _JOB_TRUNC_REP in lower:
            return "truncated_repetition"
        if "timeout" in lower:
            return "timeout"
        if "model load" in lower or "unknown model architecture" in lower:
            return "model_load"
        return "other"

    with path.open(encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.rstrip("\n")
            m_start = _JOB_NIGHT_START.search(line)
            if m_start or line.startswith("=== ") and "nightshift transcribe-night" in line:
                if current_outcomes:
                    last_outcomes = current_outcomes
                    last_fails = current_fails
                nights_started += 1
                last_start = line
                current_outcomes = Counter()
                current_fails = Counter()
                continue
            m_mod = _JOB_MODELS.match(line)
            if m_mod:
                current_models = m_mod.group(1).strip()
                last_models = current_models
                models_seen[current_models] += 1
                continue
            if ": succeeded (" in line or ": failed (" in line or ": skipped (" in line:
                # Take the last occurrence of outcome on the line
                for token in ("succeeded", "failed", "skipped"):
                    needle = f": {token} ("
                    if needle in line:
                        outcomes[token] += 1
                        current_outcomes[token] += 1
                        if token == "failed":
                            msg = line.split(": failed (", 1)[-1]
                            reason = classify_fail(msg)
                            fail_reasons[reason] += 1
                            current_fails[reason] += 1
                        break
    if current_outcomes:
        last_outcomes = current_outcomes
        last_fails = current_fails
    empty.update(
        {
            "present": True,
            "bytes": path.stat().st_size,
            "nights_started": nights_started,
            "models_seen": dict(models_seen),
            "page_outcomes": dict(outcomes),
            "fail_reasons": dict(fail_reasons),
            "last_night_start": last_start,
            "last_night_models": last_models,
            "last_night_outcomes": dict(last_outcomes),
            "last_night_fail_reasons": dict(last_fails),
        }
    )
    return empty


def summarize_nights(nights: list[dict[str, Any]]) -> dict[str, Any]:
    recent_starved = 0
    rest_ran = 0
    from_2023_ran = 0
    ingest_skipped = 0
    stopped_window = 0
    for row in nights:
        recent = (row.get("recent") or "").lower()
        from_2023 = (row.get("from_2023") or "").lower()
        rest = (row.get("rest") or "").lower()
        ingest = (row.get("ingest") or "").lower()
        if "skipped" in from_2023 and "interrupted" in from_2023:
            recent_starved += 1
        if "skipped" not in rest and rest and rest not in {"not run", ""}:
            rest_ran += 1
        if "skipped" not in from_2023 and from_2023 and from_2023 not in {"not run", ""}:
            from_2023_ran += 1
        if "skip_ingest" in ingest or ingest.startswith("skipped"):
            ingest_skipped += 1
        if "stopped at" in recent or "07:30" in recent:
            stopped_window += 1
    return {
        "nights_with_transcribe_block": len(nights),
        "nights_from_2023_and_rest_skipped_interrupted": recent_starved,
        "nights_from_2023_ran": from_2023_ran,
        "nights_rest_ran": rest_ran,
        "nights_ingest_skipped": ingest_skipped,
        "nights_recent_stopped_at_window": stopped_window,
    }


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {path}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    here = Path(__file__).resolve()
    assess_root = here.parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--projects-dir", type=Path, default=DEFAULT_PROJECTS)
    parser.add_argument("--nightshift-logs", type=Path, default=DEFAULT_NS_LOGS)
    parser.add_argument("--job-log", type=Path, default=DEFAULT_JOB_LOG)
    parser.add_argument("--out-dir", type=Path, default=assess_root / "data")
    parser.add_argument("--skip-job-log", action="store_true")
    parser.add_argument(
        "--models",
        default=",".join(TARGET_MODELS),
        help="Comma-separated Nightshift target vision tags",
    )
    args = parser.parse_args(argv)
    models = tuple(
        normalize_model(p) for p in args.models.split(",") if p.strip()
    )
    corpus, errors = collect_corpus(args.projects_dir, models)
    write_json(args.out_dir / "corpus-stats.json", corpus)
    write_json(args.out_dir / "error-by-model.json", errors)

    nights = collect_nightshift_md(args.nightshift_logs)
    snaps = collect_snapshots(args.nightshift_logs / "transcribe-page-model-snapshots.jsonl")
    job = (
        {"skipped": True}
        if args.skip_job_log
        else collect_job_log(args.job_log)
    )
    remaining = corpus["target_runs_remaining"]
    # Forecast from night-window successes on target models, last 14 calendar nights
    # counted from attempt completed_at (already aggregated in corpus as night_window).
    # Prefer snapshot deltas; else remaining / median night successes if we re-count.
    deltas = snapshot_deltas(snaps)
    pos_deltas = [d["delta_runs_done"] for d in deltas if d["delta_runs_done"] > 0]
    rate = median_or_none([float(x) for x in pos_deltas]) if pos_deltas else None
    forecast_source = "snapshots" if rate else None
    if rate is None:
        # Fall back: job-log last-night succeeded + corpus night successes / nights
        n_nights = max(1, summarize_nights(nights)["nights_with_transcribe_block"])
        night_succ = sum(corpus.get("night_window_successes_by_model", {}).values())
        # Those successes are all-time in the night window, not last-N; still a floor.
        # Better: remaining / ~65 from latest nightshift canvas if snapshots empty.
        if isinstance(job, dict) and job.get("last_night_outcomes"):
            last_ok = int(job["last_night_outcomes"].get("succeeded") or 0)
            rate = float(last_ok) if last_ok > 0 else None
            forecast_source = "last_night_job_log" if rate else None
        if rate is None and night_succ > 0:
            rate = round(night_succ / n_nights, 1)
            forecast_source = "all_time_night_successes / nights_with_block"
    shifts = None
    if rate and rate > 0:
        shifts = int((remaining + rate - 1) // rate)
    throughput = {
        "collected_at": corpus["collected_at"],
        "snapshots": snaps,
        "snapshot_deltas": deltas,
        "forecast": {
            "runs_remaining": remaining,
            "runs_per_shift": rate,
            "shifts_until_completion_status_quo": shifts,
            "source": forecast_source,
        },
        "nights_summary": summarize_nights(nights),
        "nights": nights,
        "job_log": job,
    }
    write_json(args.out_dir / "nightshift-throughput.json", throughput)
    print(
        f"pages={corpus['pages']} notebooks={corpus['notebooks']} "
        f"target {corpus['target_runs_done']}/{corpus['target_runs_total']} "
        f"({corpus['target_completion_pct']}%) remaining={remaining}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
