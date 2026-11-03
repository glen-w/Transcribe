# Confirmed spellings

Workspace list of `{from, to}` pairs for one person’s hand. Review offers
**Apply** on a single occurrence into the editor buffer; Save is still
required. There is no Apply-all and no silent replace at OCR or import time.

| Field | Value |
|-------|-------|
| `format` | `transcribe.hand-spellings` |
| `schema_version` | `1` |
| Location | `{TRANSCRIBE_DATA_DIR}/config/hand-spellings.json` |
| Cap | 200 pairs. No regular expressions |

Absence is a valid empty store. The file lives under `data/config/` and is
therefore already included in a workspace ZIP ([workspace-backup.md](workspace-backup.md)).

```json
{
  "format": "transcribe.hand-spellings",
  "schema_version": 1,
  "pairs": [{ "from": "teh", "to": "the" }]
}
```

UI copy is **Confirmed spellings**. Do not call this a lexicon (analysis
lexicons are a different mechanism) or a person.

An optional workspace switch `ocr.cleanup_spelling_hint` (default off) may
append the pair list to the cleanup prompt. Turning it on changes the cleanup
fingerprint so old skips stay valid. Off leaves fingerprints matching
pre-hint cleanups.
