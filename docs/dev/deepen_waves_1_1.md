# Deepen-in-place waves toward 1.1.0

PR-sized product and architecture follow-ups after the **1.0.1** decoupling patch. No Streamlit rewrite, no in-app trainer, no autobiography, no `transcribe.project` schema bump (additive keys only).

**Deep-test after wave N treats only that wave’s acceptance table as required.** Later waves stay sequenced, not missing.

Non-goals for the whole programme: GPU/training loop, new analysis modules, `completed_partial` job status, event bus, CLI vs UI service split, reopening the corpus-integrity gate, interior-page declutter, reindexing `pages/<source_id>/<page_index>/` on reorder.

---

## Wave 0 — Backlog honesty (this commit)

| Item | Acceptance |
|------|------------|
| Active backlog | Ranks 1–2 (0.9.0 cut, Track C) marked landed; remaining rows are 1.1 deepen-in-place |
| Track C | Yes-gates signed off as already met on the 1.0.0 tag |
| Path to 0.9.0 / 1.0 | Historical `[x]`; **Now** is this programme |
| Indexes | `DEV_INDEX` + Sphinx toctree link this file |

---

## Wave 1 — Cover Open + dirty leave — [x]

Library cover Open is a visible control under the thumb (`tx_open_cover_*`). Review dirty-leave is Stay / Discard & leave (`rw_pending_leave`).

## Wave 2 — Auto-tag suppression — [x]

Additive `suppressed_auto_tags` on `PageIndex`. Re-running auto-tag does not re-apply slugs the user removed. `transcribe.detection-auto-tag` v1 stays detector defaults.

## Wave 3 — Detect cancel — [x]

Standalone Detect can Stop after the current window (`DetectionRunCoordinator` + `cancel_check`). No new job-status enum.

## Wave 4 — U4 Inbox polish — [x]

Product buckets imported / failed / duplicated / needs-review over existing ImportRun fields. Prefill/scan `TRANSCRIBE_INBOX_DIR`. Corpus-integrity gate stays green.

## Wave 5 — Visual declutter v4 — [x]

`remove_binding_gutter` then `remove_edge_shadows`. Pillow crop insets only. `DECLUTTER_VERSION` 4 (superseded by v5 lid slivers in 1.2).

## Wave 6 — Page reorder kernel — [x]

`ProjectService.reorder_pages` permutes the `pages` array. `move_page_to_date_cluster` inserts after a confirmed date cluster. CLI. No on-disk `page_index` reindex.

## Wave 7 — Page reorder UI — [x]

Thumbnail/Review move controls; optional JS island; Date lane cluster action.

## Wave 8 — Hand-model bring-back — [x]

Export-tab checklist + install/verify docs. Training stays outside the app.

## Wave 9 — L2 load default — [x] (landed in 1.2 Wave 0)

`ProjectService.load(reconcile=False)` by default. Explicit `reconcile_interrupted()` / first-open remain writes. See [expansion_hardening_wave_1_2.md](expansion_hardening_wave_1_2.md).

## Waves 10–11 — Docs, coverage, tag — [x] (folded into 1.2)

Whole-suite tests and docs landed with the 1.2 programme; the single tag is package **1.2.0** (no separate 1.1.0 tag was cut — W1–W8 shipped in its Unreleased section).
