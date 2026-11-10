#!/usr/bin/env python3
"""Compare vision OCR attempts on one Transcribe notebook.

Stdlib walk of results/*.json. Optional CER vs qwen2.5vl:7b and edited_text
uses transcribe.services.quality when PYTHONPATH includes src/.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

COMPARE_MODELS = (
    "qwen2.5vl:7b",
    "granite3.2-vision",
    "deepseek-ocr",
    "paddleocr-vl-1.6",
    "paddlepaddle/paddleocr-vl-1.6",
)


def normalize_model(name: str) -> str:
    n = (name or "").strip().lower()
    if n.endswith(":latest"):
        n = n[: -len(":latest")]
    if n.startswith("paddlepaddle/"):
        n = n.split("/", 1)[1]
    return n


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


def attempt_provider(attempt: dict) -> str:
    payload = attempt.get("fingerprint_payload") or {}
    if isinstance(payload, dict) and payload.get("provider"):
        return str(payload["provider"])
    return ""


def attempt_text(attempt: dict) -> str:
    return (attempt.get("raw_text") or attempt.get("text") or "").strip()


def attempt_seconds(attempt: dict) -> float | None:
    meta = attempt.get("provider_metadata") or {}
    if isinstance(meta, dict):
        for key in ("total_duration", "elapsed_s", "eval_duration"):
            raw = meta.get(key)
            if isinstance(raw, (int, float)) and raw > 0:
                if key.endswith("duration") and raw > 1000:
                    return float(raw) / 1e9
                return float(raw)
    started = attempt.get("started_at")
    completed = attempt.get("completed_at")
    if isinstance(started, str) and isinstance(completed, str):
        try:
            t0 = datetime.fromisoformat(started.replace("Z", "+00:00"))
            t1 = datetime.fromisoformat(completed.replace("Z", "+00:00"))
            return max(0.0, (t1 - t0).total_seconds())
        except ValueError:
            return None
    return None


def latest_succeeded(attempts: list[dict], model: str) -> dict | None:
    want = normalize_model(model)
    latest = None
    for attempt in attempts:
        if not isinstance(attempt, dict):
            continue
        if (attempt.get("attempt_kind") or "vision") != "vision":
            continue
        if attempt.get("status") != "succeeded":
            continue
        if attempt_model(attempt) != want and not (
            want.startswith("paddle") and "paddle" in attempt_model(attempt)
        ):
            continue
        latest = attempt
    return latest


def _cer(a: str, b: str) -> float | None:
    try:
        from transcribe.services.quality import character_error_rate

        return character_error_rate(a, b)
    except Exception:  # noqa: BLE001
        return None


def load_pages(notebook: Path) -> list[dict[str, Any]]:
    manifest = json.loads((notebook / "project.json").read_text(encoding="utf-8"))
    pages = manifest.get("pages") or []
    rows: list[dict[str, Any]] = []
    results_dir = notebook / "results"
    for page in pages:
        if not isinstance(page, dict) or not page.get("page_id"):
            continue
        page_id = str(page["page_id"])
        result_path = results_dir / f"{page_id}.json"
        result: dict[str, Any] = {}
        if result_path.is_file():
            try:
                result = json.loads(result_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                result = {}
        rows.append(
            {
                "page_id": page_id,
                "index": page.get("page_index"),
                "edited_text": result.get("edited_text"),
                "attempts": result.get("attempts") or [],
            }
        )
    return rows


def summarize(notebook: Path) -> dict[str, Any]:
    pages = load_pages(notebook)
    by_model: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "attempts": 0,
            "succeeded": 0,
            "failed": 0,
            "interrupted": 0,
            "empty_success": 0,
            "seconds": [],
            "paths": defaultdict(int),
            "errors": defaultdict(int),
        }
    )
    paddle_keys = ("paddleocr-vl-1.6", "paddlepaddle/paddleocr-vl-1.6")
    pairwise: list[dict[str, Any]] = []
    previews: list[dict[str, Any]] = []

    for row in pages:
        attempts = [a for a in row["attempts"] if isinstance(a, dict)]
        latest_by_model: dict[str, dict] = {}
        for attempt in attempts:
            kind = attempt.get("attempt_kind") or "vision"
            if kind != "vision":
                continue
            model = attempt_model(attempt) or "(unknown)"
            bucket = by_model[model]
            bucket["attempts"] += 1
            status = attempt.get("status") or "other"
            if status == "succeeded":
                bucket["succeeded"] += 1
                if not attempt_text(attempt):
                    bucket["empty_success"] += 1
                latest_by_model[model] = attempt
            elif status == "failed":
                bucket["failed"] += 1
                err = (attempt.get("error") or {}) if isinstance(attempt.get("error"), dict) else {}
                code = str(err.get("code") or "failed")
                bucket["errors"][code] += 1
            elif status == "interrupted":
                bucket["interrupted"] += 1
            sec = attempt_seconds(attempt)
            if sec is not None:
                bucket["seconds"].append(sec)
            meta = attempt.get("provider_metadata") or {}
            if isinstance(meta, dict) and meta.get("path"):
                bucket["paths"][str(meta["path"])] += 1

        qwen = latest_by_model.get("qwen2.5vl:7b")
        paddle = None
        for key in latest_by_model:
            if "paddle" in key:
                paddle = latest_by_model[key]
                break
        if qwen and paddle:
            q_text = attempt_text(qwen)
            p_text = attempt_text(paddle)
            pair = {
                "page_id": row["page_id"],
                "cer_vs_7b": _cer(q_text, p_text),
                "qwen_len": len(q_text),
                "paddle_len": len(p_text),
            }
            edited = row.get("edited_text")
            if isinstance(edited, str) and edited.strip():
                pair["cer_vs_edited"] = _cer(edited.strip(), p_text)
            pairwise.append(pair)

    # Previews: mix of dense (long 7b) and short pages that have paddle.
    scored: list[tuple[int, dict]] = []
    for row in pages:
        qwen = latest_succeeded(row["attempts"], "qwen2.5vl:7b")
        paddle = None
        for attempt in row["attempts"]:
            if not isinstance(attempt, dict):
                continue
            if (attempt.get("attempt_kind") or "vision") != "vision":
                continue
            if attempt.get("status") != "succeeded":
                continue
            if "paddle" in attempt_model(attempt):
                paddle = attempt
        if not qwen:
            continue
        scored.append((len(attempt_text(qwen)), row | {"_qwen": qwen, "_paddle": paddle}))
    scored.sort(key=lambda x: -x[0])
    picks = scored[:5] + list(reversed(scored[-5:])) if len(scored) > 10 else scored
    seen: set[str] = set()
    for _, row in picks:
        pid = row["page_id"]
        if pid in seen:
            continue
        seen.add(pid)
        qwen = row["_qwen"]
        paddle = row["_paddle"]
        granite = latest_succeeded(row["attempts"], "granite3.2-vision")
        deepseek = latest_succeeded(row["attempts"], "deepseek-ocr")
        previews.append(
            {
                "page_id": pid,
                "qwen2.5vl:7b": (attempt_text(qwen)[:400] if qwen else ""),
                "granite3.2-vision": (attempt_text(granite)[:400] if granite else ""),
                "deepseek-ocr": (attempt_text(deepseek)[:400] if deepseek else ""),
                "paddle": (attempt_text(paddle)[:400] if paddle else ""),
            }
        )
        if len(previews) >= 10:
            break

    models_out = {}
    for name, bucket in sorted(by_model.items()):
        secs = bucket["seconds"]
        models_out[name] = {
            "attempts": bucket["attempts"],
            "succeeded": bucket["succeeded"],
            "failed": bucket["failed"],
            "interrupted": bucket["interrupted"],
            "empty_success": bucket["empty_success"],
            "median_s": round(statistics.median(secs), 2) if secs else None,
            "paths": dict(bucket["paths"]),
            "errors": dict(bucket["errors"]),
        }
    cers = [p["cer_vs_7b"] for p in pairwise if isinstance(p.get("cer_vs_7b"), float)]
    paddle_present = any("paddle" in m for m in models_out)
    return {
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "notebook": str(notebook),
        "title": notebook.name,
        "pages": len(pages),
        "paddle_present": paddle_present,
        "models": models_out,
        "pairwise_vs_7b_count": len(pairwise),
        "median_cer_vs_7b": round(statistics.median(cers), 4) if cers else None,
        "pairwise_sample": pairwise[:20],
        "previews": previews,
    }


def render_markdown(data: dict[str, Any]) -> str:
    models = data.get("models") or {}
    lines = [
        f"# PaddleOCR-VL MLX vs existing passes — {data.get('title')}",
        "",
        f"Collected `{data.get('collected_at')}`. Notebook `{data.get('notebook')}` "
        f"({data.get('pages')} pages).",
        "",
        "Native Apple Silicon path: Nightshift `paddle-probe` sidecar "
        "(`PaddleOCRVL` + resident `mlx_vlm.server`), Transcribe `--provider paddleocr` "
        "on branch `feat/paddleocr-mlx`. **Not** overnight `MODEL_B`.",
        "",
    ]
    if not data.get("paddle_present"):
        lines += [
            "**Paddle attempts are not on disk yet.** Re-run after "
            "`jobs/paddle-probe/run.sh` finishes.",
            "",
        ]
    lines += [
        "## Per-model attempts",
        "",
        "| Model | Attempts | Succeeded | Failed | Interrupted | Median s | Paths |",
        "|-------|---------:|----------:|-------:|------------:|---------:|-------|",
    ]
    for name, row in models.items():
        if name not in COMPARE_MODELS and "paddle" not in name and name not in (
            "qwen2.5vl:7b",
            "granite3.2-vision",
            "deepseek-ocr",
        ):
            continue
        paths = row.get("paths") or {}
        path_s = ",".join(f"{k}:{v}" for k, v in paths.items()) or "—"
        lines.append(
            f"| `{name}` | {row.get('attempts')} | {row.get('succeeded')} | "
            f"{row.get('failed')} | {row.get('interrupted')} | {row.get('median_s')!s} | {path_s} |"
        )
    lines += [
        "",
        f"Pairwise pages with both 7b and paddle: **{data.get('pairwise_vs_7b_count')}**. "
        f"Median CER vs 7b: **{data.get('median_cer_vs_7b')}**.",
        "",
        "CER is vs `qwen2.5vl:7b` (not ground truth) except where `edited_text` exists.",
        "",
        "## Side-by-side previews",
        "",
    ]
    for prev in data.get("previews") or []:
        lines.append(f"### `{prev.get('page_id')}`")
        for key in ("qwen2.5vl:7b", "granite3.2-vision", "deepseek-ocr", "paddle"):
            text = (prev.get(key) or "").replace("\n", " ")
            lines.append(f"- **{key}:** {text[:280] or '—'}")
        lines.append("")
    lines += [
        "## Decision",
        "",
        "Do **not** promote paddle to Nightshift `MODEL_B` from this sitting. "
        "Read success rate, CER vs 7b, path mix (`pipeline` vs `mlx_chat`), and M5 load notes "
        "in the job log before scheduling it overnight.",
        "",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--notebook", type=Path, required=True)
    parser.add_argument("--json", type=Path, required=True)
    parser.add_argument("--markdown", type=Path, default=None)
    args = parser.parse_args()
    if not (args.notebook / "project.json").is_file():
        print(f"error: not a notebook: {args.notebook}", file=sys.stderr)
        return 1
    data = summarize(args.notebook)
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {args.json}")
    if args.markdown:
        args.markdown.write_text(render_markdown(data), encoding="utf-8")
        print(f"wrote {args.markdown}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
