# Reading marks

Per-notebook sidecar for bookmarks and marginal notes. Absent file means the notebook has no marks. 1.0 and 1.2 notebooks stay valid.

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
    "PAGE_ID": { "bookmarked": true, "note": "optional short note" }
  }
}
```

Notes are omitted from `effective_text()`, analysis, detection, and fine-tune export. Reading-format export includes them only when `include_reading_notes` is set. Search may filter bookmarked pages through a derived archive column. That column is cache-only.

`ocr_policy: skip` on a page (optional; absent means `transcribe`) is stored on the page index, not in this file. Skip pages are not scheduled for OCR. Their export text is the marginal note, not OCR output.
