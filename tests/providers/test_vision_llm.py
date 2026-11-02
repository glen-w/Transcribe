"""Offline doubles for vision LLM detection helpers (no live Ollama)."""

from __future__ import annotations

import pytest

from transcribe.errors import ProviderError
from transcribe.providers.base import ModelInfo
from transcribe.providers.vision_llm import (
    RecordedVisionDoubleClient,
    bind_vision_llm_context,
    is_suitable_vision_model_info,
)


def test_is_suitable_vision_model_info_by_capability() -> None:
    assert is_suitable_vision_model_info(
        ModelInfo(name="m", digest="d", capabilities=["vision"], capability_known=True)
    )
    assert not is_suitable_vision_model_info(
        ModelInfo(name="m", digest="d", capabilities=["completion"], capability_known=True)
    )


def test_is_suitable_vision_model_info_falls_back_to_name_family() -> None:
    assert is_suitable_vision_model_info(
        ModelInfo(
            name="llava:latest",
            digest="d",
            capabilities=[],
            capability_known=False,
            family="llama",
        )
    )
    assert is_suitable_vision_model_info(
        ModelInfo(
            name="other",
            digest="d",
            capabilities=[],
            capability_known=False,
            family="vision-encoder",
        )
    )
    assert not is_suitable_vision_model_info(
        ModelInfo(
            name="mistral",
            digest="d",
            capabilities=[],
            capability_known=False,
            family="llama",
        )
    )


def test_recorded_vision_double_matches_prompt_prefix_and_substring() -> None:
    client = RecordedVisionDoubleClient(
        responses={"exact prefix here": '{"a":1}', "needle": '{"b":2}', "*": "{}"}
    )
    assert client.healthcheck() is True
    assert client.resolve_configured_model("x") == "x"
    assert client.model_digest("x") == "recorded-vision-digest"
    assert (
        client.analyze_images(
            model="m", prompt="exact prefix here and more", image_bytes_list=[b"x"]
        )
        == '{"a":1}'
    )
    assert (
        client.analyze_images(model="m", prompt="has needle inside", image_bytes_list=[b"x"])
        == '{"b":2}'
    )
    assert client.analyze_images(model="m", prompt="unrelated", image_bytes_list=[b"x"]) == "{}"


def test_recorded_vision_double_unhealthy_resolves_none() -> None:
    client = RecordedVisionDoubleClient(responses={}, healthy=False)
    assert client.healthcheck() is False
    assert client.resolve_configured_model("m") is None


def test_bind_vision_llm_context_with_injected_client() -> None:
    client = RecordedVisionDoubleClient(responses={"*": "{}"})
    ctx = bind_vision_llm_context(model_name="recorded-vision-double:v1", client=client)
    assert ctx is not None
    assert ctx.model_name == "recorded-vision-double:v1"
    assert ctx.resolved_model_digest == "recorded-vision-digest"
    assert ctx.client is client


def test_analyze_images_requires_bytes() -> None:
    from unittest.mock import MagicMock

    from transcribe.providers.vision_llm import OllamaVisionLLMClient

    client = OllamaVisionLLMClient.__new__(OllamaVisionLLMClient)
    client._provider = MagicMock()
    with pytest.raises(ProviderError, match="no images"):
        client.analyze_images(model="m", prompt="p", image_bytes_list=[])


def test_ollama_vision_client_health_resolve_digest_and_analyze() -> None:
    from unittest.mock import MagicMock

    from transcribe.providers.base import DiscoveryResult, ProviderResult
    from transcribe.providers.vision_llm import OllamaVisionLLMClient

    client = OllamaVisionLLMClient.__new__(OllamaVisionLLMClient)
    provider = MagicMock()
    client._provider = provider

    provider.healthcheck.side_effect = ProviderError("down", code="unavailable")
    assert client.healthcheck() is False
    provider.healthcheck.side_effect = None
    assert client.healthcheck() is True

    provider.list_vision_models.return_value = DiscoveryResult(
        models=[
            ModelInfo(name="llava:7b", digest="d1", capabilities=["vision"], capability_known=True),
            ModelInfo(name="other:1", digest="d2", capabilities=["vision"], capability_known=True),
        ]
    )
    assert client.resolve_configured_model("") is None
    assert client.resolve_configured_model("llava:7b") == "llava:7b"
    assert client.resolve_configured_model("llava") == "llava:7b"
    assert client.resolve_configured_model("missing") is None

    provider.resolve_model_identity.return_value = ("digest-ok", True)
    assert client.model_digest("llava:7b") == "digest-ok"
    provider.resolve_model_identity.return_value = ("digest-ok", False)
    assert client.model_digest("llava:7b") is None

    provider.transcribe_image.return_value = ProviderResult(
        text="ok",
        model="llava:7b",
        model_digest="d1",
        model_identity_verified=True,
        provider_metadata={},
    )
    text = client.analyze_images(
        model="llava:7b",
        prompt="user",
        system="sys",
        image_bytes_list=[b"img", b"ignored-second"],
    )
    assert text == "ok"
    call_kw = provider.transcribe_image.call_args.kwargs
    assert call_kw["image_bytes"] == b"img"
    assert call_kw["prompt"] == "sys\n\nuser"


def test_bind_vision_llm_context_returns_none_when_unhealthy() -> None:
    from unittest.mock import MagicMock, patch

    unhealthy = MagicMock()
    unhealthy.healthcheck.return_value = False
    with patch(
        "transcribe.providers.vision_llm.OllamaVisionLLMClient",
        return_value=unhealthy,
    ):
        assert bind_vision_llm_context(model_name="llava:7b") is None
