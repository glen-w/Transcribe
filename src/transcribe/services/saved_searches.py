"""Saved workspace searches (filter JSON only; never result snapshots).

Stored at ``data/config/saved-searches.json`` as ``transcribe.saved-searches``
v1. Absence is a valid empty store. Loading a malformed or unknown-format
file fails closed (SchemaError) so a corrupt file is never silently
overwritten by a later save.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from transcribe.domain.dates import ApproximateDate
from transcribe.persistence.atomic import read_json, write_json_atomic
from transcribe.persistence.locks import mutation_lock
from transcribe.persistence.schema import require_format
from transcribe.ports import Clock, IdGenerator, SystemClock, UuidGenerator, to_iso
from transcribe.runtime_paths import RuntimePaths, build_runtime_paths
from transcribe.services.archive import ArchiveFilters

FORMAT = "transcribe.saved-searches"
FILENAME = "saved-searches.json"


def filters_to_dict(filters: ArchiveFilters) -> dict[str, Any]:
    return {
        "period": filters.period,
        "year": filters.year,
        "range_start": filters.range_start.as_dict() if filters.range_start else None,
        "range_end": filters.range_end.as_dict() if filters.range_end else None,
        "query": filters.query,
        "tags": list(filters.tags),
        "media_types": list(filters.media_types),
        "project_tags": list(filters.project_tags),
        "notebook_ids": list(filters.notebook_ids),
        "include_undated": filters.include_undated,
        "people": list(filters.people),
        "places": list(filters.places),
        "include_archived": filters.include_archived,
        "collection_id": filters.collection_id,
        "bookmarked_only": filters.bookmarked_only,
    }


def filters_from_dict(data: Any) -> ArchiveFilters:
    data = data if isinstance(data, dict) else {}

    def _date(key: str) -> ApproximateDate | None:
        raw = data.get(key)
        return ApproximateDate.from_dict(raw) if isinstance(raw, dict) else None

    def _tuple(key: str) -> tuple[str, ...]:
        raw = data.get(key)
        if not isinstance(raw, list):
            return ()
        return tuple(str(x) for x in raw if str(x).strip())

    period = str(data.get("period") or "all")
    if period not in ("all", "year", "range"):
        period = "all"
    year = data.get("year")
    return ArchiveFilters(
        period=period,  # type: ignore[arg-type]
        year=int(year) if isinstance(year, int) else None,
        range_start=_date("range_start"),
        range_end=_date("range_end"),
        query=str(data.get("query") or ""),
        tags=_tuple("tags"),
        media_types=_tuple("media_types"),
        project_tags=_tuple("project_tags"),
        notebook_ids=_tuple("notebook_ids"),
        include_undated=bool(data.get("include_undated", True)),
        people=_tuple("people"),
        places=_tuple("places"),
        include_archived=bool(data.get("include_archived", False)),
        collection_id=str(data.get("collection_id") or ""),
        bookmarked_only=bool(data.get("bookmarked_only", False)),
    )


@dataclass(frozen=True)
class SavedSearch:
    search_id: str
    name: str
    query: str = ""
    order: str = "oldest"
    filters: ArchiveFilters = field(default_factory=ArchiveFilters)
    created_at: str = ""
    updated_at: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "search_id": self.search_id,
            "name": self.name,
            "query": self.query,
            "order": self.order,
            "filters": filters_to_dict(self.filters),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SavedSearch:
        order = str(data.get("order") or "oldest")
        return cls(
            search_id=str(data["search_id"]),
            name=str(data.get("name") or ""),
            query=str(data.get("query") or ""),
            order=order if order in ("oldest", "newest") else "oldest",
            filters=filters_from_dict(data.get("filters")),
            created_at=str(data.get("created_at") or ""),
            updated_at=str(data.get("updated_at") or ""),
        )


class SavedSearchStore:
    """Load/save saved searches with atomic replace under a mutation lock."""

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
        self.lock_path = self.path.with_suffix(".searches.lock")

    def list(self) -> list[SavedSearch]:
        if not self.path.exists():
            return []
        payload = require_format(read_json(self.path), FORMAT)
        rows = payload.get("searches")
        if not isinstance(rows, list):
            return []
        out = [SavedSearch.from_dict(r) for r in rows if isinstance(r, dict) and r.get("search_id")]
        return sorted(out, key=lambda s: (s.name.casefold(), s.search_id))

    def get(self, search_id: str) -> SavedSearch | None:
        return next((s for s in self.list() if s.search_id == search_id), None)

    def _save_all(self, searches: list[SavedSearch]) -> list[SavedSearch]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "format": FORMAT,
            "schema_version": 1,
            "searches": [s.as_dict() for s in searches],
        }
        with mutation_lock(self.lock_path):
            write_json_atomic(self.path, payload)
        return self.list()

    def upsert(
        self,
        name: str,
        *,
        query: str = "",
        order: str = "oldest",
        filters: ArchiveFilters | None = None,
        search_id: str | None = None,
    ) -> SavedSearch:
        name = " ".join(str(name).split())
        if not name:
            raise ValueError("saved search requires a name")
        now = to_iso(self.clock.now())
        searches = self.list()
        if search_id:
            for i, existing in enumerate(searches):
                if existing.search_id == search_id:
                    updated = SavedSearch(
                        search_id=search_id,
                        name=name,
                        query=query,
                        order=order if order in ("oldest", "newest") else "oldest",
                        filters=filters or existing.filters,
                        created_at=existing.created_at or now,
                        updated_at=now,
                    )
                    searches[i] = updated
                    self._save_all(searches)
                    return updated
            raise KeyError(search_id)
        # Name is unique case-insensitively: re-saving a name updates it.
        for existing in searches:
            if existing.name.casefold() == name.casefold():
                return self.upsert(
                    name,
                    query=query,
                    order=order,
                    filters=filters,
                    search_id=existing.search_id,
                )
        created = SavedSearch(
            search_id=self.ids.new_id(),
            name=name,
            query=query,
            order=order if order in ("oldest", "newest") else "oldest",
            filters=filters or ArchiveFilters(),
            created_at=now,
            updated_at=now,
        )
        self._save_all([*searches, created])
        return created

    def delete(self, search_id: str) -> bool:
        searches = self.list()
        kept = [s for s in searches if s.search_id != search_id]
        if len(kept) == len(searches):
            return False
        self._save_all(kept)
        return True


__all__ = ["FORMAT", "SavedSearch", "SavedSearchStore", "filters_from_dict", "filters_to_dict"]
