"""Queued-source hops for the shared OCR / Analyse batch picker (no Streamlit widgets)."""

from __future__ import annotations

from transcribe.ui.batch_source_picker import apply_queued_source, widget_keys
from transcribe.ui.targets import (
    ANALYSE_BATCH_SOURCE_KEY,
    TRANSCRIBE_BATCH_SOURCE_KEY,
)


def test_widget_keys_keep_purpose_prefixes() -> None:
    assert widget_keys("tx")["source"] == "tx_batch_source"
    assert widget_keys("ax")["source"] == "ax_batch_source"
    assert widget_keys("tx")["pick"] == "tx_batch_pick"
    assert widget_keys("ax")["pick"] == "ax_batch_pick"


def test_ocr_queued_source_applies_only_when_unset() -> None:
    options = ("pending", "import_run", "pick")
    session = {TRANSCRIBE_BATCH_SOURCE_KEY: "pick", "tx_batch_source": "pending"}
    apply_queued_source(
        session,
        queued_key=TRANSCRIBE_BATCH_SOURCE_KEY,
        widget_key="tx_batch_source",
        options=options,
        only_if_unset=True,
    )
    assert session["tx_batch_source"] == "pending"
    assert TRANSCRIBE_BATCH_SOURCE_KEY not in session


def test_analyse_queued_source_overrides_and_defaults_to_pick() -> None:
    options = ("pick", "pending", "import_run")
    session = {ANALYSE_BATCH_SOURCE_KEY: "import_run"}
    apply_queued_source(
        session,
        queued_key=ANALYSE_BATCH_SOURCE_KEY,
        widget_key="ax_batch_source",
        options=options,
        default="pick",
    )
    assert session["ax_batch_source"] == "import_run"

    empty: dict[str, str] = {}
    apply_queued_source(
        empty,
        queued_key=ANALYSE_BATCH_SOURCE_KEY,
        widget_key="ax_batch_source",
        options=options,
        default="pick",
    )
    assert empty["ax_batch_source"] == "pick"
