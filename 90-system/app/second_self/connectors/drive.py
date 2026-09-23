"""Bounded, read-only Google Drive file metadata search adapter."""

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

_DRIVE_FIELDS = "files(id,name,mimeType,modifiedTime,webViewLink,size,parents)"
_MAX_QUERY_LENGTH = 2048
_MAX_METADATA_VALUE = 512


def _safe_message(error: object) -> str:
    del error
    return "Drive is unavailable; local Second Self recall remains available."


def _item(payload: Mapping[str, Any]) -> ConnectorItem:
    item_id = payload.get("id")
    name = payload.get("name")
    if not isinstance(item_id, str) or not item_id.strip() or not isinstance(name, str):
        raise ValueError("invalid Drive file identity")
    metadata: dict[str, str] = {}
    for provider_key, metadata_key in {
        "mimeType": "mime_type",
        "modifiedTime": "modified_time",
        "size": "size",
    }.items():
        value = payload.get(provider_key)
        if isinstance(value, str) and value:
            metadata[metadata_key] = value[:_MAX_METADATA_VALUE]
    parents = payload.get("parents")
    if isinstance(parents, list) and all(isinstance(parent, str) for parent in parents):
        metadata["parents"] = ",".join(parents)[:_MAX_METADATA_VALUE]
    web_view_link = payload.get("webViewLink")
    source_uri = (
        web_view_link[:_MAX_METADATA_VALUE]
        if isinstance(web_view_link, str) and web_view_link
        else f"drive:item:{item_id[:_MAX_METADATA_VALUE]}"
    )
    return ConnectorItem(
        provider=ConnectorKind.DRIVE,
        item_id=item_id[:_MAX_METADATA_VALUE],
        title=name[:_MAX_METADATA_VALUE],
        source_uri=source_uri,
        metadata=metadata,
    )


class DriveConnector:
    """Search Drive file metadata only when explicitly enabled."""

    def __init__(self, service_factory: Callable[[], Any], *, enabled: bool = False) -> None:
        self._service_factory = service_factory
        self._enabled = enabled

    def search(self, request: ConnectorRequest) -> ConnectorResult:
        if request.kind is not ConnectorKind.DRIVE:
            raise ValueError("Drive connector requires a Drive request")
        if not self._enabled:
            return ConnectorResult(
                ConnectorKind.DRIVE,
                ConnectorState.DISABLED,
                message="Drive is disabled; local Second Self recall remains available.",
            )
        if len(request.query) > _MAX_QUERY_LENGTH:
            return ConnectorResult(
                ConnectorKind.DRIVE,
                ConnectorState.DEGRADED,
                message="Drive query exceeds the bounded input limit.",
            )
        try:
            files = self._service_factory().files()
            listed = files.list(
                q=request.query,
                pageSize=request.limit,
                spaces="drive",
                includeItemsFromAllDrives=False,
                supportsAllDrives=False,
                fields=_DRIVE_FIELDS,
            ).execute()
            raw_items = listed.get("files") if isinstance(listed, Mapping) else None
            if raw_items is None:
                return ConnectorResult(ConnectorKind.DRIVE, ConnectorState.AVAILABLE)
            if not isinstance(raw_items, list):
                raise ValueError("invalid Drive file list")
            items: list[ConnectorItem] = []
            for raw_item in raw_items[: request.limit]:
                if not isinstance(raw_item, Mapping):
                    return ConnectorResult(
                        ConnectorKind.DRIVE,
                        ConnectorState.DEGRADED,
                        message="Drive returned an unsupported result shape.",
                    )
                try:
                    items.append(_item(raw_item))
                except ValueError:
                    return ConnectorResult(
                        ConnectorKind.DRIVE,
                        ConnectorState.DEGRADED,
                        message="Drive returned an unsupported result shape.",
                    )
            return ConnectorResult(ConnectorKind.DRIVE, ConnectorState.AVAILABLE, tuple(items))
        except Exception as exc:
            return ConnectorResult(
                ConnectorKind.DRIVE,
                ConnectorState.UNAVAILABLE,
                message=_safe_message(exc),
            )
