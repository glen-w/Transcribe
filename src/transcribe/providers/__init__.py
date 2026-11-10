from __future__ import annotations

from .base import DiscoveryResult, ModelInfo, ProviderResult, VisionOCRProvider
from .factory import KNOWN_PROVIDERS, build_vision_provider, normalize_provider_id
from .ollama import (
    DEFAULT_MAX_RETRIES,
    OllamaVisionProvider,
    call_with_retries,
    invalidate_discovery_cache,
    is_local_machine_host,
    is_loopback_host,
    normalize_base_url,
)
from .paddleocr import PaddleocrVisionProvider

__all__ = [
    "DEFAULT_MAX_RETRIES",
    "DiscoveryResult",
    "KNOWN_PROVIDERS",
    "ModelInfo",
    "OllamaVisionProvider",
    "PaddleocrVisionProvider",
    "ProviderResult",
    "VisionOCRProvider",
    "build_vision_provider",
    "call_with_retries",
    "invalidate_discovery_cache",
    "is_local_machine_host",
    "is_loopback_host",
    "normalize_base_url",
    "normalize_provider_id",
]
