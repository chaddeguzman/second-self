"""Fail-closed, provider-neutral contracts for future read-only connectors."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import Mapping


class ConnectorKind(StrEnum):
    GMAIL = "gmail"
    DRIVE = "drive"


class ConnectorState(StrEnum):
    AVAILABLE = "available"
    DEGRADED = "degraded"
    DISABLED = "disabled"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True, slots=True)
class ConnectorRequest:
    """Explicit, bounded request that contains no credentials or paths."""

    kind: ConnectorKind
    query: str
    limit: int = 20

    def __post_init__(self) -> None:
        if not self.query.strip():
            raise ValueError("connector query must not be empty")
        if not 1 <= self.limit <= 100:
            raise ValueError("connector limit must be between 1 and 100")


@dataclass(frozen=True, slots=True)
class ConnectorItem:
    """Redacted metadata returned transiently by a future adapter."""

    provider: ConnectorKind
    item_id: str
    title: str
    source_uri: str
    metadata: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.item_id.strip() or not self.title.strip() or not self.source_uri.strip():
            raise ValueError("connector item identity and source attribution are required")
        if any("token" in key.casefold() or "password" in key.casefold() for key in self.metadata):
            raise ValueError("credential-like metadata is not allowed")
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))


@dataclass(frozen=True, slots=True)
class ConnectorResult:
    """Typed transient result; saving requires a separate broker transaction."""

    kind: ConnectorKind
    state: ConnectorState
    items: tuple[ConnectorItem, ...] = ()
    message: str = ""

    def __post_init__(self) -> None:
        if any(item.provider is not self.kind for item in self.items):
            raise ValueError("result items must match the connector kind")
        if self.state is not ConnectorState.AVAILABLE and self.items:
            raise ValueError("non-available connector results cannot contain items")
