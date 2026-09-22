"""Provider-neutral contracts for future external connectors."""

from .contracts import (
    ConnectorItem,
    ConnectorKind,
    ConnectorRequest,
    ConnectorResult,
    ConnectorState,
)

__all__ = [
    "ConnectorItem",
    "ConnectorKind",
    "ConnectorRequest",
    "ConnectorResult",
    "ConnectorState",
]
