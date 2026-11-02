"""Per-notebook bookmarks and marginal notes.

Sidecar ``reading-marks.json`` (``transcribe.reading-marks`` v1). Absence is
valid and means no marks. Notes never enter ``effective_text()``, analysis,
detection, or fine-tune export. Search stores only a derived bookmark flag.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from transcribe.paths import ProjectPaths
from transcribe.persistence.atomic import read_json, write_json_atomic
from transcribe.persistence.locks import mutation_lock
from transcribe.persistence.schema import SchemaError, require_format

FORMAT = "transcribe.reading-marks"
FILENAME = "reading-marks.json"
NOTE_MAX = 500


@dataclass(frozen=True)
class PageMark:
    bookmarked: bool = False
    note: str = ""

    def as_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        if self.bookmarked:
            payload["bookmarked"] = True
        if self.note:
            payload["note"] = self.note
        return payload


class ReadingMarksStore:
    def __init__(self, paths: ProjectPaths) -> None:
        self.paths = paths
        self.path = paths.root / FILENAME
        self.lock_path = paths.root / ".reading-marks.lock"

    def load(self) -> dict[str, PageMark]:
        if not self.path.is_file():
            return {}
        try:
            payload = require_format(read_json(self.path), FORMAT)
        except (SchemaError, OSError, ValueError, TypeError):
            # Fail closed for the caller that writes; readers treat a bad
            # sidecar as no marks rather than mixing it into transcription.
            return {}
        raw = payload.get("pages")
        if not isinstance(raw, dict):
            return {}
        out: dict[str, PageMark] = {}
        for page_id, row in raw.items():
            if not isinstance(row, dict):
                continue
            note = str(row.get("note") or "")[:NOTE_MAX]
            bookmarked = bool(row.get("bookmarked"))
            if not bookmarked and not note:
                continue
            out[str(page_id)] = PageMark(bookmarked=bookmarked, note=note)
        return out

    def bookmarked_ids(self) -> set[str]:
        return {page_id for page_id, mark in self.load().items() if mark.bookmarked}

    def set_mark(
        self,
        page_id: str,
        *,
        bookmarked: bool | None = None,
        note: str | None = None,
    ) -> PageMark:
        with mutation_lock(self.lock_path):
            current = self._load_strict()
            prev = current.get(page_id, PageMark())
            updated = PageMark(
                bookmarked=prev.bookmarked if bookmarked is None else bool(bookmarked),
                note=prev.note if note is None else str(note or "")[:NOTE_MAX],
            )
            if updated.bookmarked or updated.note:
                current[page_id] = updated
            else:
                current.pop(page_id, None)
            self._write(current)
            return updated

    def _load_strict(self) -> dict[str, PageMark]:
        if not self.path.is_file():
            return {}
        payload = require_format(read_json(self.path), FORMAT)
        raw = payload.get("pages")
        if not isinstance(raw, dict):
            return {}
        out: dict[str, PageMark] = {}
        for page_id, row in raw.items():
            if isinstance(row, dict):
                out[str(page_id)] = PageMark(
                    bookmarked=bool(row.get("bookmarked")),
                    note=str(row.get("note") or "")[:NOTE_MAX],
                )
        return out

    def _write(self, marks: dict[str, PageMark]) -> None:
        pages = {
            page_id: mark.as_dict()
            for page_id, mark in sorted(marks.items())
            if mark.bookmarked or mark.note
        }
        write_json_atomic(
            self.path,
            {
                "format": FORMAT,
                "schema_version": 1,
                "pages": pages,
            },
        )
