from __future__ import annotations

import copy
import hashlib

from transcribe.domain.fingerprint import (
    canonical_json_bytes,
    compute_input_fingerprint,
    fingerprint_generation_options,
    fingerprints_compatible_for_skip,
)
from transcribe.domain.models import DEFAULT_VISION_NUM_PREDICT


def _legacy_digest_with_sampler_keys(payload: dict, **extra_opts) -> tuple[str, dict]:
    old = copy.deepcopy(payload)
    opts = dict(old.get("generation_options") or {})
    opts.update(extra_opts)
    old["generation_options"] = opts
    digest = hashlib.sha256(canonical_json_bytes(old)).hexdigest()
    return digest, old


def test_fingerprint_is_order_independent_for_options():
    a, pa = compute_input_fingerprint(
        provider="ollama",
        model_name="m",
        model_digest="d",
        model_identity_verified=True,
        input_sha256="aa",
        prompt_sha256="bb",
        preprocess_profile="none",
        preprocess_version=1,
        generation_options={"temperature": 0.0, "x": 1},
    )
    b, pb = compute_input_fingerprint(
        provider="ollama",
        model_name="m",
        model_digest="d",
        model_identity_verified=True,
        input_sha256="aa",
        prompt_sha256="bb",
        preprocess_profile="none",
        preprocess_version=1,
        generation_options={"x": 1, "temperature": 0.0},
    )
    assert a == b
    assert pa == pb


def test_fingerprint_changes_with_digest():
    a, _ = compute_input_fingerprint(
        provider="ollama",
        model_name="m",
        model_digest="d1",
        model_identity_verified=True,
        input_sha256="aa",
        prompt_sha256="bb",
        preprocess_profile="none",
        preprocess_version=1,
        generation_options={"temperature": 0.0},
    )
    b, _ = compute_input_fingerprint(
        provider="ollama",
        model_name="m",
        model_digest="d2",
        model_identity_verified=True,
        input_sha256="aa",
        prompt_sha256="bb",
        preprocess_profile="none",
        preprocess_version=1,
        generation_options={"temperature": 0.0},
    )
    assert a != b


def test_fingerprint_golden_stable():
    digest, payload = compute_input_fingerprint(
        provider="ollama",
        model_name="fake-vision",
        model_digest="digest-aaa",
        model_identity_verified=True,
        input_sha256="0" * 64,
        prompt_sha256="1" * 64,
        preprocess_profile="none",
        preprocess_version=1,
        generation_options={"temperature": 0.0},
    )
    assert payload["model_name"] == "fake-vision"
    assert len(digest) == 64


def test_fingerprint_omits_default_num_predict():
    a, pa = compute_input_fingerprint(
        provider="ollama",
        model_name="m",
        model_digest="d",
        model_identity_verified=True,
        input_sha256="aa",
        prompt_sha256="bb",
        preprocess_profile="none",
        preprocess_version=1,
        generation_options={"temperature": 0.0},
    )
    b, pb = compute_input_fingerprint(
        provider="ollama",
        model_name="m",
        model_digest="d",
        model_identity_verified=True,
        input_sha256="aa",
        prompt_sha256="bb",
        preprocess_profile="none",
        preprocess_version=1,
        generation_options={
            "temperature": 0.0,
            "num_predict": DEFAULT_VISION_NUM_PREDICT,
        },
    )
    assert a == b
    assert "num_predict" not in pa["generation_options"]
    assert "num_predict" not in pb["generation_options"]
    assert "recipe_id" not in pa
    assert "recipe_id" not in pb


def test_fingerprint_changes_with_custom_num_predict():
    a, _ = compute_input_fingerprint(
        provider="ollama",
        model_name="m",
        model_digest="d",
        model_identity_verified=True,
        input_sha256="aa",
        prompt_sha256="bb",
        preprocess_profile="none",
        preprocess_version=1,
        generation_options={"temperature": 0.0, "num_predict": 512},
    )
    b, pb = compute_input_fingerprint(
        provider="ollama",
        model_name="m",
        model_digest="d",
        model_identity_verified=True,
        input_sha256="aa",
        prompt_sha256="bb",
        preprocess_profile="none",
        preprocess_version=1,
        generation_options={"temperature": 0.0, "num_predict": 4096},
    )
    assert a != b
    assert pb["generation_options"].get("num_predict") is None


def test_fingerprint_omits_repeat_penalty_and_stop():
    a, pa = compute_input_fingerprint(
        provider="ollama",
        model_name="glm-ocr",
        model_digest="d",
        model_identity_verified=True,
        input_sha256="aa",
        prompt_sha256="bb",
        preprocess_profile="none",
        preprocess_version=1,
        generation_options={"temperature": 0.0},
    )
    b, pb = compute_input_fingerprint(
        provider="ollama",
        model_name="glm-ocr",
        model_digest="d",
        model_identity_verified=True,
        input_sha256="aa",
        prompt_sha256="bb",
        preprocess_profile="none",
        preprocess_version=1,
        generation_options={
            "temperature": 0.0,
            "num_predict": DEFAULT_VISION_NUM_PREDICT,
            "repeat_penalty": 1.2,
            "stop": ["```\n```"],
        },
    )
    assert a == b
    assert "repeat_penalty" not in pa["generation_options"]
    assert "repeat_penalty" not in pb["generation_options"]
    assert "stop" not in pb["generation_options"]
    assert "num_predict" not in pb["generation_options"]


def test_fingerprint_changes_with_temperature():
    a, _ = compute_input_fingerprint(
        provider="ollama",
        model_name="m",
        model_digest="d",
        model_identity_verified=True,
        input_sha256="aa",
        prompt_sha256="bb",
        preprocess_profile="none",
        preprocess_version=1,
        generation_options={"temperature": 0.0},
    )
    b, _ = compute_input_fingerprint(
        provider="ollama",
        model_name="m",
        model_digest="d",
        model_identity_verified=True,
        input_sha256="aa",
        prompt_sha256="bb",
        preprocess_profile="none",
        preprocess_version=1,
        generation_options={"temperature": 0.2},
    )
    assert a != b


def test_fingerprint_generation_options_does_not_mutate_input():
    raw = {"temperature": 0.0, "repeat_penalty": 1.2}
    out = fingerprint_generation_options(raw)
    assert "repeat_penalty" in raw
    assert "repeat_penalty" not in out


def test_fingerprint_qwen_without_repeat_penalty_omits_default_num_predict():
    a, pa = compute_input_fingerprint(
        provider="ollama",
        model_name="qwen2.5vl:7b",
        model_digest="d",
        model_identity_verified=True,
        input_sha256="aa",
        prompt_sha256="bb",
        preprocess_profile="none",
        preprocess_version=1,
        generation_options={"temperature": 0.0},
    )
    b, pb = compute_input_fingerprint(
        provider="ollama",
        model_name="qwen2.5vl:7b",
        model_digest="d",
        model_identity_verified=True,
        input_sha256="aa",
        prompt_sha256="bb",
        preprocess_profile="none",
        preprocess_version=1,
        generation_options={"temperature": 0.0, "num_predict": 4096},
    )
    assert a == b
    assert "repeat_penalty" not in pa["generation_options"]
    assert "repeat_penalty" not in pb["generation_options"]


def test_compat_skip_legacy_repeat_penalty_payload():
    current, payload = compute_input_fingerprint(
        provider="ollama",
        model_name="glm-ocr",
        model_digest="d",
        model_identity_verified=True,
        input_sha256="aa",
        prompt_sha256="bb",
        preprocess_profile="none",
        preprocess_version=1,
        generation_options={"temperature": 0.0, "repeat_penalty": 1.2},
    )
    legacy_digest, legacy_payload = _legacy_digest_with_sampler_keys(
        payload, repeat_penalty=1.2
    )
    assert current != legacy_digest
    assert fingerprints_compatible_for_skip(
        current,
        stored_digest=legacy_digest,
        fingerprint_payload=legacy_payload,
    )


def test_compat_skip_false_when_prompt_sha_differs():
    current, payload = compute_input_fingerprint(
        provider="ollama",
        model_name="m",
        model_digest="d",
        model_identity_verified=True,
        input_sha256="aa",
        prompt_sha256="bb",
        preprocess_profile="none",
        preprocess_version=1,
        generation_options={"temperature": 0.0},
    )
    legacy_digest, legacy_payload = _legacy_digest_with_sampler_keys(
        payload, repeat_penalty=1.2
    )
    legacy_payload["prompt_sha256"] = "cc"
    assert not fingerprints_compatible_for_skip(
        current,
        stored_digest=legacy_digest,
        fingerprint_payload=legacy_payload,
    )


def test_compat_skip_false_when_temperature_differs():
    current, _ = compute_input_fingerprint(
        provider="ollama",
        model_name="m",
        model_digest="d",
        model_identity_verified=True,
        input_sha256="aa",
        prompt_sha256="bb",
        preprocess_profile="none",
        preprocess_version=1,
        generation_options={"temperature": 0.0},
    )
    _, other_payload = compute_input_fingerprint(
        provider="ollama",
        model_name="m",
        model_digest="d",
        model_identity_verified=True,
        input_sha256="aa",
        prompt_sha256="bb",
        preprocess_profile="none",
        preprocess_version=1,
        generation_options={"temperature": 0.2},
    )
    assert not fingerprints_compatible_for_skip(
        current,
        stored_digest="",
        fingerprint_payload=other_payload,
    )


def test_compat_skip_empty_payload():
    current, _ = compute_input_fingerprint(
        provider="ollama",
        model_name="m",
        model_digest="d",
        model_identity_verified=True,
        input_sha256="aa",
        prompt_sha256="bb",
        preprocess_profile="none",
        preprocess_version=1,
        generation_options={"temperature": 0.0},
    )
    assert not fingerprints_compatible_for_skip(
        current, stored_digest="deadbeef", fingerprint_payload={}
    )
    assert not fingerprints_compatible_for_skip(current, stored_digest="", fingerprint_payload=None)
