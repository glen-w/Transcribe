"""Clock / ISO helpers for injectable ports."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from transcribe.ports import parse_iso, to_iso


def test_to_iso_rejects_naive_datetime() -> None:
    with pytest.raises(ValueError, match="naive"):
        to_iso(datetime(2024, 1, 2, 3, 4, 5))


def test_to_iso_parse_iso_round_trip() -> None:
    original = datetime(2024, 6, 15, 12, 30, 45, 123456, tzinfo=timezone.utc)
    stamp = to_iso(original)
    assert stamp.endswith("Z")
    assert stamp == "2024-06-15T12:30:45.123Z"
    parsed = parse_iso(stamp)
    assert parsed.tzinfo is not None
    assert parsed.astimezone(timezone.utc).replace(microsecond=123000) == parsed.replace(
        microsecond=123000
    )
    assert parsed.year == 2024
    assert parsed.month == 6
    assert parsed.day == 15
    assert parsed.hour == 12
    assert parsed.minute == 30
    assert parsed.second == 45


def test_parse_iso_rejects_naive() -> None:
    with pytest.raises(ValueError, match="naive"):
        parse_iso("2024-01-02T03:04:05")


def test_parse_iso_accepts_offset_form() -> None:
    parsed = parse_iso("2024-01-02T03:04:05.000+00:00")
    assert parsed.tzinfo is not None
    assert to_iso(parsed) == "2024-01-02T03:04:05.000Z"
