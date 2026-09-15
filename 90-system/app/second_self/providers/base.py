"""Provider-neutral runtime interface for model health and inference."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from ..routing import ProviderCapability, RouteRequest


class ProviderHealthStatus(StrEnum):
    """Stable provider health outcomes."""

    READY = "ready"
    UNAVAILABLE = "unavailable"
    MISCONFIGURED = "misconfigured"


@dataclass(frozen=True, slots=True)
class ProviderHealth:
    """Redacted health result safe for diagnostics."""

    status: ProviderHealthStatus
    detail: str

    @property
    def ready(self) -> bool:
        return self.status is ProviderHealthStatus.READY


@dataclass(frozen=True, slots=True)
class InferenceResult:
    """In-memory provider response; callers must not log raw text."""

    provider: str
    model: str
    text: str


class ProviderError(RuntimeError):
    """Redacted provider failure suitable for a user-facing boundary."""


class ModelProvider(Protocol):
    """Replaceable model-provider contract consumed by later routing phases."""

    def capability(self) -> ProviderCapability: ...

    def health(self) -> ProviderHealth: ...

    def infer(self, request: RouteRequest, prompt: str) -> InferenceResult: ...
