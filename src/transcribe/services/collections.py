"""Notebook collections + archived state (workspace organisation).

Stored at ``data/config/notebook-collections.json`` as
``transcribe.notebook-collections`` v1. Collections are named, ordered groups
that span notebooks; archived notebooks are hidden from default pickers and
Library listing without being deleted or excluded from backup.

Boundary vs tags: tags label notebooks/pages for filtering; collections are
curated shelves and archive state is lifecycle. Neither replaces the other
(see docs/contracts/notebook-collections.md). Absence is a valid empty store;
malformed files fail closed so they are never silently overwritten.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from transcribe.persistence.atomic import read_json, write_json_atomic
from transcribe.persistence.locks import mutation_lock
from transcribe.persistence.schema import require_format
from transcribe.ports import Clock, IdGenerator, SystemClock, UuidGenerator, to_iso
from transcribe.runtime_paths import RuntimePaths, build_runtime_paths

FORMAT = "transcribe.notebook-collections"
FILENAME = "notebook-collections.json"


@dataclass(frozen=True)
class NotebookCollection:
    collection_id: str
    name: str
    description: str = ""
    project_ids: tuple[str, ...] = ()
    created_at: str = ""
    updated_at: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "collection_id": self.collection_id,
            "name": self.name,
            "description": self.description,
            "project_ids": list(self.project_ids),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> NotebookCollection:
        ids = data.get("project_ids")
        return cls(
            collection_id=str(data["collection_id"]),
            name=str(data.get("name") or ""),
            description=str(data.get("description") or ""),
            project_ids=tuple(str(x) for x in ids if str(x)) if isinstance(ids, list) else (),
            created_at=str(data.get("created_at") or ""),
            updated_at=str(data.get("updated_at") or ""),
        )


@dataclass(frozen=True)
class OrganisationState:
    collections: tuple[NotebookCollection, ...] = ()
    archived_project_ids: tuple[str, ...] = ()

    def is_archived(self, project_id: str) -> bool:
        return project_id in self.archived_project_ids

    def collections_for(self, project_id: str) -> tuple[NotebookCollection, ...]:
        return tuple(c for c in self.collections if project_id in c.project_ids)

    def collection(self, collection_id: str) -> NotebookCollection | None:
        return next((c for c in self.collections if c.collection_id == collection_id), None)


class NotebookCollectionsStore:
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
        self.lock_path = self.path.with_suffix(".collections.lock")

    def load(self) -> OrganisationState:
        if not self.path.exists():
            return OrganisationState()
        payload = require_format(read_json(self.path), FORMAT)
        rows = payload.get("collections")
        collections = (
            tuple(
                NotebookCollection.from_dict(r)
                for r in rows
                if isinstance(r, dict) and r.get("collection_id")
            )
            if isinstance(rows, list)
            else ()
        )
        archived = payload.get("archived_project_ids")
        return OrganisationState(
            collections=tuple(sorted(collections, key=lambda c: (c.name.casefold(), c.collection_id))),
            archived_project_ids=tuple(
                dict.fromkeys(str(x) for x in archived if str(x))
            )
            if isinstance(archived, list)
            else (),
        )

    def _save(self, state: OrganisationState) -> OrganisationState:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "format": FORMAT,
            "schema_version": 1,
            "collections": [c.as_dict() for c in state.collections],
            "archived_project_ids": list(state.archived_project_ids),
        }
        with mutation_lock(self.lock_path):
            write_json_atomic(self.path, payload)
        return self.load()

    def create(
        self, name: str, *, description: str = "", project_ids: tuple[str, ...] = ()
    ) -> NotebookCollection:
        name = " ".join(str(name).split())
        if not name:
            raise ValueError("collection requires a name")
        state = self.load()
        if any(c.name.casefold() == name.casefold() for c in state.collections):
            raise ValueError(f"collection named {name!r} already exists")
        now = to_iso(self.clock.now())
        created = NotebookCollection(
            collection_id=self.ids.new_id(),
            name=name,
            description=str(description or ""),
            project_ids=tuple(dict.fromkeys(project_ids)),
            created_at=now,
            updated_at=now,
        )
        self._save(
            OrganisationState(
                collections=(*state.collections, created),
                archived_project_ids=state.archived_project_ids,
            )
        )
        return created

    def _replace(self, updated: NotebookCollection) -> NotebookCollection:
        state = self.load()
        if state.collection(updated.collection_id) is None:
            raise KeyError(updated.collection_id)
        self._save(
            OrganisationState(
                collections=tuple(
                    updated if c.collection_id == updated.collection_id else c
                    for c in state.collections
                ),
                archived_project_ids=state.archived_project_ids,
            )
        )
        return updated

    def rename(self, collection_id: str, name: str, *, description: str | None = None) -> NotebookCollection:
        state = self.load()
        current = state.collection(collection_id)
        if current is None:
            raise KeyError(collection_id)
        name = " ".join(str(name).split())
        if not name:
            raise ValueError("collection requires a name")
        if any(
            c.collection_id != collection_id and c.name.casefold() == name.casefold()
            for c in state.collections
        ):
            raise ValueError(f"collection named {name!r} already exists")
        return self._replace(
            NotebookCollection(
                collection_id=current.collection_id,
                name=name,
                description=current.description if description is None else description,
                project_ids=current.project_ids,
                created_at=current.created_at,
                updated_at=to_iso(self.clock.now()),
            )
        )

    def delete(self, collection_id: str) -> bool:
        state = self.load()
        if state.collection(collection_id) is None:
            return False
        self._save(
            OrganisationState(
                collections=tuple(c for c in state.collections if c.collection_id != collection_id),
                archived_project_ids=state.archived_project_ids,
            )
        )
        return True

    def set_members(self, collection_id: str, project_ids: tuple[str, ...]) -> NotebookCollection:
        state = self.load()
        current = state.collection(collection_id)
        if current is None:
            raise KeyError(collection_id)
        return self._replace(
            NotebookCollection(
                collection_id=current.collection_id,
                name=current.name,
                description=current.description,
                project_ids=tuple(dict.fromkeys(str(x) for x in project_ids if str(x))),
                created_at=current.created_at,
                updated_at=to_iso(self.clock.now()),
            )
        )

    def assign(self, collection_id: str, project_id: str, *, member: bool = True) -> NotebookCollection:
        state = self.load()
        current = state.collection(collection_id)
        if current is None:
            raise KeyError(collection_id)
        ids = [p for p in current.project_ids if p != project_id]
        if member:
            ids.append(project_id)
        return self.set_members(collection_id, tuple(ids))

    def set_archived(self, project_id: str, *, archived: bool) -> OrganisationState:
        state = self.load()
        ids = [p for p in state.archived_project_ids if p != project_id]
        if archived:
            ids.append(project_id)
        return self._save(
            OrganisationState(collections=state.collections, archived_project_ids=tuple(ids))
        )


__all__ = [
    "FORMAT",
    "NotebookCollection",
    "NotebookCollectionsStore",
    "OrganisationState",
]
