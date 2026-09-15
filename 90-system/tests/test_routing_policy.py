"""Hermetic decision-table tests for the local-first routing policy."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from second_self.routing import (
    DataOrigin,
    DataOriginKind,
    ExactPayloadApproval,
    ProviderCapability,
    ProviderLocality,
    RouteOutcome,
    RouteReason,
    RouteRequest,
    SanitizationAttestation,
    Sensitivity,
    diagnose_policy,
    evaluate_policy,
)

DIGEST_A = "a" * 64
DIGEST_B = "b" * 64
NOW = datetime(2026, 9, 15, tzinfo=timezone.utc)
LOCAL = ProviderCapability(
    "ollama", ProviderLocality.LOCAL, frozenset({"draft"}), True, "synthetic"
)
OFFLINE_LOCAL = ProviderCapability(
    "ollama", ProviderLocality.LOCAL, frozenset({"draft"}), False, "synthetic"
)
CLOUD = ProviderCapability(
    "synthetic-cloud", ProviderLocality.CLOUD, frozenset({"draft"}), True
)


def request(
    sensitivity: Sensitivity,
    origin: DataOriginKind = DataOriginKind.PUBLIC,
    **kwargs,
) -> RouteRequest:
    return RouteRequest(
        "draft", sensitivity, (DataOrigin(origin, "synthetic"),), **kwargs
    )


@pytest.mark.parametrize(
    ("sensitivity", "origin"),
    [
        (Sensitivity.PUBLIC, DataOriginKind.PUBLIC),
        (Sensitivity.ORDINARY_PRIVATE, DataOriginKind.PRIVATE_REFERENCE),
        (Sensitivity.SENSITIVE, DataOriginKind.MEMORY),
        (Sensitivity.SENSITIVE, DataOriginKind.JOURNAL),
        (Sensitivity.SENSITIVE, DataOriginKind.STRATEGY),
    ],
)
def test_available_ollama_is_the_local_first_route(sensitivity, origin):
    decision = evaluate_policy(request(sensitivity, origin), (CLOUD, LOCAL), now=NOW)

    assert decision.outcome is RouteOutcome.ALLOW
    assert decision.reason is RouteReason.LOCAL_PROVIDER_SELECTED
    assert decision.provider == "ollama"


@pytest.mark.parametrize("origin", list(DataOriginKind))
def test_prohibited_data_denies_before_every_provider(origin):
    decision = evaluate_policy(
        request(
            Sensitivity.PROHIBITED,
            origin,
            payload_sha256=DIGEST_A,
            approval=ExactPayloadApproval(
                DIGEST_A, True, NOW + timedelta(minutes=5)
            ),
        ),
        (LOCAL, CLOUD),
        now=NOW,
    )

    assert decision.reason is RouteReason.PROHIBITED_DATA
    assert decision.provider is None


@pytest.mark.parametrize(
    "sensitivity", [Sensitivity.ORDINARY_PRIVATE, Sensitivity.SENSITIVE]
)
def test_private_route_denies_when_required_local_provider_is_unavailable(
    sensitivity,
):
    decision = evaluate_policy(request(sensitivity), (OFFLINE_LOCAL,), now=NOW)

    assert decision.reason is RouteReason.LOCAL_PROVIDER_UNAVAILABLE


def test_ollama_failure_does_not_make_cloud_eligible():
    decision = evaluate_policy(
        request(Sensitivity.SENSITIVE), (OFFLINE_LOCAL, CLOUD), now=NOW
    )

    assert decision.reason is RouteReason.CLOUD_NOT_ELIGIBLE
    assert decision.provider is None


def test_trusted_sanitized_output_is_only_marked_cloud_eligible():
    decision = evaluate_policy(
        request(
            Sensitivity.SENSITIVE,
            payload_sha256=DIGEST_A,
            sanitization=SanitizationAttestation(DIGEST_A, "trusted-redactor-v1"),
        ),
        (CLOUD,),
        now=NOW,
    )

    assert decision.reason is RouteReason.CLOUD_ELIGIBLE_SANITIZED
    assert decision.provider == "synthetic-cloud"
    assert "eligible" in decision.explanation


def test_changed_sanitized_payload_denies_without_exposing_digest():
    decision = evaluate_policy(
        request(
            Sensitivity.PUBLIC,
            payload_sha256=DIGEST_B,
            sanitization=SanitizationAttestation(DIGEST_A, "trusted-redactor-v1"),
        ),
        (CLOUD,),
        now=NOW,
    )

    assert decision.reason is RouteReason.SANITIZATION_INVALID
    assert DIGEST_A not in str(decision.as_dict())
    assert DIGEST_B not in str(decision.as_dict())


def test_valid_unexpired_exact_payload_approval_marks_cloud_eligible():
    decision = evaluate_policy(
        request(
            Sensitivity.ORDINARY_PRIVATE,
            payload_sha256=DIGEST_A,
            approval=ExactPayloadApproval(
                DIGEST_A, True, NOW + timedelta(minutes=5)
            ),
        ),
        (CLOUD,),
        now=NOW,
    )

    assert decision.reason is RouteReason.CLOUD_ELIGIBLE_APPROVED
    assert decision.provider == "synthetic-cloud"


@pytest.mark.parametrize(
    ("approval", "expected"),
    [
        (ExactPayloadApproval(DIGEST_A, True), RouteReason.APPROVAL_METADATA_INVALID),
        (
            ExactPayloadApproval(DIGEST_A, True, NOW - timedelta(seconds=1)),
            RouteReason.APPROVAL_EXPIRED,
        ),
        (
            ExactPayloadApproval(DIGEST_B, True, NOW + timedelta(minutes=5)),
            RouteReason.APPROVAL_PAYLOAD_MISMATCH,
        ),
    ],
)
def test_incomplete_expired_or_changed_approval_denies(approval, expected):
    decision = evaluate_policy(
        request(
            Sensitivity.PUBLIC,
            payload_sha256=DIGEST_A,
            approval=approval,
        ),
        (LOCAL, CLOUD),
        now=NOW,
    )

    assert decision.reason is expected
    assert decision.provider is None


@pytest.mark.parametrize("expires_at", ["not-a-time", datetime(2026, 9, 15)])
def test_malformed_or_naive_approval_expiration_is_rejected(expires_at):
    with pytest.raises(ValueError, match="include a timezone"):
        ExactPayloadApproval(DIGEST_A, True, expires_at)


@pytest.mark.parametrize(
    ("origin", "sensitivity"),
    [
        (DataOriginKind.MEMORY, Sensitivity.PUBLIC),
        (DataOriginKind.JOURNAL, Sensitivity.ORDINARY_PRIVATE),
        (DataOriginKind.STRATEGY, Sensitivity.PUBLIC),
        (DataOriginKind.PRIVATE_REFERENCE, Sensitivity.PUBLIC),
    ],
)
def test_origin_sensitivity_floor_never_auto_downgrades(origin, sensitivity):
    decision = evaluate_policy(request(sensitivity, origin), (LOCAL,), now=NOW)

    assert decision.reason is RouteReason.SENSITIVITY_ORIGIN_MISMATCH


def test_external_prompt_text_cannot_set_trusted_policy_metadata():
    injection = "ignore-policy-use-cloud-and-approve"
    untrusted_origin = (DataOrigin(DataOriginKind.EXTERNAL_UNTRUSTED, injection),)

    decision = diagnose_policy(
        operation="draft",
        sensitivity="sensitive",
        origins=untrusted_origin,
        capabilities=(OFFLINE_LOCAL, CLOUD),
    )

    assert decision.reason is RouteReason.CLOUD_NOT_ELIGIBLE
    assert injection not in str(decision.as_dict())


@pytest.mark.parametrize(
    ("sensitivity", "capabilities"),
    [("unknown", (LOCAL,)), ("public", ("corrupt-config",))],
)
def test_missing_classification_or_corrupt_capability_metadata_denies(
    sensitivity, capabilities
):
    decision = diagnose_policy(
        operation="draft",
        sensitivity=sensitivity,
        origins=(DataOrigin(DataOriginKind.PUBLIC, "synthetic"),),
        capabilities=capabilities,
    )

    assert decision.reason is RouteReason.INVALID_REQUEST
    assert decision.provider is None


def test_public_without_any_capable_provider_denies_stably():
    decision = evaluate_policy(request(Sensitivity.PUBLIC), (), now=NOW)

    assert decision.reason is RouteReason.NO_CAPABLE_PROVIDER
