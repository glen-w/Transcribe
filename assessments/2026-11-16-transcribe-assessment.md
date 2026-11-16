# Transcribe assessment — 2026-11-16

Whole-product assessment of the repository at `main` @ `4853226`. It follows the [2026-11-03 maturity survey](../docs/assessments/2026-11-03-assess.md) and records what changed since. It is **not** a release approval; tag authority stays with [release_governance.md](../docs/dev/release_governance.md).

## Verdict

The product is healthy and honest about its scope. The offline suite is green (1,409 passed, 85.8% coverage), CI and six consecutive nightlies are green, the architecture rules hold, and the scope lean has held for eight weeks. The main risks are at the edges rather than the core:

1. **The first-run promise is broken on the recommended install path.** "Open sample notebook" fails from a wheel or Docker install because the fixture is not packaged (F1). Verified against the built 1.4.0 wheel.
2. **A second OCR provider landed on `main` without the release paperwork.** `--provider paddleocr` shipped unreleased, absent from the changelog, labelled as a feature branch in five docs, and with a resume path that forgets it (F2, F3).
3. **The safety net got thinner without the docs noticing.** The nightly dropped acceptance, scale, and `pip-audit` on 2026-11-04; the changelog still advertised them (F6).
4. **The public storefront still lags.** GitHub "Latest" is `v0.1.0` against tag `v1.4.0` (F4). The landing-page footer, flagged on 2026-11-03, is now fixed.

No product work has started on ladder 1.4 (hand shelf) or 1.5 (continue reading). The fortnight since the 1.4.0 tag went to OCR throughput on the real corpus, which is the right priority but is not what the roadmap's "Now" section described.

**Freeze-planning status: `NEEDS FIXES`** — F1 and F4 before any public promotion; F2/F3 before a tag that includes the Paddle provider.

## Pins

| Pin | Value |
|-----|-------|
| Branch | `main` @ `4853226`, level with `origin/main` |
| Worktree | Clean before this sitting. This sitting changed docs only (listed under [Docs changed](#docs-changed-this-sitting)) |
| Package / `__version__` | 1.4.0 |
| Latest tag | `v1.4.0`; `main` is **5 commits ahead** (`git describe`: `v1.4.0-5-g4853226`) |
| GitHub Latest release | `v0.1.0` (2026-08-07) |
| Landing footer | 1.4.0 (matches; was 1.0.1 on 2026-11-03) |
| Python used | `.venv` interpreter, offline, temp data roots |
| Hardware context | MacBook Pro M5 Pro, 64 GB (from [README.md](README.md) pins) |

### What was and was not exercised

| Check | Result |
|-------|--------|
| Default offline suite + coverage | **pass** — 1,409 passed, 2 skipped, 3 deselected, 5 min 57 s; 85.83% (floor 80%, UI omitted) |
| `make lint` selects | **pass** |
| Full `ruff check src tests` | 523 style findings (510 on 2026-11-03); not a gate |
| `stale_refs`, `check_tracked_data`, `secrets_check`, `repo_hygiene_audit --strict`, `assert_compose_bind` | **pass** (denylist warns about ~38k ignored local paths, as before) |
| CI on HEAD | **pass** — CI and Pages deploy green on `4853226`; Nightly green 2026-11-11 through 2026-11-16 |
| Wheel contents | Inspected the existing `dist/transcribe-1.4.0` wheel (built 2026-11-10); **not rebuilt** |
| Docker image build / smoke | **not run** this sitting. F1's Docker impact is inferred from the Dockerfile plus the wheel test |
| Sphinx build | **not run** locally (CI docs job green on HEAD, before this sitting's doc edits) |
| `pip-audit` / CVE triage | **not run** |
| Live Ollama or Paddle sidecar OCR | **not run**. Model quality is covered by [2026-11-10-model-assessment.md](2026-11-10-model-assessment.md) |
| Manual UI walkthrough | **not run** |

## Size and shape

| Measure | Value | Note |
|---------|-------|------|
| Product code (scc) | 61,676 SLOC | 60,774 Python in 287 files + 902 JS |
| Tests + scripts | 30,246 SLOC | 192 files; about 1,400 test functions |
| Test : product ratio | 0.49 | |
| Tracked files | 683 | 625 on 2026-11-03; growth is mostly `assessments/` |
| Average cyclomatic complexity (radon) | B (5.4) over 2,761 blocks | |

Largest layers by raw lines: `ui` 23.8k, `services` 17.5k, `analysis` 10.0k, `detection` 3.5k. The UI is a third of the product and is excluded from coverage.

Test distribution is bottom-heavy in a good way: 873 unit, 367 service, 64 acceptance, 48 provider, 7 contract. Acceptance tests are few but are the ones that pin the product promises (edits survive re-OCR, crash-resume, corpus integrity).

## Findings

Severity: **High** breaks a documented promise for a new user; **Medium** breaks a documented feature or misleads operators; **Low** is hygiene. Each finding is tracked in [ROADMAP.md](../docs/ROADMAP.md#open-maintenance--from-the-2026-11-16-assessment) as M1–M8.

### F1 — Sample notebook is not in the wheel (High) → M1

`services/sample_notebook.py::sample_package_root()` looks for `samples/demo-notebook/` three directories above the module, which only exists in a source checkout. The fallback (`transcribe/data/sample-notebook`) is not packaged; `pyproject.toml` package-data lists only analysis lexicons and UI assets.

Evidence: importing from the unpacked `transcribe-1.4.0` wheel, `ensure_sample_fixture()` raises `FileNotFoundError: sample manifest missing`. The Dockerfile installs that wheel and copies nothing from `samples/`, so the image has the same gap. Home catches the exception and shows "Could not open sample notebook".

Why it matters: the README's "First notebook in 15 minutes" names Docker as the preferred path and "Open sample notebook" as step 2. That is the one journey a stranger is most likely to try. `tests/unit/test_sample_notebook.py` asserts the repo-root path, and the Docker smoke does not open the sample, so nothing catches it.

Fix: ship `manifest.json` as package data (the PNGs are generated), resolve it through `importlib.resources` first, add a wheel-install test, and add an "open sample" step to the Docker smoke.

### F2 — `bulk-run resume` forgets the provider (Medium) → M2

`OcrBatchRun` stores `settings` (an `OCRSettings` dict) with no provider id. `bulk-run resume` builds a `BatchOcrCoordinator` with no provider, and `_provider_for()` falls back to `OllamaVisionProvider(settings.base_url)`. A run started with `--provider paddleocr` therefore resumes by speaking the Ollama API to the sidecar on port 8112. From code reading; not executed. The single-notebook job path is fine: the frozen plan carries `provider_id` and rebuilds through the factory (`services/job.py:628`).

Fix: persist `provider_id` on the batch run additively (absent means `ollama`) and rebuild through `build_vision_provider`.

### F3 — Paddle provider landed without release paperwork (Medium) → M5, plus docs fixed

Commit `f24995c` merged `feat/paddleocr-mlx` into `main`. Afterwards:

- `CHANGELOG.md` Unreleased did not mention it. **Fixed this sitting.**
- Five docs still called it a branch (`feat/paddleocr-mlx`). **Fixed this sitting.**
- The roadmap decision log read as though no second provider was on `main`. **Fixed this sitting.**
- [PRODUCT.md](../docs/PRODUCT.md) still says "Local Ollama vision models only". Left as is: the sidecar is local and the product promise (no cloud OCR) is intact, but the sentence should be revisited when the provider is released.

The implementation itself is careful: it does not import Paddle or MLX, a non-local sidecar is refused with no override flag (stricter than Ollama's `--allow-remote-ollama`), layout dumps are stripped before storage, and the provider id is in the skip fingerprint. It has 359 lines of HTTP-level tests.

Smaller defect (**Low**, → M3): `bulk-run --provider paddleocr` without `--base-url` runs its locality check on the Ollama default URL before substituting the sidecar default (`cli/bulk.py:192-200`). With a remote `TRANSCRIBE_OLLAMA_BASE_URL` it refuses a run that would have been local. It fails closed.

### F4 — GitHub Latest release is `v0.1.0` (Medium, public) → M4

Unchanged since 2026-11-03. A visitor to the Releases page sees a three-month-old build as current.

### F5 — Roadmap "Now" did not match the fortnight's work (Medium, honesty) → fixed in docs

The roadmap says 1.4 is open and next. None of it has started: there is no `hand-shelf`, pin, or bring-back code in `src/`. Actual work since the tag was fingerprint stability, `token_repeat` deferral, the Paddle provider, and the model assessment pack. That work is defensible (the [model assessment](2026-11-10-model-assessment.md) shows the corpus backlog is the real constraint), but the roadmap should say so. "Status at a glance" now does.

One structural observation, not a defect: the package number and the ladder number have diverged (package 1.4.0 = ladder 1.3; ladder 1.4 will be package 1.5 or later). The roadmap explains this in four places, which is a sign the scheme costs more than it saves. Consider naming the ladder steps (*correct*, *proof*, *keep*) and dropping their numerals.

### F6 — Nightly depth was cut; changelog still claimed it (Low) → M6, docs fixed

Since `45620d0` (2026-11-04) the nightly runs `make test-smoke` only (9 tests). Acceptance and contracts still run on every PR through the default suite, so the real loss is the **scale budgets** and the **`pip-audit` + SBOM** job, neither of which runs anywhere now. The roadmap and `tests/README.md` already say this. The changelog entries for 1.2.0 and 1.3.0 still advertised them; an Unreleased note now records the change.

Combined with ten open Dependabot PRs (#61–#70) and no CVE triage since the tag, supply-chain attention is the weakest process area. Runtime dependencies are few (Pillow, PyMuPDF, wordcloud, plus Streamlit, pydantic, ebooklib for the UI), which limits exposure.

### F7 — Local paths and notebook titles in tracked data (Low) → M7

`assessments/data/nightshift-throughput.json` (36 occurrences), `corpus-stats.json`, two other JSON files, and two reports contain the absolute home path, and the README notes that notebook titles and page ids appear in the JSON. The `.gitignore` deliberately keeps this folder public, so this is a recorded choice, but it is worth a conscious second look since the repository is public. No page text or secrets were found; `secrets_check.sh` passes.

Related: `docs/reviews/nightshift_vision_models.md` is gitignored, yet four tracked docs link to it (`reviews/README.md`, `known_limitations.md`, `ocr_model_matrix.md`, `ocr_generate_failures.md`). Those links are dead for anyone but the maintainer. Left unchanged: whether to track the review or remove the links is a maintainer call.

### F8 — Coverage is thinnest where the new defects are (Low) → M8

| Area | Coverage |
|------|----------|
| Overall (UI omitted) | 85.8% |
| `cli/` | 73.0% — `notebook.py` 47.8%, `bulk.py` 53.5%, `export_cmd.py` 60.0% |
| `services/miss_desk.py` | 47.4% |
| `analysis/rag/` | `index.py` 28.8%, `embed.py` 49.6% (opt-in extra, not installed in the test env) |
| `services/job_timeline.py` | 61.8% |

F2 and F3's URL bug both live in CLI command bodies. Parser tests exist; command-body tests mostly do not.

## Architecture

The documented rules all hold on a fresh scan:

| Rule | Finding |
|------|---------|
| Core does not import Streamlit | **holds** — zero imports outside `ui/` |
| No `transcriptx` import | **holds** |
| Providers own no prompts or persistence | **holds** — the new Paddle provider is an HTTP client only |
| One provider seam | **partly** — `providers/factory.py` exists, but ten UI call sites and the CLI `multipass` and `models` commands construct `OllamaVisionProvider` directly. Acceptable while Ollama is the only UI backend; it is the reason F2 could happen |
| Zero TODO/FIXME in `src/` | **holds** (enforced by `stale_refs.sh`) |

Network egress is confined to four modules: `providers/ollama.py`, `providers/paddleocr.py`, `analysis/rag/embed.py` (local embeddings), and `services/places.py` (opt-in geocoding). There is no `subprocess`, `eval`, `pickle`, or `shell=True` in the package.

Complexity hotspots worth knowing before touching them:

| Block | CC |
|-------|----|
| `services/batch_metadata.py::apply_batch_metadata` | 47 (F) — new in 1.3/1.4 |
| `services/multipass.py::MultiPassCoordinator._run` | 39 |
| `services/project.py::ProjectService.delete_page` | 38 |
| `services/archive.py::ArchiveService.list_notebooks` / `.search` | 38 / 35 |

The 2026-11-03 refactor list is unchanged and still valid: `ui/review_workbench.py` (2,013 lines) remains the largest regression magnet and has no coverage measurement. None of those five candidates has been touched. That is fine under a scope freeze, but 1.4's shelf UI should not be added to `review_workbench.py` without first extracting a lane.

## Security and privacy

| Surface | Finding |
|---------|---------|
| Local-first default | Holds. Ollama remote needs explicit acknowledgement in UI and CLI; Paddle remote is refused outright |
| UI bind | Compose default `127.0.0.1:8510`; native non-loopback bind refused without `TRANSCRIBE_ALLOW_LAN=1` (`net_guard.py`). The UI has no authentication, and the docs say so |
| Backup restore | ZIP members are validated (no absolute paths, no `..`, resolved target must stay under the destination root) |
| Container | Multi-stage build, non-root `transcribe` user |
| Secrets | `.env` and `data/` ignored and untracked; denylist green |
| Supply chain | Weakest area — see F6 |
| Tracked data | See F7 |

No new security defect found. F3's URL check fails closed.

## Documentation

The doc set is large (108 maintained Markdown files, 33 contracts, all indexed) and unusually candid. Link check over non-archive Markdown: 11 broken targets, of which 7 are deliberate local `file://` or transcript ids in the assessments pack, 2 were the sample-fixture path (fixed), and 2 remain by choice (F7).

`ROADMAP.md` is 1,261 lines, and roughly 420 of them are the parked autobiography write-up plus historical 0.9/1.0 tracks. It is accurate but hard to scan; the live content is the first 320 lines. Moving the parked write-up to `docs/archive/` with a pointer would halve the file without losing anything. Not done this sitting because the roadmap's own authority rules and several anchors depend on its current layout.

### Docs changed this sitting

| File | Change |
|------|--------|
| `docs/ROADMAP.md` | Assessment pointer; "Status at a glance" states what is unreleased on `main` and that 1.4/1.5 have not started; new **Open maintenance** table (M1–M8); Paddle provider described as merged, not a branch; two decision-log rows |
| `CHANGELOG.md` | Unreleased: Paddle provider, assessments pack, nightly reduction |
| `docs/known_limitations.md` | New "First run" entry for F1; Paddle entry states CLI-only, no remote, resume caveat |
| `docs/runtime/ocr_model_recipes.md`, `docs/runtime/ocr.md`, `docs/DEV_INDEX.md` | Stale `feat/paddleocr-mlx` labels replaced |
| `samples/README.md`, `docs/usability_wave_plan.md` | Fixture path corrected to the repo root; packaging gap stated |
| `assessments/README.md`, `docs/assessments/README.md` | Index this file and the previously unindexed 2026-11-03 survey |

No source code was changed. Nothing was committed.

## Scorecard

Scores are out of 10, with the 2026-11-03 value for comparison.

| Area | 11-03 | 11-16 | Why |
|------|-------|-------|-----|
| Process | 9 | **8** | Suite, lint, hygiene, CI all green. Down one for the thinner nightly, no CVE triage, and ten unmerged Dependabot PRs |
| Product | 8 | **8** | 1.3 correct shipped and holds. No progress on 1.4/1.5, by choice |
| Public / landing | 4 | **5** | Footer fixed. GitHub Latest still `v0.1.0` |
| Packaging | 9 | **7** | Wheel builds and imports, but omits the sample fixture that the first-run docs depend on (F1). Present on 11-03 too; it was not detected then |
| Docs | 7 | **8** | After this sitting's fixes. Before them, 7: a shipped provider was documented as a branch and missing from the changelog |
| Ops / first-run | 8 | **6** | F1 breaks step 2 of the documented Docker path |
| Architecture | — | **8** | Rules hold; provider seam is half-adopted; UI concentration unchanged |
| Security / privacy | — | **8** | Sound defaults, fail-closed checks; supply-chain monitoring lapsed |

## Recommended order

1. **M1** — package the sample fixture and test it from a wheel. Small change, restores the first-run promise.
2. **M4** — publish a GitHub release for `v1.4.0`. Minutes of work.
3. **M2 + M3** with command-body tests for `bulk-run` (**M8**), then cut a patch release that names the Paddle provider (**M5**).
4. **M6** — merge or close the Dependabot PRs; run `pip-audit` once by hand and record it in [dependency_audit.md](../docs/dev/dependency_audit.md).
5. **M7** — decide whether the local paths and notebook titles in `assessments/data/` should stay public.
6. Then ladder **1.4** (hand shelf). Extract a Review lane before adding shelf UI.

## Follow-up — same day

The sections above describe `main` @ `4853226` as assessed. A fix pass followed in the working tree (uncommitted). Scores above are not revised.

| Finding | State | Proof |
|---------|-------|-------|
| F1 sample notebook (M1) | **fixed** | Installed from a read-only unpacked wheel; `image_sample_check.sh` passes on an image built from the fixed tree and fails on the pre-fix `transcribe:latest` image with the original error |
| F2 resume provider (M2) | **fixed** | `tests/unit/test_batch_ocr.py` — record round-trip, resume rebuild, unknown id rejected, remote sidecar refused on resume |
| F3 URL check (M3) | **fixed** | `tests/unit/test_cli_parser.py` |
| New: sidecar URL left in notebook settings (M9) | **fixed** | Batch and `run` tests assert the notebook's Ollama host and model are restored |
| New: unreachable sidecar failed page by page and exited 0 | **fixed for `paddleocr`** | Health pre-flight; exit 1. Observed against a dead local port before the fix |
| New: `run` exits 0 when every page fails (M10) | **open** | By design today; changing it could break scheduled jobs |
| F4, F6, F7 (M4, M6, M7) | **open** | Need a maintainer decision or an outward-facing action |

A second pass added `tests/unit/test_cli_commands.py` (24 tests that run command bodies through `main`). `cli/` coverage went from 73.0% to 91.3%, and overall from 85.8% to 86.9% (1,450 tests). Those tests found two more defects, both fixed: an unknown detector id raised a traceback (M11), and a repeat single-folder import recorded a failed ImportRun with an id-mismatch message (M12). The work was released as package **1.4.1**.

Not exercised in the follow-up: a live PaddleOCR sidecar or live Ollama run, and a manual UI click-through of **Open sample**.
