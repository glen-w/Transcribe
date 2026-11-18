"""Schedulable OCR vs deferred error tails; ocr-queue listing."""

from __future__ import annotations

import json
from pathlib import Path

from transcribe.__main__ import main
from transcribe.domain.models import EMPTY_OUTPUT_CODE, TOKEN_REPEAT_CODE
from transcribe.services.ocr_schedule import (
    OCR_FAIL_DEFER_THRESHOLD,
    list_schedulable_notebooks,
    notebook_has_schedulable_ocr,
    page_model_state,
)


def _fail(model: str, code: str, *, n: int, fp: str = "fp-a") -> list[dict]:
    rows = []
    for i in range(n):
        rows.append(
            {
                "attempt_id": f"{model}-{code}-{i}",
                "status": "failed",
                "attempt_kind": "vision",
                "input_fingerprint": fp,
                "fingerprint_payload": {"model_name": model},
                "raw_text": "",
                "error": {"code": code, "message": code},
                "provenance": {"model_name": model},
            }
        )
    return rows


def _ok(model: str, text: str = "hello") -> dict:
    return {
        "attempt_id": f"ok-{model}",
        "status": "succeeded",
        "attempt_kind": "vision",
        "input_fingerprint": "fp-ok",
        "raw_text": text,
        "provenance": {"model_name": model},
    }


def write_nb(
    root: Path,
    name: str,
    *,
    year: int | None,
    attempts: list[dict],
    extra_fails: list[dict] | None = None,
) -> Path:
    nb = root / name
    (nb / "results").mkdir(parents=True)
    page_id = "page-1"
    date = {"y": year, "m": 6, "d": 1} if year else None
    (nb / "project.json").write_text(
        json.dumps(
            {
                "format": "transcribe.project",
                "id": name,
                "title": name,
                "pages": [{"page_id": page_id, "date": date}],
            }
        ),
        encoding="utf-8",
    )
    all_attempts = list(attempts) + list(extra_fails or [])
    (nb / "results" / f"{page_id}.json").write_text(
        json.dumps(
            {
                "format": "transcribe.page-result",
                "page_id": page_id,
                "attempts": all_attempts,
            }
        ),
        encoding="utf-8",
    )
    return nb


def test_page_model_deferred_after_three_token_repeats() -> None:
    result = {"attempts": _fail("granite3.2-vision", TOKEN_REPEAT_CODE, n=3)}
    assert page_model_state(result, "granite3.2-vision") == "deferred"
    assert page_model_state(result, "qwen2.5vl:7b") == "open"


def test_page_model_deferred_empty_output() -> None:
    result = {"attempts": _fail("granite3.2-vision", EMPTY_OUTPUT_CODE, n=3)}
    assert page_model_state(result, "granite3.2-vision") == "deferred"


def test_two_fails_still_open() -> None:
    result = {"attempts": _fail("granite3.2-vision", TOKEN_REPEAT_CODE, n=2)}
    assert page_model_state(result, "granite3.2-vision") == "open"


def test_success_beats_prior_failures() -> None:
    result = {
        "attempts": _fail("qwen2.5vl:7b", TOKEN_REPEAT_CODE, n=3) + [_ok("qwen2.5vl:7b")]
    }
    assert page_model_state(result, "qwen2.5vl:7b") == "succeeded"


def test_deferred_only_notebook_not_schedulable(tmp_path: Path) -> None:
    models = {"qwen2.5vl:7b", "granite3.2-vision"}
    write_nb(
        tmp_path,
        "almost",
        year=2026,
        attempts=[_ok("qwen2.5vl:7b")] + _fail("granite3.2-vision", TOKEN_REPEAT_CODE, n=3),
    )
    write_nb(
        tmp_path,
        "empty",
        year=2026,
        attempts=[],
    )
    assert notebook_has_schedulable_ocr(tmp_path / "almost", models) is False
    assert notebook_has_schedulable_ocr(tmp_path / "empty", models) is True
    names = [p.name for p in list_schedulable_notebooks(tmp_path, models, tier="recent")]
    assert names == ["empty"]


def test_ocr_queue_cli_omits_deferred_only(tmp_path: Path, capsys) -> None:
    write_nb(
        tmp_path,
        "tail",
        year=2026,
        attempts=[_ok("qwen2.5vl:7b")]
        + _fail("granite3.2-vision", TOKEN_REPEAT_CODE, n=OCR_FAIL_DEFER_THRESHOLD),
    )
    write_nb(tmp_path, "harden", year=2026, attempts=[])
    rc = main(
        [
            "ocr-queue",
            "--projects-dir",
            str(tmp_path),
            "--tier",
            "recent",
            "--model",
            "qwen2.5vl:7b",
            "--model",
            "granite3.2-vision",
        ]
    )
    assert rc == 0
    out = capsys.readouterr().out.strip().splitlines()
    assert [Path(p).name for p in out] == ["harden"]


def test_ocr_queue_cli_182_succeeded_2_deferred_prints_nothing(
    tmp_path: Path, capsys
) -> None:
    """Plan smoke: almost-done book with only deferred tails is off the queue."""
    nb = tmp_path / "almost"
    pages: list[dict] = []
    results = nb / "results"
    results.mkdir(parents=True)
    qwen, granite = "qwen2.5vl:7b", "granite3.2-vision"
    for i in range(1, 185):
        page_id = f"page-{i:03d}"
        pages.append({"page_id": page_id, "date": {"y": 2026, "m": 6, "d": 1}})
        if i <= 182:
            attempts = [_ok(qwen), _ok(granite)]
        else:
            attempts = [_ok(qwen)] + _fail(
                granite, TOKEN_REPEAT_CODE, n=OCR_FAIL_DEFER_THRESHOLD
            )
        (results / f"{page_id}.json").write_text(
            json.dumps(
                {
                    "format": "transcribe.page-result",
                    "page_id": page_id,
                    "attempts": attempts,
                }
            ),
            encoding="utf-8",
        )
    (nb / "project.json").write_text(
        json.dumps(
            {
                "format": "transcribe.project",
                "id": "almost",
                "title": "almost",
                "pages": pages,
            }
        ),
        encoding="utf-8",
    )
    rc = main(
        [
            "ocr-queue",
            "--projects-dir",
            str(tmp_path),
            "--tier",
            "recent",
            "--model",
            qwen,
            "--model",
            granite,
        ]
    )
    assert rc == 0
    assert capsys.readouterr().out.strip() == ""
