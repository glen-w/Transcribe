# Fine-tune export (external training)

Transcribe can export a local dataset of page images + preferred/active transcriptions for **external** fine-tuning. Training is not performed inside this project.

## What you get

Running **Export → Fine-tune dataset** (UI) or `transcribe export-finetune <project>` writes:

```
finetune_export_<stamp>/
  manifest.json       # knobs, counts, model stats
  samples.jsonl       # one JSON object per included page
  images/<page_id>.png
  README.txt
```

Contract detail: [contracts/finetune-export.md](contracts/finetune-export.md). Pages with `page_role=scan` (kept scans) are omitted — they are not training positives.

## Typical external workflow

1. Prefer OCR attempts in Review (or rely on active / human edits per export knobs).
2. Export the fine-tune package from Transcribe (Export → Fine-tune dataset, or `transcribe export-finetune`).
3. Train a vision–language model elsewhere (Unsloth, Hugging Face TRL, or any SFT tool that accepts image+text JSONL). Transcribe does not train.
4. **Install in local Ollama.** Example:

   ```text
   ollama create my-hand -f Modelfile
   ```

   A Modelfile is typically `FROM <base-vision-tag>` plus an adapter path or a GGUF `FROM`. The export folder’s `README.txt` repeats this.
5. **Select the tag in Transcribe.** Settings → Models → Refresh, then pick it for OCR. If the tag needs a frozen prompt or generation overlay, add a recipe under **Settings → Models → OCR model recipes** (`match_tokens` for your tag; `freeze_prompt` only when the notebook prompt must not apply). See [ocr_model_recipes.md](runtime/ocr_model_recipes.md).
6. **Verify with multipass.** Transcribe → Advanced: run a multipass on this notebook with your previous baseline plus the new tag. Prefer/compare in Review. A better hand model is the goal; an in-app trainer is a non-goal.

## Privacy

Images and text stay on disk in the export folder. They leave the machine only if **you** copy or upload that folder to a training environment.

## Knobs

| Knob | Effect |
|------|--------|
| Prefer effective text | Use human `edited_text` when present |
| Require preferred | Skip pages without `preferred_attempt_id` |
| Include rejected | Attach other vision candidates for preference/DPO-style training |
| Image mode | `copy` or `hardlink` of active page renders |

## Detection fine-tune export

Approved/rejected detection findings can be exported the same way (images +
page text + labels) via **Export → Detection fine-tune** or
`transcribe export-detection-finetune <project>`. Contract:
[contracts/detection-finetune-export.md](contracts/detection-finetune-export.md).

## Non-goals

- No training loop, GPU job, or weight upload inside Transcribe
- No cloud fine-tune API integration
