"""Analysis unit-id helpers stay host-agnostic."""

from __future__ import annotations

from transcribe.analysis.units import page_id_from_unit_id


def test_page_id_from_unit_id() -> None:
    assert page_id_from_unit_id("abc") == "abc"
    assert page_id_from_unit_id("abc/span:10-40") == "abc"
    assert page_id_from_unit_id("") is None
    assert page_id_from_unit_id(None) is None
