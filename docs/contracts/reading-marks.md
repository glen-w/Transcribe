# Reading marks

Per-notebook sidecar for **bookmarks**. Absent file means the notebook has no marks. 1.0 and 1.2 notebooks stay valid.

The durable page note is `page_gloss` on the page index ([project-on-disk.md](project-on-disk.md)), not this file. Review and Reading expose one note box bound to gloss. A leftover `note` in this sidecar is shown only while gloss is empty and is copied into `page_gloss` on the first Save of that note (the sidecar note is then cleared). Do not add a second textarea.

| Field | Value |
|-------|--------|
| `format` | `transcribe.reading-marks` |
| `schema_version` | `1` |
| Location | `{notebook}/reading-marks.json` |

```json
{
  "format": "transcribe.reading-marks",
  "schema_version": 1,
  "pages": {
    "PAGE_ID": { "bookmarked": true, "note": "" }
  }
}
```

Bookmarks and leftover sidecar notes are omitted from `effective_text()`, analysis, detection, and fine-tune export. Reading-format export includes leftover sidecar notes only when `include_reading_notes` is set, and includes `page_gloss` only when `include_page_notes` is set. Search may filter bookmarked pages through a derived archive column. That column is cache-only. Gloss is not FTS’d.

`ocr_policy: skip` lives on the page index, not in this file — [project-on-disk.md](project-on-disk.md). Skip-page reading-format export uses `page_gloss` when notes are opted in, otherwise the leftover sidecar note (so 1.3.0 skip-export stays valid). Kept-scan pages export empty unless notes are opted in.
