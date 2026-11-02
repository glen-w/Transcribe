# Notebook collections & archived state

Workspace organisation for living with many notebooks. Shipped in 1.2
(`transcribe.services.collections.NotebookCollectionsStore`).

## Boundary vs tags

- **Tags** label notebooks and pages for filtering (tag catalog contract).
- **Collections** are curated, named shelves that span notebooks. A notebook
  may sit on several shelves. Collections carry no page-level meaning.
- **Archived** is lifecycle state: an archived notebook is hidden from
  default Library listing, search, and pickers, but is never deleted, never
  excluded from backup, and can be unarchived at any time.

Collections are **not** a second tag system and must not be used for
page-level labelling.

## Format

| Field | Value |
|-------|-------|
| `format` | `transcribe.notebook-collections` |
| `schema_version` | `1` |
| Location | `{TRANSCRIBE_DATA_DIR}/config/notebook-collections.json` |
| Writes | Atomic JSON replace under a mutation lock |

```json
{
  "format": "transcribe.notebook-collections",
  "schema_version": 1,
  "collections": [
    {
      "collection_id": "uuid-hex",
      "name": "Paris shelves",
      "description": "",
      "project_ids": ["notebook-uuid"],
      "created_at": "2026-11-02T00:00:00.000Z",
      "updated_at": "2026-11-02T00:00:00.000Z"
    }
  ],
  "archived_project_ids": ["notebook-uuid"]
}
```

## Rules

- Absence of the file is a valid empty store (no collections, nothing archived).
- Malformed or unknown-format files fail closed on load (`SchemaError`);
  a later save must never silently overwrite a corrupt file.
- Collection names are unique case-insensitively; renaming onto an existing
  name is refused.
- Membership is by notebook `project_id` (UUID), never by path: folder
  renames do not break shelves.
- Archive state lives here, not in `project.json`: archiving a notebook does
  not mutate the notebook.
- The archive SQLite cache carries `archived` / `collections_json` as
  rebuildable derived state only; this file is the authority.
- Lock order stays corpus → notebook; this store takes only its own
  config mutation lock.

## Surfaces

- Library → **Collections & archived notebooks** expander (create / rename /
  delete / members / archive toggle); Library filters include archived and
  collection selectors; notebook cards show an **Archived** caption.
- CLI: `transcribe collections list|create|rename|delete|assign|unassign|archive|unarchive`.
- Export: a collection can be exported as an anthology
  (`transcribe export --collection <id>`, Export panel Scope → Collection).
