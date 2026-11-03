"""Workspace confirmed spellings for one person's hand.

Pairs the user typed. Not a lexicon, not NER, not a Person store. Apply is
per occurrence into an editor buffer; Save still required. Absence of the
file is a valid empty store. Backup already packs ``data/config/``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from transcribe.errors import ProjectError
from transcribe.persistence.atomic import read_json, write_json_atomic
from transcribe.persistence.locks import mutation_lock
from transcribe.persistence.schema import SchemaError, require_format
from transcribe.runtime_paths import RuntimePaths, build_runtime_paths

FORMAT = "transcribe.hand-spellings"
FILENAME = "hand-spellings.json"
PAIR_CAP = 200


@dataclass(frozen=True)
class SpellingPair:
    source: str
    target: str

    def as_dict(self) -> dict[str, str]:
        return {"from": self.source, "to": self.target}

    @classmethod
    def from_dict(cls, data: Any) -> SpellingPair | None:
        if not isinstance(data, dict):
            return None
        src = str(data.get("from") or "").strip()
        dst = str(data.get("to") or "").strip()
        if not src or not dst:
            return None
        return cls(source=src, target=dst)


def apply_spelling_occurrence(text: str, source: str, target: str, index: int) -> str:
    """Replace the ``index``-th case-insensitive occurrence of ``source`` with ``target``.

    ``target`` is written as stored. ``index`` is 0-based. Out-of-range is a no-op.
    """
    needle = (source or "").strip()
    if not needle:
        return text
    pattern = re.compile(re.escape(needle), re.IGNORECASE)
    matches = list(pattern.finditer(text))
    if index < 0 or index >= len(matches):
        return text
    match = matches[index]
    return text[: match.start()] + target + text[match.end() :]


def find_spelling_occurrences(text: str, source: str) -> list[tuple[int, int, str]]:
    """Return ``(start, end, matched)`` for each case-insensitive hit."""
    needle = (source or "").strip()
    if not needle:
        return []
    pattern = re.compile(re.escape(needle), re.IGNORECASE)
    return [(m.start(), m.end(), m.group(0)) for m in pattern.finditer(text)]


class HandSpellingsStore:
    def __init__(self, runtime: RuntimePaths | None = None) -> None:
        self.runtime = runtime or build_runtime_paths()
        self.path = self.runtime.data_dir / "config" / FILENAME
        self.lock_path = self.path.with_suffix(".spellings.lock")

    def list(self) -> list[SpellingPair]:
        if not self.path.is_file():
            return []
        try:
            payload = require_format(read_json(self.path), FORMAT)
        except (SchemaError, OSError, ValueError, TypeError):
            return []
        raw = payload.get("pairs")
        if not isinstance(raw, list):
            return []
        out: list[SpellingPair] = []
        for row in raw:
            pair = SpellingPair.from_dict(row)
            if pair is not None:
                out.append(pair)
        return out[:PAIR_CAP]

    def pairs(self) -> tuple[tuple[str, str], ...]:
        return tuple((p.source, p.target) for p in self.list())

    def add(self, source: str, target: str) -> SpellingPair:
        pair = SpellingPair.from_dict({"from": source, "to": target})
        if pair is None:
            raise ProjectError("confirmed spellings need a from and a to")
        with mutation_lock(self.lock_path):
            current = self.list()
            if len(current) >= PAIR_CAP:
                raise ProjectError(f"confirmed spellings cap is {PAIR_CAP}")
            current.append(pair)
            self._write(current)
            return pair

    def replace(self, pairs: list[SpellingPair]) -> list[SpellingPair]:
        if len(pairs) > PAIR_CAP:
            raise ProjectError(f"confirmed spellings cap is {PAIR_CAP}")
        with mutation_lock(self.lock_path):
            cleaned = [p for p in pairs if p.source and p.target][:PAIR_CAP]
            self._write(cleaned)
            return cleaned

    def _write(self, pairs: list[SpellingPair]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        write_json_atomic(
            self.path,
            {
                "format": FORMAT,
                "schema_version": 1,
                "pairs": [p.as_dict() for p in pairs],
            },
        )
