"""Validated wiki proposal and result models."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class WikiProposal:
    operation: str
    changes: tuple[dict[str, str], ...]
    moves: tuple[dict[str, str], ...] = ()

    @classmethod
    def from_payload(cls, payload: Mapping[str, object]) -> "WikiProposal":
        operation = payload.get("operation")
        if operation != "wiki_process":
            raise ValueError("wiki operation must be wiki_process")
        raw_changes = payload.get("changes")
        if not isinstance(raw_changes, list):
            raise ValueError("changes must be a list")
        changes: list[dict[str, str]] = []
        for raw in raw_changes:
            if not isinstance(raw, Mapping) or not isinstance(raw.get("path"), str):
                raise ValueError("change path must be a string")
            if not isinstance(raw.get("content"), str):
                raise ValueError("content must be a string")
            changes.append({"path": raw["path"], "content": raw["content"]})
        raw_moves = payload.get("moves", [])
        if not isinstance(raw_moves, list):
            raise ValueError("moves must be a list")
        moves: list[dict[str, str]] = []
        for raw in raw_moves:
            if not isinstance(raw, Mapping) or not all(
                isinstance(raw.get(key), str) for key in ("from", "to")
            ):
                raise ValueError("move paths must be strings")
            moves.append({"from": raw["from"], "to": raw["to"]})
        return cls("wiki_process", tuple(changes), tuple(moves))


@dataclass(frozen=True, slots=True)
class WikiResult:
    status: str
    changed_paths: tuple[str, ...] = ()
    changed_count: int = 0

    def as_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "changed_paths": list(self.changed_paths),
            "changed_count": self.changed_count,
        }
