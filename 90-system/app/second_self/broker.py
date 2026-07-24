from __future__ import annotations

import difflib
import hashlib
import json
import os
import shutil
import subprocess
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from .paths import SecondSelfPaths, resolve_private_path


ALLOWED_OPERATIONS = {
    "edit",
    "migration",
    "delete",
    "move",
    "export",
    "assemble_layer1",
    "wiki_process",
}
LAYER1_SCAFFOLD_FILES = (
    "00 Memory/.gitkeep",
    "01 Notes/.gitkeep",
    "02 Journal/.gitkeep",
    "03 Strategy/.gitkeep",
    "04 References/.gitkeep",
    "05 Reviews/.gitkeep",
)


def _hash(path: Path) -> str | None:
    if not path.exists():
        return None
    digest = hashlib.sha256()
    if path.is_dir():
        for child in sorted(path.rglob("*"), key=lambda item: item.as_posix()):
            relative = child.relative_to(path).as_posix()
            digest.update(relative.encode("utf-8"))
            digest.update(b"\0")
            if child.is_file():
                with child.open("rb") as stream:
                    for block in iter(lambda: stream.read(1024 * 1024), b""):
                        digest.update(block)
            digest.update(b"\0")
        return digest.hexdigest()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _proposal_path(paths: SecondSelfPaths, proposal_id: str) -> Path:
    return paths.audit / "proposals" / f"{proposal_id}.json"


def _path_label(paths: SecondSelfPaths, path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(paths.data_root.resolve()).as_posix()
    except ValueError:
        pass
    try:
        relative = resolved.relative_to(paths.repo_root.resolve()).as_posix()
        return f"@repo/{relative}"
    except ValueError:
        pass
    return path.name


def _affected(paths: SecondSelfPaths, specification: dict[str, Any]) -> list[Path]:
    operation = specification["operation"]
    if operation in {"edit", "migration", "wiki_process"}:
        affected = [
            resolve_private_path(paths, item["path"])
            for item in specification.get("changes", [])
        ]
        if operation == "wiki_process":
            affected.extend(
                resolve_private_path(paths, item["from"])
                for item in specification.get("moves", [])
            )
        return affected
    if operation == "delete":
        return [resolve_private_path(paths, value) for value in specification["paths"]]
    if operation == "move":
        return [resolve_private_path(paths, item["from"]) for item in specification["moves"]]
    if operation == "export":
        return [resolve_private_path(paths, value) for value in specification.get("sources", [])]
    if operation == "assemble_layer1":
        return [
            paths.repo_root / "01-strategy-storage",
            *[paths.layer1 / value for value in LAYER1_SCAFFOLD_FILES],
        ]
    raise ValueError(f"Unsupported operation: {operation}")


def _exact_preview(paths: SecondSelfPaths, specification: dict[str, Any]) -> str:
    operation = specification["operation"]
    if operation in {"edit", "migration", "wiki_process"}:
        chunks: list[str] = []
        for item in specification.get("changes", []):
            path = resolve_private_path(paths, item["path"])
            old = path.read_text(encoding="utf-8") if path.exists() else ""
            new = item["content"]
            chunks.extend(
                difflib.unified_diff(
                    old.splitlines(),
                    new.splitlines(),
                    fromfile=_path_label(paths, path),
                    tofile=_path_label(paths, path),
                    lineterm="",
                )
            )
        if operation == "wiki_process":
            chunks.extend(
                [
                    "",
                    "## Source archive moves",
                    json.dumps(specification.get("moves", []), indent=2),
                ]
            )
        return "\n".join(chunks)
    if operation == "assemble_layer1":
        return json.dumps(
            {
                "operation": operation,
                "replace": "01-strategy-storage scaffold",
                "with": "junction to configured private Layer 1",
                "preserve_tracked_files": list(LAYER1_SCAFFOLD_FILES),
            },
            indent=2,
        )
    return json.dumps(specification, indent=2)


def _assemble_layer1(paths: SecondSelfPaths) -> list[str]:
    scaffold = paths.repo_root / "01-strategy-storage"
    target = paths.layer1.resolve()
    pending = paths.repo_root / ".second-self-layer1-junction.pending"

    if os.name != "nt":
        raise RuntimeError("Layer 1 junction assembly is supported only on Windows.")
    if not target.is_dir():
        raise FileNotFoundError(target)
    if os.path.isjunction(scaffold):
        if scaffold.resolve() != target:
            raise RuntimeError("Layer 1 already points to a different junction target.")
        return []
    if not scaffold.is_dir():
        raise FileNotFoundError(scaffold)
    if pending.exists() or os.path.isjunction(pending):
        raise FileExistsError(pending)

    existing_files = {
        item.relative_to(scaffold).as_posix()
        for item in scaffold.rglob("*")
        if item.is_file()
    }
    unexpected = existing_files.difference(LAYER1_SCAFFOLD_FILES)
    if unexpected:
        raise RuntimeError(
            "Layer 1 scaffold contains unexpected files: "
            + ", ".join(sorted(unexpected))
        )

    for relative in LAYER1_SCAFFOLD_FILES:
        source = scaffold / relative
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        if source.exists() and not destination.exists():
            shutil.copy2(source, destination)

    try:
        subprocess.run(
            ["cmd.exe", "/d", "/c", "mklink", "/J", str(pending), str(target)],
            check=True,
            capture_output=True,
            text=True,
        )
        shutil.rmtree(scaffold)
        pending.rename(scaffold)
    except Exception:
        if os.path.isjunction(pending):
            pending.rmdir()
        if not scaffold.exists():
            scaffold.mkdir()
            for relative in LAYER1_SCAFFOLD_FILES:
                source = target / relative
                destination = scaffold / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                if source.exists():
                    shutil.copy2(source, destination)
        raise

    return [str(scaffold), str(target)]


def propose(paths: SecondSelfPaths, specification: dict[str, Any]) -> dict[str, Any]:
    operation = specification.get("operation")
    if operation not in ALLOWED_OPERATIONS:
        raise ValueError(f"operation must be one of {sorted(ALLOWED_OPERATIONS)}")
    affected = _affected(paths, specification)
    proposal_id = datetime.now().strftime("%Y%m%d%H%M%S") + "-" + uuid.uuid4().hex[:8]
    proposal = {
        "id": proposal_id,
        "created": datetime.now().astimezone().isoformat(),
        "status": "intent-pending",
        "specification": specification,
        "input_hashes": {
            _path_label(paths, path): _hash(path)
            for path in affected
        },
        "exact_preview": _exact_preview(paths, specification),
    }
    path = _proposal_path(paths, proposal_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(proposal, indent=2) + "\n", encoding="utf-8")
    return proposal


def load_proposal(paths: SecondSelfPaths, proposal_id: str) -> dict[str, Any]:
    return json.loads(_proposal_path(paths, proposal_id).read_text(encoding="utf-8"))


def approve_intent(
    paths: SecondSelfPaths, proposal_id: str, confirmation: str
) -> dict[str, Any]:
    proposal = load_proposal(paths, proposal_id)
    expected = f"APPROVE INTENT {proposal_id}"
    if confirmation != expected:
        raise PermissionError(f"Confirmation must exactly match: {expected}")
    if proposal["status"] != "intent-pending":
        raise ValueError(f"Proposal status is {proposal['status']}")
    proposal["status"] = "exact-pending"
    proposal["intent_approved"] = datetime.now().astimezone().isoformat()
    _proposal_path(paths, proposal_id).write_text(
        json.dumps(proposal, indent=2) + "\n", encoding="utf-8"
    )
    return proposal


def _check_stale(paths: SecondSelfPaths, proposal: dict[str, Any]) -> None:
    for value, expected in proposal["input_hashes"].items():
        if value.startswith("@repo/"):
            candidate = paths.repo_root / value.removeprefix("@repo/")
        else:
            candidate = Path(value)
        if not candidate.is_absolute():
            candidate = paths.data_root / candidate
        actual = _hash(candidate)
        if actual != expected:
            raise RuntimeError(
                f"Stale approval: {value} changed after proposal. Create a new proposal."
            )


def _write_journal(path: Path, journal: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(journal, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _rollback_wiki_transaction(
    paths: SecondSelfPaths, stage: Path, journal: dict[str, Any]
) -> None:
    for move in reversed(journal.get("moves", [])):
        source = resolve_private_path(paths, move["from"])
        destination = resolve_private_path(paths, move["to"])
        if destination.exists() and not source.exists():
            source.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(destination), source)
    for change in reversed(journal.get("changes", [])):
        target = resolve_private_path(paths, change["path"])
        backup = stage / change["backup"]
        expected = change.get("expected_hash")
        if target.exists() and expected and _hash(target) not in {
            expected,
            _hash(backup) if backup.exists() else None,
        }:
            raise RuntimeError(
                f"Refusing recovery because {change['path']} has unrelated content"
            )
        if change["existed"] and backup.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            os.replace(backup, target)
        elif (
            not change["existed"]
            and target.exists()
            and (not expected or _hash(target) == expected)
        ):
            target.unlink()


def _apply_wiki_process(
    paths: SecondSelfPaths,
    specification: dict[str, Any],
    proposal_id: str,
) -> list[str]:
    from .wiki import validate_wiki_change_set

    changes = specification.get("changes", [])
    moves = specification.get("moves", [])
    if not changes:
        raise ValueError("wiki_process requires at least one wiki change")
    if len(moves) > 10:
        raise ValueError("wiki_process supports at most ten source units")

    if paths.wiki_transactions.exists():
        for existing in paths.wiki_transactions.glob("*/journal.json"):
            payload = json.loads(existing.read_text(encoding="utf-8"))
            if payload.get("status") in {"staging", "applying"}:
                raise RuntimeError(
                    f"Recover interrupted wiki transaction {payload.get('id', existing.parent.name)} first"
                )

    stage = paths.wiki_transactions / proposal_id
    if stage.exists():
        raise FileExistsError(f"Transaction staging already exists: {proposal_id}")
    (stage / "new").mkdir(parents=True)
    (stage / "backups").mkdir()
    journal_path = stage / "journal.json"
    journal: dict[str, Any] = {
        "id": proposal_id,
        "status": "staging",
        "changes": [],
        "moves": [{**item, "applied": False} for item in moves],
    }

    for index, item in enumerate(changes):
        target = resolve_private_path(paths, item["path"])
        try:
            target.relative_to(paths.wiki.resolve())
        except ValueError as exc:
            raise ValueError(f"Wiki change escapes 03-wiki: {item['path']}") from exc
        staged = stage / "new" / f"{index}.md"
        staged.write_text(item["content"], encoding="utf-8")
        backup = stage / "backups" / f"{index}.md"
        existed = target.exists()
        if existed:
            shutil.copy2(target, backup)
        journal["changes"].append(
            {
                "path": str(target.relative_to(paths.data_root).as_posix()),
                "staged": str(staged.relative_to(stage).as_posix()),
                "backup": str(backup.relative_to(stage).as_posix()),
                "existed": existed,
                "expected_hash": _hash(staged),
                "applied": False,
            }
        )

    for item in moves:
        source = resolve_private_path(paths, item["from"])
        destination = resolve_private_path(paths, item["to"])
        try:
            source.relative_to(paths.raw.resolve())
            destination.relative_to(paths.processed.resolve())
        except ValueError as exc:
            raise ValueError("wiki_process moves must be Raw -> Processed") from exc
        if not source.exists():
            raise FileNotFoundError(source)
        if destination.exists():
            raise FileExistsError(destination)

    validate_wiki_change_set(paths, changes)
    _write_journal(journal_path, journal)
    changed: list[str] = []
    try:
        journal["status"] = "applying"
        _write_journal(journal_path, journal)
        for record in journal["changes"]:
            target = resolve_private_path(paths, record["path"])
            staged = stage / record["staged"]
            target.parent.mkdir(parents=True, exist_ok=True)
            os.replace(staged, target)
            record["applied"] = True
            _write_journal(journal_path, journal)
            changed.append(str(target))
        for item in journal["moves"]:
            source = resolve_private_path(paths, item["from"])
            destination = resolve_private_path(paths, item["to"])
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(source), destination)
            item["applied"] = True
            _write_journal(journal_path, journal)
            changed.extend([str(source), str(destination)])
        journal["status"] = "committed"
        _write_journal(journal_path, journal)
        return changed
    except Exception:
        _rollback_wiki_transaction(paths, stage, journal)
        journal["status"] = "rolled-back"
        _write_journal(journal_path, journal)
        raise


def recover_wiki_transactions(paths: SecondSelfPaths) -> list[str]:
    recovered: list[str] = []
    if not paths.wiki_transactions.exists():
        return recovered
    for journal_path in sorted(paths.wiki_transactions.glob("*/journal.json")):
        journal = json.loads(journal_path.read_text(encoding="utf-8"))
        if journal.get("status") not in {"staging", "applying"}:
            continue
        _rollback_wiki_transaction(paths, journal_path.parent, journal)
        journal["status"] = "rolled-back"
        _write_journal(journal_path, journal)
        recovered.append(str(journal.get("id", journal_path.parent.name)))
    return recovered


def _apply(
    paths: SecondSelfPaths,
    specification: dict[str, Any],
    proposal_id: str,
) -> list[str]:
    operation = specification["operation"]
    changed: list[str] = []
    if operation in {"edit", "migration"}:
        for item in specification["changes"]:
            path = resolve_private_path(paths, item["path"])
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(item["content"], encoding="utf-8")
            changed.append(str(path))
    elif operation == "delete":
        stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        trash = paths.trash / stamp
        trash.mkdir(parents=True, exist_ok=True)
        for value in specification["paths"]:
            source = resolve_private_path(paths, value)
            if source.exists():
                destination = trash / source.name
                counter = 1
                while destination.exists():
                    destination = trash / f"{source.stem}-{counter}{source.suffix}"
                    counter += 1
                shutil.move(str(source), destination)
                changed.extend([str(source), str(destination)])
    elif operation == "move":
        for item in specification["moves"]:
            source = resolve_private_path(paths, item["from"])
            destination = resolve_private_path(paths, item["to"])
            destination.parent.mkdir(parents=True, exist_ok=True)
            if destination.exists():
                raise FileExistsError(destination)
            shutil.move(str(source), destination)
            changed.extend([str(source), str(destination)])
    elif operation == "export":
        destination = Path(specification["destination"]).expanduser().resolve()
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            raise FileExistsError(destination)
        destination.write_text(specification["content"], encoding="utf-8")
        changed.append(str(destination))
    elif operation == "assemble_layer1":
        changed.extend(_assemble_layer1(paths))
    elif operation == "wiki_process":
        changed.extend(_apply_wiki_process(paths, specification, proposal_id))
    return changed


def approve_exact(
    paths: SecondSelfPaths, proposal_id: str, confirmation: str, agent: str = "unknown"
) -> dict[str, Any]:
    proposal = load_proposal(paths, proposal_id)
    expected = f"APPLY {proposal_id}"
    if confirmation != expected:
        raise PermissionError(f"Confirmation must exactly match: {expected}")
    if proposal["status"] != "exact-pending":
        raise ValueError(f"Proposal status is {proposal['status']}")
    _check_stale(paths, proposal)
    operation = proposal["specification"]["operation"]
    lock: Path | None = None
    lock_handle: int | None = None
    if operation == "wiki_process":
        paths.wiki_transactions.mkdir(parents=True, exist_ok=True)
        lock = paths.wiki_transactions / ".processing.lock"
        try:
            lock_handle = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError as exc:
            raise RuntimeError("Another wiki transaction is already active") from exc
    try:
        changed = _apply(paths, proposal["specification"], proposal_id)
    finally:
        if lock_handle is not None:
            os.close(lock_handle)
        if lock is not None and lock.exists():
            lock.unlink()
    proposal["status"] = "applied"
    proposal["applied"] = datetime.now().astimezone().isoformat()
    proposal["changed_paths"] = [
        _path_label(paths, Path(value)) for value in changed
    ]
    _proposal_path(paths, proposal_id).write_text(
        json.dumps(proposal, indent=2) + "\n", encoding="utf-8"
    )
    paths.audit.mkdir(parents=True, exist_ok=True)
    event = {
        "time": proposal["applied"],
        "agent": agent,
        "action": proposal["specification"]["operation"],
        "paths": proposal["changed_paths"],
        "approval": proposal_id,
    }
    with (paths.audit / "agent-edits.jsonl").open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(event) + "\n")
    return proposal
