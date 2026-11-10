# OCR / vision model assessment — 2026-11-10

Local pack for this machine and this corpus. **Not** a Transcribe product contract. Refresh via [README.md](README.md). Notebook titles and page ids are included on purpose.

| Pin | Value |
|-----|--------|
| Date | 2026-11-10 |
| Hardware | MacBook Pro, **Apple M5 Pro**, **64 GB**, 20-core GPU |
| Transcribe vision | Ollama `VisionOCRProvider` only |
| Projects | `~/Documents/transcribe-projects` — **54 notebooks, 5977 pages** |
| Nightshift (last night, still glm) | `qwen2.5vl:7b` + `glm-ocr` + `granite3.2-vision`, rank `qwen3:8b` |
| Nightshift (code as of this afternoon) | glm **retired** from scheduled multipass; `MODEL_B` empty — see Nightshift scar `2026-11-10-glm-ocr-nightshift-retired.md` and Transcribe [`docs/reviews/nightshift_vision_models.md`](../docs/reviews/nightshift_vision_models.md) |
| Collector | [scripts/collect_model_stats.py](scripts/collect_model_stats.py) → [data/](data/) |

---

## 1. Executive summary

**Every page already has at least one succeeded vision reading.** The 18% Nightshift meter is **page × scheduled-model coverage**, not “unread pages.” `deepseek-ocr` and/or `qwen2.5vl:3b` cover the whole library. The 6k-page “transcribe ASAP” job is therefore: (a) **accept existing text** for older notebooks, and (b) **finish a 2-model compare on the last ~5 years** locally via Nightshift — not a new Transcribe provider.

| Question | Answer on this corpus |
|----------|------------------------|
| Best **scheduled first pass** | **`qwen2.5vl:7b`** — 96.3% finished success, median **11.9 s**, 59 token-repeat / 1627 ok |
| Fastest **already-on-disk** OCR | **`deepseek-ocr`** — 5783 ok / 4 empty, median **2.6 s**; quality caveat: 3884 runs used long `faithful_markdown` (146 prompt-echo pages). Recipe `free_ocr` is the live path |
| Fast second VLM | **`granite3.2-vision`** — 85.5% success, median **6.1 s**; 251 token-repeat |
| Do **not** schedule | **`glm-ocr`** — 56.6% success even after recipe; 721 token-repeat + 417 legacy `http_error`; live green sample **4/4 token-repeat** today. Nightshift already dropped it from defaults |
| Never first OCR | Thinking VLMs (`gemma4:26b` 125 empty / 44 ok; `qwen3-vl:4b` empty on mini probe); `llama3.2-vision:11b` 530 `model_load`/`http_error` |

**Status-quo ETA** (3-model remaining 14665, last night **82** succeeded): **~179 nights**. Nightshift canvas quoted ~226 at ~65/night. Both assume glm stays in the set. **It should not.**

**Recommended Nightshift ETA (this machine):** skip `rest` re-OCR (text already exists); run **`qwen2.5vl:7b` + `granite3.2-vision`** only on `recent` + `from_2023`. Remaining pair-runs **~2863**. At ~12 s/page in a full 7.5 h window that is on the order of **one to two OCR-only nights**, not 200. Optional `rest` quality pass with **7b only** is ~3245 pages / ~11 h GPU (~two more nights) if 3b/DeepSeek is not good enough to read.

Selective cloud is **not** the 6k path. Spec: later Transcribe branch `feat/selective-remote-ocr` for miss-desk leftovers only.

---

## 2. Current stack performance

Target models for the historical Nightshift triple: `qwen2.5vl:7b`, `glm-ocr`, `granite3.2-vision`. Source: [data/corpus-stats.json](data/corpus-stats.json), [data/coverage-by-tier.json](data/coverage-by-tier.json).

### Library

| | |
|--|--|
| Notebooks / pages | 54 / **5977** |
| Pages with ≥1 succeeded vision attempt | **5977 (100%)** |
| Pages with composite | 3633 |
| Pages with `edited_text` | 14 |
| Triple page×model | **3266 / 17931 (18.21%)** |
| Notebooks ≥80 / 90 / 95 / 100% of triple | 5 / 4 / 1 / 0 |

`black` is 97.1% of the triple (glm still the hole). `adventure time`, `microbe`, `xmas narwhal`, `brown`, `virus`, … are **0% of the triple** and **100%** DeepSeek and/or 3b.

### Triple coverage by date tier

| Tier | Notebooks | Pages | Triple runs done | Triple % | 7b ok | granite ok | glm ok | deepseek ok | 3b ok |
|------|----------:|------:|-----------------:|---------:|------:|-----------:|-------:|------------:|------:|
| recent (≥2025) | 12 | 1714 | 2072/5142 | **40.3%** | 1084 | 478 | 510 | 1391 | 531 |
| from_2023 | 6 | 670 | 471/2010 | **23.4%** | 195 | 148 | 128 | **669** | 181 |
| rest (≤2022 / undated) | 36 | 3593 | 723/10779 | **6.7%** | 348 | 197 | 178 | **3285** | 2862 |

Nightshift’s date order (`recent` first) plus a 7.5 h window filled with glm failures is why `from_2023` / `rest` keep showing `skipped (run interrupted)`. Last two nights: recent stopped at 07:30 on `black` / `sand blue` / `green`; later tiers never started.

### Per-model attempt outcomes (all history)

From [data/error-by-model.json](data/error-by-model.json). Counts are **attempts**, not unique pages.

| Model | Attempts | Succeeded | Failed | Int. | Finished success | Median s | Median eval | Trunc. success | Trunc+rep still success |
|-------|---------:|----------:|-------:|-----:|-----------------:|---------:|------------:|---------------:|------------------------:|
| deepseek-ocr | 5787 | 5783 | 4 | 0 | **99.9%** | 2.55 | 110 | 89 | 25 |
| qwen2.5vl:3b | 3575 | 3575 | 0 | 0 | **100%** | 9.21 | 127 | 41 | 33 |
| qwen2.5vl:7b | 1696 | 1627 | 63 | 6 | **96.3%** | 11.9 | 151 | 4 | 3 |
| granite3.2-vision | 1775 | 1514 | 257 | 3 | **85.5%** | 6.11 | 121 | 303 | 70 |
| glm-ocr | 2654 | 1490 | 1145 | 19 | **56.6%** | 31.87 | **4096** | 754 | 63 |
| llama3.2-vision:11b | 530 | 0 | 530 | 0 | 0% | 2.9 | — | 0 | 0 |
| gemma4:26b | 170 | 44 | 125 | 1 | 26.0% | 66.2 | 4096 | 5 | 0 |
| qwen3.6:27b | 24 | 15 | 8 | 0 | 65.2% | 227 | 1031 | 0 | 0 |
| qwen3-vl:8b | 9 | 4 | 3 | 2 | 57.1% | 255 | 4045 | 1 | 0 |

Night-window successes (23:30–07:30 local) are dominated by **historical DeepSeek / 3b nights**, not the current triple: 3b 2396, deepseek 2583, 7b 673, glm 855, granite 689.

---

## 3. Error anatomy

Miss-desk groups: `empty_output`, `token_repeat`, `model_load`, `timeout`, `circuit_open`, plus leftover `http_error` / `interrupted`.

### glm-ocr (do not schedule)

| Slice | Succeeded | Failed | token_repeat | http_error | timeout | empty |
|-------|----------:|-------:|-------------:|-----------:|--------:|------:|
| No recipe | 790 | 578 | 157 | **417** | 1 | 3 |
| `recipe_id=glm_ocr` (`repeat_penalty=1.2`) | 700 | 567 | **564** | 0 | 3 | 0 |

The 2026-10-23 `black` spot-check (4/4 no abort after recipe) **did not generalise**. Corpus-wide glm **with recipe** is still ~45% token-repeat. Last night’s job log: 82 succeeded / **75 failed** (42 token-repeat, 33 truncated+repetition) on the glm-heavy green pass.

Example pages (glm `token_repeat`, notebook `green`): `5b075877…`, `ee9f57d6…`, `d3807a8a…`. Live re-probe 2026-11-10: glm **error** all four; 7b and DeepSeek **ok** (see §5).

Legacy `http_error` on glm is the pre-classification llama.cpp abort (`prediction aborted, token repeat limit reached`) that used to retry three times.

### Other models

| Model | Dominant fail | Note |
|-------|---------------|------|
| granite3.2-vision | 251 `token_repeat` | Recipe `repeat_penalty=1.2` exists; still loops on some dense pages. 70 truncated+rep successes may still skip — Review repair exists |
| qwen2.5vl:7b | 59 `token_repeat` | Rare relative to glm; keep as primary |
| deepseek-ocr | 4 `empty_output` | Almost all historical `faithful_markdown`; 1694 later `free_ocr`. **146 prompt-echo** successes (instruction bullets instead of diary text) — treat as quality misses, not empty |
| llama3.2-vision:11b | 517 `http_error` + 13 `model_load` | `unknown model architecture: mllama` — picker already hides |
| gemma4:26b | 125 `empty_output` | Thinking burned `num_predict` — documented in [`ocr_model_matrix.md`](../docs/runtime/ocr_model_matrix.md) |
| qwen3-vl / qwen3.6 | empty / timeout | Thinking / huge; not a night job |

**Quality, not status:** DeepSeek on `faithful_markdown` often paraphrases the prompt (“If you have to guess…”). Examples: `brown/e4697977…`, `paris/20a8dc78…`. Prefer `free_ocr` recipe or 7b/3b for reading.

---

## 4. Nightshift operations

Sources: [data/nightshift-throughput.json](data/nightshift-throughput.json), `~/Library/Logs/nightshift-transcribe-night.log`, [`nightshift/logs/2026-11-10.md`](file:///Users/89298/Documents/nightshift/logs/2026-11-10.md).

| | |
|--|--|
| Job-log nights started | 29 (models line always the **triple**, including glm) |
| Markdown nights with a transcribe-night block | 20 |
| Recent stopped at window / 90m cap | 15 |
| from_2023 / rest skipped interrupted | 3 recent (last nights); many earlier nights listed `ok=0 failed=0` at 90m on `black` (skip-heavy glm retries) |
| Ingest skipped | 16 (`SKIP_INGEST=1` in [`focus-ocr.env`](file:///Users/89298/Documents/nightshift/jobs/transcribe-night/focus-ocr.env)) |
| Last night | 23:46–07:30, 7h 43m, recent `black, sand blue, green`; from_2023/rest skipped |
| Last-night page outcomes | succeeded **82**, failed **75**, skipped 1 |
| Job-log lifetime | succeeded 3183, failed 1101 (724 token_repeat, 374 truncated_repetition, 3 empty) |

**Default vs live:** `run.sh` now defaults `MODEL_B` empty (glm retired **today**). The log through this morning still shows glm because those nights ran **before** the env change. Confirm the next night’s models line is `qwen2.5vl:7b + granite3.2-vision`.

**Dayshift:** [`focus-cover80-granite.env`](file:///Users/89298/Documents/nightshift/jobs/dayshift/focus-cover80-granite.env) is the right shape for finishing ≥80% books. Five notebooks are already ≥80% of the *triple*; after glm drop, rollup should be qwen+granite (Nightshift already updated `LIST_TIER_ROLLUP_MODELS` in that scar).

Forecast in JSON used last-night **82** successes → **179** nights at that rate for the *triple* remainder. That rate is glm-contaminated (half the wall clock failed). Do not use it after the glm drop.

---

## 5. Hardware fit (M5 Pro 64 GB) and live probes

64 GB unified memory comfortably holds 7b VL + granite 2b + qwen3:8b rank, with headroom. Do not night-schedule 26–31b thinking VLMs; they empty or timeout.

### Mini fixture (2026-11-10, `num_predict=512`)

[data/probe-results.json](data/probe-results.json). Stale matrix in docs was **2026-08-23**.

| Tag | Load | OCR | Len | s | Notes |
|-----|------|-----|----:|--:|-------|
| glm-ocr:latest | ok | ok | 75 | 8.0 | Recipe on; **not predictive of dense pages** |
| granite3.2-vision | ok | ok | 73 | 34.5 | Slow cold load on this probe |
| qwen2.5vl:7b | ok | ok | 68 | 13.0 | |
| qwen2.5vl:3b | ok | ok | 68 | 8.6 | |
| deepseek-ocr | ok | ok | 66 | 6.8 | `free_ocr` recipe |
| minicpm-v:8b | ok | ok | 70 | 4.9 | Chatty fences |
| gemma3:4b | ok | ok | 68 | 4.8 | Non-thinking Gemma — fine for compare, not scheduled |
| llava:7b | ok | ok | 73 | 3.5 | Compare-only |
| qwen3-vl:4b | ok | **empty** | 0 | 15.6 | `eval_count=512` truncated — thinking |

Skipped: `llama3.2-vision` (known mllama fail), `gemma4:31b` / `qwen3.6:27b` (cost, empty risk).

### Green dense pages (glm-repeat cohort, not persisted)

[data/probe-green-sample.json](data/probe-green-sample.json) — 4 pages, ~18–45 MB renders, `num_predict=4096`.

| page_id prefix | 7b | glm | deepseek (`free_ocr`) |
|----------------|----|-----|------------------------|
| `5b075877` | ok 1007 chars / 17.1 s | **token_repeat 13.0 s** | ok 1001 / 7.5 s |
| `ee9f57d6` | ok 1550 / 15.5 s | **token_repeat 12.7 s** | ok 1713 / 5.3 s |
| `d3807a8a` | ok 458 / 12.4 s | **token_repeat 11.5 s** | ok 529 / 3.4 s |
| `0775ee94` | ok 2024 / 20.1 s | **token_repeat 18.1 s** | ok 2136 / 6.4 s |

**On real handwriting, glm with recipe still aborts; DeepSeek with `free_ocr` is fastest; 7b is reliable.** Mini-page glm “ok” is a trap.

`--workers`: keep **1** overnight (Ollama GPU serial). A second worker on 64 GB does not pay if llama.cpp holds one generate.

---

## 6. External / research landscape (Oct–Nov 2026)

Printed-document leaderboards (OmniDocBench, olmOCR-Bench) **overstate** specialists vs diary handwriting. Use this corpus, not OmniDocBench, to pick Nightshift tags.

| Model | Size | Ollama today | Role here |
|-------|------|--------------|-----------|
| **PaddleOCR-VL-1.6** | ~0.9B | Community `seriouswebby/paddleocr-vl-1.6` (1.8 GB), not official library | **Best candidate for empty `MODEL_B`** after a 20-page green probe. Apache-2.0. Needs its own task prompt (`OCR:`) — would need a Transcribe **recipe**, which is a product change (not this sitting) |
| GLM-OCR | 0.9B | Official `glm-ocr` | Strong on **printed** OmniDocBench; **weak on this hand**. Manual compare only |
| DeepSeek-OCR (v1) | ~3B | Official `deepseek-ocr` 6.7 GB | Already ran on almost every page. Keep recipe `free_ocr`. DeepSeek-OCR-2 is vLLM-first, not a drop-in Ollama night tag yet |
| granite3.2-vision | 2b | Official 2.4 GB | Keep as fast second VLM |
| qwen2.5vl 3b/7b | 3b/7b | Official | 7b = scheduled primary; 3b already library-wide |
| Chandra 2 / LightOnOCR-3 | 0.8–5B | Not official Ollama | Handwriting-advertised; licences (Chandra revenue cap) and serving (vLLM) — feature-branch / sidecar, not Nightshift this week |
| olmOCR 2 | ~7B | Toolkit + vLLM | English archives; overkill vs 7b already working |
| Qwen3-VL / Gemma 4 | thinking | Installed | **empty_output** — excluded in picker |

Sources (accessed 2026-11-10): [vdf.ai local OCR roundup](https://vdf.ai/blog/best-local-ocr-models/) (22 Oct 2026); [Ollama glm-ocr](https://ollama.com/library/glm-ocr); [deepseek-ocr](https://ollama.com/library/deepseek-ocr); [granite3.2-vision](https://ollama.com/library/granite3.2-vision); [paddleocr-vl-1.6 community](https://ollama.com/seriouswebby/paddleocr-vl-1.6); [Agave IS glm vs Qwen2.5-VL](https://agaveis.com/blog/from-broken-ocr-to-a-searchable-archive).

### Selective remote cost order-of-magnitude (research only)

| Lane | List price (read 2026-10/11) | ~6k pages if bulk (do not) | Miss-desk 200 pages |
|------|------------------------------|----------------------------|---------------------|
| Google Document AI Enterprise OCR | $1.50 / 1k pages (1k/mo free) | ~$9 | ~$0 |
| Mistral OCR 4.1 | $4 / 1k pages | ~$24 | ~$0.80 |
| Gemini Flash-Lite class (token) | ~$0.35–$2 / 1k pages in published arithmetic | low tens of USD | cents–dollars |
| Gemini 3.6/3.7 Flash via OpenRouter | ~$0.004–0.005 / page in OpenOCR’s page/$ | ~$25–30 | ~$1 |

**Bulk cloud is cheaper than 200 local nights but sends every diary scan off-machine.** You chose **selective** only. Local 7b+granite on 5-year remainder is **hours**, not a billing event.

---

## 7. Nightshift backlog recipe (implement in Nightshift, not Transcribe)

Do **not** add Transcribe CLI. `bulk-run notebooks --model …` already takes a variable number of `--model` flags.

### What “done” means

| Goal | Mechanism |
|------|-----------|
| **Readable library this week** | Effective text already exists on 5977/5977 pages (DeepSeek and/or 3b, plus 7b on many recent pages). Optional: in Review, prefer 7b > 3b > DeepSeek `free_ocr` > DeepSeek `faithful_markdown` |
| **Last ~5 years compare + composite** | Nightshift `recent` + `from_2023`: `MODEL_A=qwen2.5vl:7b` `MODEL_C=granite3.2-vision` `MODEL_B=` `TEXT_MODEL=qwen3:8b` |
| **Older notebooks** | **Skip scheduled OCR** (`SKIP_REST=1`) unless you want a 7b quality pass |

### Remaining work if 5-year pair only

| Tier | Missing 7b | Missing granite | Pair-runs left |
|------|-----------:|----------------:|---------------:|
| recent | 630 | 1236 | **1866** |
| from_2023 | 475 | 522 | **997** |
| **5-year total** | | | **2863** |
| rest (optional 7b-only) | 3245 | — | 3245 |

At ~12 s/page (7b median; granite often faster): 2863 × 12 s ≈ **9.5 h** ≈ **one full night + a short dayshift**, if glm is gone and `rest` is skipped.

Optional rest 7b: 3245 × 12 s ≈ **11 h** extra. Run as dedicated nights: `SKIP_RECENT=1 SKIP_FROM_2023=1 MODEL_C= MODEL_A=qwen2.5vl:7b`.

### Env sketch (Nightshift repo, after you confirm)

Overnight (`focus-ocr.env` or plist — **not** Transcribe):

```sh
SKIP_INGEST=1
NOTEBOOKS_MAX=0
TIER_MAX_MINUTES=0          # or keep 90 on recent only once per-tier models exist
SKIP_REST=1                 # 5-year first
MODEL_A=qwen2.5vl:7b
MODEL_B=
MODEL_C=granite3.2-vision
TEXT_MODEL=qwen3:8b
```

Dayshift extra GPU: `DAYSHIFT_SKIP_SUMMARIZE=1 DAYSHIFT_FIRST=transcribe`. Cover-80 granite fill: `DAYSHIFT_FOCUS=cover80-granite` with rollup **qwen+granite** (already in the glm-retirement scar).

**Per-tier model lists** (`MODELS_REST` vs `MODELS_RECENT`) are the clean `run.sh` change if you later want rest-7b and 5-year-pair in one night without skip flags. Tests: `test_transcribe_list_tier.py` / `contract.sh`. Not required to start tomorrow: skip flags are enough.

### Do not

- Put glm back on `MODEL_B` “for compare” on the full library.
- Wait for `feat/selective-remote-ocr` to clear the 6k backlog.
- Pull `qwen3-vl` / `gemma4` into Nightshift.
- Change Transcribe `main`.

### After glm drop, recompute canvas forecast

`runs_total` becomes pages × 2. Morning snapshot 2026-11-10 is still ×3 (`17931`). Next night-canvas pass should pick up `MODEL_B` empty.

---

## 8. `feat/selective-remote-ocr` (Transcribe feature branch, later)

**Not implemented in this sitting.** Nightshift must stay Ollama-only until this lands and you opt in.

### Goal

Offload a **named page list** (miss-desk `token_repeat` / prompt-echo DeepSeek / empty) to a cheap multimodal API; persist attempts with provenance; keep `main` local-default.

### Non-goals

Bulk 6k cloud OCR; overnight `transcribe-night` calling OpenRouter; silent image exfil.

### Shape

- New `VisionOCRProvider` (LiteLLM or OpenAI-compat OpenRouter) beside [`providers/ollama.py`](../src/transcribe/providers/ollama.py). `JobCoordinator` already takes a provider.
- Ack as severe as `--allow-remote-ollama`: images leave the machine.
- CLI: `transcribe run <project> --pages-file ids.txt --provider litellm --model google/gemini-2.5-flash-lite` (names illustrative) **or** Miss Desk “Retry these” bound to that provider.
- Fingerprint includes `provider` + remote model id so local successes still skip.
- Recipes: short OCR prompt; exclude thinking models.
- Keys only in gitignored `.env`. No keys in LaunchAgent plists.
- Tests: fake HTTP; refuse without ack; CI never bills.
- Optional later Nightshift job: **paused-by-default**, reads an export file, never part of 00:15 `transcribe-night`.

### When it is worth opening the branch

After 5-year local pair + optional rest 7b, if Review still has a **few hundred** bad pages and a Flash-Lite/Mistral OCR spot-check on 20 of them beats 7b. Cost of 200 pages is **dollars**, not the reason to delay local nights.

### Merge bar

Local-first default unchanged; privacy copy reviewed; cost note in runtime docs; Nightshift overnight still Ollama-only.

---

## 9. Foundation protocol (for a future user / other Mac)

Reproducible, hardware-labelled:

1. Pin hardware (chip, RAM) and `ollama -v`.
2. `python3 assessments/scripts/collect_model_stats.py` — corpus + errors + Nightshift scrape.
3. Mini probe: `python3 assessments/scripts/probe_focus.py` (or full `scripts/probe_ollama_vision_models.py` if you accept hours on 27b tags).
4. Dense-page probe: 4–10 **real** pages that already `token_repeat` on the candidate; do not trust mini-page glm/llava.
5. Fill the roles table: first OCR / compare / rank-only / do-not-use-first.
6. Schedule via **ops** (Nightshift env), not product forks.
7. Date the JSON; keep `/assessments/` tracked so the next host can compare.

### Model roles (this host, 2026-11-10)

| Role | Tag |
|------|-----|
| First scheduled OCR | `qwen2.5vl:7b` |
| Fast compare | `granite3.2-vision` |
| Already-library / speed | `qwen2.5vl:3b`, `deepseek-ocr` + `free_ocr` |
| Rank / composite | `qwen3:8b` |
| Manual OCR-oriented | `glm-ocr` (expect repeats on dense hand) |
| Probe later as MODEL_B | PaddleOCR-VL-1.6 (community) after recipe design |
| Do not use first | `gemma4*`, `qwen3-vl*`, `qwen3.6*`, `llama3.2-vision` |

Fingerprint note: changing `repeat_penalty` or frozen prompt **re-OCRs** succeeded pages once. Sampler-only overlays that are already in the hash will skip.

---

## 10. Follow-ups

| When | What | Repo |
|------|------|------|
| Next night | Confirm job log models line has **no glm** | Nightshift |
| This week | `SKIP_REST=1`, full-window 7b+granite on recent → from_2023 | Nightshift env |
| Optional | Rest 7b-only nights | Nightshift |
| Optional | 20-page PaddleOCR-VL probe; if it beats granite on this hand, set `MODEL_B` | Nightshift + later Transcribe recipe on a branch |
| Later | `feat/selective-remote-ocr` | Transcribe **branch**, not `main` |
| If asked | Refresh tracked `ocr_model_matrix.md` (probe date 2026-11-10) | Transcribe `main` — **out of this sitting** |

---

## Appendix — artifact index

| File | |
|------|--|
| [data/corpus-stats.json](data/corpus-stats.json) | Pages, notebooks, triple completion |
| [data/error-by-model.json](data/error-by-model.json) | Attempt histogram + example failures |
| [data/coverage-by-tier.json](data/coverage-by-tier.json) | Succeeded counts per tier per model |
| [data/nightshift-throughput.json](data/nightshift-throughput.json) | Night markdown + job log + forecast |
| [data/probe-results.json](data/probe-results.json) | Mini-page live probe |
| [data/probe-green-sample.json](data/probe-green-sample.json) | 4 green pages, not written to page-results |
| [data/chat-evidence.md](data/chat-evidence.md) | Transcript pointers |
| [scripts/collect_model_stats.py](scripts/collect_model_stats.py) | Rerun collector |
| [scripts/probe_focus.py](scripts/probe_focus.py) | Rerun focused probe |
