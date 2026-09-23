"""Provider-neutral contracts for future external actions.

This module deliberately contains data validation and approval binding only.
It has no provider client, network call, file mutation, or execute method.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

_MAX_ID_LENGTH = 128
_MAX_TEXT_LENGTH = 512


class ActionKind(StrEnum):
    DRAFT_EMAIL = "draft_email"
    SEND_EMAIL = "send_email"
    UPLOAD_FILE = "upload_file"


class ActionStatus(StrEnum):
    PENDING = "pending"
    APPROVAL_REQUIRED = "approval_required"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    COMPLETED = "completed"
    FAILED = "failed"


_ACTION_SCOPES: Mapping[ActionKind, tuple[str, ...]] = {
    ActionKind.DRAFT_EMAIL: ("email.draft",),
    ActionKind.SEND_EMAIL: ("email.send",),
    ActionKind.UPLOAD_FILE: ("drive.upload",),
}


def allowed_scopes(kind: ActionKind) -> tuple[str, ...]:
    """Return the exact scopes permitted for one future action kind."""

    if not isinstance(kind, ActionKind):
        raise ValueError("action kind is unsupported")
    return _ACTION_SCOPES[kind]


def _bounded_text(value: object, label: str, *, maximum: int = _MAX_TEXT_LENGTH) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ValueError(f"{label} must be a non-empty bounded string")
    return value


def _digest(value: object) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError("payload_digest must be a lowercase SHA-256 digest")
    return value


def _timestamp(value: object, label: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise ValueError(f"{label} must be timezone-aware")
    return value


@dataclass(frozen=True, slots=True)
class ActionRequest:
    """A pending future action containing metadata, never raw action content."""

    request_id: str
    kind: ActionKind
    scope: str
    target: str
    payload_digest: str
    preview: str
    status: ActionStatus = ActionStatus.PENDING

    def __post_init__(self) -> None:
        _bounded_text(self.request_id, "request_id", maximum=_MAX_ID_LENGTH)
        if not isinstance(self.kind, ActionKind):
            raise ValueError("action kind is unsupported")
        if self.scope not in allowed_scopes(self.kind):
            raise ValueError("scope is not allowed for this action kind")
        _bounded_text(self.scope, "scope", maximum=_MAX_ID_LENGTH)
        _bounded_text(self.target, "target")
        _digest(self.payload_digest)
        _bounded_text(self.preview, "preview")
        if self.status is not ActionStatus.PENDING:
            raise ValueError("new action requests must be pending")

    def as_dict(self) -> dict[str, object]:
        return {
            "request_id": self.request_id,
            "kind": self.kind.value,
            "scope": self.scope,
            "target": self.target,
            "payload_digest": self.payload_digest,
            "preview": self.preview,
            "status": self.status.value,
        }


@dataclass(frozen=True, slots=True)
class ActionApproval:
    """An exact, time-bounded human approval for one action request."""

    request_id: str
    kind: ActionKind
    scope: str
    payload_digest: str
    approved_by: str
    approved_at: datetime
    expires_at: datetime

    def __post_init__(self) -> None:
        _bounded_text(self.request_id, "request_id", maximum=_MAX_ID_LENGTH)
        if not isinstance(self.kind, ActionKind):
            raise ValueError("action kind is unsupported")
        if self.scope not in allowed_scopes(self.kind):
            raise ValueError("scope is not allowed for this action kind")
        _digest(self.payload_digest)
        _bounded_text(self.approved_by, "approved_by", maximum=_MAX_ID_LENGTH)
        approved_at = _timestamp(self.approved_at, "approved_at")
        expires_at = _timestamp(self.expires_at, "expires_at")
        if expires_at <= approved_at:
            raise ValueError("expires_at must be after approved_at")

    def is_valid_for(self, request: ActionRequest, *, now: datetime) -> bool:
        if _timestamp(now, "now") >= self.expires_at:
            return False
        return (
            request.request_id == self.request_id
            and request.kind is self.kind
            and request.scope == self.scope
            and request.payload_digest == self.payload_digest
            and request.status is ActionStatus.PENDING
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "request_id": self.request_id,
            "kind": self.kind.value,
            "scope": self.scope,
            "payload_digest": self.payload_digest,
            "approved_by": self.approved_by,
            "approved_at": self.approved_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
        }


@dataclass(frozen=True, slots=True)
class ActionAudit:
    """Redacted audit metadata for a future action lifecycle event."""

    request_id: str
    kind: ActionKind
    scope: str
    payload_digest: str
    status: ActionStatus
    actor: str
    recorded_at: datetime

    def __post_init__(self) -> None:
        _bounded_text(self.request_id, "request_id", maximum=_MAX_ID_LENGTH)
        if not isinstance(self.kind, ActionKind):
            raise ValueError("action kind is unsupported")
        if self.scope not in allowed_scopes(self.kind):
            raise ValueError("scope is not allowed for this action kind")
        _digest(self.payload_digest)
        if not isinstance(self.status, ActionStatus):
            raise ValueError("action status is unsupported")
        _bounded_text(self.actor, "actor", maximum=_MAX_ID_LENGTH)
        _timestamp(self.recorded_at, "recorded_at")

    def as_dict(self) -> dict[str, object]:
        return {
            "request_id": self.request_id,
            "kind": self.kind.value,
            "scope": self.scope,
            "payload_digest": self.payload_digest,
            "status": self.status.value,
            "actor": self.actor,
            "recorded_at": self.recorded_at.isoformat(),
        }
