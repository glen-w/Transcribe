# Transcribe roadmap

**Product definition:** [PRODUCT.md](PRODUCT.md)  
**Active product focus:** [1.3–1.5 The durable notebook](dev/durable_notebook_1_3.md) — correction, proof the hand came back, keep the corpus. Acceptance checklists live in that file  
**Previous release:** [1.2 expansion & hardening](dev/expansion_hardening_wave_1_2.md) — tagged **1.2.0** (folds in 1.1 deepen W1–W9)  
**Wave plans (done tracks):** [usability_wave_plan.md](usability_wave_plan.md) · [infrastructure_wave_0_9_plan.md](infrastructure_wave_0_9_plan.md)  
**Critical path:** [Active backlog](#active-backlog--ranked) · [Now — The durable notebook](#now--135-the-durable-notebook)  
**Historical 0.9 / 1.0 path:** [Path to 0.9.0 / 1.0](#path-to-090--10) — tagged; Track C signed off  
**Scope boundary:** [Scope lean — 24 Sep 2026](#scope-lean--24-sep-2026)  
**On file, not this product:** [After 1.0 — autobiography](#after-10--notebook-anchored-autobiography-workbench----on-file) — those old 1.1–2.0 labels are **not** package 1.3–1.5  
**Analysis porting map:** [dev/analysis_module_porting.md](dev/analysis_module_porting.md)  
**Core delivery history:** [archive/plans/analysis_wave1_plan.md](archive/plans/analysis_wave1_plan.md)  
**TranscriptX handoff (future):** [INTEGRATION_SEAM.md](INTEGRATION_SEAM.md) — post–TX 1.0; not a dependency. A reverse file-import of TX exports is **not** a Transcribe release; it lives in the parked autobiography write-up (old label 1.6).  
**Indexes:** [USER_INDEX.md](USER_INDEX.md) · [DEV_INDEX.md](DEV_INDEX.md) · [CONTRACT_INDEX.md](CONTRACT_INDEX.md)  
**Architecture candidates (not 0.9):** [reviews/architecture_from_evidence.md](reviews/architecture_from_evidence.md) · [Later — Architecture follow-ups](#later--architecture-follow-ups-from-evidence-review--candidates)

> **Status legend:** [ ] planned · [~] in progress · [x] done · [−] deferred / parked · [?] candidate (uncommitted)

---

## How to read this document

| If you need… | Go to |
|--------------|--------|
| What this product is (and is not) | [Scope lean](#scope-lean--24-sep-2026) · [PRODUCT.md](PRODUCT.md) |
| What to build next | [Active backlog](#active-backlog--ranked) · [The durable notebook](#now--135-the-durable-notebook) · [dev/durable_notebook_1_3.md](dev/durable_notebook_1_3.md) |
| Track detail for usability | [usability_wave_plan.md](usability_wave_plan.md) (authority for U0–U4) |
| Track detail for maintainer infra | [infrastructure_wave_0_9_plan.md](infrastructure_wave_0_9_plan.md) (authority for I0–I6) |
| What already shipped | [Status at a glance](#status-at-a-glance) · [Shipped programmes](#shipped-programmes) |
| Ideas not scheduled | [Near-term candidates](#near-term-candidates--not-on-the-090-path) · [Later candidates](#later-candidates--uncommitted--) |
| Autobiography / context corpus | [After 1.0](#after-10--notebook-anchored-autobiography-workbench----on-file) — **on file only** |

**Authority rules**

1. This file sequences product priorities. It does **not** define runtime schemas — contracts under `docs/contracts/` do.
2. Companion wave plans own acceptance checklists for open tracks. When status drifts, update the wave plan **and** this file in the same change.
3. Archived plans under `docs/archive/plans/` are delivery history. Do not treat them as live backlog.
4. Do not schedule work from the [After 1.0](#after-10--notebook-anchored-autobiography-workbench----on-file) write-up in this repository.

---

## Status at a glance

**Package:** **1.4.0**. Notebook freeze tagged **1.0.0**; **1.0.1** is layering/decoupling ([dev/refactor_waves_1_0_1.md](dev/refactor_waves_1_0_1.md)). **1.3.0** shipped [durability and OCR truth](dev/expansion_hardening_wave_1_3.md). **1.4.0** tags [durable notebook](dev/durable_notebook_1_3.md) **1.3 correct** (W1–W8). It is not the ladder’s **1.4 proof** (hand shelf). Open: **1.4** hand shelf / bring-back report, **1.5** continue-reading. **1.2** folded in the 1.1 deepen waves.

```text
0.6.x → 0.7.0 → 0.8.0 → 0.8.5 → 0.8.6 → 0.8.7 → 0.8.8 → 0.9.0 → 1.0.0 → 1.0.1 → 1.2.0 → 1.3 → 1.4 → 1.5
         I0–I1    I2–I3   patch   product  patch   I5+docs  U2+I6   freeze  decoupling  expand   correct  proof   keep
                                  cut      cut
```

| Horizon | Status | What it means |
|---------|--------|---------------|
| **Now** | [~] | Package **1.4.0** tagged 1.3 correct (W1–W8) on [the durable notebook](dev/durable_notebook_1_3.md). Open: ladder **1.4** hand shelf / bring-back report, **1.5** continue-reading (restore-one and declutter v6 already shipped) |
| **1.2.0** | [x] | **Expansion & hardening** ([dev/expansion_hardening_wave_1_2.md](dev/expansion_hardening_wave_1_2.md)): L2 load default, failure/security/scale hardening, search + collections + export expansion, quality loop, declutter v5 |
| **0.9.0** | [x] | Changelog cut — U2 + I0–I6 |
| **1.0** | [x] | Notebook workbench freeze (`v1.0.0`); **1.0.1** is the decoupling patch; Track C signed off |
| **Parked** | [−] | Autobiography programme — [on file](#after-10--notebook-anchored-autobiography-workbench----on-file), future separate product. Its old release numbers are not this ladder |

| Programme | Status | Authority |
|-----------|--------|-----------|
| Core analysis (25 modules) | [x] | [analysis_wave1_plan.md](archive/plans/analysis_wave1_plan.md) |
| OCR lifecycle (multipass / prefer / fine-tune export) | [x] | [ocr-multipass](contracts/ocr-multipass.md) · PR #15 |
| Detection Prompt Hub + Detect | [x] | [detection_wave2_plan.md](archive/plans/detection_wave2_plan.md) |
| Usability **U0–U1** (trust + Analyse UX) | [x] | [usability_wave_plan.md](usability_wave_plan.md) |
| Usability **U3** (daily workbench) | [x] | same |
| Usability **U4** (corpus / inbox gate) | [x] gate green | [corpus-integrity](contracts/corpus-integrity.md); Inbox polish may continue |
| Usability **U2** (first-run) | [x] | Home, Diagnostics, sample notebook (`samples/demo-notebook/`), first-run docs |
| Infra **I0–I6** | [x] | [infrastructure_wave_0_9_plan.md](infrastructure_wave_0_9_plan.md) — I6 nightly / Docker smoke / issue templates |
| Detection fine-tune export | [x] | [detection-finetune-export](contracts/detection-finetune-export.md) |
| Ignore pages (Reader) | [x] | `ui.hide_ignored_pages`; Show ignored; Review mark/unmark |
| Notebook corpus / bulk import | [x] | [notebook-corpus](contracts/notebook-corpus.md) |
| Bulk Analyse (GUI + CLI) | [x] | [analysis-batch-run](contracts/analysis-batch-run.md) |
| Workspace backup / restore | [x] | [workspace-backup](contracts/workspace-backup.md) |
| Visual declutter (scanner bed / overscan / wedges / gutter / shadows / lid slivers) | [x] | v4 binding gutter + edge shadows; **v5 lid slivers (1.2)** |
| Hand-specific model (external fine-tune) | [x] | Export + install/verify docs; training stays outside the app |

A stranger-testing round is **not** a release gate ([dev/user_testing_0_9.md](dev/user_testing_0_9.md)).

---

## Scope lean — 24 Sep 2026

**Lean, not a closed tag.** Glen is contracting this product. Do not schedule the autobiography programme as Transcribe 1.1–2.0. The long write-up under [After 1.0](#after-10--notebook-anchored-autobiography-workbench----on-file) stays in this file so a later product can use it. It is not a backlog for this repo.

**This product is four jobs:**

1. **Transcribe handwritten pages** — import scans, local vision OCR, review and correct, export.
2. **Test models** — multipass compare, prefer/promote, the model matrix and picker. Shipped. Keep using it; refresh probes when models change.
3. **Fine-tune for one person’s hand** — export page images + corrected text, train **outside** this app, install the model in Ollama, verify with multipass. Export is shipped ([finetune_export.md](finetune_export.md)). An in-app training loop is a non-goal. The open job is a model that reads that handwriting reliably, not a trainer inside Transcribe.
4. **Read, tag, and explore notebooks** — Reading, Library, search, tag catalogue. Shipped with the daily workbench (U3). Maintain this. Do not grow it into a life view.

**Scheduled remainder of those jobs:** [1.3–1.5 The durable notebook](#now--135-the-durable-notebook). 1.3 thickens *correct*. 1.4 turns “verify with multipass” from a paragraph in the fine-tune README into a shelf the user can re-run. 1.5 makes a large corpus recoverable one notebook at a time. That programme does not add a fifth job.

**Freeze (stop growing):**

- Context importers, photos-as-evidence, People-as-identity, Slices, reconstruction, page time-of-day, and the old 1.1–2.0 release table as *this* product’s ladder.
- New analysis modules. The 25-module set stays as shipped. Deferred reinterpretations stay deferred.
- Detection fine-tune export is shipped (approved/rejected labels). It is not the hand-model job.
- A UI rewrite. Streamlit stays the host because the notebook workbench runs on it, not because an Autobiography view might need another frontend.

**Public cut:** U2 and I6 are landed. Package **0.9.0** and the **1.0** notebook freeze are cut. A stranger-testing round is not a release gate. Personal use of the four jobs above does not wait on that cut.

Older sentences in this repo that say “after 1.0, Transcribe grows into an autobiography workbench” are superseded by this section.

---

## Version ladder (this product)

| Label | Meaning |
|-------|---------|
| **0.7.0** | Developer lanes + PR CI honesty gate (**I0–I1**). Makefile, `tests/README.md`, GitHub Actions matrix 3.10–3.12, compose-bind assert. |
| **0.8.0** | Release hygiene + quality gates (**I2–I3**). `scripts/release/*`, `release_governance.md`, coverage fail-under, pre-commit, CI `release-checks`. |
| **0.8.5** | Product patch on 0.8.0: cover-page skip in ink metrics; Analyse batch pick labels show published status. |
| **0.8.6** | Post-U3 product cut: OCR Review workbench, export typography/cover/ignore-pages, Sphinx docs (**I4**), Ask history, Detect → Workflow nav, chart colours, detection tag approval. |
| **0.8.7** | Product patch: names + lexical detectors, Review/Library polish, Detect accept-per-page, circuit CLI honesty, action-link appearance. |
| **0.8.8** | Docs/ops patch: GitHub Pages landing (**I5**), Docker-preferred install path, public docs reframe for first-time users. |
| **0.9.0** | Package/tag when **U2** + **0.9 infrastructure wave (I0–I6)** exit gates are green. Notebook product is first-run capable and maintainer-operable. |
| **1.0** | Notebook workbench declared complete for the [scope lean](#scope-lean--24-sep-2026): transcribe, compare models, hand-specific model via external fine-tune, read / tag / explore. Not a runway for autobiography. A stranger-testing round is not a release gate. |
| **1.0.1** | Layering and decoupling on the frozen notebook ([dev/refactor_waves_1_0_1.md](dev/refactor_waves_1_0_1.md)). |
| **1.2.0** | Expansion and hardening on shipped surfaces ([dev/expansion_hardening_wave_1_2.md](dev/expansion_hardening_wave_1_2.md)). Search, collections, export filters and custom fonts, collect-only quality ratings, declutter v5, L2 load default. No separate 1.1.0 tag. |
| **1.3** | **Correct.** Cleanup becomes a verdict, misses can be retried as a set, drawings can be kept scans, confirmed spellings suggest and never write. [Wave plan](dev/durable_notebook_1_3.md). |
| **1.4** | **Proof.** A personal shelf of corrected pages scores an installed hand model against `edited_text`. The report does not switch the workspace model. Training stays outside. |
| **1.5** | **Keep.** Restore one notebook out of a workspace ZIP, export a longevity bundle, declutter v6 outside the page, continue reading. |
| **Parked** | Autobiography write-up — [on file](#after-10--notebook-anchored-autobiography-workbench----on-file). Future separate product. Its labels 1.1–2.0 are not rows on this ladder. Package 1.3 is not “People”. |

---

## Active backlog — ranked

**Now:** **1.4** proof (hand shelf / bring-back report) and **1.5** keep (continue-reading). 1.3 correct waves 1–8 are implemented. Do not schedule autobiography from this list.

| Rank | Item | Status | Wave | Detail |
|------|------|--------|------|--------|
| 1 | **Text-cleanup verdict** | [x] | 1.3 W1 | Review can accept, reject, or edit a second-pass cleanup proposal. Visual Cleanup lane stays declutter |
| 2 | **Divergence banner** | [x] | 1.3 W2 | A newer reading that disagrees with `edited_text` is announced and does not clear the edit |
| 3 | **Miss desk** | [x] | 1.3 W3 | Failed OCR grouped by `error.code`; retry builds a plan for that page set only |
| 4 | **Kept scan** | [x] | 1.3 W4 | `page_role=scan` stays in Reading, leaves the OCR queue, and is not a fine-tune positive |
| 5 | **Unsure + gloss** | [x] | 1.3 W5 | Page-level unsure filter; one plain-text note, absent from effective text |
| 6 | **Confirmed spellings** | [x] | 1.3 W6 | `{from, to}` pairs, per-occurrence Apply into the buffer, Save still required |
| 7 | **Batch metadata** | [x] | 1.3 W7 | Tags, dates, ignore, role, certainty on an explicit page set; lock refuses |
| 8 | **1.3 exit** | [x] | 1.3 W8 | Docs, offline tests, known-limitations honesty. Tag only on a release request |

**Next, not open:** 1.4 shelf and bring-back report · 1.5 continue-reading and remaining keep work (restore-one and declutter v6 already shipped in 1.3.0). Do not crop shelf pages mid-1.4.

**Landed (no longer backlog):** 0.9.0 package cut · Track C freeze checks (signed off on 1.0.0) · U2.2 sample notebook · U2.4 first-run docs · I6 sustaining lanes · Ignore pages (Reader) · Detection fine-tune export · 1.0.1 decoupling · 1.1 deepen W1–W9 ([dev/deepen_waves_1_1.md](dev/deepen_waves_1_1.md): Cover Open, dirty leave, auto-tag suppression, Detect cancel, Inbox polish, declutter v4, reorder, hand-model docs) · **1.2 expansion & hardening (H1–H4, E1–E5)** · **1.3 correct (W1–W8)**.

---

<a id="now--135-the-durable-notebook"></a>
<a id="now--135-the-durable-notebook----planned"></a>

## Now — 1.3–1.5 The durable notebook

Authority for acceptance: [dev/durable_notebook_1_3.md](dev/durable_notebook_1_3.md). Usability **U0–U4**, infra **I0–I6**, and **1.2.0** are done. Do **not** schedule deferred-reinterpretation ports or autobiography.

**Thesis.** The workbench can already import, read, compare, export, search, and collect. What it still asks the user to hold in their head is the practice around one handwriting: which pages failed and why, whether cleanup helped, which spellings this hand actually uses, whether the model they trained elsewhere is better than the one it replaced, and how to get a single notebook back when a workspace ZIP is the only copy. 1.3–1.5 build that practice. They do not build a life view.

**Package numbers collide with the parked write-up.** Autobiography’s old table uses 1.3 for People, 1.4 for WhatsApp, and 1.5 for CSV. Those rows stay [on file](#after-10--notebook-anchored-autobiography-workbench----on-file). Package **1.3** on this ladder is the correction release. Implementing People because the numeral matches is a scope break.

```text
1.3 correct ──► 1.4 proof the hand came back
     │
     └────────► 1.5 keep the corpus
```

The 1.3 exit gate is green. **1.4 is open.** 1.5 may be designed alongside 1.4. Declutter v6 already shipped in 1.3.0; do not crop shelf pages mid-1.4. Per-notebook restore does not wait on the shelf.

### What “thicker” means here

Each release has one sentence a user could say out loud.

| Release | The user can say |
|---------|------------------|
| **1.3** | “I can finish a bad page without hunting, and the app will not ‘help’ by overwriting what I typed.” |
| **1.4** | “I pinned forty pages I trust, pointed the new model at them, and got a list of pages where it got worse.” |
| **1.5** | “I pulled one notebook out of last year’s ZIP, and the others stayed where they were.” |

### Invariants

- Additive fields only. A 1.2 notebook loads. Absent `page_role` means `text`. Absent gloss means no note.
- `edited_text` is cleared only by the user, on purpose, through a control that says so.
- Review → **Cleanup** remains the visual declutter re-apply. Text cleanup grows a different control.
- Confirmed spellings are pairs the user typed. They are not a Person, not NER, and not an analysis lexicon.
- The bring-back report is a derived comparison. It does not write `published.json` and it does not change the workspace vision model.
- Kept scans are still notebook pages (a drawing in a diary). They are not a photo library and they do not open `data/context/`.
- Pins and glosses are one page each. They are not Slices.
- No in-app trainer, no new analysis module, no `completed_partial`, no schema_version bump, no Streamlit replacement.

### 1.3 — Correct — [x] tagged **1.4.0**

**Product goal:** The human step after OCR is **correct**. Make that step faster and harder to undo by accident.

**UX**

- **Cleanup as a proposal.** Where a second-pass cleanup exists, Review shows raw vision text and the proposal. **Accept** saves it as the edit. **Reject** records a no and leaves the page. **Edit** drops the proposal into the buffer and waits for Save. If an edit is already there, Accept uses the existing keep-or-adopt gate and offers to keep the edit.
- **Divergence.** When a later OCR reading is far from the saved correction (same character-error measure the quality store already computes), Transcription says so. The banner has no “replace my text” action.
- **Miss desk.** Failed OCR, which is already the queue, groups by the error codes the job already writes (`empty_output`, `token_repeat`, model load, timeouts, other). **Retry these** starts an ordinary OCR job whose page set is that group and whose model is the one the user just picked. Uncorrected misses are not described as training data.
- **Kept scan.** A page can be marked as a scan to keep: it stays in Reading with its image, drops out of the OCR schedule and out of fine-tune positives, and is not a failure. **Ignore in Reader** still means “hide”. A ticket can be a kept scan and also ignored.
- **Unsure.** A page-level flag and a Review filter. Character-span markup waits; offsets die on the next keystroke.
- **Gloss.** One short plain note on the page (500 characters). It is not the transcription, not an analysis unit, and not a search corpus in this release. Reading shows it. Export includes it only when asked.
- **Confirmed spellings.** A workspace list of pairs (`from` → `to`), capped at 200, no patterns. Review offers **Apply** on one occurrence into the unsaved buffer. There is no Apply-all. A switch, default off, may add the list to the cleanup prompt; turning it on changes the cleanup fingerprint so old skips stay valid.
- **Batch metadata.** On an explicit set of pages in the open notebook: tag, approve or ignore dates, ignore, kept-scan, unsure. Refused while that notebook’s OCR or analysis lock is held. Gloss is not in the batch list, so a slip does not wipe notes.

**Architecture.** New persisted shapes are additive page fields (`page_role`, `page_certainty`, `page_gloss`, `ocr_policy`) and one config file `transcribe.hand-spellings`. Quality-store cleanup verdicts gain a Review writer beside the CLI. The miss desk is a read-model over attempt errors plus the existing plan/job path. No new job status.

**Reuse.** Cleanup object on the attempt, quality store CER, Failed OCR, prefer edit-gate, `JobCoordinator` page sets, tag catalogue, ignore flag, workspace backup of `data/config/`.

**Risks.** Accept that silently replaces a careful edit. A spelling list that rewrites OCR before the user looks. Kept scan used as a side door for a photo corpus. Gloss growing threads, replies, or highlights. The miss desk growing a second queue with its own status enum. Naming spellings “lexicon” and colliding with analysis lexicons, or “people” and colliding with the parked Person store.

**Exit.** [Wave plan](dev/durable_notebook_1_3.md) Waves 1–8 met. A 1.2 notebook round-trips. The existing “`edited_text` survives re-OCR” smoke stays green. Known limitations say spellings suggest, kept scans are pages, gloss is one note, and the miss desk does not export unread pages as targets. Stretch that shipped with W5/W6 (not deferred to 1.3.1): gloss-in-export (`include_page_notes`) and the cleanup-prompt hint (`cleanup_spelling_hint`, default off). Tag only on an explicit release request.

### 1.4 — Proof the hand came back — [ ] open (1.3 exit green)

**Product goal:** Job 3’s open remainder. Export and “install, then multipass” are shipped as docs. This release is the measurement the user can repeat after the next model, on pages they have already corrected, on this machine.

**UX**

- **Shelf.** The user pins corrected pages (start the cap at 40). A pin stores the notebook, the page, and the fingerprint of the text they trust. If they edit the page later, the pin is stale and the report says so instead of scoring the old text.
- **Bring-back report.** Pick the new vision tag (and the previous one, when they want a delta). The run covers the shelf only. The report lists character error against `edited_text`, pages that got worse, and pages that came back empty. It lives in Diagnostics or on the Transcribe surface as a report, not as a new Analyse view.
- **No silent promotion.** The report does not change the workspace default model. The user picks the tag in the existing picker if the numbers convince them.
- **Correction file.** A CLI export of the quality store’s OCR samples (the text pair and the edit distance) to a local folder. Same rule as fine-tune export: it leaves the machine only if the user copies it.
- **Difficulty on the fine-tune row.** When a quality sample exists, the JSONL row gains `edit_distance` and `reference_chars`. External training can up-weight hard pages. Rows without a sample omit the fields.
- **Hand label (stretch).** An optional short string on a page (“my hand”, “letter pasted in”), at most a handful of distinct labels in one notebook. Review can filter. Settings may show which vision tag the user associated with that label. The association is a hint on the picker, not an automatic switch, and not an identity.

**Architecture.** `hand-shelf.json` under config (backup already packs config). The compare runs through the normal OCR job restricted to shelf page ids, then a pure function over attempts versus `edited_text`. Fine-tune JSONL fields are additive. `hand_label` is an additive page string. No weights, no GPU, no upload.

**Reuse.** Fine-tune export, multipass single-model path, quality-store Levenshtein, stub-vision test pattern from the import→OCR smoke kit, recipe overlay for the installed tag (already documented).

**Risks.** Treating the shelf as ground truth the model must be trained on inside the app. Auto-selecting the winner. Scoring uncorrected OCR against itself and calling it accuracy. Letting hand labels become a Person directory with merge and privacy. Cropping (1.5) or rewriting page text (1.3) while a report is the release gate — which is why 1.4 starts after 1.3 and v6 waits on the report.

**Exit.** Shelf pin/unpin, stale warning, offline two-page report, settings untouched by the report service, correction JSONL written locally, fine-tune contract updated. Hand label may slip with a decision-log row. [finetune_export.md](finetune_export.md) step 6 points at the shelf once it exists, and keeps the manual multipass path for notebooks that have no shelf.

### 1.5 — Keep the corpus — [ ] after 1.3

**Product goal:** A workspace that has lived for years can lose one notebook, gain a bad scan edge, and still be read. Recovery is precise. Pretty export is a different button from the bundle you would trust in a decade.

**UX**

- **Restore one notebook** from a workspace ZIP. If that id is already on disk, the command refuses unless the operator asks to replace, and replace moves the current project directory aside and prints the path. The other notebooks in the workspace are not unpacked over. There is still no merge of page files and no encrypted ZIP (key management stays out of this programme).
- **Longevity profile.** One export writes the images, Markdown, notebook JSON, and a checksum manifest, then the existing `verify-export` must succeed on that folder. EPUB remains the reading gift; this profile is the archive.
- **Upgrade check.** A read-only doctor pass lists notebooks that fail a default load, files whose `format` this package does not know, and backup manifests older than the running version. It does not rewrite them.
- **Unapproved dates.** A Library/Search chip hides them. Default is today’s behaviour (they stay visible). This is not time-of-day and not “other pages near this date”.
- **Declutter v6.** Punch-hole *margins* and scanner calibration stripes, as crops of a blank outer strip. A hole or stripe inside the page area is a no-op — no inpaint. Notebooks marked **ruled** skip those two ops so staff lines are not read as stripes. `unknown` paper (the default) keeps v6 available and conservative. Re-apply stays explicit. `DECLUTTER_VERSION` becomes 6.
- **Quarantine.** Diagnostics lists quarantine children and their sizes. Delete is confirmed and cannot address a path outside that directory. The doctor warning clears when the directory is empty.
- **Continue reading.** Each notebook remembers the last page and up to 50 named pins. The Library cover offers **Continue**. A pin opens that page even if Reader’s hide-ignored setting would have skipped it, when the user chooses the pin. Pins are not collections and not episodes.
- **Stretch.** EPUB/HTML chapters split on approved date clusters, with undated pages in a trailing section. Reading can use one of the curated body fonts as a display choice without changing the export family.

**Architecture.** Restore is a narrowed unpack of the existing ZIP role roots plus a corpus-index row update, under the corpus lock, followed by `workspace-doctor`. Longevity export composes shipped exporters plus `verify-export`. The date chip is an `ArchiveFilters` flag defaulting off. Declutter identity gains ops and the paper-stock flag the same way v5 added lid slivers. Pins are a small JSON the backup already includes via config or the project tree — chosen in the wave, documented in the contract, absent file means “no pins”.

**Reuse.** Workspace backup manifest, safety-copy habit from full restore, `verify-export`, `workspace-doctor`, declutter provenance, Library cover Open, curated font list.

**Risks.** Restore-one that is actually restore-all with a filter applied too late. Aside-copy failing and the replace continuing. v6 eating a ruled margin or a hole that sits in the writing. Continue-reading becoming a Slice with members and dates. The longevity profile quietly dropping ignored pages or kept scans that the JSON is supposed to retain (JSON keeps every page; the Markdown half follows the same exclude-ignored default as other reading formats, and the profile’s README says so).

**Exit.** Two-notebook fixture: restore one, the other unchanged; collision without the flag fails. Longevity folder passes `verify-export`. Doctor reports a planted unknown format and does not rewrite a healthy workspace. Margin hole crops; in-page hole does not; ruled notebook skips v6. Quarantine delete is confined. Pins survive a backup round-trip. Chapters and the reading-font choice may slip with a decision-log row.

### Recorded, not scheduled — [?]

Worth keeping next to this programme so they are not reinvented as scope. They are not waves.

| Idea | Why it waits |
|------|----------------|
| Character-span “unsure” | Offsets rot when the user edits. Page-level unsure ships first |
| Facing-page spreads (two-up) | Needs a spread model. Reorder already fixes the common scan-order mistake |
| Per-page higher `num_predict` re-run | The fingerprint rule for a non-default cap already exists. A button is polish after the miss desk shows truncation is common |
| Patterns tab | Still “only if usage justifies”. Themes already consume the payloads |
| Ask RAG auto-ingest after OCR | The setting is reserved and stays off. Shelf and corrections come first |
| Drag-and-drop reorder as a supported path | Numbered moves and the CLI are the supported route. Promoting the island is a browser-quirk project |
| Backup encryption | Real need, separate design (passphrase, no recovery, threat model). Out of 1.5 |
| Page-level merge from a ZIP | Conflicts with user edits. Replace-the-notebook-or-refuse is the 1.5 rule |
| Related pages by date window | Computed notebook dates, on file as autobiography’s old 1.1. Not this ladder |
| Read-aloud | New speech dependency. Not one of the four jobs |

### Cross-cutting tests

`hand-spellings` is contracted ([contracts/hand-spellings.md](contracts/hand-spellings.md)). Contracts for `hand-shelf` and reading pins are written in the wave that first saves the file, then linked from [CONTRACT_INDEX.md](CONTRACT_INDEX.md). Offline default lane only: stub vision, no live Ollama, no network. The import→OCR smoke kit remains the regression for “a correction survives a re-run”; 1.4 adds a shelf fixture beside it rather than replacing it. Scale budgets from 1.2 stay in nightly. A 1.2 backup of a workspace that has none of the new files still restores with the existing replace-only command.

---

## Path to 0.9.0 / 1.0

**Status:** [x] done — **0.9.0** (2026-10-23) and **1.0.0** notebook freeze tagged; **1.0.1** decoupling patch. Historical sequencing from package **0.8.8**. Companion tracks: [usability_wave_plan.md](usability_wave_plan.md) (U2), [infrastructure_wave_0_9_plan.md](infrastructure_wave_0_9_plan.md) (I0–I6). A stranger-testing round is not a release gate ([dev/user_testing_0_9.md](dev/user_testing_0_9.md)). Live work is [1.3–1.5 The durable notebook](#now--135-the-durable-notebook). This path is historical.

**Thesis:** Cut an operable **0.9.0**, then declare **1.0** as the notebook contract. Harden the existing notebook/OCR/analysis/corpus stack. Do **not** ship photos-as-context, WhatsApp, a People store, Slices, reconstruction, or time-of-day storage in this repo.

```text
U2 (sample + first-run docs)  ─┐
                               ├─► 0.9.0 cut ─► 1.0 notebook freeze
I0–I6 (infra wave)           ─┘
```

### Track A — U2 (product; required for 0.9.0)

**Status:** [x] done. Full acceptance detail: [usability_wave_plan.md](usability_wave_plan.md) §6.

| Item | Status | Work |
|------|--------|------|
| U2.1 Home | [x] | Create / Import + Ollama health; no sample wizard on empty Home |
| U2.3 Diagnostics | [x] | Workspace / notebook doctor in System → Diagnostics |
| **U2.2 Sample notebook** | [x] | Fixture under `samples/demo-notebook/`; Home **Open sample** via init/import; pre-seeded text for offline Analyse Quick |
| **U2.4 First-run docs** | [x] | “First notebook in 15 minutes” in README (**Docker preferred**); port **8510**, known first-run bites |

**U2 exit:** sample path smoke; README / user guide first-run without reading contracts — **met**.

**Risks / anti-patterns**

- Reintroducing a TranscriptX-style guided wizard that Home deliberately removed.
- Sample notebook as a second on-disk project format (must reuse init/import).
- Writing U2 docs only in deep runtime notes — first-run path must be linked from README empty-state / Start here.
- Blocking U2 on I6 or on stranger testing.

**Key files:** `ui/home.py`, `ui/diagnostics.py`, `samples/` (U2.2), README, `docs/runtime/installation.md`, `docs/runtime/docker.md`, `docs/user_guide.md`.

### Track B — I0–I6 (infra; required for 0.9.0)

Full track plan: [infrastructure_wave_0_9_plan.md](infrastructure_wave_0_9_plan.md). Does **not** schedule autobiography or write U2 content (may host docs).

| Track | Status | Intent |
|-------|--------|--------|
| **I0** Developer lanes & inventory | [x] | `Makefile` + `tests/README.md` lane vocabulary; marker policy; light docs/script inventory |
| **I1** PR CI honesty gate | [x] | Lint + offline smoke/default suite on Python 3.10–3.12; compose-bind assert |
| **I2** Release hygiene + governance | [x] | `scripts/release/*`, secrets/denylist, `release_governance.md`, dependency audit log |
| **I3** Quality gates | [x] | Coverage fail-under, pre-commit, partial CI `release-checks` |
| **I4** Hosted docs | [x] | Sphinx over existing Markdown, `.[docs]`, `.readthedocs.yml` scaffold, CI docs job |
| **I5** Public landing | [x] | Modest `website/` + GitHub Pages assemble; workflow tour with generated screenshots and GIFs (`make docs-media`) |
| **I6** Sustaining lanes | [x] | Nightly acceptance/offline heavy, Docker smoke in release-checks, issue templates |

Suggested cut order (historical): **I0+I1** (0.7.0) → **I2+I3** (0.8.0) → **I4** → **I5** (0.8.8) → **I6**. All tracks landed; U2 + I0–I6 enable the **0.9.0** package cut.

#### I6 — Sustaining lanes — [x] done

| Deliverable | Status | Notes |
|-------------|--------|-------|
| `nightly.yml` | [x] | Offline acceptance + contracts (no live Ollama) |
| Docker in `release-checks` | [x] | `docker compose build` + `make docker-smoke` |
| Issue templates | [x] | Bug + feature + `config.yml` |

**I6 exit:** met.

**Infra exit gate (whole wave):** green PR CI on the Python matrix; Makefile/CI/`# pre-release` share lane names; tag authority is `docs/dev/release_governance.md` with script-backed evidence; Sphinx builds in CI and Pages (or documented RTD go-live) can publish the guide; coverage + secrets gates enforced; nightly (or equivalent) runs heavier offline suites without live Ollama.

**Already landed (do not rebuild in I0–I6):** offline default pytest suite, acceptance gates, Markdown docs authority/indexes/archive, Docker Compose loopback bind docs, root `SECURITY.md` / `CONTRIBUTING.md` / `CHANGELOG.md`, agent SOPs, **I4 Sphinx / CI docs job**, **I5 Pages landing**, **I6 nightly / Docker smoke / issue templates**.

### Track C — Notebook freeze checks (docs + rules)

**Foundation readiness checklist** for the 1.0 freeze. Lean 24 Sep 2026: rows that only serve a context corpus are **not** 1.0 gates. Rows that serve the notebook product still belong.

No runtime context schema and no `data/context/` tree in this repo. The checklist below is historical intent where it mentions autobiography; do not treat it as permission to start the parked programme:

| # | Checklist item | Intent | 1.0 gate? |
|-----|----------------|--------|-----------|
| 1 | **Notebook core freeze** | `transcribe.project` v1, `page-result` v1, `AnalysisDocument` v1 remain loadable; After 1.0 is **additive-only**; do not generalize `SourceDocument` | Yes — signed off on **1.0.0** |
| 2 | **Human metadata vocabulary** | ClaimStatus documented as a map onto existing `date_approved` / detection `review_status` / `edited_text` ([TERMS.md](TERMS.md)). Runtime ClaimStatus schema waits for a future product | Docs only — met |
| 3 | **Rebuildability proven** | Archive FTS delete-and-rebuild; backup excludes `data/cache/`; corpus + hardening acceptance suites green on CI (I1/I6) | Yes — signed off on **1.0.0** |
| 4 | **Extensibility noted** | Future lock order **corpus → context → notebook**; context trees must be optional (absence = valid 1.0 workspace). See [ARCHITECTURE.md](ARCHITECTURE.md) | Docs only (parked programme) — met |
| 5 | **Longevity minimum for testers** | Pre-upgrade backup + restore verify documented in first-run / [backup_and_restore.md](backup_and_restore.md); refuse/recover copy for schema bumps. Full “archive readable without Transcribe” stays candidate | Thin yes — signed off on **1.0.0** |
| 6 | **Known-limitations honesty** | First-run bites, remote Ollama, unapproved dates on timeline, Analyse optional extras — visible to unfamiliar users | Yes — signed off on **1.0.0** |
| 7 | **Explicit non-goals** | No WhatsApp/Telegram/photo-context corpus; no Person store; no Slices; no ReconstructionBundle; no page time-of-day field; no `AnalysisDocument` v1 bump | Yes — signed off on **1.0.0** |

Optional U4 Inbox polish may continue but is **not** on the 0.9.0 critical path.

### 0.9.0 cut

**[x] tagged 2026-10-23.** Intermediate cuts: **0.7.0** = I0+I1; **0.8.0** = I2+I3; **0.8.5** = product patch; **0.8.6** = post-U3 product cut + **I4** Sphinx/CI docs; **0.8.7** = names/lexical detectors, Review/Library polish, circuit CLI honesty; **0.8.8** = **I5** Pages landing + Docker-preferred install docs. **I6** + **U2** enabled the cut.

### 1.0 freeze — definition of done

**1.0** declares the notebook workbench complete for the [scope lean](#scope-lean--24-sep-2026) and the [PRODUCT.md](PRODUCT.md) promise.

| Gate | Evidence |
|------|----------|
| Product promise | Import → OCR → Review → Analyse (optional) → Export → Backup works via documented Docker path |
| U2 acceptance | Sample + first-run docs closed |
| Infra | I0–I6 exit gate green; **0.9.0** tagged |
| Foundation | Track C rows marked Yes — **signed off** on the **1.0.0** tag (this file, Track C table) |
| Contracts | Core schemas remain loadable; no context corpus on disk |
| Honesty | [known_limitations.md](known_limitations.md) covers first-run bites; miss list = Failed OCR; VL OCR ≠ text LLM |
| Scope | PRODUCT / ROADMAP still page-first; autobiography still on file, not scheduled |

Autobiography does **not** start afterwards inside this repo. The write-up stays [on file](#after-10--notebook-anchored-autobiography-workbench----on-file).

---

## Shipped — 1.2 expansion & hardening — [x] landed

Authority: [dev/expansion_hardening_wave_1_2.md](dev/expansion_hardening_wave_1_2.md). The 1.1 deepen-in-place waves (W1–W9) are folded in. Usability **U0–U4** and infra **I0–I6** are done. Do **not** schedule deferred-reinterpretation ports or autobiography.

## Usability wave — [x] done (Inbox polish may continue)

Priority after shipping the core module set. **Do not** schedule deferred-reinterpretation ports while this focus is open. Full track plan: [usability_wave_plan.md](usability_wave_plan.md). Detection Prompt Hub / Detect UI is a **shipped parallel track** ([detection_wave2_plan.md](archive/plans/detection_wave2_plan.md); not this wave’s definition of done — avoid calling Detection the product “Wave 2” in usability docs).

**Wave summary**

| Track | Status | Outcome |
|-------|--------|---------|
| **U0** Trust foundation | [x] | Preset identity, plan-hash bind, content revision, shared health, export provenance |
| **U1** Analyse product UX | [x] | Product views, status strip, OCR Advanced |
| **U2** First-run & operability | [x] | Sample notebook + first-run docs landed — enables **0.9.0** with I0–I6 |
| **U3** Daily workbench | [x] | Review queues, Reading, Search/Library polish, model copy |
| **U4** Corpus UX | [x] gate green | Bulk import / inbox supported; Inbox polish may continue |

### U0–U1 — Product hardening (embedded) — [x] done

Phased checklist (see [product hardening plan](archive/plans/product_hardening_plan.md)): **#10 → #3/#4 → #1/#2 → #5/#6 → #11/#12 → #13 → #7–9**.

| Phase | Status | Outcome | Wave track |
|-------|--------|---------|------------|
| **1** — #10, #3, #4 | [x] | Analyse has one launcher and one freshness authority | done |
| **2** — #1, #2 | [x] | Runs survive UI/process interruption and execute from frozen inputs | done |
| **3** — #5, #6 | [x] | Users can trust exactly what a preset will run | **U0** (done) |
| **4** — #11, #12 | [x] | Every analysis surface gives the same answer to “is this current and healthy?” | **U0** (done) |
| **5** — #13 | [x] | Exports identify exactly which notebook revision produced them | **U0** (done) |
| **6** — #7, #8, #9 | [x] | Analyse surfaces are simplified around user tasks rather than module mechanics | **U1** (done) |

| Track | Intent |
|-------|--------|
| **Robustness** | Honest capability / cache / parent freshness; crash-reopen and stale-evidence behaviour; offline test coverage for shipped modules; clearer failure and empty-success paths. **Also landed (OCR deepen-in-place):** consecutive vision **timeout** circuit (skip remaining pages for that model after 3) and fatal **model-load** circuit (skip after the first unrecoverable Ollama loader error, e.g. unsupported architecture) — see [known_limitations.md](known_limitations.md) |
| **Analyse UX** | One batch run action, one freshness model, Ask remains ad-hoc; deepen Overview / Themes / Mood / Moments / Summaries as **product** read-models (not module consoles). **Also landed:** Overview/Mood **corpus / period average** charts ([dev/analysis_visual_compare.md](dev/analysis_visual_compare.md)); Moments / page-series **Jump to page** into Reading; Analyse launcher vs View consume split ([public_surfaces.md](public_surfaces.md)) |
| **Payload polish** | People & places map tab shipped (NER read-model + opt-in geocode). Patterns tab and deliberate keyphrase enrichment for wordclouds/topics remain optional polish — not a back door for deferred reinterpretations |
| **OCR text quality** | Prefer existing **second-pass LLM OCR cleanup / verification** (and review edits) over a separate `ocr_quality` analysis module |

Infra checklist already landed for the core set: [analysis_wave1_hardening_plan.md](archive/plans/analysis_wave1_hardening_plan.md). Further work stays deepen-in-place on shipped surfaces and contracts.

**Hardening exit gate (U0+U1):** Crash/reopen behaviour, stale detection, offline operation, export provenance, and normal Analyse workflows are covered by acceptance tests, and no ordinary user workflow requires understanding module/cache internals. Named suite: [tests/acceptance/hardening/](../tests/acceptance/hardening/).

### U2 — First-run & operability — [x] done

| Track | Status | Intent |
|-------|--------|--------|
| **U2 First-run & operability** | [x] | Setup path, sample notebook, model guidance, doctor/diagnostics in UI, first-run docs path |

Detail: [Path to 0.9.0 — Track A](#track-a--u2-product-required-for-090) · [usability_wave_plan.md](usability_wave_plan.md) §6. **Shipped:** Home (Create / Import / **Open sample**), Diagnostics, `samples/demo-notebook/`, first-run install docs.

### U3 — Daily workbench — [x] done

| Track | Status | Intent |
|-------|--------|--------|
| **U3 Daily workbench** | [x] | Review as needs-attention queue, Reading mode, Search/Library filter parity, organisation polish, model/runtime product copy — **without** requiring bulk corpus activation |

**Also landed with U3:** Library activity-bin click filter; Library cover-grid paging (`ui.archive_notebooks_initial`, default show-all); page delete in the viewer; model-information expander wired to live picker selection on Transcribe panels.

**Post-U3 deepen-in-place (shipped, not a new wave track):** OCR hang / model-load fail-fast circuits; Compare OCR attempt previews escape markdown so Prefer/Promote stays readable; Analyse Moments jump-to-page; Overview/Mood this-vs-corpus/period charts (PR #25). **OCR Review workbench:** scan + tabbed review lanes (Transcription / Date / Tags / OCR / Cleanup / Other), disagreement-centric review, merged draft as recommendation not vote ([ocr_review_workbench_plan.md](dev/ocr_review_workbench_plan.md)).

### U4 — Corpus UX — [x] gate green (Inbox polish may continue)

Bulk inbox / import recovery is **supported**. The [corpus-integrity acceptance gate](contracts/corpus-integrity.md#acceptance-gate) is green. See usability-wave **U4** and [Shipped — Notebook corpus](#shipped--notebook-corpus--bulk-import--x). Remaining Inbox polish (e.g. richer needs-review taxonomy / `TRANSCRIBE_INBOX_DIR` scan) may continue without reopening the gate.

**Ignore pages — shipped:** mark/unmark in Review; Reader omits ignored by default (`ui.hide_ignored_pages`) with **Show ignored** override; export **Exclude ignored pages** (default on) for reading formats; JSON keeps the full notebook. **Future:** include/exclude export pages by tag (AND filter, same semantics as Reading/Library).

---

## Next — 0.9 Infrastructure wave — [x] done (I0–I6)

Detail lives in [Path to 0.9.0](#path-to-090--10) Track B and [infrastructure_wave_0_9_plan.md](infrastructure_wave_0_9_plan.md). Wave exit + U2 enable the **0.9.0** cut. A stranger-testing round is not an I7 track and not a release gate. **I0–I6** are done.

---

## Next — Release / onboarding / operability — [x] done (via U2)

Committed under [usability_wave_plan.md](usability_wave_plan.md) **U2** — **required for the 0.9.0 cut**:

- **Shipped:** Home (Create / Import / **Open sample** + Ollama health), System → Diagnostics, sample notebook (U2.2), first-run install docs path (U2.4)

Longevity **minimum for testers** (pre-upgrade backup + restore verify copy) is on the 0.9 path foundation checklist above. Full “archive readable without Transcribe” stays a lifecycle candidate.

---

## Shipped programmes

Capability already on `main`. Kept here so “Next” is not polluted with done work. Do not reopen as new waves.

### Shipped — Notebook corpus / bulk import — [x]

**Bulk-import generation** is **runtime-normative**: corpus index, ImportPlan/ImportRun, duplicate policy, orchestrator, doctor, CLI, and Inbox UI. Runtime stays compatible with `transcribe.project` v1 notebooks that lack corpus registration. Acceptance suite: [tests/acceptance/corpus/](../tests/acceptance/corpus/).

| Gate | Authority |
|------|-----------|
| Corpus identity, index, locks | [contracts/notebook-corpus.md](contracts/notebook-corpus.md) |
| Managed originals / duplicates | [contracts/source-asset.md](contracts/source-asset.md) |
| ImportRun / plan / resume | [contracts/import-run.md](contracts/import-run.md) |
| Doctor + executable acceptance suite | [contracts/corpus-integrity.md](contracts/corpus-integrity.md) |

**Shipped:** corpus index registration + discovery, ImportPlan/ImportRun orchestrator with crash hooks, `skip_existing_v1` / `create_duplicate_v1`, folder adapters, CLI `bulk-import` / `bulk-run` / `corpus-doctor`, **Workflow → Import → Batch** (legacy Inbox alias), **Workflow → Transcribe → Batch** (unified Import/Transcribe target switcher + batch OCR), live progress for import / batch OCR / transcribe jobs, corpus doctor ImportRun ID checks, and the synthetic multi-notebook acceptance suite (crash-injection, idempotency, duplicate policy, index rebuild, deep doctor, fixture coverage).

**Related product outcome:** import recovery / inbox as a daily workflow. Usability-wave **U4** gate mechanics are done; richer outcome taxonomy / inbox-dir scan remain optional polish.

### Shipped — OCR lifecycle package — [x]

Ambitious OCR features on the durable attempt model: multipass multi-model runs, compare/prefer/promote, composite candidates, preference stats, fine-tune export. Contracts: [ocr-multipass](contracts/ocr-multipass.md), [ocr-preference](contracts/ocr-preference.md), [finetune-export](contracts/finetune-export.md), extended [page-result](contracts/page-result.md). Outline for external training: [finetune_export.md](finetune_export.md). Shipped via [PR #15](https://github.com/glen-w/Transcribe/pull/15).

| Wave | Status | Outcome |
|------|--------|---------|
| **W0** | [x] | Prefer/promote APIs, `activate` flag, prefer modes, settings |
| **W1** | [x] | MultiPass orchestrator + CLI |
| **W2** | [x] | Rank + composite (text model) |
| **W3** | [x] | Compare/Prefer Review GUI + single-page re-run |
| **W4** | [x] | Preference ledger + pre-run hints |
| **W5** | [x] | Fine-tune export + docs |
| **Batch multipass** | [x] | Compare models over OcrBatchRun (UI + `bulk-run` multi `--model`) |
| **OCR fail-fast circuits** | [x] | Timeout circuit (3) + fatal model-load circuit (1) per frozen vision plan; multipass continues with remaining models |

### Shipped — Bulk run analysis (GUI) — [x]

Multi-notebook **Analyse → Batch**: same Target / selection modes as Transcribe Batch (`pending` | `import_run` | `pick`), one frozen Analyse plan applied sequentially per notebook. Orchestration only — not cross-notebook synthesis.

Delivery plan: [bulk_run_analysis_plan.md](archive/plans/bulk_run_analysis_plan.md). Contract: [contracts/analysis-batch-run.md](contracts/analysis-batch-run.md). Distinct from ROADMAP “Corpus-level Analyse” under later candidates.

| Slice | Status | Outcome |
|-------|--------|---------|
| **A0** Plan + pointers | [x] | Delivery plan (selection, dual-bar progress, test matrix, docs checklist) |
| **A1** Persistence + coordinator | [x] | `AnalysisBatchRun` + sequential coordinator + offline unit/selection/progress-mapper tests |
| **A2** GUI Target + live progress | [x] | Analyse This notebook \| Batch; same three sources; dual progress bars + stop + post-run summary |
| **A3** Handoffs + CLI + docs | [x] | CLI `bulk-analyse`; public surfaces / user guide / limitations |

### Shipped — Detection fine-tune export — [x]

Extend the shipped OCR **fine-tune export** pattern to **prompt-backed Detection**: export page images + effective text with **approved / rejected** finding labels as a local dataset for **external** detector fine-tuning (Transcribe does not train in-app).

Contracts: [finetune-export](contracts/finetune-export.md), [detection-finetune-export](contracts/detection-finetune-export.md), [finetune_export.md](finetune_export.md). CLI `export-detection-finetune` + Export UI tab.

| Outcome | Intent |
|---------|--------|
| **Review-labelled export** | Approved findings = positives; rejected = negatives/hard negatives; unreviewed excluded by default |
| **Finding-aware samples** | JSONL rows tie image + text window to span boundaries, `finding_type`, detector + prompt provenance, `review_status` |
| **Per-detector datasets** | Filter by `detector_id` / `finding_type`; same privacy model as OCR export — user copies the folder; no network upload |

### Shipped — Detection + Prompt Hub — [x]

Built-ins `poetry`, `todo_lists`, `lists`, `quotations`, `beer_labels`, lexical `first_person` / `swear_words`, `names` (people from NER) + declarative custom detectors; View → Detect; findings under `detection/`. Settings → Prompts hub for OCR, cleanup, and detection prompts. See [detection_wave2_plan.md](archive/plans/detection_wave2_plan.md) + detection contracts.

### Shipped — Preprocessing (visual declutter lane) — [x]

Two separate lanes. Do not conflate human-facing scan cleanup with OCR input transforms.

| Lane | Audience | Default | Intent |
|------|----------|---------|--------|
| **1. Visual declutter** | Human (reading / review of scans) | **On** for imports; global off-switch in settings | Clean up scanned page images for people. **Shipped:** `remove_scan_borders` + `remove_uniform_overscan` + `remove_corner_wedges` + `remove_binding_gutter` + `remove_edge_shadows` (Pillow, deterministic; grey/light-grey scanner beds, stark-white gutters, residual rounded-corner bed wedges, dark binding/lid strips, remaining edge-anchored shadows). Applies at **import** and via explicit **Re-apply visual declutter** (Settings → Configuration). Changing the setting alone does not rewrite notebooks. Render provenance records state, geometry, and declutter identity. |
| **2. OCR optimisation** | Vision model input | **Off** (`none`); opt-in | Transforms meant to help OCR. Shipped today: optional Pillow **`gentle_contrast`**. Further OCR preprocess profiles are **deferred**. |

**Rules of thumb**

- Visual declutter defaults help the common “dump of scans” path; power users can disable it workspace-wide (`ingest.visual_declutter_enabled`).
- OCR preprocess stays conservative and off-by-default so fingerprints / skip-resume stay predictable; expanding profiles is a deliberate product choice, not creep from declutter work.
- Declutter identity (`enabled` + `DECLUTTER_VERSION` + ordered ops + frozen detection params) is frozen into ingest journal / render provenance; crash recovery never pairs mismatched pixels and metadata. OCR invalidation follows the final active render SHA.
- Explicit declutter re-apply is shipped; OCR-optimisation reprocess remains opt-in / future. Defaults above are unchanged.

Lid slivers shipped in 1.2. Punch-hole margins and calibration stripes are package **1.5** (crop-only, outside the page).

### Shipped — Export / backup / tagging (highlights)

| Capability | Notes |
|------------|-------|
| **Export readability** | EPUB/PDF/HTML, 25 curated body fonts, export profiles, multi-notebook anthology (provenance via U0 #13), **exclude ignored pages** toggle. Candidate: user-uploaded custom fonts; future: include/exclude by tag |
| **Workspace backup / restore** | Full-workspace ZIP (`transcribe.workspace-backup` v1): create/verify/restore via CLI + Settings → Configuration → Backup; replace-only restore with automatic safety ZIP; corpus-doctor after restore ([workspace-backup.md](contracts/workspace-backup.md)) |
| **Tag catalogue** | Labels, colours, rename/merge; viewer click-to-filter; detection auto-tag ([tag-catalog.md](contracts/tag-catalog.md)) |

---

## Near-term candidates — not on the 0.9.0 path

Uncommitted deepen-in-place. May land before or after 1.0, but **must not** delay the **0.9.0** tag.

### Preprocessing expansion — [x] partial

**Visual declutter v4 — binding gutter + edge shadows — [x] shipped** (v5 lid slivers added in 1.2)

Stay outside the page: high-confidence, edge-anchored artefacts only — never alter pixels inside the detected page area. That keeps declutter distinct from document restoration (no bleed-through, whitening, stains, ruled lines, hole punching, creases, page-wide shadow fix, or handwritten-margin cleanup).

Shipped after scanner-bed borders + stark-white overscan + corner wedges: **binding gutter** → **edge shadows** → (1.2) **lid slivers** (thin uniform dark/coloured edge bands). **1.5** schedules punch-hole margins and calibration stripes, still crop-only and outside the page, with ruled notebooks skipping those ops.

### Corpus & product lifecycle — remaining rows — [?]

Primary direction for living with many notebooks. **U3** pulled Review UX, reading mode, search deepening, organisation polish, and model/runtime management. **U4** covers import recovery / inbox (gate green). Remaining rows stay uncommitted candidates.

| Outcome | Intent | Wave / status |
|---------|--------|---------------|
| **Search (first-class)** | Full-text across notebooks; date / tag / entity filters; jump-to-page; saved searches | **[x] done (1.2)** — U3 date/tag/jump; 1.2 published-NER entity filters + saved searches ([saved-searches](contracts/saved-searches.md)) |
| **Notebook organisation** | Titles, descriptions, tags/collections, archive state, sort order, cover/thumbnail | **[x] done (1.2)** — U3 tag chips + sort; 1.2 collections + archived state ([notebook-collections](contracts/notebook-collections.md)) |
| **Page reordering & date repair** | Drag/drop thumbnail grid to reorder after scan upload errors; “move suspiciously dated page to end of confirmed date cluster” | **[x] done** (1.1 W6–W7) |
| **Import recovery / inbox** | Continuations of bulk import as a daily workflow | **U4** (gate green; polish open) |
| **Reading mode** | Clean chronological in-app reading | **U3** (done) |
| **Backup / restore / portability** | Full-workspace ZIP | **[x] done** |
| **Data longevity / upgrades** | Migration UX, pre-upgrade backup, refusal/recovery, “archive remains readable without Transcribe” | **0.9 path (thin)** done; **1.2:** `verify-export` + `workspace-doctor`. **1.5:** per-notebook restore, longevity profile, upgrade check |
| **Model & runtime management** | Product abstraction over installed OCR/text models | **U3** (done) |
| **Quality / evaluation loop** | Sampled OCR accuracy review, cleanup accept/reject, analysis usefulness ratings, local regression fixtures | **[x] done (1.2)** — [quality-ratings](contracts/quality-ratings.md) + import→OCR smoke kit |
| **Quality ratings (thumbs)** | Collect-only local ratings | **[x] done (1.2)** — analysis `up`/`down` in the quality store (CLI) |
| **Ignore pages (Reader)** | Mark/unmark in Review; Reader hide-by-default + **Show ignored**; export exclude ignored | **[x] done** |
| **Detection fine-tune export** | Approved/rejected Detect labels → external training datasets | **[x] done** — see [Shipped — Detection fine-tune export](#shipped--detection-fine-tune-export--x) |
| **OCR cleanup quality** | Second-pass cleanup as a Review verdict, without a separate analysis module | **[x] done (1.3)** — [durable notebook](#now--135-the-durable-notebook) |
| **People & places / Patterns** | Places map shipped; Patterns tab only if usage justifies. A Person store is the on-file autobiography label, not package **1.3** | Places shipped; Patterns unscheduled |
| **Page scan fullscreen** | Click scan → black lightbox, with `st.image` hover toolbar as fallback | **[x] done (1.2)** — `ui/page_lightbox.py` island (JS safekeeping below is its source). Streamlit has no fullscreen API ([streamlit/streamlit/issues/8031](https://github.com/streamlit/streamlit/issues/8031)) |

<details>
<summary>Custom JS lightbox (source of the wired `ui/page_lightbox.py` island, kept for reference)</summary>

```javascript
(function () {
  const parent = window.parent;
  if (!parent) return;

  function ensureOverlay() {
    let overlay = parent.document.getElementById("tx-page-lightbox");
    if (overlay) return overlay;
    overlay = parent.document.createElement("div");
    overlay.id = "tx-page-lightbox";
    overlay.style.cssText = [
      "display:none", "position:fixed", "inset:0", "z-index:999999",
      "background:#000", "cursor:zoom-out", "align-items:center",
      "justify-content:center", "padding:1rem", "box-sizing:border-box",
    ].join(";");
    overlay.setAttribute("role", "dialog");
    overlay.setAttribute("aria-modal", "true");
    overlay.setAttribute("aria-label", "Page scan fullscreen");

    const img = parent.document.createElement("img");
    img.id = "tx-page-lightbox-img";
    img.style.cssText = [
      "max-width:100%", "max-height:100%", "object-fit:contain",
      "cursor:default", "user-select:none",
    ].join(";");
    img.addEventListener("click", (e) => e.stopPropagation());

    overlay.appendChild(img);
    overlay.addEventListener("click", () => {
      overlay.style.display = "none";
      img.removeAttribute("src");
    });
    parent.document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && overlay.style.display !== "none") {
        overlay.style.display = "none";
        img.removeAttribute("src");
      }
    });
    parent.document.body.appendChild(overlay);
    return overlay;
  }

  parent.txOpenPageLightbox = function (src) {
    const overlay = ensureOverlay();
    const img = parent.document.getElementById("tx-page-lightbox-img");
    img.src = src;
    overlay.style.display = "flex";
  };
})();

// Per-image bind (inject via components.html after st.image in a keyed container):
// root.querySelector('[data-testid="stImage"] img').addEventListener('click', (e) => {
//   e.preventDefault(); e.stopPropagation();
//   parent.txOpenPageLightbox(img.src);
// });
```

</details>

---

## Analysis surface

The roadmap’s analysis surface is largely complete. **U2 shipped.** The open product work is [The durable notebook](#now--135-the-durable-notebook) (correction, hand-model proof, corpus keep), not more analysis modules.

Architecture: verbatim-ish analytical cores plus thin notebook adapters over canonical `AnalysisDocument` units; durable analysis is project-local under optional `analysis/` ([project-on-disk](contracts/project-on-disk.md), [analysis-run-storage](contracts/analysis-run-storage.md)). Pins: [dev/analysis_port_pins.md](dev/analysis_port_pins.md).

### Shipped capabilities

| Capability | Shipped |
|------------|---------|
| **OCR lifecycle** | multipass compare, prefer/promote, composite, preference hints, fine-tune export; timeout + model-load fail-fast circuits |
| **Notebook metrics** | stats, lexical diversity, understandability |
| **Page ink / blankness** | Pillow coverage %, blankness %, dominant ink hue (Review + Analyse Overview; not a text Analyse module) |
| **Language** | NER, sentiment, epistemic markers, entity sentiment, keyphrases |
| **Themes** | wordclouds, topic modeling, BERTopic, semantic similarity, topic shift |
| **Mood & salience** | emotion family, affect tension, moments |
| **Synthesis** | highlights, summary, insights |
| **Optional local LLM** | summary, action items, Ask notebook, narrative summary |

Exact module IDs, dependency history, slices 1.1–1e.2, TX pins, and implementation gates: [analysis_wave1_plan.md](archive/plans/analysis_wave1_plan.md). Disposition and notebook reinterpret notes: [analysis_module_porting.md](dev/analysis_module_porting.md).

LLM modules are optional at runtime (local text Ollama); deterministic `highlights` → `summary` → `insights` work offline.

### Deferred analysis candidates — not scheduled — [−]

**Decision (2026-08-09):** Reinterpretation module work is **deferred**. Product focus is robustness and UX for the shipped core set (see **Now**). Need for these notebook reinterpretation outputs is unproven; do not schedule them while the usability wave’s open track (**U2**) is the priority — revisit only when product reopens the disposition map.

**`ocr_quality` deferred specifically:** a dedicated OCR-quality analysis module is not scheduled. Prefer improving transcribed text via the existing **second-pass LLM OCR cleanup / verification** path (and human review edits). Revisit only if cleanup + review leave a clear, user-facing quality gap that analysis (not OCR) should own.

| Module / target | Disposition | Notebook reinterpretation |
|-----------------|-------------|---------------------------|
| `politeness` | Reinterpret | → tone / formality |
| `echoes` | Reinterpret | → repeated ideas/phrases across pages or notebooks |
| `temporal_dynamics` | Reinterpret | → change through notebook chronology |
| `momentum` | Reinterpret | → density / idea-flow (not conversational flow) |
| `transcript_output` | Reinterpret | → clean notebook text / export |
| `simplified_transcript` | Reinterpret | → simplified / cleaned notebook text |
| `chart_descriptions` | Reinterpret | LLM descriptions once notebook charts exist |
| **`ocr_quality`** | **New (special case)** | Notebook analogue of TX `transcript_quality`, **not a port**. Deferred — not a substitute for OCR cleanup/verification. |

### Future analysis candidates — uncommitted

Worth considering only after hardening and any deliberate reopen of deferred rows. Several need a content-generic redesign or a new module identity. These are **not** planned work.

| Module / target | Notebook angle |
|-----------------|----------------|
| `tics` | Recurring phrases / habitual wording |
| `insight_eligibility` | Keep if made content-generic |
| `qa_analysis` | Self-posed questions and subsequent answers |
| `acts` | Note-type classification (observation / question / task / reflection) |
| `conversation_loops` | Recurring unresolved themes — implement **separately**; do not pretend it is the same module |

### Explicit non-goals / do-not-port

Intrinsically transcript-, speaker-, or audio-specific. Documented so they are not accidentally scheduled. Exhaustive module list: [analysis_module_porting.md](dev/analysis_module_porting.md).

| Family | Examples |
|--------|----------|
| **Speaker interaction** | `interactions`, `contagion` |
| **Audio / timing** | `pauses`, `voice_*` family, `prosody_dashboard` |
| **ASR-specific** | `transcript_quality` (notebook `ocr_quality` remains deferred above) |
| **Speaker-conditioned synthesis** | `llm_speaker_summary` |

### Product scope beyond analysis modules

Still the more central product surface than speculative analysis work:

- OCR pipeline — import, vision OCR, optional second-pass cleanup; multipass / prefer / promote / composite / fine-tune export (**shipped**); detection fine-tune export (**shipped**)
- Preprocessing — visual declutter vs OCR optimisation — see [Shipped — Preprocessing](#shipped--preprocessing-visual-declutter-lane--x-partial)
- Notebook corpus — bulk import supported; inbox polish optional
- Living with notebooks — organisation, search, reading, review (**U3** shipped)
- Longevity — workspace backup/restore **shipped**; broader archive-without-Transcribe remains candidate
- Operability — **U2** shipped; model/runtime management shipped with U3
- Maintainer infrastructure — I0–I6 shipped → **0.9.0** tag → **1.0**
- Autobiography — [on file](#after-10--notebook-anchored-autobiography-workbench----on-file), not this repo’s backlog ([scope lean](#scope-lean--24-sep-2026))

---

## Future metadata

- Page **time-of-day** metadata (from diary stamps like `YYMMDD HHMM` / similar): **scheduled 1.1** in the parked autobiography write-up (not 1.0). Storage alongside `ApproximateDate`, UI, archive indexing, and analysis policy. Date auto-extraction currently ignores time. AnalysisDocument unit `date` stays `YYYY-MM-DD` so fingerprints do not break.

---
## After 1.0 — Notebook-anchored autobiography workbench — [−] on file

**Status (lean 24 Sep 2026):** **on file for a future separate product.** Not planned, not gated, not Transcribe 1.1–2.0. Do not implement any of it in this repository. Do not delete it. Release numbers below (1.1–2.0) are labels from when this was the next Transcribe programme; they are not this repo’s version ladder. Authority for *that future product’s* sequencing, if it is ever started elsewhere. Does not define shipped schemas.

**Thesis:** Handwritten notebooks are the primary source material. Everything else becomes evidence, context, and memory around them. The system helps reconstruct a life from surviving evidence while preserving a clear distinction between what was actually recorded, what was extracted, and what the machine infers.

This is **not** a generic note-taking app, PKM system, or AI journal. The core object remains the scanned handwritten notebook page. The ambition is a **local-first augmented autobiography workbench** around that primary source.

```text
Primary sources (notebooks / pages)
        ↓
contextual sources (photos, chats, audio, mood, text)
        ↓
extracted knowledge (dates, NER, EXIF, people/places)
        ↓
relationships / Slices
        ↓
autobiographical interpretation (cited, never a substitute for the page)
```

**1.0 stays notebook-first.** Finish the [Path to 0.9.0 / 1.0](#path-to-090--10) (U2, I0–I6, foundation checklist). No WhatsApp, photo libraries, Slices, reconstruction, or time-of-day storage in 1.0.

### What to preserve

The current architecture is the right core. Post-1.0 **extends** it; it does not replace it.

- File-shaped system of record: `project.json`, managed `sources/`, renders, `results/<page_id>.json`. SQLite (`archive.sqlite`) stays a **disposable FTS cache** ([ARCHITECTURE.md](ARCHITECTURE.md), `ArchiveService`).
- UUID identities; never reconstruct IDs from paths ([notebook-corpus.md](contracts/notebook-corpus.md)).
- Import copies bytes; external path is provenance only ([source-asset.md](contracts/source-asset.md)).
- OCR attempts append-only; `edited_text` is user-owned ([page-result.md](contracts/page-result.md)).
- `ApproximateDate` plus `date_source` `extracted|inherited` vs `date_approved` ([domain dates](../src/transcribe/domain/dates.py)); human metadata protection in [notebook-corpus.md](contracts/notebook-corpus.md).
- Analysis evidence `{unit_id, quote, source_ref, content_fingerprint}` and stale-citation rules ([analysis-result.md](contracts/analysis-result.md)).
- Frozen `AnalysisDocument` v1 `source_ref` kinds `{page, page_span}` only ([analysis-document.md](contracts/analysis-document.md)). **Do not bump this schema to cite chats.**
- Detection `review_status` `unreviewed|approved|rejected` and review carry-forward ([detection-finding.md](contracts/detection-finding.md)).
- ImportRun `scan → plan → validate → commit` ([import-run.md](contracts/import-run.md)).
- Workspace backup packs authority, excludes `data/cache/` ([workspace-backup.md](contracts/workspace-backup.md)).
- Ask notebook (`llm_custom_qa`): grounded chunks, citations, **abstain** if unsupported.
- PageSpec IA, stay-don’t-bounce, jump-to-Reading, and the UI/core Streamlit boundary ([ARCHITECTURE.md](ARCHITECTURE.md) · `test_core_no_streamlit`). Grow Reading / Library / Search. **Working default:** Streamlit through 2.0 — do not assume a new frontend in 1.x. The **host** (Streamlit vs a later native/SPA client) is a reopenable decision, not a scheduled track — [UI host](#ui-host-working-default--reopen-with-evidence).

**Derived today, not durable domain objects:** People and Places are NER surface-form read-models (`PlacesService`). Mood → **Moments** is the `moments` salience module (quoted pages) — **not** autobiographical episodes. Analysis delivery “slices” in module registry are unrelated. Do not reuse those names for Slices / Person.

### Architectural constraints (do not violate)

- **Do not** extend `SourceDocument` / `PageIndex` to messages, CSV rows, or photos-as-pages. Contextual imports are a **sibling context corpus**, not notebooks.
- **Do not** make SQLite the system of record. Extend `archive.sqlite` as a rebuildable projection over notebooks **and** context records.
- **Do not** introduce a Personal Knowledge Graph database, a vector DB as **default** retrieval, live messenger APIs, or a generic “document” type. Opt-in Ask RAG (LanceDB extra) is the exception — it must stay off until `analysis.rag.enabled`.
- **Do not** change `AnalysisDocument` v1. Multi-source reconstruction uses a new `ReconstructionBundle` (name TBD).
- **Do not** rename Mood → Moments. Product **Slice** = confirmed life episode.
- **Do not** call into TranscriptX libraries. 1.6 imports TX **export files** only ([INTEGRATION_SEAM.md](INTEGRATION_SEAM.md)).
- Scale: one JSON file per WhatsApp message is the wrong shape (10^5 messages). Use collection manifests + JSONL shards + FTS. Photos stay file-per-original (like `sources/`).

### Domain model (intent — contracts later)

Absence of all new types remains a valid 1.0 workspace. `transcribe.project` schema_version **1** stays loadable without a context index (same rule as corpus index).

| Concept | Role |
|---------|------|
| **Notebook / Page / SourceAsset / OCRAttempt** | Unchanged primary-source stack |
| **ContextCollection** | One imported bundle (WhatsApp chat, Telegram JSON, photo folder, TX export, CSV). Stable `collection_id`. Not a notebook |
| **ContextRecord** | One message, photo, transcript segment, mood row, or journal entry. Stable `record_id`. Kind-specific raw payload; participants start as **strings** |
| **TemporalClaim** | Wraps `ApproximateDate`; adds instants, ranges, optional time-of-day. Do not replace page `ApproximateDate` |
| **Entity** | Durable Person (then Place): aliases, mentions, merge/split history, privacy. NER remains extracted until confirmed |
| **EvidenceLink** | `{from_ref, to_ref, relation, status, provenance}`. Relations start small: `same_day`, `near_date`, `depicts`, `participant`, `mentions`, `part_of_slice`, `same_bytes`. JSON/JSONL + rebuildable index — not a graph DB |
| **Slice** | User-owned (or user-confirmed) episode with heterogeneous members. Suggested slices never auto-promote |
| **ReconstructionBundle** | Run-scoped pack of cited records for a question. Not stored as autobiography |

**ClaimStatus** (internal; generalizes existing `date_approved` / detection review / `edited_text` — not a new six-layer ontology):

| Status | Existing analogue | Meaning |
|--------|-------------------|---------|
| `recorded` | SourceAsset bytes, export line, EXIF, CSV cell | Directly present in an artefact |
| `transcribed` | OCR `raw_text`, imported transcript | Machine or human rendering into text |
| `corrected` | `edited_text`, human-set dates | User-owned correction |
| `extracted` | NER, EXIF, `date_source: extracted` | Derived metadata |
| `suggested` | unapproved date, unreviewed detection | Machine proposal |
| `confirmed` | `date_approved`, detection `approved` | Explicit user confirmation |
| `rejected` | detection `rejected`, date ignore | Explicit user rejection |
| `interpreted` | LLM insights, reconstruction answers | Model narrative with citations |
| `speculative` | weak support / abstain-adjacent | Interpreted with weak evidence |

**Product chrome uses four layers:** Evidence · Extraction · Confirmation · Interpretation. Never show an interpretation as if it were a notebook page.

Identity: machine may **suggest** that “Anna” and “Anna W” match; only the user **confirms**. Support split after merge. Conflicting claims: store both; UI shows conflict; user may supersede without erasing. Exports are snapshots — re-import is a new collection version, not live sync.

User copy: say **notebook page** vs **imported evidence**. Avoid “Source” in new APIs (`SourceDocument` stays notebook originals).

### Ingestion architecture

Two families share the ImportRun **lifecycle**, not the notebook page schema:

```text
scan → plan → validate → commit
```

- **Family A — Notebook import** (existing): JPEG/PNG/PDF → SourceAsset → pages → renders → OCR.
- **Family B — Context import** (new from 1.2): adapters emit `ContextCollection` + `ContextRecord[]`. Preallocate IDs. Copy originals. Hash. Crash journal. Duplicate taxonomy by bytes (and platform+chat+native id when present).

Adapters land **one family per release**, not a plugin framework in 1.1:

| Adapter | Release | Notes |
|---------|---------|-------|
| `photo_folder` | 1.2 | EXIF dates; SHA-256 vs notebook sources (`same_bytes` link, not merge). No face recognition. Do not OCR via `JobCoordinator` |
| `whatsapp_export` | 1.4 | `_chat.txt` / zip; one collection per conversation; JSONL (+ monthly shards). **No chat-app UI** |
| `tabular_csv` / `plaintext_journal` | 1.5 | User column mapping; no Daylio schema |
| `telegram_json` | 1.6 | Native fields in raw payload. **Do not** coerce to WhatsApp shape. Shared **index projection** only (`kind, t, participants[], text, collection_id`) |
| `transcriptx_bundle` | 1.6 | TX export files: transcript required; audio optional; summary if present; speakers as strings. No ASR re-run, no TX package |

#### Future context import candidates — [?] uncommitted

Worth recording after the committed **1.2–1.6** sequence. Same Family B rules: user-provided **export files only** (no live APIs, scrapers, or OAuth sync); `ContextCollection` + `ContextRecord`; re-import = new snapshot; treat like chats/photos in backup sensitivity.

| Source | Typical export | Evidence role | Notes |
|--------|----------------|---------------|-------|
| **Spotify / Last.fm** | Spotify account data JSON (extended streaming history); Last.fm scrobble CSV or GDPR export | Music listened to near a page date | Timestamps → `TemporalClaim`; artist/track/album as record text. No streaming API or scrobble daemon |
| **Amazon purchases** | Order history CSV (“Download order reports”); GDPR/data-request bundle | Purchases as dated commercial activity | Order date, item title, category; likely extends `tabular_csv` or a thin dedicated adapter; strip or user-control shipping/payment fields |
| **Browser / search history** | Chrome/Firefox/Safari export; Google Takeout (Chrome history, My Activity) | Web pages and queries around dates | High volume — JSONL sharding like WhatsApp; URL, title, visit time, search query; among the most privacy-sensitive imports |
| **Google Maps Timeline** | Google Takeout Location History (JSON) | Visits, stays, movement | Complements NER **Places** (extracted mentions) with GPS-derived places; segment records with start/end; geocode policy unchanged (opt-in) |
| **Calendar** | `.ics` export; Google/Apple/Microsoft Takeout | Scheduled events around pages | Event title, time range, location string, attendees as strings → Person suggestions. **Not** a calendar product — evidence only (see non-goals) |

Evaluate after **1.6** (shared context index + doctor + backup) and **1.8** (Related evidence panel proves cross-source value). One adapter per release; no universal importer framework before three post-1.6 adapters ship.

On-disk sketch (absence valid). Recommend bulky originals in `TRANSCRIBE_CONTEXT_DIR` (sibling of projects); indexes under `data/context/`; both packed in backup; cache still excluded:

```text
{TRANSCRIBE_CONTEXT_DIR}/<collection_id>/
  collection.json
  originals/
  records.jsonl          # or monthly shards
data/context/
  context-index.json
  entities/people/
  entities/places/
  slices/
  links.jsonl
data/cache/archive.sqlite   # disposable; new records tables
```

Lock order: **corpus → context → notebook**. Never invert. `context-doctor` analogue of corpus-doctor.

### Retrieval (do not ship “chat with your journal”)

1. Structured filters (date window, notebook, collection kind, entity, Slice, tags) — extend `ArchiveFilters`
2. FTS on page effective text **and** record text (`record_kind` discriminator)
3. Link traversal (confirmed, then suggested `near_date`)
4. Deterministic aggregations (first/last mention, gaps, mood series)
5. Grounded LLM **only** on a ReconstructionBundle from (1–4); same abstain/citation contract as Ask notebook

Embeddings / vector DBs are **not** default 1.x retrieval. Archive Search stays SQLite FTS. In-notebook `semantic_similarity` is TF-IDF BoW. **Ask RAG** (`llm_rag_qa`) is an **opt-in extra** (`transcribe[rag]`, `analysis.rag.enabled=false`): a disposable per-notebook LanceDB index, not corpus Reconstruct. Compute `near_date` through 1.6; persist only user-confirmed links and Slice membership.

### Killer UX and Autobiography view

**1.8 — Life around a page:** Reading stays page-central (scan + effective text). A **Related evidence** panel lists same-day / nearby chats, photos, audio, mood, people, places, Slices, other pages. Wander: page → evidence → Slice → person → place → another page. Not a messaging UI. Cap lists (“14 messages” + sample 3). Empty state if no context imported.

**1.9 — Autobiography:** years → months → weeks → days → pages → evidence. Distinct from Library activity (the **notebook** diary timeline): show **gaps** (chats/photos without a notebook page, or the reverse); notebook activity as the spine; Slices as labeled bands, not calendar events; Evidence vs Interpretation layers. Not a streak calendar.

Stay on Streamlit `PageSpec`s through 2.0. If density becomes a wall, a narrow HTML/JS island is allowed (same pattern as Review hotkeys); a SPA or native rewrite is **post-2.0** unless the [UI host](#ui-host-working-default--reopen-with-evidence) questions are explicitly reopened with 1.8–1.9 evidence.

### UI host (working default — reopen with evidence)

Not a 1.x track. Do not block **1.0** or **1.1–1.7** on a frontend change. Streamlit remains the supported interactive surface ([public_surfaces.md](public_surfaces.md)).

**Working default through 2.0:** Streamlit `PageSpec`s; stay-don’t-bounce; jump-to-Reading; HTML/JS islands when density or interaction APIs fail (Review hotkeys already; page-scan lightbox is a near-term candidate). Core packages still must not import Streamlit. A React / Gradio / native rewrite stays in [Explicitly not to build yet](#explicitly-not-to-build-yet).

**Why this is a decision, not a freeze forever:** the GUI is a large Streamlit product on a clean service boundary (UI ~38k LOC, ~2k `st.` calls; services/CLI already share the kernel; `test_core_no_streamlit` holds). A fully custom native interface is **architecturally feasible** and **not a framework swap**: presentation, navigation state (`st.session_state` / rerun), CSS/DOM overlays, iframe hotkeys, and Altair/`st.map`/wordcloud islands would be reimplemented. Highest Streamlit friction today: **Review**, **Reading / page viewer**, **Library**. There is **no HTTP/IPC API** — UI calls services in-process. TranscriptX is also Streamlit; a Transcribe host change diverges presentation unless both products later share a frontend programme.

**Reopen when (any):** 1.8 Related evidence or 1.9 Autobiography is unusable even with an HTML island; Review/Reading interaction debt (keyboard, lightbox, split pane) blocks the autobiography UX; Docker `transcribe-web` and a future desktop shell cannot share one client. Do not reopen because another stack is fashionable.

**If reopened, decide in this order** (defaults until decided): [Open architectural questions](#open-architectural-questions) 8, 11–16. Sketch: evidence first → optional local API/IPC → one heavy surface (Review/Reading) as a strangler → Settings last. Full parity is a multi-year programme, not a release item.

### Releases (1.1–2.0)

Each release has one product purpose. Do not dump “2.0 everything.”

**These numerals are not package versions.** Package **1.0.0**, **1.0.1**, and **1.2.0** are already tagged. The live ladder is [The durable notebook](#now--135-the-durable-notebook): package **1.3** correct, **1.4** proof, **1.5** keep. A row below that shares a number (People, WhatsApp, CSV) is this parked product, not that package.

| Release | Purpose | Status |
|---------|---------|--------|
| **1.0** | Harden notebook/OCR/analysis (U2 + I0–I6 → **0.9.0** → freeze). No context corpus | [−] historical label; package **1.0.0** is tagged |
| **1.1** | Time around a page — related notebook pages by date window | [−] on file |
| **1.2** | Photographs as contextual evidence (proves sibling corpus) | [−] on file; not package **1.2.0** |
| **1.3** | People as confirmed identities (aliases, merge/split, privacy) | [−] on file; not package **1.3** |
| **1.4** | WhatsApp export as high-volume context | [−] on file; not package **1.4** |
| **1.5** | Mood / flexible CSV / plaintext journals | [−] on file; not package **1.5** |
| **1.6** | Telegram JSON + TranscriptX file import | [−] on file |
| **1.7** | Slices (user objects first; suggestions off by default) | [−] on file |
| **1.8** | Related-evidence panel on Reading (killer UX) | [−] on file |
| **1.9** | Autobiography view (grains + gaps) | [−] on file |
| **2.0** | Historical reconstruction — cited answers over a retrieved bundle | [−] on file |

#### 1.0 — Harden the notebook workbench (gate, not this programme)

**Product goal:** A trustworthy local notebook/OCR/analysis product a non-expert can install, transcribe, review, search, analyse, export, and back up.

**UX:** Finish U2 (sample notebook, first-run install path). I0–I6 → **0.9.0** cut. Inbox polish optional. A stranger-testing round is not a release gate.

**Architecture:** No new domain entities. Time-of-day waits for **1.1**. Foundation checklist on [Path to 0.9.0](#path-to-090--10) signed off.

**Risks:** Starting autobiography before the gate. Do not sneak WhatsApp into 1.0.

**Exit:** U2 acceptance; I0–I6 exit gate; 0.9.0 tagged; foundation checklist; PRODUCT still page-first; corpus/hardening gates green.

#### 1.1 — Time around a page (notebook-only)

**Product goal:** Answer “what else in my notebooks belongs with this page?” without new importers.

**UX:** Reading shows other pages in a date window (this notebook + corpus). Search/Library: tighter range; optional exclude unapproved dates; and a configurable ignore list so extracted dates from pages whose Detect categories match (e.g. label/packaging) are treated as `rejected`/unapproved by default. Add date-window presets (`same day`, `3 days`, `1 week`, `1 month`) and group related pages by temporal proximity (`same day`, `nearby`, `same week`). Allow previous/next **dated** page jumps across the corpus. Show date-source / confidence badges (explicit on page, inherited, manual correction) and a quick exact-only filter chip so inherited or weak dates can be hidden. Page **time-of-day** from diary stamps (`YYMMDD HHMM`) stored alongside `ApproximateDate`. Optional **estimated writing time** per page/notebook from OCR word count and a user-set average words-per-minute; label as approximate and allow workspace/user override. Entity filters on Search only if a cheap NER join exists; otherwise wait for 1.3.

**Architecture:** Additive page time on `PageIndex` (legacy = null). `ArchiveService.related_pages(page_id, window)` plus previous/next dated-page lookups over the same index. Date-source / confidence is a read-model over existing page date state (explicit extraction, inherited notebook date, manual review), not a new autobiography entity. Estimated writing duration is derived, not authored metadata: persist only the configured WPM setting and recompute from approved/current page text. Document ClaimStatus vocabulary in contracts (map existing date/detection/edit states). No `ContextCollection` yet. Relatedness is **computed**, not persisted links.

**Reuse:** `ApproximateDate`, ArchiveService, Reading, `view_jumps`, existing date review state.

**AI:** None. No LLM for relatedness.

**Storage / migration:** Additive `project.json` fields; AnalysisDocument dates stay `YYYY-MM-DD` (do not break fingerprints). Archive indexes rebuildable.

**Risks:** Turning Archive into a calendar. Over-linking inherited dates. Presenting unapproved dates as confirmed. Letting date-source badges imply more certainty than the underlying extraction/review state supports. Treating estimated writing time as exact despite OCR noise, edits, or non-prose pages.

**Exit:** Related-pages panel; window/precision tests; window presets and temporal grouping in Reading/Search; previous/next dated-page jumps; inherited/unapproved/ignored-by-category dates visually distinct with exact-only filter and source badges; estimated writing time clearly marked approximate and derived from configurable WPM; no context schema shipped.

#### 1.2 — Photographs as contextual evidence

**Product goal:** Dated photographs sit **beside** notebooks, not inside them.

**UX:** Import a photo folder (Workflow → Import Context, or a clearly named sibling — not “new notebook”). Reading: photos on/near the page date (EXIF or filename). Open original. Duplicate notice if SHA matches a notebook source. Copy that scans belong in notebook Import.

**Architecture:** `ContextCollection` + `ContextRecord` kind `photo`. `context-index.json`. EXIF → TemporalClaim `extracted`. EvidenceLink `same_bytes` / computed `near_date`. Archive `records` table. Backup packs context. Context lock; order corpus → context → notebook.

**Reuse:** ImportRun lifecycle, SourceAsset copy/hash/duplicate taxonomy.

**AI:** Deterministic EXIF. Optional on-demand VLM caption = `interpreted`. No auto face ID.

**Migration:** Workspaces without `data/context/` remain valid. Old backup ZIPs restore; new members additive.

**Risks:** Dumping notebook scans here. Fake pages. Running photo OCR through JobCoordinator.

**Exit:** Import/roundtrip/doctor; related photos on a dated page; SHA dedup vs notebooks; backup/restore with photos; 1.0 notebooks untouched.

#### 1.3 — People as confirmed identities

**Product goal:** “Anna” in a notebook can become a Person the user owns, without pretending NER was identity.

**UX:** Person profile: mentions, pages, dates, later photos/chats. Confirm/reject suggestions. Aliases. Merge/split. Privacy hide. Keep People & Places → People as the **extracted mention** layer. Place confirmation if it fits this release; otherwise Person-only and Place later.

**Architecture:** `data/context/entities/people/<id>.json`. Mentions → `page_id` / `record_id` + quote + fingerprint. NER rerun carry-forward (detection-review pattern). Suggested matches `status=suggested`.

**Reuse:** `PersonMention`, NER evidence, `entity_sentiment` as extracted tone, tag merge UX.

**AI:** Optional similarity suggestions. Deterministic exact-alias. User confirms. Never silent merge.

**Risks:** Auto-merge; social-graph product; contact sync; treating FAC as people.

**Exit:** Create person from mention; alias; refuse silent merge; profile → Reading; NER rerun preserves confirmations. Empty entity store = today’s People & Places → People.

#### 1.4 — WhatsApp as high-volume context

**Product goal:** Imported chats become dated evidence around notebook pages, not a messaging app.

**UX:** Import WhatsApp zip/folder; pick chats. Evidence counts (“14 messages with X, 11–13 Sep”). Open a **record card** (timestamp, sender, text, attachment name), not a bubble thread. Link senders to People as suggestions.

**Architecture:** `whatsapp_export` adapter. Collection per conversation. `records.jsonl` (+ monthly shards). Shared index projection for future Telegram. Participants as strings until linked.

**Provenance:** source file + byte/line range. Re-import = new snapshot. No live API.

**Storage:** JSONL + FTS. Original zip preserved. Missing attachments are gaps. Scale test: 100k synthetic messages, doctor, FTS rebuild budget.

**Risks:** Chat UI gravity; unifying with Telegram too early; importing into notebooks; backup size (document sensitivity like page images).

**Exit:** Parse fixture; evidence counts; jump to record; FTS; no thread view as primary.

#### 1.5 — Mood, CSV, and miscellaneous personal records

**Product goal:** Longitudinal mood and other dated text become context without a vendor lock-in.

**UX:** CSV import with column mapping (date/time, mood, notes, extras). Optional plaintext journal. Mood sparkline on the evidence panel. Generic records searchable.

**Architecture:** `tabular_csv` + `plaintext_journal`. Mapping stored on the collection; re-parse from original file + mapping. Do **not** auto-Analyse CSV as a notebook. Do not invent mood from handwriting modules here.

**Risks:** Quantified-self product; universal importer framework — these two adapters only.

**Exit:** Mapped CSV roundtrip; mood near a page; bad headers fail validate; original CSV preserved.

#### 1.6 — Telegram and TranscriptX imports

**Product goal:** Second messenger + spoken-life artefacts; adapters may differ internally.

**UX:** Telegram Desktop JSON (selected chats). TranscriptX bundle: transcript required; audio optional; summary if present. Evidence: “Audio, 13 Sep” → transcript card → optional audio file — not a TX clone.

**Architecture:** `telegram.message` keeps native ids, edits, service messages. `transcriptx.segment` (or document + cues). Speakers as strings → Person suggestions. Still no TX runtime. If TX 1.0 export contract is late, pin a frozen fixture adapter.

**AI:** Do not re-transcribe. Optional on-demand summary only if TX summary absent — labeled `interpreted`.

**Risks:** Porting TX speaker/audio modules; audio-first drift; dual-write with live TX.

**Exit:** Telegram fixture ≠ WhatsApp schema; TX import without TX package; speakers suggest people; audio optional; doctor.

#### 1.7 — Slices

**Product goal:** Name a period of life and hang heterogeneous evidence on it.

**UX:** Create Slice “Moving to Paris”; add pages 143–157, chats, photos, people. Slice view = member timeline. From a page: “Add to Slice.” Machine suggestions off by default; never auto-create.

**Architecture:** One JSON per slice under `data/context/slices/`. Links `part_of_slice`. Suggestion job frozen like Analyse; cannot publish without confirm. Do **not** run the 25 notebook modules on a Slice as a fake project.

**Risks:** Auto-biography chapters; PKM maps; renaming Mood → Moments.

**Exit:** CRUD Slice; mixed-kind members; Reading shows Slice chips; suggestions cannot publish without confirm.

#### 1.8 — Life around a page (killer UX)

**Product goal:** Wander a life from a handwritten page using everything ingested so far.

**UX:** Page image + text central; Related evidence beside/under. Honest empty states. Distinguish confirmed vs suggested vs interpreted.

**Architecture:** `EvidencePanelService` read-model over Archive + links. Precomputed `near_date` index in sqlite; bump `archive.generation`. No new system of record.

**AI:** None required. Optional panel summary waits for 2.0.

**Risks:** Clutter; Streamlit rerun lag; replacing the scan. Density here is the first honest test of the Streamlit host — prefer an HTML island over a frontend rewrite ([UI host](#ui-host-working-default--reopen-with-evidence) question 8).

**Exit:** Fixture workspace (notebook + photos + WhatsApp); jumps work; layer honesty.

#### 1.9 — Autobiography view

**Product goal:** Navigate life at year/month/week/day with the notebook as spine, including gaps.

**UX:** New primary nav **Autobiography**. Not an Archive clone. Settings for which layers show.

**Architecture:** Aggregations over archive sqlite. Gap = interval with context but no dated notebook page (or vice versa).

**AI:** None on the canvas. Optional interpreted captions behind a toggle, cited.

**Risks:** Calendar product; streak gamification; hiding notebooks behind chats. Grain navigation may stress Streamlit density the same way 1.8 does — HTML island allowed; do not use 1.9 to justify a SPA.

**Exit:** Grain navigation; gap visibility; click to page/Slice/person; notebooks-only still works (other layers empty).

#### 2.0 — Historical reconstruction

**Product goal:** Ask reconstruction questions and get **cited** answers that lead back to pages, messages, photos, transcripts, mood rows.

**UX:** **Reconstruct** (name TBD) — does **not** replace Ask notebook (single-notebook grounded QA). Question → retrieved bundle → answer with layer tags and clickable citations. Abstain if weak. Show conflicting sources.

Example questions (retrieve evidence, then optionally interpret): What was happening around this entry? When did I first think about moving to Paris? What did I repeatedly worry about? How did my relationship with X change? What themes recur? What changed between 2018 and 2024?

**Architecture:** ReconstructionBundle builder (filters + FTS + links + Slice). LLM answers **only from the bundle**; JSON claims `{text, refs[], status}`. New coordinator; do not clobber notebooks; **do not** change `AnalysisDocument` v1. Hard cap bundle size. No tool-calling over the whole disk.

**Reuse:** `llm_custom_qa` abstain/cite, chunking, AnalysisCoordinator, `OllamaTextClient`.

**Storage:** Reconstruction runs are derived. Default backup: user-confirmed notes only, not raw runs.

**Risks:** Chatbot gravity; hallucinated life; embeddings-as-magic; prompt-stuffing the corpus.

**Exit:** Gold citation fixtures; abstain test; conflict display; Ask notebook still works; AnalysisDocument v1 unchanged; PRODUCT thesis still true.

### Cross-cutting infrastructure

- Format registry: add formats in `src/transcribe/persistence/schema.py` when each release ships
- CLI: `context-import`, `context-doctor`; UI and CLI share services; core still must not import Streamlit
- Privacy: remote-Ollama ack unchanged; geocode stays opt-in; reconstruction sends **retrieved text** to local LLM only; backups containing chats/photos are sensitive (same honesty as page images)
- Reprocessing: parse frozen in collection; re-parse explicit; entity/Slice confirmations carry forward
- IDs: UUID hex; never path-derived
- Export `transcribe.notebook` stays **notebook-only** through 2.0 unless a separate autobiography export is designed later
- Streamlit IA: add `PageSpec`s slowly; stay-don’t-bounce preserved. Treat PageSpec, interface-menus, action IDs, and workspace settings as **host-agnostic contracts**; do not encode `st.session_state` keys or CSS `:has()` overlays as product rules. Host change is a reopenable decision — [UI host](#ui-host-working-default--reopen-with-evidence)

### Testing strategy

Contracts first, then unit parsers, then acceptance (mirror [tests/acceptance/corpus/](../tests/acceptance/corpus/)).

- **1.1:** date window / precision / unapproved honesty
- **1.2–1.6:** synthetic fixtures (WhatsApp, Telegram JSON, CSV, photo EXIF, fake TX bundle); plan/commit/idempotency/crash
- **Scale:** 100k-message FTS rebuild budget, offline
- **1.3:** merge/split/carry-forward (mirror detection review tests)
- **1.7:** Slice membership; suggestions cannot publish
- **1.8–1.9:** UI contract tests (copy, jumps)
- **2.0:** gold citations + abstain; fake Ollama; stale fingerprint citations

No live WhatsApp/Telegram/Ollama in default CI. Doctor deep-hash originals. Backup gate extended.

### Explicitly not to build yet

- Universal PKM / Zettelkasten / knowledge-graph DB
- Live WhatsApp / Telegram / email APIs or scrapers
- Chat-with-your-life as the home screen
- Face recognition / biometric identity / automatic identity merge
- Vector DB as default retrieval; SQLite as authority; task-queue worker fleet
- React / Gradio / native rewrite as a 1.x or 2.0 delivery item (Streamlit through 2.0 is the working default; reopen only via [UI host](#ui-host-working-default--reopen-with-evidence), not because another stack is fashionable)
- Treating photos/chats as notebook pages
- Porting TX speaker/audio modules (`interactions`, `pauses`, `voice_*`)
- Cloud OCR/sync; multi-user social graph
- Calendar **app** or quantified-self **dashboards** as the product (importing calendar **exports** as dated evidence is a separate candidate — [Future context import candidates](#future-context-import-candidates--uncommitted))
- Deferred analysis ports (`politeness`, `echoes`, …) disguised as autobiography
- Universal plugin importer before three adapters exist
- Schema bump of `AnalysisDocument` v1 for messages

### Implementation order

1. Finish **1.0** via [Path to 0.9.0 / 1.0](#path-to-090--10). Freeze notebook core.
2. Contracts for ClaimStatus + TemporalClaim + context-index **before** photo code (1.1–1.2).
3. **1.1** related pages → **1.2** photos → **1.3** people → **1.4** WhatsApp → **1.5** CSV/mood → **1.6** Telegram + TX → **1.7** Slices → **1.8** evidence panel → **1.9** Autobiography → **2.0** reconstruction (LLM last).

Do not parallelize 1.2 schema with 1.4 parsers until context-index / doctor / backup exist.

### Open architectural questions

Defaults for implementers; revisit with evidence:

1. Context binaries in `TRANSCRIBE_CONTEXT_DIR` vs under `data/` — recommend sibling + `data/context/` index.
2. Persist `near_date` links vs compute-only — compute through 1.6.
3. Place entities in 1.3 vs later — Person in 1.3; Place if it fits.
4. Thread view — never primary; optional debug expander.
5. Reconstruction runs in backup — confirmed notes only.
6. TX export pin — frozen fixture if TX 1.0 is late.
7. Time-of-day in 1.0 vs 1.1 — **1.1**.
8. Streamlit density at 1.8 — HTML island allowed; SPA not. **Reopen after 1.8/1.9** if Related evidence or Autobiography is unusable even with an island. Options then: more islands vs extract a local API + one heavy surface (Review/Reading) vs a host change. SPA remains post-2.0 unless this question is explicitly reopened.
9. Conflicts — show both; supersede, don’t erase.
10. If users dump notebook scans as “photos,” offer **promote photo → notebook page** rather than collapsing models.
11. **Local API / IPC before a second UI?** UI and CLI call services in-process today. A SPA, Tauri, or other out-of-process client needs a contract (notebook/corpus listing, page read/update, job start/stop/progress, analysis health, settings). Default: **no API** until a host change is decided. If extracted, UI and CLI should share it; do not invent OCR/persistence rules in the client.
12. **If a second UI is warranted, which host?** Local web SPA (optional Tauri/Electron shell) vs in-process desktop (Qt/PySide) vs another Python web stack. Gradio is not a workbench replacement. Drivers: Docker `transcribe-web` needs a web client; Qt-only splits desktop vs container; NiceGUI/Flet/Reflex are unlikely to beat Streamlit enough to justify a rewrite. TranscriptX stays Streamlit — a Transcribe host change diverges presentation unless both later share a frontend programme.
13. **Strangler vs cutover.** If migrating, phase by user pain (Review → Reading/page viewer → Library → Transcribe/Analyse launchers + progress → analysis consume → Settings last). Keep Streamlit for Settings/Diagnostics until parity. Do not dual-run two full GUIs without freezing Streamlit feature scope. Full parity is multi-year, not a release row.
14. **Docker `transcribe-web` vs desktop-only.** Streamlit-in-container is the supported web surface. A Qt-only Review tool is a slice, not a replacement, unless a web client exists for Compose.
15. **Host-agnostic vs Streamlit accident.** Portable: PageSpec IA and gating, `interface-menus`, action IDs, workspace settings, tagging kernel, review alignment / composite / places / analysis display helpers. Not portable: scattered `st.session_state` keys, CSS `:has()` cover overlays, iframe parent-document hotkeys, Altair/`st.map` wiring. A second UI must re-specify navigation state (today: `ui_mode`, `root`, page-viewer overlay, review buffers) — there is no central state object.
16. **Are Review/Reading JS islands enough through 2.0?** Prefer islands (lightbox, shortcuts, Related evidence density) over a host change until 1.8 evidence. Click-to-fullscreen is already a near-term candidate (Streamlit has no API; custom JS safekeeping in this file). Reopen 8 + 16 together if islands accumulate into an unofficial SPA.


## Later — Architecture follow-ups from evidence review — [?] candidates

Not on the critical path to the **0.9.0** tag (U2 + I0–I6 already landed). Evidence, blast radius, and “do not replace JSON-on-disk / add an event bus / split CLI vs UI services” live in [architecture_from_evidence.md](reviews/architecture_from_evidence.md) (2026-09-03).

**Already done from that review (do not re-open as new work):** L1 CLI `transcribe run` exits 1 on `circuit_open` (job record stays `completed`); cancel / “Completed with gaps” chrome; detection `reconcile_interrupted` no-ops while the OCR **or** analysis lock is held; snapshot mappers in `ui/progress_snapshots.py`; **L3** published-NER-only names detector; **P1** cleanup soft-failure fingerprint; **Confirms** before Reset settings / Re-apply declutter. Do **not** add a `completed_partial` job status without a schema and test plan — coordinators keep `completed` + `circuit_open`.

| ID | Outcome | Review | Notes |
|----|---------|--------|-------|
| **L2** | `ProjectService.load` is a read by default; reconcile interrupted attempts is an explicit reopen path | P2 #3, L2 | **[x] done (1.2)** — `load()` defaults to `reconcile=False`; `reconcile_interrupted()` / deliberate `reconcile=True` at notebook-open and run-freeze are the explicit reopen paths. |
| **L3** | Names / people detector consumes **published** NER only — no nested `AnalysisRunner.run_module("ner")` | P2 #4, L3 | **[x] done** — Detect returns `unavailable_dependency` when NER is missing/stale. |
| **L4** | One schema registry for every written `format` (including job-record, settings, profiles, interface-menus) | P2 #7, L4 | **[x] done** — `SUPPORTED` lists settings, profile, job-record, interface-menus, geocode-cache. Settings/profile still load via `ConfigError`; interface-menus on-disk files may omit `format`. |
| **P1 leftover** | Cleanup LLM failure must not seal cleanup into the OCR skip fingerprint while the page keeps raw text | P1 #2 | **[x] done** — `cleanup_fingerprint_for_attempt` omits cleanup on `provider_failed`. |
| **P2 split** | Split `ProjectService` along SoT I/O vs review / dates / declutter / reconcile | P2 #6 | **[x] done** — dates / review-repair / declutter collaborators; `load()` remains the public API. |
| **Detect cancel** | Detect can be stopped like OCR/Analyse | P3 | **[x] done** — `DetectionRunCoordinator` + Stop after current window. |
| **Confirms** | Confirm before Reset whole workspace settings and Re-apply visual declutter | P3 | **[x] done** — Settings confirmation step before both actions. |
| **Cover Open** | Library cover Open is a visible control | P3 | **[x] done** — labelled Open under the thumb (`tx_open_cover_*`); click-on-image overlay stays transparent. |
| **Dirty leave** | Review dirty-leave does not require a second Prev/Next to discard | P3 | **[x] done** — Stay / Discard & leave (`rw_pending_leave`). |
| **Auto-tag** | Re-running auto-tag does not re-apply slugs the user removed | P3 | **[x] done** — `PageIndex.suppressed_auto_tags`; explicit Apply may clear. |
| **Chart palettes** | Config chart-colour defaults do not import `transcribe.ui` | residual | **[x] done** — defaults live in `config.chart_colors`; `ChartColorsConfig` no longer imports `ui`. |

Leave `effective_text()` as the integration bus, session-only routing, and on-disk `completed` + `circuit_open` unless a later review reopens them with evidence.

---

## Later candidates — uncommitted — [?]

Worth recording without scheduling. Rows that used to point at the autobiography programme are marked. That programme is [on file](#after-10--notebook-anchored-autobiography-workbench----on-file), not this repo’s backlog.

- Cross-notebook links / related pages — **scheduled 1.1** (notebook date windows; computed, not a graph)
- **Context import candidates (post-1.6)** — Spotify/Last.fm exports, Amazon purchase history, browser/search history, Google Maps Timeline, calendar exports — [Future context import candidates](#future-context-import-candidates--uncommitted) in After 1.0
- Corpus-level Analyse / search (cross-notebook products — **not** Bulk Analyse orchestration above). **2.0 reconstruction** is retrieved-evidence QA, not a cross-notebook Analyse runner; a corpus Analyse product remains uncommitted
- Bookmarks / favourites — **pulled into package 1.5** as continue-reading pins (one page each, not Slices)
- Annotations distinct from OCR corrections — **package 1.3** is one page gloss; character spans stay unscheduled (see [Recorded, not scheduled](#recorded-not-scheduled--))
- Batch metadata editing — **package 1.3**
- Image-only / non-OCR page handling — **package 1.3** kept scan (`page_role`)
- **Detection fine-tune export** — shipped (approved/rejected Detect labels → external training datasets)
- **Custom / native UI host** (SPA, Tauri, Qt, …) — uncommitted; not a 1.x track. Working default is Streamlit through 2.0. Reopen only with 1.8–1.9 evidence via [UI host](#ui-host-working-default--reopen-with-evidence); do not schedule a rewrite from this list.

---

## Decision log (scope & sequencing)

| When | Decision | Supersedes |
|------|----------|------------|
| 2026-08-09 | Defer reinterpretation analysis modules; focus usability on shipped core | Scheduling `politeness` / `echoes` / … as next ports |
| 2026-08–09 | Usability wave (U0–U4) is the active product focus after core modules | Analysis-wave expansion as default next work |
| 2026-09 | 0.9 infrastructure wave (I0–I6) runs parallel with U2; both required for 0.9.0 | Serializing product usability behind CI scaffolding |
| 2026-09-03 | Architecture evidence review: land L1 + lock reconcile; park L2–L4 / P3 as candidates | Opportunistic refactors without evidence |
| 2026-09-04 | 0.8.8: I5 Pages + Docker-preferred first-run docs framing | Host/Python as the only documented path |
| 24 Sep 2026 | **Scope lean:** product stops at notebook workbench; autobiography on file for a future separate product | “After 1.0 Transcribe becomes autobiography” as this repo’s ladder |
| 2026-09+ | Stranger-testing is **not** a release gate | Stranger-testing as I7 / path-to-1.0 step |
| Expansion wave (#47) | U2.2/U2.4, ignore-pages Reader, detection fine-tune export, I6 landed | Treating those as open 0.9.0 blockers |
| 2026-11-02 | **1.1 deepen-in-place** is the active product focus after 1.0.1; Track C signed off as already met on 1.0.0; 0.9.0/1.0 path is historical | Stale active-backlog ranks 1–2 (0.9.0 cut / Track C as open) |
| 2026-11-02 | **1.2 expansion & hardening** (balanced-max, one release): H1–H4 hardening + E1–E5 expansion on shipped surfaces only; L2 landed; package **1.2.0** | Treating saved searches / collections / quality loop / declutter v5 as uncommitted candidates |
| 2026-11-02 | **1.3.0 durability & OCR truth** is the notebook-workbench release after 1.2.0. It is not the parked autobiography “1.3 People” row | Scheduling Person identities as Transcribe 1.3 |
| 2026-11-02 | **1.3–1.5 The durable notebook** is the active horizon after 1.2.0: correct, prove an external hand model, keep the corpus. Package 1.3 is not the on-file “People” label | An empty backlog, and reading autobiography 1.3–1.5 as this repo’s next tags |
| 2026-11-03 | **1.3 correct W1–W8 implemented** (cleanup verdict, divergence banner, miss desk, kept scan, unsure/gloss, confirmed spellings, batch-meta). Stretch included (gloss export, cleanup-hint). No version bump/tag until an explicit release request. Next open: 1.4 shelf | Treating W1–W8 as still the ranked Now backlog |

