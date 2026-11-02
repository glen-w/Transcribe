# Quality ratings & the evaluation loop

Local, collect-only quality signals. Shipped in 1.2
(`transcribe.services.quality.QualityRatingStore`). **No telemetry**: nothing
is sent anywhere; the file never leaves the machine unless the user copies
the workspace or a backup that includes config.

| Field | Value |
|-------|-------|
| `format` | `transcribe.quality-ratings` |
| `schema_version` | `1` |
| Location | `{TRANSCRIBE_DATA_DIR}/config/quality-ratings.json` |
| Writes | Atomic JSON append-replace under a mutation lock |

## Kinds and verdicts

| Kind | Verdicts | Source |
|------|----------|--------|
| `ocr_sample` | `accept` / `edit` / `reject` | First human correction of an OCR reading in Review (recorded automatically on save), or `transcribe quality rate` |
| `cleanup` | `accept` / `reject` | Reviewer judgement of second-pass cleanup output (CLI today) |
| `analysis` | `up` / `down` | Usefulness rating for an analysis output (CLI today) |

For `ocr_sample`, when OCR text and reviewed text are both recorded, the
entry carries `edit_distance` (Levenshtein) and `reference_chars`, so the
character error rate is `edit_distance / reference_chars`. Verdicts derive
as: untouched → `accept`, emptied → `reject`, otherwise → `edit`.

Summaries (`QualityRatingStore.summary`) report counts per kind/verdict,
mean CER over OCR samples, cleanup acceptance ratio, and analysis up ratio.
Diagnostics shows the workspace summary. Sampled pages for a manual review
pass can be drawn deterministically with `sample_page_ids`.

## Scoreboard

`transcribe quality scoreboard` (and Diagnostics, when a notebook is open) scores succeeded attempts against `edited_text` with the same character error rate. Rows are grouped by model tag, digest, and whether the text is the vision reading or an applied cleanup. The scoreboard is computed on read. It does not copy OCR text into `quality-ratings.json` and it does not upload anything.

This is the user-facing OCR-quality surface. A dedicated `ocr_quality`
analysis module remains deferred (see ROADMAP); improving text stays with
second-pass cleanup / verification and human review.

## Import → OCR smoke kit

`tests/acceptance/ocr_lifecycle/test_import_ocr_smoke_kit.py` implements the
design in `docs/dev/smoke_kit_import_ocr.md`: import → stub-vision OCR →
correct → re-OCR proves `edited_text` survives and whitespace output lands
as `empty_output` on Review **Failed OCR**. Offline, no GPU, runs in PR CI.
