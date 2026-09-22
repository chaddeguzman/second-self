"""Bounded, read-only Gmail metadata search adapter."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from .contracts import (
    ConnectorItem,
    ConnectorKind,
    ConnectorRequest,
    ConnectorResult,
    ConnectorState,
)

_METADATA_HEADERS = ("Subject", "From", "To", "Date")
_MAX_METADATA_VALUE = 512


def _safe_message(error: object) -> str:
    del error
    return "Gmail is unavailable; local Second Self recall remains available."


def _headers(payload: Mapping[str, Any]) -> dict[str, str]:
    raw_headers = payload.get("payload", {}).get("headers", [])
    if not isinstance(raw_headers, list):
        raise ValueError("invalid Gmail headers")
    result: dict[str, str] = {}
    allowed = {name.casefold(): name.casefold() for name in _METADATA_HEADERS}
    for header in raw_headers:
        if not isinstance(header, Mapping):
            raise ValueError("invalid Gmail header")
        name = header.get("name")
        value = header.get("value")
        if not isinstance(name, str) or not isinstance(value, str):
            continue
        normalized = allowed.get(name.casefold())
        if normalized:
            result[normalized] = value[:_MAX_METADATA_VALUE]
    return result


def _item(payload: Mapping[str, Any]) -> ConnectorItem:
    item_id = payload.get("id")
    if not isinstance(item_id, str) or not item_id.strip():
        raise ValueError("invalid Gmail message identity")
    metadata = _headers(payload)
    thread_id = payload.get("threadId")
    if isinstance(thread_id, str) and thread_id:
        metadata["thread_id"] = thread_id[:_MAX_METADATA_VALUE]
    labels = payload.get("labelIds")
    if isinstance(labels, list) and all(isinstance(label, str) for label in labels):
        metadata["labels"] = ",".join(labels)[:_MAX_METADATA_VALUE]
    internal_date = payload.get("internalDate")
    if isinstance(internal_date, str) and internal_date:
        metadata["internal_date"] = internal_date[:_MAX_METADATA_VALUE]
    return ConnectorItem(
        provider=ConnectorKind.GMAIL,
        item_id=item_id,
        title=metadata.get("subject", "(no subject)"),
        source_uri=f"https://mail.google.com/mail/u/0/#all/{item_id}",
        metadata=metadata,
    )


class GmailConnector:
    """Search Gmail message metadata only when explicitly enabled."""

    def __init__(self, service_factory: Callable[[], Any], *, enabled: bool = False) -> None:
        self._service_factory = service_factory
        self._enabled = enabled

    def search(self, request: ConnectorRequest) -> ConnectorResult:
        if request.kind is not ConnectorKind.GMAIL:
            raise ValueError("Gmail connector requires a Gmail request")
        if not self._enabled:
            return ConnectorResult(
                ConnectorKind.GMAIL,
                ConnectorState.DISABLED,
                message="Gmail is disabled; local Second Self recall remains available.",
            )
        try:
            messages = self._service_factory().users().messages()
            listed = messages.list(
                userId="me",
                q=request.query,
                maxResults=request.limit,
                includeSpamTrash=False,
            ).execute()
            raw_items = listed.get("messages") if isinstance(listed, Mapping) else None
            if raw_items is None:
                return ConnectorResult(ConnectorKind.GMAIL, ConnectorState.AVAILABLE)
            if not isinstance(raw_items, list):
                raise ValueError("invalid Gmail message list")
            items: list[ConnectorItem] = []
            for raw_item in raw_items[: request.limit]:
                if not isinstance(raw_item, Mapping) or not isinstance(raw_item.get("id"), str):
                    return ConnectorResult(
                        ConnectorKind.GMAIL,
                        ConnectorState.DEGRADED,
                        message="Gmail returned an unsupported result shape.",
                    )
                detail = messages.get(
                    userId="me",
                    id=raw_item["id"],
                    format="metadata",
                    metadataHeaders=list(_METADATA_HEADERS),
                ).execute()
                if not isinstance(detail, Mapping):
                    return ConnectorResult(
                        ConnectorKind.GMAIL,
                        ConnectorState.DEGRADED,
                        message="Gmail returned an unsupported result shape.",
                    )
                items.append(_item(detail))
            return ConnectorResult(ConnectorKind.GMAIL, ConnectorState.AVAILABLE, tuple(items))
        except Exception as exc:
            return ConnectorResult(
                ConnectorKind.GMAIL,
                ConnectorState.UNAVAILABLE,
                message=_safe_message(exc),
            )
