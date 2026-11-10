# Chat / transcript evidence (OCR models)

Short excerpts that explain *why* recipes, miss-desk codes, and the glm Nightshift drop exist. Not a git history. Transcript ids are Cursor agent chats under this workspace.

## [Harden OCR recipes](7bf208e5-6865-4853-be09-da242203a705)

Plan table (2026-10-ish sitting) mapped failures to whether a recipe can help:

- **glm-ocr** `token repeat limit reached` (~58% → ~12% on a `black` spot-check with `repeat_penalty=1.2`) — recipe overlay, do not change prompt.
- **DeepSeek-OCR** empty `eval_count=1` on long `faithful_*` — freeze `free_ocr`.
- **Thinking** tags (`gemma4`, `qwen3-vl`) empty OCR — picker exclusion, not a prompt patch.
- **llama3.2-vision** `mllama` load fail — hide + `model_load` circuit.

This sitting’s corpus scan shows the glm recipe **did not** hold at library scale (still ~45% fail with `recipe_id=glm_ocr`). That matches Nightshift’s 2026-11-10 retirement of glm from the scheduled set.

## [Durable notebook / miss desk](3ba24a78-ad59-4af3-bae5-6dd423d058e9)

Wave 3 grouped Failed OCR by `error.code` (`empty_output`, `token_repeat`, `model_load`, `timeout`, `circuit_open`) and Retry-these builds a normal OCR plan for that page set. Uncorrected misses are not fine-tune targets. This assessment uses the same buckets.

## [OCR generate failures review](docs/reviews/ocr_generate_failures.md) (docs, not chat)

Night of 2026-10-22/23, notebook `black`: glm 29 succeeded / 39 token-repeat / 1 timeout among finished pages; granite truncated looping text stored as success. Decisions: classify `token_repeat` as non-retriable; glm `repeat_penalty`; truncated+repetition fails; SIGINT abort; `:latest` identity alias.

## This assessment sitting ([OCR model assessment](de6624c0-614e-459b-bad1-e3dfe22424b1))

Constraints locked before collection:

- Transcribe `main` stays clean; gitignored `/assessments/` only.
- ASAP backlog is a **Nightshift** ops change, not a Transcribe provider.
- Selective remote offload is **`feat/selective-remote-ocr` later**, named miss-desk pages only.
- Last ~5 years keep multipass + composite; `rest` is speed-first.
- Cloud images: selective, not bulk.
