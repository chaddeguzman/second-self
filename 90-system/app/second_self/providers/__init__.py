"""Replaceable model-provider interfaces and adapters."""

from .base import (
    InferenceResult,
    ModelProvider,
    ProviderError,
    ProviderHealth,
    ProviderHealthStatus,
)
from .ollama import OllamaConfig, OllamaProvider, load_ollama_config

__all__ = [
    "InferenceResult",
    "ModelProvider",
    "OllamaConfig",
    "OllamaProvider",
    "ProviderError",
    "ProviderHealth",
    "ProviderHealthStatus",
    "load_ollama_config",
]
