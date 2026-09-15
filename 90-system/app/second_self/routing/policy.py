"""Fail-closed local-first routing policy over trusted request metadata."""

from __future__ import annotations

import hmac
from datetime import datetime, timezone

from .contracts import (
    DataOrigin,
    DataOriginKind,
    ProviderCapability,
    ProviderLocality,
    RouteDecision,
    RouteReason,
    RouteRequest,
    Sensitivity,
    validate_request,
)

SENSITIVE_ORIGINS = {
    DataOriginKind.MEMORY,
    DataOriginKind.JOURNAL,
    DataOriginKind.STRATEGY,
}


def _metadata_denial(
    request: RouteRequest, *, now: datetime
) -> RouteDecision | None:
    """Validate approval and sanitization bindings before provider selection."""
    denial = validate_request(request)
    if denial is not None:
        return denial

    approval = request.approval
    if approval is not None:
        if approval.expires_at is None:
            return RouteDecision.denied(
                RouteReason.APPROVAL_METADATA_INVALID,
                "exact-payload approval metadata is incomplete",
            )
        if approval.expires_at <= now:
            return RouteDecision.denied(
                RouteReason.APPROVAL_EXPIRED,
                "exact-payload approval has expired",
            )

    sanitization = request.sanitization
    if sanitization is not None and (
        request.payload_sha256 is None
        or not hmac.compare_digest(
            sanitization.payload_sha256, request.payload_sha256
        )
    ):
        return RouteDecision.denied(
            RouteReason.SANITIZATION_INVALID,
            "sanitization metadata does not match the payload",
        )
    return None


def _origin_denial(request: RouteRequest) -> RouteDecision | None:
    """Enforce origin sensitivity floors without inspecting request content."""
    kinds = {origin.kind for origin in request.origins}
    if kinds & SENSITIVE_ORIGINS and request.sensitivity is not Sensitivity.SENSITIVE:
        return RouteDecision.denied(
            RouteReason.SENSITIVITY_ORIGIN_MISMATCH,
            "Memory, Journal, and Strategy origins require sensitive routing",
        )
    if (
        DataOriginKind.PRIVATE_REFERENCE in kinds
        and request.sensitivity is Sensitivity.PUBLIC
    ):
        return RouteDecision.denied(
            RouteReason.SENSITIVITY_ORIGIN_MISMATCH,
            "private reference origins cannot use public routing",
        )
    return None


def evaluate_policy(
    request: RouteRequest,
    capabilities: tuple[ProviderCapability, ...],
    *,
    now: datetime | None = None,
) -> RouteDecision:
    """Select local Ollama or mark cloud eligibility without invoking either."""
    current_time = now or datetime.now(timezone.utc)
    if not isinstance(current_time, datetime) or current_time.utcoffset() is None:
        return RouteDecision.denied(
            RouteReason.INVALID_REQUEST, "routing request metadata is invalid"
        )
    if not isinstance(request, RouteRequest) or not isinstance(capabilities, tuple):
        return RouteDecision.denied(
            RouteReason.INVALID_REQUEST, "routing request metadata is invalid"
        )
    if any(not isinstance(item, ProviderCapability) for item in capabilities):
        return RouteDecision.denied(
            RouteReason.INVALID_REQUEST, "routing request metadata is invalid"
        )

    denial = _metadata_denial(request, now=current_time)
    if denial is not None:
        return denial
    denial = _origin_denial(request)
    if denial is not None:
        return denial

    local_ollama = next(
        (
            capability
            for capability in capabilities
            if capability.provider == "ollama"
            and capability.locality is ProviderLocality.LOCAL
            and capability.supports(request.operation)
        ),
        None,
    )
    if local_ollama is not None:
        return RouteDecision.allowed(
            local_ollama.provider,
            RouteReason.LOCAL_PROVIDER_SELECTED,
            "available local provider selected",
        )

    cloud = next(
        (
            capability
            for capability in capabilities
            if capability.locality is ProviderLocality.CLOUD
            and capability.supports(request.operation)
        ),
        None,
    )
    if cloud is not None and request.sanitization is not None:
        return RouteDecision.allowed(
            cloud.provider,
            RouteReason.CLOUD_ELIGIBLE_SANITIZED,
            "cloud provider is eligible for trusted sanitized output",
        )
    if cloud is not None and request.approval is not None:
        return RouteDecision.allowed(
            cloud.provider,
            RouteReason.CLOUD_ELIGIBLE_APPROVED,
            "cloud provider is eligible for the exact approved payload",
        )
    if cloud is not None:
        return RouteDecision.denied(
            RouteReason.CLOUD_NOT_ELIGIBLE,
            "cloud requires trusted sanitization or exact-payload approval",
        )

    if request.sensitivity in (
        Sensitivity.ORDINARY_PRIVATE,
        Sensitivity.SENSITIVE,
    ):
        return RouteDecision.denied(
            RouteReason.LOCAL_PROVIDER_UNAVAILABLE,
            "required local provider is unavailable",
        )
    return RouteDecision.denied(
        RouteReason.NO_CAPABLE_PROVIDER,
        "no available provider advertises this operation",
    )


def diagnose_policy(
    *,
    operation: str,
    sensitivity: str,
    origins: tuple[DataOrigin, ...],
    capabilities: tuple[ProviderCapability, ...] = (),
) -> RouteDecision:
    """Build trusted metadata for CLI diagnostics, denying malformed input."""
    try:
        request = RouteRequest(operation, Sensitivity(sensitivity), origins)
    except (TypeError, ValueError):
        return RouteDecision.denied(
            RouteReason.INVALID_REQUEST, "routing request metadata is invalid"
        )
    return evaluate_policy(request, capabilities)
