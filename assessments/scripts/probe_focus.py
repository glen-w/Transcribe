#!/usr/bin/env python3
"""Focused live Ollama probe for the assessment pack (not the full library).

Uses Transcribe's job prompt/recipe path via PYTHONPATH=src.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from transcribe.providers.ollama import OllamaVisionProvider, ollama_healthcheck  # noqa: E402
from transcribe.prompts import REGISTRY  # noqa: E402
from transcribe.services.model_advice import advise_model  # noqa: E402
from transcribe.services.ocr_model_recipes import recipe_for_model, recipe_prompt  # noqa: E402

DEFAULT_MODELS = (
    "glm-ocr:latest",
    "granite3.2-vision:latest",
    "qwen2.5vl:7b",
    "qwen2.5vl:3b",
    "deepseek-ocr:latest",
    "minicpm-v:8b",
    "gemma3:4b",
    "llava:7b",
    "qwen3-vl:4b",
)


def probe_one(provider: OllamaVisionProvider, name: str, image_bytes: bytes, num_predict: int) -> dict:
    recipe = recipe_for_model(name)
    use_recipe_prompt = recipe is not None and recipe.freeze_prompt
    prompt = recipe_prompt(recipe)[2] if use_recipe_prompt else REGISTRY["faithful_markdown"].body
    options = {"temperature": 0.0, "num_predict": num_predict}
    if recipe and recipe.generation_options:
        options.update(recipe.generation_options)
    row: dict = {
        "model": name,
        "advice_kind": advise_model(name, role="vision").kind,
        "prompt_id": recipe.prompt_id if use_recipe_prompt else "faithful_markdown",
        "recipe_id": recipe.recipe_id if recipe else "",
        "options": options,
    }
    t0 = time.monotonic()
    try:
        provider.probe_vision_model_load(model=name)
        row["load_probe"] = "ok"
    except Exception as exc:  # noqa: BLE001
        row["load_probe"] = f"fail: {exc}"
    try:
        res = provider.transcribe_image(
            model=name,
            prompt=prompt,
            image_bytes=image_bytes,
            options=options,
        )
        text = (res.text or "").strip()
        meta = res.provider_metadata or {}
        row["ocr_status"] = "empty" if not text else "ok"
        row["text_len"] = len(text)
        row["text_preview"] = text[:160].replace("\n", " ")
        row["eval_count"] = meta.get("eval_count")
        row["truncated"] = meta.get("truncated")
    except Exception as exc:  # noqa: BLE001
        row["ocr_status"] = "error"
        row["error"] = str(exc)[:240]
    row["elapsed_s"] = round(time.monotonic() - t0, 1)
    return row


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:11434")
    parser.add_argument("--fixture", type=Path, default=ROOT / "tests/fixtures/mini_page.png")
    parser.add_argument("--json", type=Path, default=ROOT / "assessments/data/probe-results.json")
    parser.add_argument("--timeout", type=float, default=180.0)
    parser.add_argument("--num-predict", type=int, default=512)
    parser.add_argument("--models", default=",".join(DEFAULT_MODELS))
    args = parser.parse_args()
    if not ollama_healthcheck(args.base_url):
        raise SystemExit(f"Ollama not reachable at {args.base_url}")
    image_bytes = args.fixture.read_bytes()
    provider = OllamaVisionProvider(args.base_url, request_timeout=args.timeout)
    names = [n.strip() for n in args.models.split(",") if n.strip()]
    results = []
    for i, name in enumerate(names, 1):
        print(f"[{i}/{len(names)}] {name}", flush=True)
        row = probe_one(provider, name, image_bytes, args.num_predict)
        print(
            f"  load={row.get('load_probe')} ocr={row.get('ocr_status')} "
            f"len={row.get('text_len', 0)} {row['elapsed_s']}s",
            flush=True,
        )
        results.append(row)
    args.json.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "collected_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "fixture": str(args.fixture),
        "hardware": "Apple M5 Pro 64GB",
        "note": "Focused subset; not every installed vision tag. llama3.2-vision / gemma4 skipped (known fail).",
        "results": results,
    }
    args.json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
