# Changelog

All notable changes to Transcribe will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- Roadmap: **Now** is [1.3–1.5 The durable notebook](docs/dev/durable_notebook_1_3.md) (correction practice, a shelf that scores an external hand model, per-notebook restore). Package **1.2.0** stays the shipped release. Autobiography’s old 1.3–1.5 labels are not these package numbers.

## [1.3.0] - 2026-11-02

Durability and OCR truth ([docs/dev/expansion_hardening_wave_1_3.md](docs/dev/expansion_hardening_wave_1_3.md)). This package version is the notebook workbench after 1.2.0. It is not the parked autobiography “People” row.

### Added

- **Restore one notebook:** `transcribe backup restore-notebook` extracts a single notebook from a workspace ZIP (`--dry-run`, `--force` replaces that folder only). A failure before rename leaves the live folder in place.
- **Archive hot path:** TTL refresh skips `ProjectService.load` when a stat-only signature still matches. Nightly scale lane adds a 100×40 budget; the smaller fixture stays on the PR suite.
- **Format census** in `workspace-doctor`: unknown formats and schema versions are reported and left untouched. There is still no migrator.
- **Job outcome read-model:** `completed` plus `circuit_open` is reported as completed-with-gaps. On-disk status stays `completed`. `transcribe run --retry-failed` schedules failed, interrupted, and empty-output pages only.
- **Correction scoreboard:** `transcribe quality scoreboard` and Diagnostics score succeeded readings against human corrections. Local only.
- **Review cleanup judgement:** accept or reject writes the existing cleanup quality rating and does not delete the attempt.
- **Reading marks:** per-notebook bookmarks and marginal notes (`transcribe.reading-marks`). They do not enter the transcription. Search can filter bookmarked pages.
- **Do-not-OCR pages:** optional `ocr_policy: skip`. Those pages are not scheduled and their export text is the marginal note, not OCR.
- **Batch metadata:** `transcribe pages batch` dry-runs unless `--apply` (approve dates, ignore, unignore, add or remove a tag). Empty selections are refused.
- **Declutter v6:** punch-hole margins and scanner calibration stripes, still outside the page interior.

## [1.2.0] - 2026-11-02

Expansion & hardening wave ([docs/dev/expansion_hardening_wave_1_2.md](docs/dev/expansion_hardening_wave_1_2.md)): balanced-max hardening (H1–H4) and expansion (E1–E5) on shipped surfaces, folding in the 1.1 deepen waves below. No separate 1.1.0 tag was cut.

### Added

- **Search first-class:** published-NER People/Places filters in Library and Search (`ArchiveFilters.people`/`places`, archive `entities_json`), and **saved searches** (`transcribe.saved-searches`; Search expander, `transcribe saved-search`, `transcribe search --saved`).
- **Notebook collections & archived state** (`transcribe.notebook-collections`): Library Collections manager, archive/unarchive (hidden by default, never deleted, always in backup), collection + archived filters, Export anthology by collection (`--collection`).
- **Export by tag:** reading-format include (AND) / exclude (any) page-tag filters in Export panel and CLI (`--include-tag` / `--exclude-tag`); notebook JSON keeps every page. Custom body fonts (`custom:<Family>`, `register_custom_font`, `--custom-font`).
- **Quality & evaluation loop** (`transcribe.quality-ratings`, all local): sampled OCR ratings auto-recorded on first Review correction (with character error rate), cleanup/analysis ratings via `transcribe quality`, Diagnostics quality summary, deterministic page sampling.
- **Import → OCR smoke kit** implemented (`tests/acceptance/ocr_lifecycle/test_import_ocr_smoke_kit.py`, stub vision, no GPU): human corrections survive re-OCR; whitespace output is an `empty_output` miss.
- **Diagnostics job timeline:** validated OCR/Analyse/Detect run records per notebook (record id = correlation id; malformed records shown as invalid, never trusted).
- **Scale lane:** synthetic 25-notebook / 500-page Archive budgets (`make test-scale`, nightly `scale` marker).
- **Longevity:** `transcribe verify-export <dir>` proves an export is readable standalone (manifest, checksums, revision stamps, EPUB/PDF sanity); `transcribe workspace-doctor` sweeps corpus + every notebook.
- **Declutter v5:** `remove_lid_slivers` crops thin (4–15 px) uniform dark/coloured edge slivers below the normal min band (`DECLUTTER_VERSION` 5).
- **Page-scan lightbox:** click a large scan in Reading/Review for a black fullscreen overlay (Esc/click closes); `st.image` hover fullscreen remains the fallback.
- Supply chain: Dependabot (actions/pip/docker) and a nightly `pip-audit` + CycloneDX SBOM job.

### Changed

- **`ProjectService.load()` defaults to `reconcile=False`** (L2): loading is a read; interrupting orphaned runs is the explicit notebook-open path (`reconcile=True` / `reconcile_interrupted()`), used deliberately by the shell, Analysis freeze, and batch starts.
- Hardening: OCR jobs fail before scheduling when free disk is below the shared headroom (`DiskFullError`); the native UI refuses an unacknowledged non-loopback bind (`TRANSCRIBE_ALLOW_LAN=1` opts in); Diagnostics output is redacted for credentials and workspace roots.
- The narrow-gutter declutter case that used to no-op below the min band now crops as a v5 lid sliver.

### Added (1.1 deepen waves, previously Unreleased)

- **Workflow tour** ([docs/workflows.md](docs/workflows.md)): 20 screenshots and two short GIFs (a review pass; repairing an out-of-order page) of the real UI on an invented sample notebook, linked from the README, user guide, first-notebook guide, and the landing page. Regenerate with `make docs-media` (`scripts/docs/capture_docs_media.py`; Playwright, no real pages, no OCR). `tests/unit/test_docs_media.py` guards image links, orphans, and size budgets.
- Tracked-binary allowlist accepts `[[globs]]` entries (`docs/images/*`, `website/images/*`).
- Import-run contract documents the outcome buckets; TERMS gains notebook order, date cluster, and outcome buckets.

### Fixed

- The global stylesheet was sent once per session, but Streamlit drops elements a rerun does not re-emit, so after the first click the sidebar lost its styling and the Library cover showed two **Open** buttons. It is now re-sent each run (`inject_global_styles`).
- Thumbnails showed the drag-and-drop bridge field (raw page ids) under the grid. It is now hidden; drag and the numbered Move controls are unchanged.
- Docs: Detect is under **Workflow**, not View; CLI table lists `pages`; Review lane, Cleanup (v4), page-order, Discard & leave, Detect Stop, inbox scan, and hand-model bring-back are described where users look for them.

### Changed

- GitHub repository display name is **Transcribe** (`glen-w/Transcribe`), matching the product name already used in the UI and docs. Python package, CLI (`transcribe` / `./transcribe.sh`), and Docker (`transcribe-web`) stay lowercase.
- Roadmap honesty: **Now** is [1.2 expansion & hardening](docs/dev/expansion_hardening_wave_1_2.md) (1.1 deepen W1–W9 folded in); 0.9.0 / 1.0 / Track C are signed off as landed.
- Library cover Open is a labelled control under the thumbnail. Review unsaved navigation uses Stay / Discard & leave instead of a second Prev/Next click.
- Auto-tag no longer re-applies slugs the user removed (`PageIndex.suppressed_auto_tags`). Explicit Apply can clear the tombstone.
- Standalone Detect can Stop after the current window (background coordinator, same cancel path Analyse already used).
- Import Batch shows imported / failed / duplicated / needs-review outcomes and can scan `TRANSCRIBE_INBOX_DIR`.
- Visual declutter v4 crops dark binding gutters and remaining edge shadows (Pillow insets only). Existing notebooks stay as stored until Re-apply / Cleanup.
- Notebook page order can be permuted (`transcribe pages reorder` / `move-to-date-cluster`) without renaming on-disk `page_index` directories. Review Other / Thumbnails expose Move up/down/to position; Date lane can move a regression to its date cluster.
- Fine-tune export README and Export tab spell out `ollama create` / recipe overlay / multipass verify. Training stays outside the app.

## [1.0.1] - 2026-11-02

### Added

- **Ask RAG** (opt-in): View → Ask mode Grounded / RAG / Both, Paperful-shaped LanceDB index + Ollama embeddings, workspace `analysis.rag.*` under Settings → Analysis. Default Ask stays grounded. Extra `transcribe[rag]`; Compose image installs it. CLI `transcribe rag ingest` ( `--library` / `--dry-run` / `--force`) warms indexes overnight without an Ask LLM call.
- OCR generate hardening from the 2026-10-23 overnight glm-ocr run: [docs/reviews/ocr_generate_failures.md](docs/reviews/ocr_generate_failures.md). Ollama `token repeat limit reached` is `token_repeat` (not retried). glm-ocr recipe overlays `repeat_penalty=1.2` without changing the prompt. Truncated output that also loops is failed. SIGINT persists `interrupted` and `POST /api/abort`. `name` / `name:latest` are the same model identity for skip.
- Granite vision recipe (`repeat_penalty=1.2`) and `repair_truncated_repetition_successes` so historical truncated+looping “successes” demote to `token_repeat` and do not skip forever — [ocr_model_recipes.md](docs/runtime/ocr_model_recipes.md).
- Truncated OCR: fail prompt-echo / early loops; **trim** late fence/loop tails (≥70% into the text) and keep the diary prefix. glm/granite recipes add `stop=["```\\n```"]` plus `repeat_penalty=1.2` (a lone fence stop emptied glm pages that open with ` ```markdown `).
- Workspace-configurable OCR model recipes (`data/config/ocr-model-recipes.json` + **Settings → Models**): disable/override builtins, add custom lanes, `freeze_prompt` so glm/granite stay options-only, tighter granite/deepseek matching, `recipe_id` on plan/provenance — [ocr_model_recipes.md](docs/runtime/ocr_model_recipes.md).

### Changed

- Package **1.0.1**. Layering refactor in PR-sized waves: chart palettes live in config (no Streamlit import), CLI split into `transcribe.cli`, shared OCR/Analyse batch notebook picker (`tx_*` / `ax_*` keys kept), Reading/Review renderers as resolve → chrome → body, `ProjectService` dates/review-repair/declutter collaborators. `load()` stays the public API; `reconcile_interrupted()` is the explicit reopen path.
- Coverage floor raised to 80 (UI still omitted).

## [1.0.0] - 2026-10-23

### Added

- Notebook workbench freeze for the scope-lean product: transcribe, compare models, external fine-tune, read / tag / explore. 1.0 gate docs (severity, ops, manual acceptance, analysis audit) are on the tag checklist.
- Review **Other** → **Ignore in Reader** (Reading hide + export reading-format omit).

### Changed

- Package **1.0.0**. Autobiography remains on file, not this product.
- **Streamlit shell:** inject global CSS once per session and cache the sidebar logo, on top of the earlier rerun caches.

## [0.9.0] - 2026-10-23

### Added

- **U2.2 / U2.4:** bundled `samples/demo-notebook/` with Home **Open sample notebook** and **New notebook → Open sample**; README “First notebook in 15 minutes” path (Docker preferred).
- **Ignore pages (Reader):** `ProjectService.set_page_ignored`, Reading hide-by-default + **Show ignored** override, Review **Ignore in Reader**, workspace `ui.hide_ignored_pages`.
- **Detection fine-tune export:** CLI `export-detection-finetune`, Export UI tab, contract [docs/contracts/detection-finetune-export.md](docs/contracts/detection-finetune-export.md) (approved/rejected labels; unreviewed excluded by default).
- **I6:** `.github/workflows/nightly.yml` (offline acceptance + contracts), Docker image smoke on PR `release-checks` (skips with an explicit reason when Docker is missing), GitHub issue templates.
- Maintainer **1.0** gate pack: severity triage, release-ops, manual acceptance, and a 25-module analysis quality audit.

### Changed

- **Streamlit efficiency (PR1):** session/process caches for shell CSS + logo, published-analysis nav gate, Review queue index (repair-once), View health across tab hops, and vendored wordcloud2.js; Analyse this-notebook progress polls at 1s. Audit: [docs/dev/streamlit_efficiency_audit.md](docs/dev/streamlit_efficiency_audit.md).
- **L3:** Names detector consumes **published** NER only — no nested Analyse `run_module("ner")`.
- **P1:** Cleanup soft-failure no longer seals cleanup into the OCR skip fingerprint (resume can retry cleanup).
- Settings confirms before **Reset whole workspace settings** and **Re-apply visual declutter**.
- Coverage floor raised to 75; default pytest suite uses `--timeout=60`.
- Scope lean (24 Sep 2026): this product stops at the notebook workbench (transcribe, compare models, external fine-tune for one hand, read / tag / explore). The autobiography programme stays on file in the roadmap for a future separate product. It is not Transcribe 1.1–2.0.
- Design note for an import→OCR smoke kit ([docs/dev/smoke_kit_import_ocr.md](docs/dev/smoke_kit_import_ocr.md)). Not implemented. PR CI still does not run a vision model.
- A stranger-testing round is not a release gate.
- Roadmap reorganised: status-at-a-glance, ranked active backlog, thickened U2/I6/1.0 freeze criteria, shipped programmes grouped separately from candidates, decision log. Autobiography write-up remains on file.

## [0.8.8] - 2026-09-04

### Added

- Maintainer **I5:** public landing site (`website/`) plus GitHub Pages assemble (`make pages-site`, `scripts/release/assemble_pages_site.sh`, `.github/workflows/pages.yml`). Sphinx `/guide/` shares the sticky header chrome from `website/chrome/`.

### Changed

- Public install docs (README, installation, Docker, website landing) prefer **Docker**; host/Python (`./transcribe.sh`) is documented as advanced.
- Public docs (README, Sphinx Start here, website, user guide, installation) lead with outcomes and GUI steps for a first-time user. Classification `Type:` / `Authority:` headers are removed so they no longer render on hosted pages.

## [0.8.7] - 2026-09-03

### Added

- Architecture review from code evidence: [docs/reviews/architecture_from_evidence.md](docs/reviews/architecture_from_evidence.md). Remaining decoupling is on the roadmap as unscheduled candidates.
- **Settings → Interface:** configurable action-link appearance (icon only, text only, or both) with a global default and per-section overrides. Install default is icon+text everywhere except Library cover cards (icons only).
- Built-in **`names`** detector (Names / people): spaCy `PERSON` entities per page from published NER, or a NER run when none is current. Auto-tag applies those person names, not a generic `names` tag.
- Built-in lexical detectors **`first_person`** (count standalone `I`/`i`) and **`swear_words`** (lexicon hit counts). Deterministic OCR text match; no LLM. Published `page_counts` is a per-page series (including zeros); findings still mark pages at/above `min_count` for auto-tag.
- Reading / Library / Detect page viewer **Compare in Review** deep-link when multiple OCR attempts exist (replaces Prefer/Promote expander).
- Review **Build merged draft** when two or more vision readings exist and no current composite; rank rationales shown on evidence radios.
- Detect findings and page-viewer detection rows: **Accept** marks the finding approved and applies remaining span tags (Reject still declines without tagging).
- Multi-page Detect findings: per-page **Accept this page** / **Reject this page** on each page tab; **Accept remaining** keeps accepted pages and skips rejected ones.

### Changed

- Single-model **`transcribe run`** exits **1** when the timeout or `model_load` circuit skipped remaining pages (`circuit_open`). Job records still store `status=completed` so skip/resume is unchanged. Multipass overall-complete is unchanged (remaining models still run).
- Progress chrome distinguishes **Cancelled** and **Completed with gaps** (circuit / batch partial) from Failed. Cancelled runs no longer render as errors. OCR snapshot mapping lives in `transcribe.ui.progress_snapshots` so it can be tested without loading the Transcribe page.
- Detection `reconcile_interrupted` no-ops while the notebook **analysis** lock is held (as well as the OCR job lock), so Analyse+detect is not false-interrupted by `ProjectService.load()`.
- After 1.0 roadmap records **UI host** as reopenable decisions (Streamlit through 2.0 remains the working default; no rewrite scheduled). See [docs/ROADMAP.md](docs/ROADMAP.md#ui-host-working-default--reopen-with-evidence).
- Detect Findings for lexical counters (`first_person`, `swear_words`) is a per-page count table and chart from OCR text, not review-style finding cards.
- **Library** absorbs the former Archive page: default **Covers** thumbnail overview (filters, clickable activity bins, paging); **Activity** is a selectable per-notebook histogram list. Legacy `Archive` / `View` nav ids still open Library.
- **Review** workbench: lane switcher (one body at a time); OCR evidence + disagreements live in the **Transcription** lane; compact page chrome and icon disagreement nav; queue defaults to **High disagreement** when present; single-pass filter counts; all-pages rank/merge behind confirm.
- Review lane switcher is a tab-like segmented control (not radio buttons); Streamlit `st.tabs` is still avoided so only one lane body runs. Changing pages (prev/next, jump, thumbnails, Skip, Save + Mark reviewed) keeps the selected lane.
- Punctuation-only / prompt-instruction disagreement spans are not navigable Review steps (still affect agreement %). Failed OCR attempts appear as captions, not evidence radios.
- Transcribe Advanced and multipass rows use the same OCR settings labels as Review (**When setting a notebook default**, **Seed transcription from merged draft after multipass**).
- **Review → Other → Re-run OCR** opens a vision-model picker and can force OCR on this page, all pages, or pages not marked reviewed.
- Whitespace-only OCR is **failed** (`empty_output`) and no longer replaces a prior succeeded reading. Review repairs historical empty `succeeded` attempts.
- **DeepSeek-OCR** (and documented recipe tags) freeze a short `free_ocr` prompt unless a custom prompt is set — [ocr_model_recipes.md](docs/runtime/ocr_model_recipes.md).
- **Rank and merge existing OCR** (Review and Transcribe) ranks on-disk readings from different jobs and builds a merged draft without a same-session multipass.
- Cursor slash-command copies under `.cursor/commands/` are gitignored (local filled copies).

### Fixed

- Loading workspace / notebook config no longer imports Streamlit via chart-colour defaults (`ui/chart_colors.py` imports Streamlit only when rendering charts).

## [0.8.6] - 2026-08-19

### Added

- Maintainer **I4:** Sphinx hosted docs over the existing Markdown corpus (`docs/conf.py` + MyST + Furo, `.[docs]`, `make docs` → `scripts/release/build_docs.sh`, `.readthedocs.yml` scaffold, CI `docs` job). Glob toctrees keep contracts/runtime/dev pages in the hosted tree. Read the Docs public hostname remains owner-gated.
- **OCR Review workbench** (Workflow → Review): two-pane scan + tabbed review lanes (Transcription / Date / Tags / Other), source-only disagreement review, merged draft as recommendation, `review_status` + fingerprints so “reviewed” means the current transcription.
- **Ask history** on View → Ask: browse prior `llm_custom_qa` attempts for the open notebook.
- **Export readability:** 25 curated body fonts, optional notebook cover image in HTML/EPUB/PDF, and **Exclude ignored pages** (default on) for reading formats.
- **Settings → Configuration → Overview:** chart colour overrides for sentiment/emotion bar charts; **Show Advanced expanders** (`ui.view_show_advanced`) gates raw JSON on View pages.
- **Detection tag approval** rows (✓ / ✓✓ / ✕) on Detect findings and the page viewer.
- Shared **icons** module and page-scan **lightbox** in Reading / Review.

### Changed

- **Review workbench** right pane is tabbed (**Transcription** · **Date** · **Tags** · **Other**) so date and tag review no longer sit below the fold; lane-specific **💾 Save date** / **💾 Save tags** buttons.
- **Detect** moves to **Workflow** (primary nav View order: Read · Overview · Summaries · Ask · Themes · Mood).
- Multipass treats a composite as stale when source OCR evidence changes; rank/composite re-runs until a current merged draft exists. Stale composites are retained.
- Per-notebook OCR settings relabelled (**When setting a notebook default**, **Seed transcription from merged draft after multipass**); project overrides writable from Review → Other.

## [0.8.5] - 2026-08-18

### Added

- Analyse → Batch **Pick notebooks** labels show published status in brackets (`BMO (no analysis)`, `Jake (existing degraded analysis)`, …). Content freshness stays on **Notebooks needing analysis**.

### Changed

- Page ink / blankness metrics skip the notebook’s explicit cover page (`cover_page_id`): Reader no longer shows page-used / ink / paper under the cover scan, and Overview rollups/charts omit that page.

## [0.8.0] - 2026-08-17

### Added

- Maintainer **I2–I3**: release hygiene kit (`scripts/secrets_check.sh`, `scripts/release/*`), [docs/dev/release_governance.md](docs/dev/release_governance.md) tag checklist, [docs/dev/dependency_audit.md](docs/dev/dependency_audit.md), coverage gate (`.coveragerc` `fail_under = 70`, UI omitted), root `.pre-commit-config.yaml`, CI `release-checks` (secrets, tracked-data, stale refs, compose bind, wheel import).

### Changed

- EPUB missing-dependency hint now recommends `pip install -e '.[export]'` (no published PyPI package).
- Settings Profiles / Models panels run in `@st.fragment`; creating a notebook invalidates listing caches instead of `st.cache_resource.clear()` (keeps live OCR/Analyse coordinators).

## [0.7.0] - 2026-08-17

### Added

- Maintainer **I0–I1** lanes: root `Makefile` (`test-smoke` / `test-fast` / `test-contracts` / `test-acceptance` / `docker-smoke`), [tests/README.md](tests/README.md), GitHub Actions CI (ruff critical + offline smoke/default suite on Python 3.10–3.12), compose loopback bind assert (`scripts/release/assert_compose_bind.sh`).
- Post-1.0 **autobiography workbench** sequencing on [docs/ROADMAP.md](docs/ROADMAP.md) (releases 1.1–2.0): notebook-anchored contextual evidence, Slices, cited reconstruction. Gated on 1.0. Not shipped behaviour.
- Path to **0.9.0** / **0.9-1** / **1.0** on the roadmap: U2 + I0–I6 → 0.9.0 cut → unfamiliar-user testing ([docs/dev/user_testing_0_9.md](docs/dev/user_testing_0_9.md)) → 1.0 freeze with foundation checklist for After 1.0.

### Changed

- `.[dev]` extras include pytest-cov, pytest-timeout, and ruff so CI and later coverage gates share one install.

## [0.6.5] - 2026-08-16

### Fixed

- Restore Detect knobs on analysis UI presets (`allow_detection`, `detector_ids`) so the Docker UI can import again. Thorough still includes detectors by default.

## [0.6.2] - 2026-08-16

### Added

- Planned **0.9 infrastructure wave** ([docs/infrastructure_wave_0_9_plan.md](docs/infrastructure_wave_0_9_plan.md)): CI, test lanes, release hygiene, and hosted docs, patterned on TranscriptX maintainer infra. Package stays **0.6.x** until that programme lands; then **user testing** toward **1.0**.

### Changed

- Roadmap points at archived delivery-history plans under `docs/archive/plans/` and `docs/dev/analysis_module_porting.md`.

## [0.6.1] - 2026-08-16

### Fixed

- Restore **Settings → Configuration → Backup** (create / verify / dry-run / restore via on-disk paths) and document workspace backup/restore as shipped. CLI `backup` / `restore` was never removed.

## [0.6.0] - 2026-08-15

### Added

- Organisation tagging (workspace catalogue, viewer filter, detection auto-tag).

### Changed

- Documentation organisation brought toward TranscriptX maturity: `docs/archive/` for shipped delivery plans, sectioned user/dev indexes, `docs/dev/docs_architecture.md`, deeper `docs/runtime/` task guides, root `CONTRIBUTING.md` / `SECURITY.md` / changelog.

## [0.5.0] - 2026-08

### Added

- Local-first handwritten notebook OCR workbench (Streamlit UI on port **8510**, CLI, shared services).
- Page-preserving projects, multipass OCR, Prefer/Promote, fine-tune export, Prompt Hub + Detect.
- Core notebook analysis module set with Analyse presets and View consume surfaces.
- Corpus bulk import, batch OCR, batch Analyse (acceptance gates green).
- Full-workspace backup / restore ZIP (`transcribe.workspace-backup`).

### Notes

- Pre-0.5 history is not reconstructed in this file. Product sequencing and shipped capability detail: [docs/ROADMAP.md](docs/ROADMAP.md).
