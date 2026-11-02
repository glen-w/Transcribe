# Saved searches

Named, reusable workspace search filters. Shipped in 1.2
(`transcribe.services.saved_searches.SavedSearchStore`).

## Rules

- A saved search stores **filter JSON only** — query text, order, and an
  `ArchiveFilters` snapshot. It never stores result snapshots, snippets, or
  page lists; applying it re-runs the search against the current index.
- People/places entries are published-NER surface forms (see below); they
  are filters over derived cache state, not identity assertions.

| Field | Value |
|-------|-------|
| `format` | `transcribe.saved-searches` |
| `schema_version` | `1` |
| Location | `{TRANSCRIBE_DATA_DIR}/config/saved-searches.json` |
| Writes | Atomic JSON replace under a mutation lock |

- Absence is a valid empty store. Malformed files fail closed.
- Names are unique case-insensitively; saving an existing name updates it.
- Unknown filter keys on load are ignored; unknown `period` falls back to
  `all`. Dates round-trip as `ApproximateDate` dicts.

## Entity filters (Archive)

`ArchiveFilters.people` / `places` match **published NER only**: during
archive reindex, entities from `analysis/ner/published.json` are grouped by
page (`unit_id`) into the disposable SQLite cache (`pages.entities_json`).
`people` requires label `PERSON`; `places` requires `GPE` / `LOC` / `FAC`.
Matching is case-insensitive on the surface form and AND across requested
surfaces. Notebooks without published NER simply have no entity rows — they
never match an entity filter. This mirrors the shipped `names` detector rule
(published NER only, no nested re-runs).

## Surfaces

- Search page → **Saved searches** expander (apply / save current / delete).
- CLI: `transcribe saved-search list|save|delete`,
  `transcribe search [--saved <id-or-name>] [--people a,b] [--places x,y]`.
