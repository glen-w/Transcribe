"""Chart colour palettes for analysis View bar charts.

Host-agnostic: workspace config and CLI must resolve palettes without
importing ``transcribe.ui`` or Streamlit. Streamlit rendering stays in
``transcribe.ui.chart_colors``.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from transcribe.tagging.colors import parse_hex_color

DEFAULT_SENTIMENT_COLORS: dict[str, str] = {
    "negative": "#c43c3c",
    "neutral": "#e6b422",
    "positive": "#2f8f4e",
}

DEFAULT_EMOTION_COLORS: dict[str, str] = {
    "anger": "#c43c3c",
    "fear": "#e07070",
    "joy": "#2f8f4e",
    "sadness": "#888888",
    "surprise": "#e6b422",
    "trust": "#4a7ab8",
}

SENTIMENT_ORDER = ("negative", "neutral", "positive")
EMOTION_ORDER = ("anger", "fear", "joy", "sadness", "surprise", "trust")


def _sanitise_palette(
    raw: Any,
    *,
    defaults: Mapping[str, str],
) -> dict[str, str]:
    out = dict(defaults)
    if not isinstance(raw, Mapping):
        return out
    for key, value in raw.items():
        label = str(key).strip().casefold()
        if not label or label not in defaults:
            continue
        try:
            out[label] = parse_hex_color(str(value))
        except ValueError:
            continue
    return out


def sanitise_chart_colors(data: Mapping[str, Any] | None) -> dict[str, dict[str, str]]:
    data = data or {}
    return {
        "sentiment": _sanitise_palette(data.get("sentiment"), defaults=DEFAULT_SENTIMENT_COLORS),
        "emotion": _sanitise_palette(data.get("emotion"), defaults=DEFAULT_EMOTION_COLORS),
    }


def color_for_label(label: str, palette: Mapping[str, str], *, fallback: str = "#888888") -> str:
    key = str(label).casefold()
    return palette.get(key, fallback)
