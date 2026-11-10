"""Construct a vision OCR provider. Ollama is the product default."""

from __future__ import annotations

from transcribe.errors import ProviderError
from transcribe.providers.base import VisionOCRProvider
from transcribe.providers.ollama import normalize_base_url

KNOWN_PROVIDERS = ("ollama", "paddleocr")


def normalize_provider_id(provider_id: str | None) -> str:
    raw = (provider_id or "ollama").strip().lower()
    if not raw:
        return "ollama"
    if raw in {"paddle", "mlx", "paddleocr-vl"}:
        return "paddleocr"
    return raw


def build_vision_provider(
    provider_id: str | None,
    base_url: str,
    **kwargs,
) -> VisionOCRProvider:
    """Return a vision provider. Unknown ids raise ``ProviderError``."""
    pid = normalize_provider_id(provider_id)
    url = normalize_base_url(base_url)
    if pid == "ollama":
        from transcribe.providers.ollama import OllamaVisionProvider

        return OllamaVisionProvider(url, **kwargs)
    if pid == "paddleocr":
        from transcribe.providers.paddleocr import PaddleocrVisionProvider

        return PaddleocrVisionProvider(url, **kwargs)
    raise ProviderError(
        f"Unknown vision provider {pid!r}. Choose ollama or paddleocr.",
        code="provider_unknown",
    )
