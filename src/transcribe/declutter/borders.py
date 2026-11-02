"""Deterministic scanner-bed, overscan, binding-gutter, and edge-shadow crop (Pillow-only)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

from PIL import Image

Edge = Literal["left", "right", "top", "bottom"]


@dataclass(frozen=True)
class ScanBorderParams:
    min_dimension_px: int = 64
    grey_mean_min: int = 40
    # Include light grey / off-white scanner beds (~210–230). Stay below typical
    # cream paper (~240) so blank cream pages are not walked as bed.
    grey_mean_max: int = 235
    max_strip_variance: float = 100.0
    # When a strip mean stays bed-like but variance spikes (scanner texture /
    # JPEG noise), keep walking until variance reaches this paper-like floor
    # or mean leaves the grey band. Handwriting/ruled paper is typically >>2e3.
    noisy_bed_variance_max: float = 800.0
    # Once a bed mean is established, stop when strip mean drifts farther than
    # this (prevents green/kraft page content in the grey luminance band from
    # being walked as noisy bed until soft_max).
    bed_ref_mean_tol: float = 30.0
    interior_probe_px: int = 16
    # Skip soft page-edge shadow between bed and bright paper before probing.
    # Immediate adjacent probes often sit in the transition and fail min_mean_delta
    # even when a clear grey bed is present (common on flatbed overscan).
    interior_probe_offset_px: int = 32
    min_mean_delta: float = 25.0
    paper_inset_px: int = 2
    min_remaining_fraction_num: int = 70
    min_remaining_fraction_den: int = 100
    min_remaining_edge_px: int = 32
    aspect_min_num: int = 1
    aspect_min_den: int = 5
    aspect_max_num: int = 5
    aspect_max_den: int = 1
    # Soft search budget retained in frozen param identity (legacy / journal compat).
    max_band_cap_px: int = 400


@dataclass(frozen=True)
class UniformOverscanParams:
    """Stark-white blank overscan / letterbox gutter (not grey scanner bed)."""

    min_dimension_px: int = 64
    # Stark white only (#FFFFFF gutters / scanner software pads). Keep this high
    # so near-white paper (e.g. L≈252) is not walked as overscan until content.
    # Cream paper (~240) fails white_mean_min and relies on min_mean_delta vs 255.
    white_mean_min: int = 254
    max_strip_variance: float = 100.0
    interior_probe_px: int = 16
    interior_probe_offset_px: int = 32
    # Cream (~240) vs stark white (255) is ~15; keep this below that gap.
    min_mean_delta: float = 12.0
    paper_inset_px: int = 2
    min_remaining_fraction_num: int = 70
    min_remaining_fraction_den: int = 100
    min_remaining_edge_px: int = 32
    aspect_min_num: int = 1
    aspect_min_den: int = 5
    aspect_max_num: int = 5
    aspect_max_den: int = 1
    max_band_cap_px: int = 400


@dataclass(frozen=True)
class CornerWedgeParams:
    """Residual scanner-bed wedges at rounded page corners (edge-anchored only)."""

    min_dimension_px: int = 64
    max_wedge_px: int = 48
    min_wedge_px: int = 6
    # Local 3×3 mean/var must look like light grey bed or stark white. Mid-tone
    # page content (green covers, kraft) sits below this and must not match.
    bed_mean_min: int = 175
    local_radius_px: int = 1
    paper_inset_px: int = 1
    min_remaining_fraction_num: int = 70
    min_remaining_fraction_den: int = 100
    min_remaining_edge_px: int = 32
    aspect_min_num: int = 1
    aspect_min_den: int = 5
    aspect_max_num: int = 5
    aspect_max_den: int = 1


@dataclass(frozen=True)
class BindingGutterParams:
    """Dark left/right binding or lid strip (below grey-bed luminance)."""

    min_dimension_px: int = 64
    # Stay below ScanBorderParams.grey_mean_min so grey-bed walk owns mid greys.
    dark_mean_min: int = 0
    dark_mean_max: int = 38
    # Spine texture / JPEG noise; handwriting on paper is typically >>2e3.
    max_strip_variance: float = 1200.0
    gutter_ref_mean_tol: float = 25.0
    interior_probe_px: int = 16
    interior_probe_offset_px: int = 32
    # Paper must be substantially brighter than the dark strip.
    min_mean_delta: float = 40.0
    paper_inset_px: int = 2
    min_remaining_fraction_num: int = 70
    min_remaining_fraction_den: int = 100
    min_remaining_edge_px: int = 32
    aspect_min_num: int = 1
    aspect_min_den: int = 5
    aspect_max_num: int = 5
    aspect_max_den: int = 1
    max_band_cap_px: int = 96


@dataclass(frozen=True)
class EdgeShadowParams:
    """Short remaining edge-anchored shadow band (outside the page)."""

    min_dimension_px: int = 64
    shadow_mean_min: int = 80
    # Above grey_mean_max so residual near-paper darkening can still qualify.
    shadow_mean_max: int = 245
    # Textured shadow that grey noisy-bed (800) rejects; handwriting is >>2e3.
    max_strip_variance: float = 1500.0
    # Tight so a soft page-edge gradient into paper stops before min_band.
    shadow_ref_mean_tol: float = 8.0
    interior_probe_px: int = 16
    interior_probe_offset_px: int = 32
    min_mean_delta: float = 25.0
    paper_inset_px: int = 1
    min_remaining_fraction_num: int = 70
    min_remaining_fraction_den: int = 100
    min_remaining_edge_px: int = 32
    aspect_min_num: int = 1
    aspect_min_den: int = 5
    aspect_max_num: int = 5
    aspect_max_den: int = 1
    max_band_cap_px: int = 40


@dataclass(frozen=True)
class LidSliverParams:
    """Very thin uniform lid/background sliver below the normal min band.

    Existing walks reject bands thinner than ``_min_band_px`` (8-16px) so a
    4-15px scanner-lid sliver survives. This op accepts only a full-edge,
    near-uniform strip whose mean differs clearly from the interior probe.
    Crop insets only; never touches interior pixels.
    """

    min_dimension_px: int = 64
    min_sliver_px: int = 4
    max_sliver_px: int = 15
    # Lid slivers are solid dark/coloured scanner-lid bands. Near-paper means
    # (>= this) belong to overscan/shadow ops or are page-edge gradients.
    band_mean_max: float = 200.0
    max_strip_variance: float = 300.0
    ref_mean_tol: float = 10.0
    interior_probe_px: int = 16
    interior_probe_offset_px: int = 2
    min_mean_delta: float = 25.0
    paper_inset_px: int = 1
    min_remaining_fraction_num: int = 70
    min_remaining_fraction_den: int = 100
    min_remaining_edge_px: int = 32
    aspect_min_num: int = 1
    aspect_min_den: int = 5
    aspect_max_num: int = 5
    aspect_max_den: int = 1


SCAN_BORDER_PARAMS = ScanBorderParams()
UNIFORM_OVERSCAN_PARAMS = UniformOverscanParams()
CORNER_WEDGE_PARAMS = CornerWedgeParams()
BINDING_GUTTER_PARAMS = BindingGutterParams()
EDGE_SHADOW_PARAMS = EdgeShadowParams()
LID_SLIVER_PARAMS = LidSliverParams()


@dataclass(frozen=True)
class PunchHoleParams:
    """Blank outer strip that contains a dark punch hole. Interior stays."""

    min_dimension_px: int = 64
    min_band_px: int = 14
    max_band_px: int = 36
    dark_max: int = 70
    min_dark_pixels: int = 12
    paper_mean_min: float = 210.0
    paper_var_max: float = 400.0


@dataclass(frozen=True)
class CalibrationStripeParams:
    """Edge-anchored high-contrast bar. Does not crop interior bars."""

    min_dimension_px: int = 64
    min_px: int = 8
    max_px: int = 28
    dark_max: int = 50
    light_min: int = 200
    min_run_px: int = 4
    min_runs: int = 4
    paper_mean_min: float = 180.0
    paper_var_max: float = 250.0


PUNCH_HOLE_PARAMS = PunchHoleParams()
CALIBRATION_STRIPE_PARAMS = CalibrationStripeParams()

# Multi-pass budget: L-shaped grey+white overscan needs a second crop after the
# first edge type is removed so full-strip stats become uniform again. Extra
# passes cover binding gutter / residual edge shadow after beds are gone.
_MAX_BORDER_PASSES = 6


def _min_band_px(dim: int) -> int:
    # At least 8px; grow gently with size but cap so narrow top beds (~20–30px)
    # on tall scans still qualify (uncapped 1% of 3000px = 30 rejects a 28px bed).
    return max(8, min(16, (dim + 99) // 100))


def _soft_max_band_px(
    dim: int,
    *,
    min_remaining_edge_px: int,
    min_remaining_fraction_num: int,
    min_remaining_fraction_den: int,
) -> int:
    """Hard upper bound for an edge band walk.

    Leaves ``min_remaining_edge_px`` and respects the remaining-area fraction so a
    single edge cannot consume the page before the joint remaining-area check.
    """
    by_edge = max(0, dim - min_remaining_edge_px)
    by_frac = dim - ((dim * min_remaining_fraction_num) // min_remaining_fraction_den)
    return min(by_edge, by_frac)


def _histogram_mean_var(hist: list[int]) -> tuple[float, float]:
    n = sum(hist)
    if n == 0:
        return 0.0, 0.0
    mean = sum(i * hist[i] for i in range(256)) / n
    var = sum(hist[i] * (i - mean) ** 2 for i in range(256)) / n
    return mean, var


def _strip_stats_vertical(gray: Image.Image, x: int) -> tuple[float, float]:
    """Mean and population variance for column x (full height)."""
    height = gray.size[1]
    hist = gray.crop((x, 0, x + 1, height)).histogram()[:256]
    return _histogram_mean_var(hist)


def _strip_stats_horizontal(gray: Image.Image, y: int) -> tuple[float, float]:
    width = gray.size[0]
    hist = gray.crop((0, y, width, y + 1)).histogram()[:256]
    return _histogram_mean_var(hist)


def _region_mean_vertical(gray: Image.Image, x0: int, x1: int) -> float:
    """Mean of columns [x0, x1)."""
    if x1 <= x0:
        return 0.0
    height = gray.size[1]
    hist = gray.crop((x0, 0, x1, height)).histogram()[:256]
    mean, _var = _histogram_mean_var(hist)
    return mean


def _region_mean_horizontal(gray: Image.Image, y0: int, y1: int) -> float:
    if y1 <= y0:
        return 0.0
    width = gray.size[0]
    hist = gray.crop((0, y0, width, y1)).histogram()[:256]
    mean, _var = _histogram_mean_var(hist)
    return mean


def _is_scanner_grey(mean: float, var: float, params: ScanBorderParams) -> bool:
    return params.grey_mean_min <= mean <= params.grey_mean_max and var <= params.max_strip_variance


def _mean_in_grey_range(mean: float, params: ScanBorderParams) -> bool:
    return params.grey_mean_min <= mean <= params.grey_mean_max


def _is_noisy_bed(mean: float, var: float, params: ScanBorderParams) -> bool:
    """Bed-like mean with elevated variance (texture / compression), not paper."""
    return _mean_in_grey_range(mean, params) and var <= params.noisy_bed_variance_max


def _is_stark_white(mean: float, var: float, params: UniformOverscanParams) -> bool:
    return mean >= params.white_mean_min and var <= params.max_strip_variance


def _walk_grey_band(
    *,
    dim: int,
    params: ScanBorderParams,
    sample: Callable[[int], tuple[float, float]],
) -> int:
    """Walk from the edge while columns/rows look like scanner grey.

    Continues up to ``soft_max`` (remaining-area safe). After the strict
    low-variance walk stops, tolerates noisy bed strips whose mean remains grey
    so JPEG/scanner texture does not truncate the band early.

    A reference mean from the first bed strips stops the walk when luminance
    drifts (e.g. light-grey bed → green/kraft page still inside grey_mean_max).
    """
    soft_max = _soft_max_band_px(
        dim,
        min_remaining_edge_px=params.min_remaining_edge_px,
        min_remaining_fraction_num=params.min_remaining_fraction_num,
        min_remaining_fraction_den=params.min_remaining_fraction_den,
    )
    min_band = _min_band_px(dim)
    k = 0
    ref_mean: float | None = None
    while k < soft_max:
        mean, var = sample(k)
        if ref_mean is not None and abs(mean - ref_mean) > params.bed_ref_mean_tol:
            break
        if _is_scanner_grey(mean, var, params):
            if ref_mean is None:
                ref_mean = mean
            k += 1
            continue
        # Strict grey ended. Allow noisy continuation only once we already have a
        # band and only while mean stays bed-like below the paper-variance floor.
        if k >= min_band and _is_noisy_bed(mean, var, params):
            k += 1
            continue
        break
    return k


def _walk_white_band(
    *,
    dim: int,
    params: UniformOverscanParams,
    sample: Callable[[int], tuple[float, float]],
) -> int:
    """Walk from the edge while columns/rows are stark uniform white."""
    soft_max = _soft_max_band_px(
        dim,
        min_remaining_edge_px=params.min_remaining_edge_px,
        min_remaining_fraction_num=params.min_remaining_fraction_num,
        min_remaining_fraction_den=params.min_remaining_fraction_den,
    )
    k = 0
    while k < soft_max:
        mean, var = sample(k)
        if _is_stark_white(mean, var, params):
            k += 1
            continue
        break
    return k


def _is_binding_gutter(mean: float, var: float, params: BindingGutterParams) -> bool:
    return params.dark_mean_min <= mean <= params.dark_mean_max and var <= params.max_strip_variance


def _walk_dark_gutter_band(
    *,
    dim: int,
    params: BindingGutterParams,
    sample: Callable[[int], tuple[float, float]],
) -> int:
    """Walk left/right while columns look like a dark binding or lid strip."""
    soft_max = min(
        _soft_max_band_px(
            dim,
            min_remaining_edge_px=params.min_remaining_edge_px,
            min_remaining_fraction_num=params.min_remaining_fraction_num,
            min_remaining_fraction_den=params.min_remaining_fraction_den,
        ),
        params.max_band_cap_px,
    )
    k = 0
    ref_mean: float | None = None
    while k < soft_max:
        mean, var = sample(k)
        if not _is_binding_gutter(mean, var, params):
            break
        if ref_mean is not None and abs(mean - ref_mean) > params.gutter_ref_mean_tol:
            break
        if ref_mean is None:
            ref_mean = mean
        k += 1
    return k


def _is_edge_shadow(mean: float, var: float, params: EdgeShadowParams) -> bool:
    return (
        params.shadow_mean_min <= mean <= params.shadow_mean_max
        and var <= params.max_strip_variance
    )


def _walk_edge_shadow_band(
    *,
    dim: int,
    params: EdgeShadowParams,
    sample: Callable[[int], tuple[float, float]],
) -> int:
    """Walk a short remaining shadow band; stop on luminance drift into paper."""
    soft_max = min(
        _soft_max_band_px(
            dim,
            min_remaining_edge_px=params.min_remaining_edge_px,
            min_remaining_fraction_num=params.min_remaining_fraction_num,
            min_remaining_fraction_den=params.min_remaining_fraction_den,
        ),
        params.max_band_cap_px,
    )
    k = 0
    ref_mean: float | None = None
    while k < soft_max:
        mean, var = sample(k)
        if not _is_edge_shadow(mean, var, params):
            break
        if ref_mean is not None and abs(mean - ref_mean) > params.shadow_ref_mean_tol:
            break
        if ref_mean is None:
            ref_mean = mean
        k += 1
    return k


def _inset_from_band(
    *,
    dim: int,
    k: int,
    min_mean_delta: float,
    paper_inset_px: int,
    min_remaining_edge_px: int,
    min_remaining_fraction_num: int,
    min_remaining_fraction_den: int,
    mu_band: float,
    mu_probe: float,
    require_probe_brighter: bool = False,
) -> int:
    min_band = _min_band_px(dim)
    if k < min_band:
        return 0
    soft_max = _soft_max_band_px(
        dim,
        min_remaining_edge_px=min_remaining_edge_px,
        min_remaining_fraction_num=min_remaining_fraction_num,
        min_remaining_fraction_den=min_remaining_fraction_den,
    )
    if k >= soft_max:
        return 0
    if require_probe_brighter:
        if mu_probe - mu_band < min_mean_delta:
            return 0
    elif abs(mu_band - mu_probe) < min_mean_delta:
        return 0
    inset = k + paper_inset_px
    max_inset = dim - min_remaining_edge_px
    if max_inset < k:
        return 0
    if inset > max_inset:
        inset = max_inset
    return inset


def _interior_probe_span(
    remaining: int, *, interior_probe_px: int, interior_probe_offset_px: int
) -> tuple[int, int]:
    """Return (offset, probe_width) into the page past a detected band.

    Prefers a full ``interior_probe_px`` window; shrinks the soft-shadow offset
    first when remaining interior is tight.
    """
    if remaining <= 0:
        return 0, 0
    offset = min(
        interior_probe_offset_px,
        max(0, remaining - interior_probe_px),
    )
    probe = min(interior_probe_px, remaining - offset)
    return offset, probe


def _edge_inset(
    gray: Image.Image,
    edge: Edge,
    *,
    walk: Callable[..., int],
    walk_params: ScanBorderParams | UniformOverscanParams | BindingGutterParams | EdgeShadowParams,
    require_probe_brighter: bool = False,
) -> int:
    width, height = gray.size
    dim = width if edge in ("left", "right") else height

    if edge == "left":

        def sample(k: int) -> tuple[float, float]:
            return _strip_stats_vertical(gray, k)

        def band_mean(k: int) -> float:
            return _region_mean_vertical(gray, 0, k)

        def probe_mean(k: int, offset: int, probe: int) -> float:
            return _region_mean_vertical(gray, k + offset, k + offset + probe)

    elif edge == "right":

        def sample(k: int) -> tuple[float, float]:
            return _strip_stats_vertical(gray, width - 1 - k)

        def band_mean(k: int) -> float:
            return _region_mean_vertical(gray, width - k, width)

        def probe_mean(k: int, offset: int, probe: int) -> float:
            return _region_mean_vertical(gray, width - k - offset - probe, width - k - offset)

    elif edge == "top":

        def sample(k: int) -> tuple[float, float]:
            return _strip_stats_horizontal(gray, k)

        def band_mean(k: int) -> float:
            return _region_mean_horizontal(gray, 0, k)

        def probe_mean(k: int, offset: int, probe: int) -> float:
            return _region_mean_horizontal(gray, k + offset, k + offset + probe)

    else:  # bottom

        def sample(k: int) -> tuple[float, float]:
            return _strip_stats_horizontal(gray, height - 1 - k)

        def band_mean(k: int) -> float:
            return _region_mean_horizontal(gray, height - k, height)

        def probe_mean(k: int, offset: int, probe: int) -> float:
            return _region_mean_horizontal(gray, height - k - offset - probe, height - k - offset)

    k = walk(dim=dim, params=walk_params, sample=sample)
    remaining = dim - k
    offset, probe = _interior_probe_span(
        remaining,
        interior_probe_px=walk_params.interior_probe_px,
        interior_probe_offset_px=walk_params.interior_probe_offset_px,
    )
    if probe <= 0:
        return 0
    return _inset_from_band(
        dim=dim,
        k=k,
        min_mean_delta=walk_params.min_mean_delta,
        paper_inset_px=walk_params.paper_inset_px,
        min_remaining_edge_px=walk_params.min_remaining_edge_px,
        min_remaining_fraction_num=walk_params.min_remaining_fraction_num,
        min_remaining_fraction_den=walk_params.min_remaining_fraction_den,
        mu_band=band_mean(k),
        mu_probe=probe_mean(k, offset, probe),
        require_probe_brighter=require_probe_brighter,
    )


def _validate_insets(
    width: int,
    height: int,
    left: int,
    top: int,
    right: int,
    bottom: int,
    *,
    min_remaining_edge_px: int,
    min_remaining_fraction_num: int,
    min_remaining_fraction_den: int,
    aspect_min_num: int,
    aspect_min_den: int,
    aspect_max_num: int,
    aspect_max_den: int,
) -> tuple[tuple[int, int, int, int] | None, str]:
    if left == 0 and right == 0 and top == 0 and bottom == 0:
        return None, "noop: no border detected"

    rem_w = width - left - right
    rem_h = height - top - bottom
    min_w = max(
        min_remaining_edge_px,
        (width * min_remaining_fraction_num) // min_remaining_fraction_den,
    )
    min_h = max(
        min_remaining_edge_px,
        (height * min_remaining_fraction_num) // min_remaining_fraction_den,
    )
    if rem_w < min_w or rem_h < min_h:
        return None, "noop: remaining area below limit"

    if rem_h <= 0 or rem_w <= 0:
        return None, "noop: remaining area below limit"
    if rem_w * aspect_min_den < rem_h * aspect_min_num:
        return None, "noop: aspect ratio out of range"
    if rem_w * aspect_max_den > rem_h * aspect_max_num:
        return None, "noop: aspect ratio out of range"

    return (left, top, right, bottom), ""


def detect_scan_border_insets(
    gray: Image.Image, params: ScanBorderParams = SCAN_BORDER_PARAMS
) -> tuple[tuple[int, int, int, int] | None, str]:
    """Return (left, top, right, bottom) grey-bed insets or None with noop reason.

    ``gray`` must be mode ``L``.
    """
    if gray.mode != "L":
        raise ValueError(f"expected mode L, got {gray.mode!r}")
    width, height = gray.size
    if width < params.min_dimension_px or height < params.min_dimension_px:
        return None, "noop: image below minimum dimension"

    left = _edge_inset(gray, "left", walk=_walk_grey_band, walk_params=params)
    right = _edge_inset(gray, "right", walk=_walk_grey_band, walk_params=params)
    top = _edge_inset(gray, "top", walk=_walk_grey_band, walk_params=params)
    bottom = _edge_inset(gray, "bottom", walk=_walk_grey_band, walk_params=params)

    return _validate_insets(
        width,
        height,
        left,
        top,
        right,
        bottom,
        min_remaining_edge_px=params.min_remaining_edge_px,
        min_remaining_fraction_num=params.min_remaining_fraction_num,
        min_remaining_fraction_den=params.min_remaining_fraction_den,
        aspect_min_num=params.aspect_min_num,
        aspect_min_den=params.aspect_min_den,
        aspect_max_num=params.aspect_max_num,
        aspect_max_den=params.aspect_max_den,
    )


def detect_white_border_insets(
    gray: Image.Image, params: UniformOverscanParams = UNIFORM_OVERSCAN_PARAMS
) -> tuple[tuple[int, int, int, int] | None, str]:
    """Return (left, top, right, bottom) stark-white overscan insets or None.

    ``gray`` must be mode ``L``.
    """
    if gray.mode != "L":
        raise ValueError(f"expected mode L, got {gray.mode!r}")
    width, height = gray.size
    if width < params.min_dimension_px or height < params.min_dimension_px:
        return None, "noop: image below minimum dimension"

    left = _edge_inset(gray, "left", walk=_walk_white_band, walk_params=params)
    right = _edge_inset(gray, "right", walk=_walk_white_band, walk_params=params)
    top = _edge_inset(gray, "top", walk=_walk_white_band, walk_params=params)
    bottom = _edge_inset(gray, "bottom", walk=_walk_white_band, walk_params=params)

    return _validate_insets(
        width,
        height,
        left,
        top,
        right,
        bottom,
        min_remaining_edge_px=params.min_remaining_edge_px,
        min_remaining_fraction_num=params.min_remaining_fraction_num,
        min_remaining_fraction_den=params.min_remaining_fraction_den,
        aspect_min_num=params.aspect_min_num,
        aspect_min_den=params.aspect_min_den,
        aspect_max_num=params.aspect_max_num,
        aspect_max_den=params.aspect_max_den,
    )


def detect_binding_gutter_insets(
    gray: Image.Image, params: BindingGutterParams = BINDING_GUTTER_PARAMS
) -> tuple[tuple[int, int, int, int] | None, str]:
    """Return left/right dark-gutter insets or None. Top/bottom stay 0.

    ``gray`` must be mode ``L``.
    """
    if gray.mode != "L":
        raise ValueError(f"expected mode L, got {gray.mode!r}")
    width, height = gray.size
    if width < params.min_dimension_px or height < params.min_dimension_px:
        return None, "noop: image below minimum dimension"

    left = _edge_inset(
        gray,
        "left",
        walk=_walk_dark_gutter_band,
        walk_params=params,
        require_probe_brighter=True,
    )
    right = _edge_inset(
        gray,
        "right",
        walk=_walk_dark_gutter_band,
        walk_params=params,
        require_probe_brighter=True,
    )
    return _validate_insets(
        width,
        height,
        left,
        0,
        right,
        0,
        min_remaining_edge_px=params.min_remaining_edge_px,
        min_remaining_fraction_num=params.min_remaining_fraction_num,
        min_remaining_fraction_den=params.min_remaining_fraction_den,
        aspect_min_num=params.aspect_min_num,
        aspect_min_den=params.aspect_min_den,
        aspect_max_num=params.aspect_max_num,
        aspect_max_den=params.aspect_max_den,
    )


def detect_edge_shadow_insets(
    gray: Image.Image, params: EdgeShadowParams = EDGE_SHADOW_PARAMS
) -> tuple[tuple[int, int, int, int] | None, str]:
    """Return remaining edge-anchored shadow insets or None.

    ``gray`` must be mode ``L``.
    """
    if gray.mode != "L":
        raise ValueError(f"expected mode L, got {gray.mode!r}")
    width, height = gray.size
    if width < params.min_dimension_px or height < params.min_dimension_px:
        return None, "noop: image below minimum dimension"

    left = _edge_inset(
        gray,
        "left",
        walk=_walk_edge_shadow_band,
        walk_params=params,
        require_probe_brighter=True,
    )
    right = _edge_inset(
        gray,
        "right",
        walk=_walk_edge_shadow_band,
        walk_params=params,
        require_probe_brighter=True,
    )
    top = _edge_inset(
        gray,
        "top",
        walk=_walk_edge_shadow_band,
        walk_params=params,
        require_probe_brighter=True,
    )
    bottom = _edge_inset(
        gray,
        "bottom",
        walk=_walk_edge_shadow_band,
        walk_params=params,
        require_probe_brighter=True,
    )
    return _validate_insets(
        width,
        height,
        left,
        top,
        right,
        bottom,
        min_remaining_edge_px=params.min_remaining_edge_px,
        min_remaining_fraction_num=params.min_remaining_fraction_num,
        min_remaining_fraction_den=params.min_remaining_fraction_den,
        aspect_min_num=params.aspect_min_num,
        aspect_min_den=params.aspect_min_den,
        aspect_max_num=params.aspect_max_num,
        aspect_max_den=params.aspect_max_den,
    )


def _walk_lid_sliver_band(
    *,
    dim: int,
    params: LidSliverParams,
    sample: Callable[[int], tuple[float, float]],
) -> int:
    k = 0
    ref_mean: float | None = None
    while k < params.max_sliver_px:
        mean, var = sample(k)
        if var > params.max_strip_variance:
            break
        if ref_mean is not None and abs(mean - ref_mean) > params.ref_mean_tol:
            break
        if ref_mean is None:
            ref_mean = mean
        k += 1
    return k


def detect_lid_sliver_insets(
    gray: Image.Image, params: LidSliverParams = LID_SLIVER_PARAMS
) -> tuple[tuple[int, int, int, int] | None, str]:
    """Return insets for thin (4-15px) uniform edge slivers or None."""
    if gray.mode != "L":
        raise ValueError(f"expected mode L, got {gray.mode!r}")
    width, height = gray.size
    if width < params.min_dimension_px or height < params.min_dimension_px:
        return None, "noop: image below minimum dimension"

    def inset_for(edge: Edge) -> int:
        dim = width if edge in ("left", "right") else height
        if edge == "left":
            sample = lambda k: _strip_stats_vertical(gray, k)  # noqa: E731
            band = lambda k: _region_mean_vertical(gray, 0, k)  # noqa: E731
            probe = lambda k, off, n: _region_mean_vertical(gray, k + off, k + off + n)  # noqa: E731
        elif edge == "right":
            sample = lambda k: _strip_stats_vertical(gray, width - 1 - k)  # noqa: E731
            band = lambda k: _region_mean_vertical(gray, width - k, width)  # noqa: E731
            probe = lambda k, off, n: _region_mean_vertical(  # noqa: E731
                gray, width - k - off - n, width - k - off
            )
        elif edge == "top":
            sample = lambda k: _strip_stats_horizontal(gray, k)  # noqa: E731
            band = lambda k: _region_mean_horizontal(gray, 0, k)  # noqa: E731
            probe = lambda k, off, n: _region_mean_horizontal(gray, k + off, k + off + n)  # noqa: E731
        else:
            sample = lambda k: _strip_stats_horizontal(gray, height - 1 - k)  # noqa: E731
            band = lambda k: _region_mean_horizontal(gray, height - k, height)  # noqa: E731
            probe = lambda k, off, n: _region_mean_horizontal(  # noqa: E731
                gray, height - k - off - n, height - k - off
            )
        k = _walk_lid_sliver_band(dim=dim, params=params, sample=sample)
        if k < params.min_sliver_px or k > params.max_sliver_px:
            return 0
        remaining = dim - k
        offset, probe_n = _interior_probe_span(
            remaining,
            interior_probe_px=params.interior_probe_px,
            interior_probe_offset_px=params.interior_probe_offset_px,
        )
        if probe_n <= 0:
            return 0
        band_mean = band(k)
        if band_mean > params.band_mean_max:
            return 0
        if abs(probe(k, offset, probe_n) - band_mean) < params.min_mean_delta:
            return 0
        return min(k + params.paper_inset_px, dim - params.min_remaining_edge_px)

    return _validate_insets(
        width,
        height,
        inset_for("left"),
        inset_for("top"),
        inset_for("right"),
        inset_for("bottom"),
        min_remaining_edge_px=params.min_remaining_edge_px,
        min_remaining_fraction_num=params.min_remaining_fraction_num,
        min_remaining_fraction_den=params.min_remaining_fraction_den,
        aspect_min_num=params.aspect_min_num,
        aspect_min_den=params.aspect_min_den,
        aspect_max_num=params.aspect_max_num,
        aspect_max_den=params.aspect_max_den,
    )


def _merge_insets(
    a: tuple[int, int, int, int] | None,
    b: tuple[int, int, int, int] | None,
) -> tuple[int, int, int, int]:
    aa = a or (0, 0, 0, 0)
    bb = b or (0, 0, 0, 0)
    return (
        max(aa[0], bb[0]),
        max(aa[1], bb[1]),
        max(aa[2], bb[2]),
        max(aa[3], bb[3]),
    )


def _local_is_bed(
    gray: Image.Image,
    x: int,
    y: int,
    *,
    scan_params: ScanBorderParams,
    overscan_params: UniformOverscanParams,
    wedge_params: CornerWedgeParams,
    radius: int,
) -> bool:
    width, height = gray.size
    x0 = max(0, x - radius)
    x1 = min(width, x + radius + 1)
    y0 = max(0, y - radius)
    y1 = min(height, y + radius + 1)
    hist = gray.crop((x0, y0, x1, y1)).histogram()[:256]
    mean, var = _histogram_mean_var(hist)
    if _is_stark_white(mean, var, overscan_params):
        return True
    if mean < wedge_params.bed_mean_min:
        return False
    if _is_scanner_grey(mean, var, scan_params):
        return True
    if _is_noisy_bed(mean, var, scan_params):
        return True
    return False


def _bed_run_from_right(
    gray: Image.Image,
    y: int,
    max_run: int,
    *,
    scan_params: ScanBorderParams,
    overscan_params: UniformOverscanParams,
    wedge_params: CornerWedgeParams,
    radius: int,
) -> int:
    width, _height = gray.size
    run = 0
    for dx in range(max_run):
        if _local_is_bed(
            gray,
            width - 1 - dx,
            y,
            scan_params=scan_params,
            overscan_params=overscan_params,
            wedge_params=wedge_params,
            radius=radius,
        ):
            run = dx + 1
        else:
            break
    return run


def _bed_run_from_left(
    gray: Image.Image,
    y: int,
    max_run: int,
    *,
    scan_params: ScanBorderParams,
    overscan_params: UniformOverscanParams,
    wedge_params: CornerWedgeParams,
    radius: int,
) -> int:
    run = 0
    for dx in range(max_run):
        if _local_is_bed(
            gray,
            dx,
            y,
            scan_params=scan_params,
            overscan_params=overscan_params,
            wedge_params=wedge_params,
            radius=radius,
        ):
            run = dx + 1
        else:
            break
    return run


def _best_corner_trim(
    runs: list[int], *, min_wedge_px: int, paper_inset_px: int
) -> tuple[int, int]:
    """Minimal (along_edge_a, along_edge_b) axis-aligned trim clearing bed runs.

    ``runs[i]`` is bed depth along edge B on the i-th scanline from edge A.
    Returns extras to add to (edge A inset, edge B inset).
    """
    if not runs or max(runs) < min_wedge_px:
        return 0, 0
    max_w = len(runs)
    best: tuple[int, int, int] | None = None  # cost, da, db
    for da in range(0, max_w + 1):
        rest = runs[da:] if da < max_w else []
        db = max(rest) if rest else 0
        if da == 0 and db == 0:
            continue
        if not all(runs[i] <= db for i in range(da, max_w)):
            continue
        cost = da + db
        if best is None or cost < best[0]:
            best = (cost, da, db)
    if best is None:
        return 0, 0
    _cost, da, db = best
    if da < min_wedge_px and db < min_wedge_px:
        return 0, 0
    if da:
        da = min(max_w, da + paper_inset_px)
    if db:
        db = min(max_w, db + paper_inset_px)
    return da, db


def detect_corner_wedge_insets(
    gray: Image.Image,
    *,
    wedge_params: CornerWedgeParams = CORNER_WEDGE_PARAMS,
    scan_params: ScanBorderParams = SCAN_BORDER_PARAMS,
    overscan_params: UniformOverscanParams = UNIFORM_OVERSCAN_PARAMS,
) -> tuple[tuple[int, int, int, int] | None, str]:
    """Return insets that clear residual bed wedges at rounded page corners.

    Edge-anchored only: samples bed runs in each corner and picks a cheap
    axis-aligned trim. Does not rewrite interior pixels.
    """
    if gray.mode != "L":
        raise ValueError(f"expected mode L, got {gray.mode!r}")
    width, height = gray.size
    if width < wedge_params.min_dimension_px or height < wedge_params.min_dimension_px:
        return None, "noop: image below minimum dimension"

    max_w = min(wedge_params.max_wedge_px, width // 4, height // 4)
    if max_w < wedge_params.min_wedge_px:
        return None, "noop: no border detected"

    radius = wedge_params.local_radius_px
    left = top = right = bottom = 0

    # Top-right: runs[dy] = bed depth from the right on row dy
    tr_runs = [
        _bed_run_from_right(
            gray,
            dy,
            max_w,
            scan_params=scan_params,
            overscan_params=overscan_params,
            wedge_params=wedge_params,
            radius=radius,
        )
        for dy in range(max_w)
    ]
    tr_top, tr_right = _best_corner_trim(
        tr_runs,
        min_wedge_px=wedge_params.min_wedge_px,
        paper_inset_px=wedge_params.paper_inset_px,
    )
    top = max(top, tr_top)
    right = max(right, tr_right)

    # Top-left
    tl_runs = [
        _bed_run_from_left(
            gray,
            dy,
            max_w,
            scan_params=scan_params,
            overscan_params=overscan_params,
            wedge_params=wedge_params,
            radius=radius,
        )
        for dy in range(max_w)
    ]
    tl_top, tl_left = _best_corner_trim(
        tl_runs,
        min_wedge_px=wedge_params.min_wedge_px,
        paper_inset_px=wedge_params.paper_inset_px,
    )
    top = max(top, tl_top)
    left = max(left, tl_left)

    # Bottom-right
    br_runs = [
        _bed_run_from_right(
            gray,
            height - 1 - dy,
            max_w,
            scan_params=scan_params,
            overscan_params=overscan_params,
            wedge_params=wedge_params,
            radius=radius,
        )
        for dy in range(max_w)
    ]
    br_bottom, br_right = _best_corner_trim(
        br_runs,
        min_wedge_px=wedge_params.min_wedge_px,
        paper_inset_px=wedge_params.paper_inset_px,
    )
    bottom = max(bottom, br_bottom)
    right = max(right, br_right)

    # Bottom-left
    bl_runs = [
        _bed_run_from_left(
            gray,
            height - 1 - dy,
            max_w,
            scan_params=scan_params,
            overscan_params=overscan_params,
            wedge_params=wedge_params,
            radius=radius,
        )
        for dy in range(max_w)
    ]
    bl_bottom, bl_left = _best_corner_trim(
        bl_runs,
        min_wedge_px=wedge_params.min_wedge_px,
        paper_inset_px=wedge_params.paper_inset_px,
    )
    bottom = max(bottom, bl_bottom)
    left = max(left, bl_left)

    return _validate_insets(
        width,
        height,
        left,
        top,
        right,
        bottom,
        min_remaining_edge_px=wedge_params.min_remaining_edge_px,
        min_remaining_fraction_num=wedge_params.min_remaining_fraction_num,
        min_remaining_fraction_den=wedge_params.min_remaining_fraction_den,
        aspect_min_num=wedge_params.aspect_min_num,
        aspect_min_den=wedge_params.aspect_min_den,
        aspect_max_num=wedge_params.aspect_max_num,
        aspect_max_den=wedge_params.aspect_max_den,
    )


def _mean_var(values: list[int]) -> tuple[float, float]:
    if not values:
        return 0.0, 0.0
    mean = sum(values) / len(values)
    var = sum((value - mean) ** 2 for value in values) / len(values)
    return mean, var


def _punch_band(gray: Image.Image, *, edge: str, params: PunchHoleParams) -> int:
    width, height = gray.size
    for band in range(params.max_band_px, params.min_band_px - 1, -1):
        if edge == "left":
            xs = range(0, band)
            inner_x = band
        else:
            xs = range(width - band, width)
            inner_x = width - band - 1
        if inner_x < 0 or inner_x >= width:
            continue
        row_dark = []
        for y in range(height):
            row_dark.append(
                sum(1 for x in xs if int(gray.getpixel((x, y))) <= params.dark_max)
            )
        hole_limit = max(6, int(band * 0.4))
        hole_rows = [count >= 4 and count <= hole_limit for count in row_dark]
        best_start = best_end = -1
        y = 0
        while y < height:
            if not hole_rows[y]:
                y += 1
                continue
            end = y
            while end < height and hole_rows[end]:
                end += 1
            if end - y > best_end - best_start:
                best_start, best_end = y, end
            y = end
        span = best_end - best_start
        if span < 8 or span > 40:
            continue
        nearby = range(max(0, best_start - 8), min(height, best_end + 8))
        paper = [
            int(gray.getpixel((x, yy)))
            for yy in nearby
            if yy < best_start or yy >= best_end
            for x in list(xs)[::2]
        ]
        mean, var = _mean_var(paper)
        if mean < params.paper_mean_min or var > params.paper_var_max:
            continue
        inner = [int(gray.getpixel((inner_x, yy))) for yy in range(best_start, best_end)]
        inner_mean, inner_var = _mean_var(inner)
        if inner_mean < params.paper_mean_min or inner_var > params.paper_var_max:
            continue
        return band
    return 0


def detect_punch_hole_insets(
    gray: Image.Image,
    params: PunchHoleParams = PUNCH_HOLE_PARAMS,
) -> tuple[tuple[int, int, int, int] | None, str]:
    width, height = gray.size
    if width < params.min_dimension_px or height < params.min_dimension_px:
        return None, "noop: image below minimum dimension"
    left = _punch_band(gray, edge="left", params=params)
    right = _punch_band(gray, edge="right", params=params)
    if left == 0 and right == 0:
        return None, "noop: no punch-hole margin"
    return (left, 0, right, 0), ""


def _calibration_depth(gray: Image.Image, *, edge: str, params: CalibrationStripeParams) -> int:
    width, height = gray.size
    for depth in range(params.max_px, params.min_px - 1, -1):
        if edge == "top":
            rows = range(0, depth)
            probe = depth
        else:
            rows = range(height - depth, height)
            probe = height - depth - 1
        if probe < 0 or probe >= height:
            continue
        samples: list[int] = []
        for x in range(width):
            samples.append(int(sum(int(gray.getpixel((x, y))) for y in rows) / depth))
        dark_runs = 0
        light_runs = 0
        state: str | None = None
        length = 0
        for value in samples:
            kind = "d" if value <= params.dark_max else "l" if value >= params.light_min else "m"
            if kind == "m" or kind != state:
                if state == "d" and length >= params.min_run_px:
                    dark_runs += 1
                elif state == "l" and length >= params.min_run_px:
                    light_runs += 1
                state = None if kind == "m" else kind
                length = 0 if kind == "m" else 1
            else:
                length += 1
        if state == "d" and length >= params.min_run_px:
            dark_runs += 1
        elif state == "l" and length >= params.min_run_px:
            light_runs += 1
        if dark_runs < 2 or light_runs < 2:
            continue
        probe_vals = [int(gray.getpixel((x, probe))) for x in range(0, width, max(1, width // 32))]
        mean, var = _mean_var(probe_vals)
        if mean >= params.paper_mean_min and var <= params.paper_var_max:
            return depth
    return 0


def detect_calibration_stripe_insets(
    gray: Image.Image,
    params: CalibrationStripeParams = CALIBRATION_STRIPE_PARAMS,
) -> tuple[tuple[int, int, int, int] | None, str]:
    width, height = gray.size
    if width < params.min_dimension_px or height < params.min_dimension_px:
        return None, "noop: image below minimum dimension"
    top = _calibration_depth(gray, edge="top", params=params)
    bottom = _calibration_depth(gray, edge="bottom", params=params)
    if top == 0 and bottom == 0:
        return None, "noop: no calibration stripe"
    return (0, top, 0, bottom), ""


def detect_declutter_border_insets(
    gray: Image.Image,
    *,
    scan_params: ScanBorderParams = SCAN_BORDER_PARAMS,
    overscan_params: UniformOverscanParams = UNIFORM_OVERSCAN_PARAMS,
    wedge_params: CornerWedgeParams = CORNER_WEDGE_PARAMS,
    gutter_params: BindingGutterParams = BINDING_GUTTER_PARAMS,
    shadow_params: EdgeShadowParams = EDGE_SHADOW_PARAMS,
    lid_params: LidSliverParams = LID_SLIVER_PARAMS,
    punch_params: PunchHoleParams = PUNCH_HOLE_PARAMS,
    stripe_params: CalibrationStripeParams = CALIBRATION_STRIPE_PARAMS,
) -> tuple[tuple[int, int, int, int] | None, str]:
    """Detect scanner beds, binding gutters, and residual edge shadows (multi-pass).

    L-shaped artefacts (e.g. grey bed on the right + white gutter on the bottom)
    make full-strip stats non-uniform on the shared corner. Cropping one edge
    type and re-detecting recovers the other. Rounded page corners leave bed
    wedges after axis-aligned bed crops; ``remove_corner_wedges`` clears those.
    Dark left/right binding strips and remaining edge-anchored shadows extend
    the same crop. Insets are returned in original image coordinates.
    """
    if gray.mode != "L":
        raise ValueError(f"expected mode L, got {gray.mode!r}")
    orig_w, orig_h = gray.size
    if orig_w < scan_params.min_dimension_px or orig_h < scan_params.min_dimension_px:
        return None, "noop: image below minimum dimension"

    acc_left = acc_top = acc_right = acc_bottom = 0
    working = gray
    last_reason = "noop: no border detected"

    for _ in range(_MAX_BORDER_PASSES):
        grey_insets, grey_reason = detect_scan_border_insets(working, scan_params)
        white_insets, white_reason = detect_white_border_insets(working, overscan_params)
        merged = _merge_insets(grey_insets, white_insets)
        # Corner wedges only after an edge bed crop: residual light-bed triangles
        # at rounded page corners. Running on the full frame false-fires on the
        # same light beds as left/right extras.
        wedge_reason = "noop: no border detected"
        if acc_left or acc_top or acc_right or acc_bottom:
            wedge_insets, wedge_reason = detect_corner_wedge_insets(
                working,
                wedge_params=wedge_params,
                scan_params=scan_params,
                overscan_params=overscan_params,
            )
            merged = _merge_insets(merged, wedge_insets)
        gutter_insets, gutter_reason = detect_binding_gutter_insets(working, gutter_params)
        merged = _merge_insets(merged, gutter_insets)
        shadow_insets, shadow_reason = detect_edge_shadow_insets(working, shadow_params)
        merged = _merge_insets(merged, shadow_insets)
        lid_insets, lid_reason = detect_lid_sliver_insets(working, lid_params)
        merged = _merge_insets(merged, lid_insets)
        punch_insets, punch_reason = detect_punch_hole_insets(working, punch_params)
        merged = _merge_insets(merged, punch_insets)
        stripe_insets, stripe_reason = detect_calibration_stripe_insets(working, stripe_params)
        merged = _merge_insets(merged, stripe_insets)
        if merged == (0, 0, 0, 0):
            for reason in (
                grey_reason,
                white_reason,
                wedge_reason,
                gutter_reason,
                shadow_reason,
                lid_reason,
                punch_reason,
                stripe_reason,
            ):
                if reason != "noop: no border detected":
                    last_reason = reason
                    break
            else:
                last_reason = "noop: no border detected"
            break

        left, top, right, bottom = merged
        # Validate against the *original* frame with accumulated insets so a
        # later pass cannot violate remaining-area / aspect safety.
        trial = (
            acc_left + left,
            acc_top + top,
            acc_right + right,
            acc_bottom + bottom,
        )
        validated, reason = _validate_insets(
            orig_w,
            orig_h,
            trial[0],
            trial[1],
            trial[2],
            trial[3],
            min_remaining_edge_px=scan_params.min_remaining_edge_px,
            min_remaining_fraction_num=scan_params.min_remaining_fraction_num,
            min_remaining_fraction_den=scan_params.min_remaining_fraction_den,
            aspect_min_num=scan_params.aspect_min_num,
            aspect_min_den=scan_params.aspect_min_den,
            aspect_max_num=scan_params.aspect_max_num,
            aspect_max_den=scan_params.aspect_max_den,
        )
        if validated is None:
            last_reason = reason
            break

        acc_left, acc_top, acc_right, acc_bottom = validated
        w, h = working.size
        working = working.crop((left, top, w - right, h - bottom))
    else:
        last_reason = "noop: no border detected"

    if acc_left == 0 and acc_top == 0 and acc_right == 0 and acc_bottom == 0:
        return None, last_reason
    return (acc_left, acc_top, acc_right, acc_bottom), ""
