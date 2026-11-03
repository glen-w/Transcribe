# The durable notebook — 1.3–1.5

PR-sized waves for package **1.3.0**, then exit gates for **1.4** and **1.5**. Product narrative, risks, and sequencing live in [ROADMAP.md](../ROADMAP.md) (Now — The durable notebook). This file is the acceptance authority for **1.4–1.5**. Waves 1–8 (1.3 correct) are implemented; no package tag until an explicit release request.

**Plan origin:** maintainer request to creatively and robustly expand and thicken the roadmap after **1.2.0** landed (2026-11-02).

**Deep-test after wave N treats only that wave’s acceptance table as required.** Later waves stay sequenced, not missing.

Package **1.3.0** shipped a first slice ([expansion_hardening_wave_1_3.md](expansion_hardening_wave_1_3.md)): per-notebook restore, format census, retry-failed, a correction scoreboard, reading-mark notes, `ocr_policy: skip`, batch metadata, and declutter v6. Waves 1–8 below are now implemented (correction practice). They do not add the 1.4 hand shelf. No package tag until an explicit release request.

## Invariants (every wave)

- Scope lean holds: four jobs, no autobiography, no context corpus, no Person store, no Slices, no reconstruction, no time-of-day field.
- No new analysis module and no `ocr_quality` module. No in-app trainer. No UI rewrite. SQLite stays a disposable cache.
- `transcribe.project` / `transcribe.page-result` stay schema_version **1**. New fields are additive; absence on a 1.2 file is the documented default.
- `edited_text` stays user-owned. No wave may clear it, overwrite it from cleanup, or apply a spelling pair without an explicit control and a Save.
- Review → **Cleanup** remains visual declutter. Text-cleanup verdicts are a different control and must not be labelled Cleanup.
- Job records stay `completed` + `circuit_open`. No `completed_partial`.
- Core still must not import Streamlit. UI and CLI share services.
- Confirmed spellings are strings the user typed. They are not people, not NER, not the analysis lexicon.

**Number collision:** package **1.3 / 1.4 / 1.5** here are this notebook product. The same numerals under [After 1.0](../ROADMAP.md#after-10--notebook-anchored-autobiography-workbench----on-file) are historical labels for a different product (People, WhatsApp, CSV). Do not implement those rows because a package number matches.

## Explicitly out of 1.3–1.5

Autobiography imports, backup encryption, page-level merge restore, character-span annotations, facing-page spreads, Patterns tab, Ask RAG auto-ingest, a drag-and-drop reorder rewrite, interior declutter (inpaint, ruled-line removal, stain removal), silent spelling replacement, cloud OCR, audio read-aloud.

---

## Wave 0 — Roadmap honesty — [x] this change

| Item | Acceptance |
|------|------------|
| Active backlog | Ranks are 1.3 waves; 1.1 and 1.2 ranks stay marked landed |
| Now | ROADMAP **Now** is this programme; 1.2 heading is shipped, not a second Now |
| Indexes | `DEV_INDEX`, `USER_INDEX`, `index.md` toctree, README Advanced, usability-wave status line, PRODUCT path sentence |
| Collision | Autobiography release table marked on file, not the package ladder |
| Decision log | 2026-11-02 row for this programme |

---

## Wave 1 — Text-cleanup verdict — [x]

Second-pass OCR cleanup already stores `execution_status` / `acceptance_status` on the attempt. The quality store already has `cleanup` accept/reject, CLI only. This wave is the Review control.

| Item | Acceptance |
|------|------------|
| Surface | On the Transcription lane (or OCR lane): raw vision text, cleanup proposal, and three actions. The visual **Cleanup** lane is unchanged and still means declutter |
| Accept | Writes the proposal into `edited_text` only when the user activates Accept, then Save (or one explicitly named **Accept cleanup** that is itself the save). Records `cleanup` / `accept` |
| Reject | Leaves effective text unchanged. Records `cleanup` / `reject`. Does not delete the cleanup object |
| Edit | Seeds the editor with the proposal and does not persist until the existing Save. A seeded buffer counts as dirty-leave |
| Guard | If `edited_text` is already set, Accept requires the same keep-or-adopt choice as `prefer_promote_with_edit_gate`. Default offer is keep the edit |
| Offline test | Fixture attempt with `cleanup.execution_status=provider_ok` and a proposal distinct from raw text. Accept, reject, and dirty-leave each asserted. `provider_failed` shows no Accept |

Contract touch (write it in this wave, additive): [page-result](../contracts/page-result.md) cleanup section gains the user verdict cross-link; [quality-ratings](../contracts/quality-ratings.md) notes the Review source beside the CLI.

---

## Wave 2 — Divergence banner — [x]

| Item | Acceptance |
|------|------------|
| When | `edited_text` is set, a succeeded attempt has non-empty `raw_text`, and character error rate of raw vs edit is at or above a workspace threshold |
| UI | Transcription shows a banner that a newer reading diverges from the correction. Banner has no button that clears `edited_text` |
| Threshold | Settings value, default documented in known limitations. Changing it does not rewrite results |
| Measure | Same Levenshtein the quality store uses. Computed for display; not a new analysis module |
| Offline test | Below-threshold pair shows no banner; above-threshold pair shows it; banner path does not call a clear-edit API |

---

## Wave 3 — Miss desk — [x]

Review **Failed OCR** stays the queue. This wave groups it and can retry a subset.

| Item | Acceptance |
|------|------------|
| Groups | Counts by existing `error.code` (`empty_output`, `token_repeat`, `model_load`, timeout / `circuit_open` pages, other). Unknown codes fall into other, never dropped |
| Retry | User picks one group (or an explicit page set) and one vision model. That builds a frozen OCR plan containing only those page ids. Pages outside the set are not scheduled |
| Reuse | `JobCoordinator` / existing batch-page selection. Cancel, disk budget, and circuits behave as on any other OCR job |
| Copy | The desk states that an uncorrected miss is not a fine-tune target. No `finetune_hold` flag |
| Offline test | Two `empty_output` pages and one succeeded page: the plan’s page ids are only the two misses |

---

## Wave 4 — Kept scan — [x]

A page that is a drawing, a pasted photo, a ticket, or a cover with no text to read. Distinct from **Ignore in Reader** (which hides a page). A kept scan stays in Reading as an image.

| Item | Acceptance |
|------|------------|
| Field | Additive `page_role`: `text` (default) \| `scan`. Absent on legacy files means `text` |
| OCR | `scan` pages are not scheduled. Switching back to `text` makes them eligible again. In-flight jobs are not rewritten |
| Reading | `scan` pages render the image and a one-line role caption. They are not Failed OCR |
| Analyse | No text unit is built from a `scan` page. Existing published analysis is stale by the normal revision rules when the role flips a page that had text |
| Fine-tune | `scan` pages are excluded from OCR fine-tune positives |
| Ignore | Orthogonal. A page may be `scan` and ignored. Export exclude-ignored is unchanged |
| Offline test | 1.2-shaped notebook loads; a flipped page is skipped by a frozen plan; reader fixture includes the image caption |

Schema note in [project-on-disk](../contracts/project-on-disk.md) / page index: additive key, default `text`. No schema_version bump.

---

## Wave 5 — Unsure and gloss — [x]

| Item | Acceptance |
|------|------------|
| Certainty | Additive `page_certainty`: absent or `sure` \| `unsure`. Review filter **Unsure**. Does not by itself change `review_status` |
| Gloss | Additive `page_gloss`, plain text, maximum 500 characters, one per page. Not `edited_text`. Not an `AnalysisDocument` unit. Not FTS’d as a second corpus in 1.3 (Reading shows it under the page; Search does not) |
| Export | Reading-format option **Include page notes**, default off. Notebook JSON keeps the field either way |
| Offline test | Over-long gloss refused. Export with the option off omits gloss bodies. Effective text unchanged by both fields |

Character-offset uncertainty is out of this wave (offsets rot on the next edit).

---

## Wave 6 — Confirmed spellings — [x]

Workspace file, one person’s hand across notebooks. Pairs, not a dictionary product.

| Item | Acceptance |
|------|------------|
| Format | `transcribe.hand-spellings`, schema_version 1, under `data/config/`. Registered in `persistence/schema.py`. Entries are `{from, to}` strings. Cap **200**. No regular expressions |
| Suggest | Review highlights an occurrence of `from` (case-insensitive match, replacement uses `to` as written) and offers **Apply** for that occurrence into the editor buffer. Save is still required. **Apply all** is out |
| Guard | No path writes `edited_text` without Save. No import-time or OCR-time silent replace |
| Cleanup hint | Workspace switch, default **off**, may append the pair list to the cleanup prompt. On changes the cleanup fingerprint. Off omits it, so old fingerprints still match |
| Name | UI copy says **Confirmed spellings**. Do not call this a lexicon (analysis lexicons are a different mechanism) or a person |
| Offline test | Apply changes the buffer only. Cap rejects the 201st pair. Fingerprint test: hint off matches a pre-hint cleanup fingerprint; hint on does not |
| Backup | File lives under `data/config/` and is therefore already in the workspace ZIP. Document that in the contract |

---

## Wave 7 — Batch metadata — [x]

| Item | Acceptance |
|------|------------|
| Selection | Current notebook, explicit page ids (Review multi-select or CLI). No cross-notebook batch in 1.3 |
| Actions | Add tag, remove tag, approve dates, ignore dates, set/clear ignore, set `page_role`, set `page_certainty`. Gloss is not a batch action |
| Lock | Refused while this notebook’s OCR or analysis lock is held. Unselected pages byte-identical |
| CLI | `transcribe pages batch-meta` shares the service with the UI |
| Offline test | Lock held → error, no write. Two-page selection does not touch a third page |

---

## Wave 8 — 1.3 exit — [x]

| Item | Acceptance |
|------|------------|
| Docs | User guide, known limitations, CONTRACT_INDEX, public surfaces for the new CLI, CHANGELOG when the release is actually cut |
| Suites | New tests in the offline default lane. No live Ollama |
| Honesty | Known limitations name: spellings are suggestions, kept scans are not a photo library, gloss is one note, miss desk does not export garbage as training targets |
| Tag | Checklist green. Version bump and tag only on an explicit release request |

**1.3 exit gate:** Waves 1–7 acceptance tables green; a 1.2 notebook loads with default `page_role=text` and no gloss; `edited_text` survival re-OCR test still green; no context directory introduced.

Stretch **landed** with Waves 5–6 (not deferred to 1.3.1): Wave 5 gloss export option (`export.include_page_notes`, default off), Wave 6 cleanup-hint switch (`ocr.cleanup_spelling_hint`, default off). Waves 1–4 and the suggest/apply spelling path remain the original tag blockers. Tag only on an explicit release request.

---

## 1.4 — Proof the hand came back — [ ] open (1.3 exit green)

1.3 correct waves 1–8 are implemented. The shelf compares against `edited_text` and cleanup verdicts; do not reopen those fields as 1.4 work.

| ID | Outcome | Exit |
|----|---------|------|
| **P1** | **Hand shelf.** User pins corrected pages (`notebook_id`, `page_id`, effective-text fingerprint) in `data/config/hand-shelf.json`. Cap documented (start at 40). Unpin and stale-fingerprint warning when the correction changes | Roundtrip; pin refuses a page with no `edited_text`; stale pin does not silently count as a pass |
| **P2** | **Bring-back report.** CLI (and a Diagnostics or Transcribe panel) runs the chosen vision tag over the shelf only and reports CER vs `edited_text`, pages worse than the previous tag, and pages that became `empty_output`. Report is derived. It is not an analysis module and not published.json | Offline test with a stub vision provider and two shelf pages; report names the worse page |
| **P3** | **Promotion stays explicit.** The report has no button that changes the workspace default vision model. Copy tells the user to pick the tag themselves if they like the numbers | Test that the compare service does not write settings |
| **P4** | **Correction export.** `transcribe quality export-corrections <dir>` writes local JSONL of recorded OCR-sample pairs (image path optional, text + edit distance). Same privacy posture as fine-tune export: the user copies the folder | File mode 0600 on the JSONL where the platform allows; nothing uploaded |
| **P5** | **Fine-tune difficulty.** Additive JSONL fields on OCR fine-tune rows when a quality sample exists: `edit_distance`, `reference_chars`. Omitted when unknown. Older consumers ignore unknown keys | Contract note in finetune-export; fixture row with and without a sample |
| **P6** | **Hand label (stretch).** Optional free-string `hand_label` on a page, cap on distinct labels per notebook (8). Filter in Review. Optional map in settings from label → vision tag is a hint the Transcribe picker can display, not an automatic model switch | Absent label is today’s behaviour. No entity store. No cross-notebook identity resolution |

**1.4 exit:** P1–P5 green. P6 may slip with a decision-log row. Training still does not run in this repository.

---

## 1.5 — Keep a corpus for years — [ ] after 1.3 exit

May proceed in parallel with 1.4 only for items that do not change page-result fields 1.4 is reading. Prefer finishing 1.4 P2 before declutter v6 so shelf images and shelf reports are not mid-crop. Per-notebook restore does not wait on the shelf.

| ID | Outcome | Exit |
|----|---------|------|
| **K1** | **Per-notebook restore.** `transcribe backup restore-notebook <zip> <notebook_id>` extracts one project and its corpus index row. Id collision refuses unless `--replace-notebook`. Replace moves the existing project directory aside first and tells the operator the path. No page-level merge. Corpus lock. `workspace-doctor` after. Full-workspace restore stays replace-only | Fixture zip with two notebooks; restore one; the other on-disk notebook unchanged; collision without the flag fails closed |
| **K2** | **Longevity export profile.** One export path (`--profile longevity` or equivalent) writes images + Markdown + notebook JSON + checksum manifest, then passes `verify-export`. Distinct from a pretty EPUB | `verify-export` succeeds on the profile output |
| **K3** | **Upgrade check.** `workspace-doctor` mode that is read-only and reports unknown `format` members, notebooks that fail a default `load()`, and backup manifest versions older than this package. No rewrite | A planted unknown file is reported; a healthy 1.2 workspace exits 0 |
| **K4** | **Unapproved dates.** Library/Search chip to hide unapproved dates, default off so today’s timeline stays. Not time-of-day. Not related-pages | Filter on hides an unapproved page from the timeline and leaves it in the notebook |
| **K5** | **Declutter v6.** `remove_punch_hole_margins` and `remove_calibration_stripes`: crop a blank outer strip only. A mark inside the detected page area is a no-op (no inpaint). `DECLUTTER_VERSION` 6. Provenance identity includes the new ops. Re-apply stays explicit. Notebook `paper_stock`: `unknown` (default) \| `ruled` \| `blank`. `ruled` skips v6 stripe/hole ops for that notebook | Fixture hole in the margin crops; fixture hole in the text block does not; ruled notebook skips; version bump recorded |
| **K6** | **Quarantine review.** Diagnostics lists `data/corpus/quarantine/` children with sizes and a confirmed delete of those children only. Doctor warning clears when the directory is empty | Delete refuses paths outside the quarantine directory |
| **K7** | **Continue reading.** Per notebook: `last_page_id` plus up to 50 pins `{page_id, label}` in a small notebook-local or config file that backup already packs. Library cover offers **Continue**. Pins are not Slices and have no members except one page | Restore keeps pins. Cap enforced. Ignore-hidden pin still opens when the user chooses it |
| **K8** | **Date chapters (stretch).** Reading-format export can break EPUB/HTML chapters on approved date clusters. Undated pages stay in a trailing section | Fixture with two approved dates yields two chapters; unapproved dates do not open a chapter |
| **K9** | **Reading font (stretch).** Reading uses one of the already-curated export body fonts as a workspace display choice. No new font upload path (custom fonts stay an export feature) | Choice does not affect export unless the user also sets the export family |

**1.5 exit:** K1–K7 green. K8–K9 may slip with a decision-log row. A workspace with no new files still restores under the 1.2 replace-only path.

---

## Suggested seams (not a prescription)

| Wave | Likely homes |
|------|----------------|
| 1 | `ui/review_workbench.py`, cleanup record readers, `services/quality.py` |
| 2 | Review transcription lane, shared Levenshtein helper used by the quality store |
| 3 | Review Failed OCR, OCR plan builder (`services/job.py` or batch page selection) |
| 4–5 | `PageIndex` additive fields, analysis document builder (skip `scan`), export options, fine-tune page filter |
| 6 | New store beside `services/quality.py`, schema registry, Review suggestion, cleanup fingerprint |
| 7 | `ProjectService` or a small collaborator, CLI `pages` |
| 1.4 | New shelf store, a report service, `export-finetune` row writer, `quality` CLI |
| 1.5 | `services` backup restore, `workspace_doctor.py`, `declutter/`, archive filters, Library cover |

New formats (`hand-spellings`, `hand-shelf`, reading pins) get a contract page in the wave that first writes them, and a row in `CONTRACT_INDEX`. Do not add `data/context/`.
