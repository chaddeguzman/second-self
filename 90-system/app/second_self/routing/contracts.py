"""Fail-closed data contracts for provider-neutral model routing.

These types carry metadata only. Raw prompts and responses are deliberately not
part of the contract, so dry-run diagnostics cannot persist or display them.
Provider invocation is deliberately separate; the policy consumes these
trusted metadata objects without carrying prompt or response content.
"""

from __future__ import annotations

import hmac
import re
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
OPERATION_RE = re.compile(r"^[a-z][a-z0-9._-]{0,63}$")


class Sensitivity(StrEnum):
    """The only accepted sensitivity classifications."""

    PUBLIC = "public"
    ORDINARY_PRIVATE = "ordinary_private"
    SENSITIVE = "sensitive"
    PROHIBITED = "prohibited"


class DataOriginKind(StrEnum):
    """Stable, non-path origin categories supplied by trusted callers."""

    PUBLIC = "public"
    MEMORY = "memory"
    JOURNAL = "journal"
    STRATEGY = "strategy"
    PRIVATE_REFERENCE = "private_reference"
    EXTERNAL_UNTRUSTED = "external_untrusted"


class ProviderLocality(StrEnum):
    """Whether a provider executes locally or sends data to a cloud service."""

    LOCAL = "local"
    CLOUD = "cloud"


class RouteOutcome(StrEnum):
    """Stable top-level routing outcomes."""

    ALLOW = "allow"
    DENY = "deny"


class RouteReason(StrEnum):
    """Stable reason codes consumed by diagnostics and later policy phases."""

    CAPABLE_PROVIDER = "capable_provider"
    INVALID_REQUEST = "invalid_request"
    PROHIBITED_DATA = "prohibited_data"
    NO_CAPABLE_PROVIDER = "no_capable_provider"
    APPROVAL_METADATA_INVALID = "approval_metadata_invalid"
    APPROVAL_PAYLOAD_MISMATCH = "approval_payload_mismatch"
    APPROVAL_EXPIRED = "approval_expired"
    SANITIZATION_INVALID = "sanitization_invalid"
    SENSITIVITY_ORIGIN_MISMATCH = "sensitivity_origin_mismatch"
    LOCAL_PROVIDER_SELECTED = "local_provider_selected"
    LOCAL_PROVIDER_UNAVAILABLE = "local_provider_unavailable"
    CLOUD_ELIGIBLE_SANITIZED = "cloud_eligible_sanitized"
    CLOUD_ELIGIBLE_APPROVED = "cloud_eligible_approved"
    CLOUD_NOT_ELIGIBLE = "cloud_not_eligible"


@dataclass(frozen=True, slots=True)
class DataOrigin:
    """A path-free origin category with an optional non-sensitive source ID."""

    kind: DataOriginKind
    source_id: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.kind, DataOriginKind):
            raise ValueError("data origin kind is invalid")
        if self.source_id is not None:
            source_id = self.source_id.strip()
            if not source_id or len(source_id) > 64 or any(
                separator in source_id for separator in ("/", "\\", ":")
            ):
                raise ValueError("origin source ID must be short and path-free")


@dataclass(frozen=True, slots=True)
class ExactPayloadApproval:
    """Approval proof bound only to a one-way digest of the reviewed payload."""

    payload_sha256: str
    approved: bool
    expires_at: datetime | None = None

    def __post_init__(self) -> None:
        if not SHA256_RE.fullmatch(self.payload_sha256):
            raise ValueError("approval payload digest must be lowercase SHA-256")
        if not isinstance(self.approved, bool):
            raise ValueError("approval state must be boolean")
        if self.expires_at is not None and (
            not isinstance(self.expires_at, datetime)
            or self.expires_at.utcoffset() is None
        ):
            raise ValueError("approval expiration must include a timezone")


@dataclass(frozen=True, slots=True)
class SanitizationAttestation:
    """Trusted transformation metadata bound to its exact sanitized output."""

    payload_sha256: str
    transform_id: str

    def __post_init__(self) -> None:
        if not SHA256_RE.fullmatch(self.payload_sha256):
            raise ValueError("sanitized payload digest must be lowercase SHA-256")
        if not OPERATION_RE.fullmatch(self.transform_id):
            raise ValueError("sanitization transform ID is invalid")


@dataclass(frozen=True, slots=True)
class ProviderCapability:
    """Provider metadata used by later availability and policy decisions."""

    provider: str
    locality: ProviderLocality
    supported_operations: frozenset[str]
    available: bool
    configured_model: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.provider, str) or not OPERATION_RE.fullmatch(
            self.provider
        ):
            raise ValueError("provider name must use a stable identifier")
        if not isinstance(self.locality, ProviderLocality):
            raise ValueError("provider locality is invalid")
        if not isinstance(self.available, bool):
            raise ValueError("provider availability must be boolean")
        if (
            not isinstance(self.supported_operations, frozenset)
            or not self.supported_operations
            or any(
                not isinstance(operation, str)
                or not OPERATION_RE.fullmatch(operation)
                for operation in self.supported_operations
            )
        ):
            raise ValueError("provider operations must use stable operation names")
        if self.configured_model is not None and (
            not isinstance(self.configured_model, str)
            or not self.configured_model.strip()
        ):
            raise ValueError("configured model cannot be blank")

    def supports(self, operation: str) -> bool:
        """Return whether this available provider advertises the operation."""
        return self.available and operation in self.supported_operations


@dataclass(frozen=True, slots=True)
class RouteRequest:
    """Metadata-only request presented to routing validation and policy."""

    operation: str
    sensitivity: Sensitivity
    origins: tuple[DataOrigin, ...]
    payload_sha256: str | None = None
    approval: ExactPayloadApproval | None = None
    sanitization: SanitizationAttestation | None = None

    def __post_init__(self) -> None:
        if not OPERATION_RE.fullmatch(self.operation):
            raise ValueError("operation name is invalid")
        if not self.origins:
            raise ValueError("at least one trusted data origin is required")
        if not isinstance(self.sensitivity, Sensitivity):
            raise ValueError("sensitivity is invalid")
        if not isinstance(self.origins, tuple) or any(
            not isinstance(origin, DataOrigin) for origin in self.origins
        ):
            raise ValueError("data origins are invalid")
        if self.approval is not None and not isinstance(
            self.approval, ExactPayloadApproval
        ):
            raise ValueError("approval metadata is invalid")
        if self.sanitization is not None and not isinstance(
            self.sanitization, SanitizationAttestation
        ):
            raise ValueError("sanitization metadata is invalid")
        if self.payload_sha256 is not None and not SHA256_RE.fullmatch(
            self.payload_sha256
        ):
            raise ValueError("payload digest must be lowercase SHA-256")


@dataclass(frozen=True, slots=True)
class RouteDenial:
    """Stable denial reason with a redacted human explanation."""

    reason: RouteReason
    explanation: str


@dataclass(frozen=True, slots=True)
class RouteDecision:
    """Provider-neutral allow/deny decision returned without request content."""

    outcome: RouteOutcome
    reason: RouteReason
    explanation: str
    provider: str | None = None
    denial: RouteDenial | None = None

    @classmethod
    def denied(cls, reason: RouteReason, explanation: str) -> RouteDecision:
        denial = RouteDenial(reason, explanation)
        return cls(RouteOutcome.DENY, reason, explanation, denial=denial)

    @classmethod
    def allowed(
        cls,
        provider: str,
        reason: RouteReason = RouteReason.CAPABLE_PROVIDER,
        explanation: str = "request may use the selected provider",
    ) -> RouteDecision:
        return cls(
            RouteOutcome.ALLOW,
            reason,
            explanation,
            provider=provider,
        )

    def as_dict(self) -> dict[str, str | None]:
        """Return the stable, payload-free diagnostic representation."""
        return {
            "outcome": self.outcome.value,
            "reason": self.reason.value,
            "provider": self.provider,
            "explanation": self.explanation,
        }


def validate_request(request: RouteRequest) -> RouteDecision | None:
    """Return a denial for prohibited or invalid approval metadata."""
    if request.sensitivity is Sensitivity.PROHIBITED:
        return RouteDecision.denied(
            RouteReason.PROHIBITED_DATA,
            "prohibited data cannot be submitted to any model",
        )
    if request.approval is not None:
        if not request.approval.approved or request.payload_sha256 is None:
            return RouteDecision.denied(
                RouteReason.APPROVAL_METADATA_INVALID,
                "exact-payload approval metadata is incomplete",
            )
        if not hmac.compare_digest(
            request.approval.payload_sha256, request.payload_sha256
        ):
            return RouteDecision.denied(
                RouteReason.APPROVAL_PAYLOAD_MISMATCH,
                "payload changed after approval",
            )
    return None


def diagnose_route(
    *,
    operation: str,
    sensitivity: str,
    origins: tuple[DataOrigin, ...],
    capabilities: tuple[ProviderCapability, ...] = (),
    payload_sha256: str | None = None,
    approval: ExactPayloadApproval | None = None,
) -> RouteDecision:
    """Validate metadata and explain a route without invoking any provider."""
    try:
        request = RouteRequest(
            operation=operation,
            sensitivity=Sensitivity(sensitivity),
            origins=origins,
            payload_sha256=payload_sha256,
            approval=approval,
        )
    except (TypeError, ValueError):
        return RouteDecision.denied(
            RouteReason.INVALID_REQUEST, "routing request metadata is invalid"
        )

    denial = validate_request(request)
    if denial is not None:
        return denial

    if not isinstance(capabilities, tuple) or any(
        not isinstance(capability, ProviderCapability)
        for capability in capabilities
    ):
        return RouteDecision.denied(
            RouteReason.INVALID_REQUEST, "routing request metadata is invalid"
        )
    for capability in capabilities:
        if capability.supports(request.operation):
            return RouteDecision.allowed(capability.provider)
    return RouteDecision.denied(
        RouteReason.NO_CAPABLE_PROVIDER,
        "no available provider advertises this operation",
    )
