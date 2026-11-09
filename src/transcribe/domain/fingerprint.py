"""Structural input fingerprint for OCR skip/resume."""

from __future__ import annotations

import copy
import hashlib
import json
from typing import Any

from transcribe.domain.models import DEFAULT_VISION_NUM_PREDICT

# Recipe / sampler overlays — not structural skip identity (like default num_predict).
SKIP_OMIT_GENERATION_KEYS = frozenset({"repeat_penalty", "stop"})


def canonical_json_bytes(obj: dict[str, Any]) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def fingerprint_generation_options(opts: dict[str, Any] | None) -> dict[str, Any]:
    """Canonical generation options for skip fingerprints.

    Default vision ``num_predict`` is a transport safety cap, not a quality
    input — omit it so existing attempts without the key still skip-match.
    Non-default ``num_predict`` is included and changes the fingerprint.

    ``repeat_penalty`` and ``stop`` are anti-loop recipe overlays merged at
    JobPlan freeze — omit them so recipe tuning does not bust skip.
    """
    out = dict(opts or {})
    for key in SKIP_OMIT_GENERATION_KEYS:
        out.pop(key, None)
    raw = out.get("num_predict")
    if raw is None:
        return out
    try:
        if int(raw) == DEFAULT_VISION_NUM_PREDICT:
            out.pop("num_predict", None)
    except (TypeError, ValueError):
        out.pop("num_predict", None)
    return out


def digest_from_fingerprint_payload(payload: dict[str, Any]) -> str:
    """Re-hash a persisted fingerprint_payload with current canonical rules."""
    body = copy.deepcopy(payload)
    opts = body.get("generation_options")
    if not isinstance(opts, dict):
        opts = {}
    body["generation_options"] = fingerprint_generation_options(opts)
    return hashlib.sha256(canonical_json_bytes(body)).hexdigest()


def fingerprints_compatible_for_skip(
    current_digest: str,
    *,
    stored_digest: str,
    fingerprint_payload: dict[str, Any] | None,
) -> bool:
    """True if a stored attempt should skip against ``current_digest``."""
    if current_digest and stored_digest and current_digest == stored_digest:
        return True
    if not fingerprint_payload or not isinstance(fingerprint_payload, dict):
        return False
    try:
        return current_digest == digest_from_fingerprint_payload(fingerprint_payload)
    except (TypeError, ValueError, OverflowError):
        return False


def compute_input_fingerprint(
    *,
    provider: str,
    model_name: str,
    model_digest: str | None,
    model_identity_verified: bool,
    input_sha256: str,
    prompt_sha256: str,
    preprocess_profile: str,
    preprocess_version: int,
    generation_options: dict[str, Any],
    cleanup: dict[str, Any] | None = None,
) -> tuple[str, dict[str, Any]]:
    """Return (hex digest, canonical fingerprint object).

    When cleanup is enabled, pass a dict with frozen cleanup identity fields.
    When disabled, omit ``cleanup`` (None) so fingerprints stay compatible with
    pre-cleanup attempts.
    """
    payload: dict[str, Any] = {
        "provider": provider,
        "model_name": model_name,
        "model_digest": model_digest,
        "model_identity_verified": model_identity_verified,
        "input_sha256": input_sha256,
        "prompt_sha256": prompt_sha256,
        "preprocess": {"profile": preprocess_profile, "version": preprocess_version},
        "generation_options": fingerprint_generation_options(generation_options),
    }
    if cleanup is not None:
        payload["cleanup"] = cleanup
    digest = hashlib.sha256(canonical_json_bytes(payload)).hexdigest()
    return digest, payload


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))
