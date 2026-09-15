"""Tests for fail-closed, provider-neutral routing contracts."""

from __future__ import annotations

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
    Sensitivity,
    diagnose_route,
)
from second_self.routing.contracts import validate_request

DIGEST_A = "a" * 64
DIGEST_B = "b" * 64
ORIGINS = (DataOrigin(DataOriginKind.PUBLIC, "synthetic"),)


def test_sensitivity_has_exactly_four_stable_values():
    assert [level.value for level in Sensitivity] == [
        "public",
        "ordinary_private",
        "sensitive",
        "prohibited",
    ]


@pytest.mark.parametrize(
    "level", ["public", "ordinary_private", "sensitive"]
)
def test_valid_level_without_capability_denies(level):
    decision = diagnose_route(operation="summarize", sensitivity=level, origins=ORIGINS)

    assert decision.outcome is RouteOutcome.DENY
    assert decision.reason is RouteReason.NO_CAPABLE_PROVIDER


def test_prohibited_denies_before_capability_selection():
    capability = ProviderCapability(
        "synthetic-local",
        ProviderLocality.LOCAL,
        frozenset({"summarize"}),
        available=True,
    )

    decision = diagnose_route(
        operation="summarize",
        sensitivity="prohibited",
        origins=ORIGINS,
        capabilities=(capability,),
    )

    assert decision.reason is RouteReason.PROHIBITED_DATA
    assert decision.provider is None


@pytest.mark.parametrize(
    ("operation", "sensitivity", "origins"),
    [
        ("", "public", ORIGINS),
        ("UPPERCASE", "public", ORIGINS),
        ("summarize", "unknown", ORIGINS),
        ("summarize", "public", ()),
    ],
)
def test_unknown_or_malformed_request_is_stable_denial(
    operation, sensitivity, origins
):
    decision = diagnose_route(
        operation=operation, sensitivity=sensitivity, origins=origins
    )

    assert decision.reason is RouteReason.INVALID_REQUEST
    assert decision.provider is None


def test_matching_exact_payload_approval_is_valid_metadata():
    request = RouteRequest(
        "summarize",
        Sensitivity.SENSITIVE,
        ORIGINS,
        payload_sha256=DIGEST_A,
        approval=ExactPayloadApproval(DIGEST_A, approved=True),
    )

    assert validate_request(request) is None


def test_changed_payload_invalidates_approval_without_exposing_digest():
    decision = diagnose_route(
        operation="summarize",
        sensitivity="sensitive",
        origins=ORIGINS,
        payload_sha256=DIGEST_B,
        approval=ExactPayloadApproval(DIGEST_A, approved=True),
    )

    assert decision.reason is RouteReason.APPROVAL_PAYLOAD_MISMATCH
    assert DIGEST_A not in str(decision.as_dict())
    assert DIGEST_B not in str(decision.as_dict())


@pytest.mark.parametrize(
    ("digest", "approved"), [(DIGEST_A, False), (None, True)]
)
def test_incomplete_approval_metadata_denies(digest, approved):
    decision = diagnose_route(
        operation="summarize",
        sensitivity="sensitive",
        origins=ORIGINS,
        payload_sha256=digest,
        approval=ExactPayloadApproval(DIGEST_A, approved=approved),
    )

    assert decision.reason is RouteReason.APPROVAL_METADATA_INVALID


@pytest.mark.parametrize("digest", ["", "A" * 64, "a" * 63, "not-a-digest"])
def test_malformed_approval_digest_is_rejected(digest):
    with pytest.raises(ValueError, match="lowercase SHA-256"):
        ExactPayloadApproval(digest, approved=True)


def test_capability_contract_can_describe_allow_without_invocation():
    capability = ProviderCapability(
        "synthetic-local",
        ProviderLocality.LOCAL,
        frozenset({"summarize"}),
        available=True,
        configured_model="synthetic-model",
    )

    decision = diagnose_route(
        operation="summarize",
        sensitivity="public",
        origins=ORIGINS,
        capabilities=(capability,),
    )

    assert decision.outcome is RouteOutcome.ALLOW
    assert decision.provider == "synthetic-local"


def test_data_origin_identifier_must_be_path_free():
    with pytest.raises(ValueError, match="path-free"):
        DataOrigin(DataOriginKind.MEMORY, "private/note.md")


def test_unknown_origin_kind_is_rejected():
    with pytest.raises(ValueError, match="origin kind"):
        DataOrigin("external-document")


def test_malformed_capability_collection_denies():
    decision = diagnose_route(
        operation="summarize",
        sensitivity="public",
        origins=ORIGINS,
        capabilities=("not-a-capability",),
    )

    assert decision.reason is RouteReason.INVALID_REQUEST
