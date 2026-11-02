"""Streamlit rendering for analysis View bar charts.

Palette defaults and sanitise live in ``transcribe.config.chart_colors`` so
workspace config can resolve colours without importing this package.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from transcribe.config.chart_colors import (
    DEFAULT_EMOTION_COLORS,
    DEFAULT_SENTIMENT_COLORS,
    EMOTION_ORDER,
    SENTIMENT_ORDER,
    color_for_label,
    sanitise_chart_colors,
)

__all__ = [
    "DEFAULT_EMOTION_COLORS",
    "DEFAULT_SENTIMENT_COLORS",
    "EMOTION_ORDER",
    "SENTIMENT_ORDER",
    "color_for_label",
    "render_colored_bar_pairs",
    "sanitise_chart_colors",
]


def render_colored_bar_pairs(
    pairs: list[tuple[str, float]],
    *,
    x_name: str,
    y_name: str,
    palette: Mapping[str, str],
    sort_order: Sequence[str] | None = None,
    fallback: str = "#888888",
) -> None:
    import streamlit as st

    if not pairs:
        return
    order: list[str] = []
    if sort_order:
        order = [k for k in sort_order if any(label == k for label, _ in pairs)]
    for label, _ in pairs:
        if label not in order:
            order.append(label)
    sorted_pairs = sorted(
        pairs,
        key=lambda p: order.index(p[0]) if p[0] in order else len(order),
    )
    labels = [k for k, _ in sorted_pairs]
    values = [v for _, v in sorted_pairs]
    try:
        import altair as alt
        import pandas as pd

        df = pd.DataFrame({x_name: labels, y_name: values})
        color_scale = alt.Scale(
            domain=labels,
            range=[color_for_label(t, palette, fallback=fallback) for t in labels],
        )
        chart = (
            alt.Chart(df)
            .mark_bar()
            .encode(
                x=alt.X(f"{x_name}:N", title=x_name, sort=order),
                y=alt.Y(f"{y_name}:Q", title=y_name),
                color=alt.Color(f"{x_name}:N", scale=color_scale, legend=None),
                tooltip=[
                    alt.Tooltip(f"{x_name}:N", title=x_name.title()),
                    alt.Tooltip(f"{y_name}:Q", title=y_name.title()),
                ],
            )
            .properties(height=220)
        )
        st.altair_chart(chart, width="stretch")
    except Exception:
        st.bar_chart({x_name: labels, y_name: values}, x=x_name, y=y_name)
