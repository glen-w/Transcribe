# Architecture

Transcribe keeps a small ownership model on purpose.

## Shape

```text
Streamlit UI (8510) ──┐
                      ├──► services (project, ingest, job, export, archive, doctor)
CLI (`transcribe.cli`) ─┘              │
                                     ▼
                    workspace (data/)
                    ├── corpus/          # corpus-index + import-runs (bulk import)
                    ├── projects/<…>/    # one managed notebook directory each
                    │     ├── project.json
                    │     ├── sources/ + pages/ renders
                    │     ├── results/<page_id>.json
                    │     ├── analysis/   (optional until first analysis artifact)
                    │     ├── detection/  (optional until first detection artifact)
                    │     └── page_metrics/ (optional until first ink/blankness publish)
                    └── cache/archive.sqlite   (disposable)
```

## Ownership boundaries

| Concern | Owner |
|---------|-------|
| Corpus identity, notebook order, workspace locks | [contracts/notebook-corpus.md](contracts/notebook-corpus.md) |
| Managed originals, fingerprints, duplicates | [contracts/source-asset.md](contracts/source-asset.md) |
| Bulk ImportRun / plan / resume | [contracts/import-run.md](contracts/import-run.md) |
| Corpus/notebook integrity + bulk-import acceptance gate | [contracts/corpus-integrity.md](contracts/corpus-integrity.md) |
| Durable notebook directory layout + per-notebook journal | [contracts/project-on-disk.md](contracts/project-on-disk.md) |
| OCR generations + edits | Per-page results — [contracts/page-result.md](contracts/page-result.md) |
| Analysis inputs / results / storage / eligibility | [contracts/analysis-document.md](contracts/analysis-document.md) · [analysis-result.md](contracts/analysis-result.md) · [analysis-run-storage.md](contracts/analysis-run-storage.md) · [notebook-eligibility.md](contracts/notebook-eligibility.md) |
| Prompt definitions / detection findings / detection runs | [contracts/prompt-definition.md](contracts/prompt-definition.md) · [contracts/detection-definition.md](contracts/detection-definition.md) · [contracts/detection-finding.md](contracts/detection-finding.md) · [contracts/detection-run-storage.md](contracts/detection-run-storage.md) |
| Page ink / blankness / hue metrics | [contracts/page-metrics.md](contracts/page-metrics.md) |
| Portable interchange | Export snapshot — [contracts/notebook-export.md](contracts/notebook-export.md) |
| OCR HTTP | `VisionOCRProvider` (Ollama implementation) |
| Chart palettes (`ui.chart_colors`) | `transcribe.config.chart_colors` — UI renders only |
| Batch notebook source radio | `ui.batch_source_picker` — OCR (`tx_*`) and Analyse (`ax_*`); coordinators stay separate |
| Reading / Review chrome | `page_viewer` and `review_workbench` orchestrate resolve → chrome → body; lanes stay purpose-specific |
| Analyse product rows | Streamlit-free shaping in `ui.analysis_display_helpers`; widgets render only |
| UI widgets | `transcribe.ui` only — must not invent OCR/persistence rules |
| Organisation tag catalog (slugs, labels, colours) | [contracts/tag-catalog.md](contracts/tag-catalog.md) |
| Workspace search/timeline | `ArchiveService` over rebuildable SQLite |
| Notebook collections / archived state (1.2) | [contracts/notebook-collections.md](contracts/notebook-collections.md) — workspace config is authority; SQLite carries derived flags only |
| Saved searches (1.2) | [contracts/saved-searches.md](contracts/saved-searches.md) — filter JSON only, never result snapshots |
| Quality ratings (1.2) | [contracts/quality-ratings.md](contracts/quality-ratings.md) — collect-only local file; no telemetry |
| Confirmed spellings (1.3) | [contracts/hand-spellings.md](contracts/hand-spellings.md) — workspace `{from, to}` pairs; Apply is buffer-only |
| Kept scan / gloss / skip-OCR (1.3) | Additive `page_role` / `page_certainty` / `page_gloss` / `ocr_policy` on [project-on-disk.md](contracts/project-on-disk.md); jobs use `skip_ocr()` |
| Job timeline (1.2) | `services/job_timeline` read-model over validated OCR/analysis/detection run records (Diagnostics) |
| Bind guard (1.2) | `transcribe.net_guard` — non-loopback UI binds require explicit acknowledgement |

## Key runtime objects (shape, not schema)

- **ProjectService** — load/save settings and metadata with load→modify→validate→write under the mutation lock. Dates, review-repair, and declutter are collaborators; public methods stay on `ProjectService`. Since 1.2 (L2), `load()` defaults to `reconcile=False` (a read); notebook open is the explicit write via `load(reconcile=True)` / `reconcile_interrupted()`, which interrupts orphaned OCR/analysis/detection runs. `reorder_pages` / `move_page_to_date_cluster` permute only the `pages` array (never `page_index` or render directories), refuse OCR and analysis locks, and re-infer unapproved inherited dates; UI and CLI both call them ([contracts/project-on-disk.md](contracts/project-on-disk.md#page-reorder)).
- **IngestService** — stages, journals, promotes, then commits the manifest; recovers incomplete journals on open/load
- **JobCoordinator / JobPlan** — freezes model identity, prompt, preprocess, options, targets, provider binding, and optional OCR cleanup identity (mode/model/digest/validator policy) at job start; workers consume the plan, not live UI settings. Multipass reuses frozen single-model plans with `activate=false` / `pass_id`, then rank + composite ([contracts/ocr-multipass.md](contracts/ocr-multipass.md)). Per frozen vision plan: after **3 consecutive timeouts** or **1 fatal model-load** error (`unknown model architecture` / loader crash), remaining pages are skipped (`circuit_open`) so a hung or unloadable model does not burn the notebook; multipass continues with remaining models. Token-repeat aborts fail that page only (no identical retry, no consecutive circuit). SIGINT persists `interrupted` and `POST /api/abort` for the current model.
- **OcrBatchRun** — durable multi-notebook OCR batch ([contracts/ocr-batch-run.md](contracts/ocr-batch-run.md)); UI Workflow → Transcribe → Batch
- **AnalysisBatchRun** — durable multi-notebook Analyse batch ([contracts/analysis-batch-run.md](contracts/analysis-batch-run.md)); UI Workflow → Analyse → Batch (orchestration only; publish stays per-notebook)
- **ExportService** — one coherent snapshot, then multi-format promote
- **ArchiveService** — disposable FTS cache with WAL/busy timeout and delete-and-rebuild on corruption; cheap TTL short-circuit uses a workspace mutation-generation token (callers bump after project mutations)
- **DoctorService** — structural integrity (+ optional deep hashing); quarantined ingest journals reported as errors
- **CorpusDoctorService / CorpusIndexStore / ImportRunStore** — workspace corpus authority under `data/corpus/` (runtime-normative; see corpus contracts)
- **AnalysisCoordinator / AnalysisRunPlan / AnalysisRunner / AnalysisStorage** — project-scoped async batch runs freeze an `AnalysisRunPlan` (modules, EffectiveConfig, text-model identity) and execute under `.transcribe.analysis.lock`; publish under `analysis/`; UI freshness via `module_freshness` / `planned_cache_identity` (UI must not hand-build cache identities). Mid-run settings apply to the next run only; crash/reopen marks orphaned attempts/runs `interrupted` without clobbering published results. Opt-in Ask RAG (`llm_rag_qa`) uses a disposable LanceDB index under `{project}/.cache/rag/`
- **DetectionCoordinator** — in-process Detect run with cooperative cancel (`request_cancel`, `cancel_check` down to the runner); the UI **Stop after current window** button is the only caller. No cross-process queue
- **DetectionRunner / DetectionStorage / prompt_engine / Prompt Hub** — prompt-backed page/window detectors (`poetry`, `todo_lists`, `lists`, `quotations`, `beer_labels`, custom) plus lexical counters (`first_person`, `swear_words`) and `names` (people from NER); publish findings under `detection/`; Settings → Prompts resolves OCR/cleanup/detection definitions with workspace overrides; freshness via `detector_freshness` / planned cache identity. Opt-in auto-tag unions `finding_type` (or detected person names for `names`) onto span pages and is **not** part of detector cache identity
- **TagService / TagCatalogStore** — workspace `personal_corpus.tag-catalog` at `data/config/tag-catalog.json`; assignments remain `tags: string[]` on notebooks/pages; host-agnostic kernel in `transcribe.tagging.kernel` for a future TranscriptX copy
- **PageMetricsService** — Pillow ink coverage / blankness / dominant hue over active renders; publish under `page_metrics/`; cache identity = algorithm version + ordered `(page_id, render_sha256)` (not text Analyse)
- **Visual declutter** — Pillow scanner-border / binding-gutter / edge-shadow crop at import and via `ProjectService.reapply_visual_declutter` (Settings → Configuration); provenance on renders ([contracts/source-asset.md](contracts/source-asset.md))
- **CleanupVerdict / edit divergence / miss desk** — Review collaborators over existing cleanup records, quality-store CER, and attempt error codes. No new job status. Core must not import Streamlit
- **HandSpellingsStore** — `data/config/hand-spellings.json`; packed by workspace backup with the rest of `data/config/`
- **Ollama discovery cache** — thread-safe model metadata keyed by normalized base URL + transport timeout; providers stay lightweight execution clients. `/api/embed` is used only by opt-in Ask RAG

## Explicit non-goals for the core architecture

- Making SQLite the system of record
- Introducing a task queue or multi-process worker fleet for v1
- Coupling to TranscriptX libraries
- Making a post-1.0 context corpus (photos, chats, Slices) part of v1 — sequenced on [ROADMAP.md](ROADMAP.md) **After 1.0**; that programme must not make SQLite the system of record
- Creating `data/context/` or context locks before **1.0** — absence of context trees remains a valid workspace; future lock order is **corpus → context → notebook** (documented for After 1.0; not implemented)

Shipped core analysis + deferred / future / out-of-scope dispositions: [ROADMAP.md](ROADMAP.md). Path to 0.9.0 / 0.9-1 / 1.0: [ROADMAP.md](ROADMAP.md). Docs authority model: [dev/CONTRIBUTING.md](dev/CONTRIBUTING.md).
