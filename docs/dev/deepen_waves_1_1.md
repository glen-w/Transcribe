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

## Wave 2 — Auto-tag suppression

Additive `suppressed_auto_tags` on `PageIndex`. Re-running auto-tag does not re-apply slugs the user removed. `transcribe.detection-auto-tag` v1 stays detector defaults.

## Wave 3 — Detect cancel

Standalone Detect can Stop after the current window (thread + `cancel_check`). No new job-status enum.

## Wave 4 — U4 Inbox polish

Product buckets imported / failed / duplicated / needs-review over existing ImportRun fields. Prefill/scan `TRANSCRIBE_INBOX_DIR`. Corpus-integrity gate stays green.

## Wave 5 — Visual declutter v4

`remove_binding_gutter` then `remove_edge_shadows`. Pillow crop insets only. `DECLUTTER_VERSION` 4.

## Wave 6 — Page reorder kernel

`ProjectService.reorder_pages` permutes the `pages` array. `move_page_to_date_cluster` inserts after a confirmed date cluster. CLI. No on-disk `page_index` reindex.

## Wave 7 — Page reorder UI

Thumbnail/Review move controls; optional JS island; Date lane cluster action.

## Wave 8 — Hand-model bring-back

Export-tab checklist + install/verify docs. Training stays outside the app.

## Wave 9 — L2 load default

`ProjectService.load(reconcile=False)` by default. Explicit `reconcile_interrupted()` / first-open remain writes.

## Waves 10–11 — Docs, coverage, tag

Whole-suite tests; coverage floor if stable; package **1.1.0**; `# pre-release` then tag when governance is green.
