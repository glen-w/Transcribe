"""Local quality & evaluation loop (collect-only; no telemetry).

Stored at ``data/config/quality-ratings.json`` as ``transcribe.quality-ratings``
v1. Records three local signals:

- ``ocr_sample`` — a sampled page whose OCR was accepted, edited (with a
  character edit distance), or rejected by the reviewer.
- ``cleanup`` — second-pass cleanup output accepted or rejected.
- ``analysis`` — a thumbs up/down usefulness rating for an analysis output.

Nothing leaves the machine. Summaries are counts over the local file only.
See docs/contracts/quality-ratings.md.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any, Literal

from transcribe.domain.models import Project
from transcribe.persistence.atomic import read_json, write_json_atomic
from transcribe.persistence.locks import mutation_lock
from transcribe.persistence.schema import require_format
from transcribe.ports import Clock, IdGenerator, SystemClock, UuidGenerator, to_iso
from transcribe.runtime_paths import RuntimePaths, build_runtime_paths

FORMAT = "transcribe.quality-ratings"
FILENAME = "quality-ratings.json"

QualityKind = Literal["ocr_sample", "cleanup", "analysis"]
Verdict = Literal["accept", "edit", "reject", "up", "down"]

_VERDICTS: dict[str, frozenset[str]] = {
    "ocr_sample": frozenset({"accept", "edit", "reject"}),
    "cleanup": frozenset({"accept", "reject"}),
    "analysis": frozenset({"up", "down"}),
}


def edit_distance(a: str, b: str) -> int:
    """Levenshtein distance (bounded inputs; reviewer samples are page-sized)."""
    if a == b:
        return 0
    if len(a) < len(b):
        a, b = b, a
    previous = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        current = [i]
        for j, cb in enumerate(b, start=1):
            current.append(
                min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + (ca != cb))
            )
        previous = current
    return previous[-1]


def character_error_rate(reference: str, hypothesis: str) -> float | None:
    """CER of hypothesis vs reference; None when reference is empty."""
    if not reference:
        return None
    return edit_distance(reference, hypothesis) / len(reference)


def sample_page_ids(project: Project, sample_size: int) -> list[str]:
    """Deterministic evenly-spaced page sample (stable across runs)."""
    ids = [p.page_id for p in project.pages]
    if sample_size <= 0 or not ids:
        return []
    if sample_size >= len(ids):
        return ids
    step = len(ids) / sample_size
    return [ids[min(len(ids) - 1, int(i * step))] for i in range(sample_size)]


@dataclass(frozen=True)
class QualityRating:
    rating_id: str
    kind: str
    verdict: str
    project_id: str = ""
    page_id: str | None = None
    module_id: str | None = None
    edit_distance: int | None = None
    reference_chars: int | None = None
    notes: str = ""
    created_at: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "rating_id": self.rating_id,
            "kind": self.kind,
            "verdict": self.verdict,
            "project_id": self.project_id,
            "page_id": self.page_id,
            "module_id": self.module_id,
            "edit_distance": self.edit_distance,
            "reference_chars": self.reference_chars,
            "notes": self.notes,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> QualityRating:
        return cls(
            rating_id=str(data["rating_id"]),
            kind=str(data.get("kind") or ""),
            verdict=str(data.get("verdict") or ""),
            project_id=str(data.get("project_id") or ""),
            page_id=data.get("page_id"),
            module_id=data.get("module_id"),
            edit_distance=data.get("edit_distance"),
            reference_chars=data.get("reference_chars"),
            notes=str(data.get("notes") or ""),
            created_at=str(data.get("created_at") or ""),
        )

    @property
    def cer(self) -> float | None:
        if self.edit_distance is None or not self.reference_chars:
            return None
        return self.edit_distance / self.reference_chars


class QualityRatingStore:
    def __init__(
        self,
        runtime: RuntimePaths | None = None,
        *,
        clock: Clock | None = None,
        ids: IdGenerator | None = None,
    ) -> None:
        self.runtime = runtime or build_runtime_paths()
        self.clock = clock or SystemClock()
        self.ids = ids or UuidGenerator()
        self.path = self.runtime.data_dir / "config" / FILENAME
        self.lock_path = self.path.with_suffix(".quality.lock")

    def list(self, *, project_id: str | None = None) -> list[QualityRating]:
        if not self.path.exists():
            return []
        payload = require_format(read_json(self.path), FORMAT)
        rows = payload.get("ratings")
        if not isinstance(rows, list):
            return []
        out = [
            QualityRating.from_dict(r)
            for r in rows
            if isinstance(r, dict) and r.get("rating_id")
        ]
        if project_id is not None:
            out = [r for r in out if r.project_id == project_id]
        return out

    def record(
        self,
        kind: QualityKind,
        verdict: Verdict,
        *,
        project_id: str = "",
        page_id: str | None = None,
        module_id: str | None = None,
        reference: str | None = None,
        hypothesis: str | None = None,
        notes: str = "",
    ) -> QualityRating:
        allowed = _VERDICTS.get(kind)
        if allowed is None or verdict not in allowed:
            raise ValueError(f"verdict {verdict!r} is not valid for kind {kind!r}")
        distance: int | None = None
        ref_chars: int | None = None
        if reference is not None and hypothesis is not None:
            distance = edit_distance(reference, hypothesis)
            ref_chars = len(reference)
        rating = QualityRating(
            rating_id=self.ids.new_id(),
            kind=kind,
            verdict=verdict,
            project_id=project_id,
            page_id=page_id,
            module_id=module_id,
            edit_distance=distance,
            reference_chars=ref_chars,
            notes=str(notes or "")[:500],
            created_at=to_iso(self.clock.now()),
        )
        ratings = [*self.list(), rating]
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "format": FORMAT,
            "schema_version": 1,
            "ratings": [r.as_dict() for r in ratings],
        }
        with mutation_lock(self.lock_path):
            write_json_atomic(self.path, payload)
        return rating

    def record_ocr_sample(
        self,
        *,
        project_id: str,
        page_id: str,
        ocr_text: str,
        reviewed_text: str | None,
    ) -> QualityRating:
        """Verdict derived from the review: untouched=accept, edited=edit, emptied=reject."""
        if reviewed_text is None or reviewed_text == ocr_text:
            verdict: Verdict = "accept"
        elif not reviewed_text.strip():
            verdict = "reject"
        else:
            verdict = "edit"
        return self.record(
            "ocr_sample",
            verdict,
            project_id=project_id,
            page_id=page_id,
            reference=reviewed_text if reviewed_text is not None else ocr_text,
            hypothesis=ocr_text,
        )

    def summary(self, *, project_id: str | None = None) -> dict[str, Any]:
        ratings = self.list(project_id=project_id)
        by_kind_verdict = Counter(f"{r.kind}:{r.verdict}" for r in ratings)
        cers = [r.cer for r in ratings if r.kind == "ocr_sample" and r.cer is not None]
        return {
            "total": len(ratings),
            "by_kind_verdict": dict(sorted(by_kind_verdict.items())),
            "ocr_samples": sum(1 for r in ratings if r.kind == "ocr_sample"),
            "mean_cer": (sum(cers) / len(cers)) if cers else None,
            "cleanup_acceptance": _acceptance(ratings, "cleanup"),
            "analysis_up_ratio": _acceptance(ratings, "analysis", positive="up"),
        }


def _acceptance(ratings: list[QualityRating], kind: str, positive: str = "accept") -> float | None:
    rows = [r for r in ratings if r.kind == kind]
    if not rows:
        return None
    return sum(1 for r in rows if r.verdict == positive) / len(rows)


__all__ = [
    "FORMAT",
    "QualityRating",
    "QualityRatingStore",
    "character_error_rate",
    "edit_distance",
    "sample_page_ids",
]
