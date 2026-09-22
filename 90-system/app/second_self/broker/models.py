"""Validated broker boundary models with stable public serialization."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

ALLOWED_OPERATIONS = frozenset(
    {"edit", "migration", "delete", "move", "export", "assemble_layer1", "wiki_process", "link_fix"}
)


def _mapping(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be an object")
    return dict(value)


def _string_list(value: object, label: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"{label} must be a list of strings")
    return tuple(value)


@dataclass(frozen=True, slots=True)
class BrokerSpecification:
    operation: str
    payload: dict[str, object]

    @classmethod
    def from_payload(cls, payload: Mapping[str, object]) -> "BrokerSpecification":
        value = _mapping(payload, "specification")
        operation = value.get("operation")
        if not isinstance(operation, str) or operation not in ALLOWED_OPERATIONS:
            raise ValueError(f"unsupported operation: {operation!r}")
        changes = value.get("changes")
        if changes is not None:
            if not isinstance(changes, list):
                raise ValueError("changes must be a list")
            for item in changes:
                change = _mapping(item, "change")
                if not isinstance(change.get("path"), str):
                    raise ValueError("change path must be a string")
                if "content" in change and not isinstance(change["content"], str):
                    raise ValueError("content must be a string")
        moves = value.get("moves")
        if moves is not None:
            if not isinstance(moves, list):
                raise ValueError("moves must be a list")
            for item in moves:
                move = _mapping(item, "move")
                for key in ("from", "to"):
                    if not isinstance(move.get(key), str):
                        raise ValueError(f"move {key} must be a string")
        if "paths" in value:
            _string_list(value["paths"], "paths")
        return cls(operation, value)

    def as_dict(self) -> dict[str, object]:
        return dict(self.payload)


@dataclass(frozen=True, slots=True)
class BrokerProposal:
    proposal_id: str
    created: str
    status: str
    schema: str
    version: int
    specification: BrokerSpecification
    input_hashes: dict[str, object]
    exact_preview: str
    approval_digest: str = ""

    @classmethod
    def from_payload(
        cls,
        payload: Mapping[str, object],
        *,
        validate_schema: bool = True,
    ) -> "BrokerProposal":
        value = _mapping(payload, "proposal")
        required = (
            "id",
            "created",
            "status",
            "schema",
            "version",
            "specification",
            "input_hashes",
            "exact_preview",
        )
        if any(key not in value for key in required):
            raise ValueError("proposal is missing required fields")
        if not all(
            isinstance(value[key], str)
            for key in ("id", "created", "status", "schema", "exact_preview")
        ):
            raise ValueError("proposal scalar fields must be strings")
        if not isinstance(value["version"], int):
            raise ValueError("proposal version must be an integer")
        if validate_schema and (
            value["schema"] != "second-self-broker-proposal" or value["version"] != 1
        ):
            raise ValueError("proposal schema is unsupported")
        return cls(
            str(value["id"]), str(value["created"]), str(value["status"]), str(value["schema"]),
            int(value["version"]),
            BrokerSpecification.from_payload(_mapping(value["specification"], "specification")),
            _mapping(value["input_hashes"], "input_hashes"), str(value["exact_preview"]),
            str(value.get("approval_digest", "")),
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.proposal_id,
            "created": self.created,
            "status": self.status,
            "schema": self.schema,
            "version": self.version,
            "specification": self.specification.as_dict(),
            "input_hashes": dict(self.input_hashes),
            "exact_preview": self.exact_preview,
            "approval_digest": self.approval_digest,
        }


@dataclass(frozen=True, slots=True)
class BrokerResult:
    status: str
    changed_paths: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, object]:
        return {"status": self.status, "changed_paths": list(self.changed_paths)}
