from __future__ import annotations

import difflib
import hashlib
import hmac
import json
import os
import shutil
import subprocess
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from ..core.paths import SecondSelfPaths, resolve_private_path
from ..core.scaffold import PUBLIC_SCAFFOLD_FILES


ALLOWED_OPERATIONS = {
    "edit",
    "migration",
    "delete",
    "move",
    "export",
    "assemble_layer1",
    "wiki_process",
    "link_fix",
}
LAYER1_SCAFFOLD_FILES = PUBLIC_SCAFFOLD_FILES["01-strategy-storage"]
APPROVAL_PENDING_STATUSES = {
    "approval-pending",
    "intent-pending",
    "exact-pending",
}
PROPOSAL_SCHEMA = "second-self-broker-proposal"
PROPOSAL_VERSION = 1
TRANSACTION_SCHEMA = "second-self-broker-transaction"
TRANSACTION_VERSION = 1
WIKI_LOCK_STALE_SECONDS = 15 * 60
WIKI_LOCK_SCHEMA = "second-self-wiki-lock"


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


def _proposal_lock_path(paths: SecondSelfPaths, proposal_id: str) -> Path:
    return _proposal_path(paths, proposal_id).with_suffix(".lock")


def _approval_digest(proposal: dict[str, Any]) -> str:
    payload = {
        "specification": proposal["specification"],
        "input_hashes": proposal["input_hashes"],
        "exact_preview": proposal["exact_preview"],
    }
    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _validate_proposal_schema(proposal: dict[str, Any]) -> None:
    if (
        proposal.get("schema") != PROPOSAL_SCHEMA
        or proposal.get("version") != PROPOSAL_VERSION
    ):
        raise RuntimeError(
            "Proposal schema is unsupported. Create a new proposal."
        )


def _validate_approval_digest(proposal: dict[str, Any]) -> None:
    supplied = proposal.get("approval_digest")
    if (
        not isinstance(supplied, str)
        or len(supplied) != 64
        or any(character not in "0123456789abcdef" for character in supplied)
    ):
        raise RuntimeError(
            "Proposal integrity metadata is missing or invalid. "
            "Create a new proposal."
        )
    try:
        expected = _approval_digest(proposal)
    except (KeyError, TypeError, ValueError) as exc:
        raise RuntimeError(
            "Proposal integrity metadata is missing or invalid. "
            "Create a new proposal."
        ) from exc
    if not hmac.compare_digest(supplied, expected):
        raise RuntimeError(
            "Proposal integrity check failed. Create a new proposal."
        )


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
    if operation == "link_fix":
        return [resolve_private_path(paths, item["path"]) for item in specification["fixes"]]
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
    if operation == "link_fix":
        chunks: list[str] = []
        for item in specification["fixes"]:
            path = resolve_private_path(paths, item["path"])
            old = path.read_text(encoding="utf-8") if path.exists() else ""
            new = old
            for replacement in item.get("replacements", []):
                new = new.replace(replacement["old"], replacement["new"], 1)
            chunks.extend(
                difflib.unified_diff(
                    old.splitlines(),
                    new.splitlines(),
                    fromfile=_path_label(paths, path),
                    tofile=_path_label(paths, path),
                    lineterm="",
                )
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
        "status": "approval-pending",
        "schema": PROPOSAL_SCHEMA,
        "version": PROPOSAL_VERSION,
        "specification": specification,
        "input_hashes": {
            _path_label(paths, path): _hash(path)
            for path in affected
        },
        "exact_preview": _exact_preview(paths, specification),
    }
    proposal["approval_digest"] = _approval_digest(proposal)
    path = _proposal_path(paths, proposal_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(proposal, indent=2) + "\n", encoding="utf-8")
    return proposal


def load_proposal(paths: SecondSelfPaths, proposal_id: str) -> dict[str, Any]:
    return json.loads(_proposal_path(paths, proposal_id).read_text(encoding="utf-8"))


def _approval_decision(confirmation: str) -> bool:
    decision = confirmation.strip().casefold()
    if decision in {"y", "yes"}:
        return True
    if decision in {"n", "no"}:
        return False
    raise PermissionError("Answer Yes or No (Y/N).")


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


def _transaction_stage(paths: SecondSelfPaths, proposal_id: str) -> Path:
    return paths.audit / "transactions" / proposal_id


def _transaction_targets(
    paths: SecondSelfPaths, specification: dict[str, Any]
) -> list[Path]:
    targets = list(_affected(paths, specification))
    operation = specification["operation"]
    if operation in {"move", "wiki_process"}:
        targets.extend(
            resolve_private_path(paths, item["to"])
            for item in specification.get("moves", [])
        )
    elif operation == "export":
        targets.append(Path(specification["destination"]).expanduser().resolve())
    unique: list[Path] = []
    seen: set[str] = set()
    for target in targets:
        key = str(target.resolve()).casefold()
        if key not in seen:
            seen.add(key)
            unique.append(target)
    return unique


def _remove_transaction_path(path: Path) -> None:
    if os.path.isjunction(path):
        path.rmdir()
    elif path.is_dir():
        shutil.rmtree(path)
    elif path.exists():
        path.unlink()


def _begin_transaction(
    paths: SecondSelfPaths, proposal_id: str, specification: dict[str, Any]
) -> tuple[Path, dict[str, Any]]:
    stage = _transaction_stage(paths, proposal_id)
    if stage.exists():
        raise FileExistsError(f"Transaction staging already exists: {proposal_id}")
    backups = stage / "backups"
    backups.mkdir(parents=True)
    records: list[dict[str, Any]] = []
    try:
        for index, target in enumerate(_transaction_targets(paths, specification)):
            existed = target.exists() or os.path.isjunction(target)
            record: dict[str, Any] = {
                "path": str(target),
                "backup": f"{index}",
                "existed": existed,
                "original_hash": _hash(target),
                "kind": "missing",
            }
            if existed and os.path.isjunction(target):
                record["kind"] = "junction"
                record["target"] = str(target.resolve())
            elif existed and target.is_dir():
                record["kind"] = "directory"
                shutil.copytree(target, backups / str(index))
            elif existed:
                record["kind"] = "file"
                shutil.copy2(target, backups / str(index))
            records.append(record)
        journal = {
            "schema": TRANSACTION_SCHEMA,
            "version": TRANSACTION_VERSION,
            "id": proposal_id,
            "operation": specification["operation"],
            "status": "staging",
            "records": records,
            "dynamic_paths": [],
        }
        _write_journal(stage / "journal.json", journal)
        journal["status"] = "applying"
        _write_journal(stage / "journal.json", journal)
        return stage, journal
    except Exception:
        shutil.rmtree(stage, ignore_errors=True)
        raise


def _rollback_transaction(stage: Path, journal: dict[str, Any]) -> None:
    for value in reversed(journal.get("dynamic_paths", [])):
        path = Path(value)
        if path.exists() or os.path.isjunction(path):
            _remove_transaction_path(path)
    for record in reversed(journal.get("records", [])):
        path = Path(record["path"])
        if path.exists() or os.path.isjunction(path):
            _remove_transaction_path(path)
        if not record.get("existed"):
            continue
        kind = record.get("kind")
        if kind == "junction":
            subprocess.run(
                ["cmd.exe", "/d", "/c", "mklink", "/J", str(path), record["target"]],
                check=True,
                capture_output=True,
                text=True,
            )
        elif kind == "directory":
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(stage / "backups" / record["backup"], path)
        elif kind == "file":
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(stage / "backups" / record["backup"], path)


def _checkpoint_transaction(stage: Path, journal: dict[str, Any]) -> None:
    hashes = {
        record["path"]: _hash(Path(record["path"]))
        for record in journal.get("records", [])
    }
    hashes.update(
        {value: _hash(Path(value)) for value in journal.get("dynamic_paths", [])}
    )
    journal["checkpoint_hashes"] = hashes
    _write_journal(stage / "journal.json", journal)


def _assert_recovery_safe(journal: dict[str, Any]) -> None:
    checkpoint_hashes = journal.get("checkpoint_hashes", {})
    for record in journal.get("records", []):
        path = Path(record["path"])
        current_hash = _hash(path)
        allowed = {record.get("original_hash"), checkpoint_hashes.get(str(path))}
        if current_hash not in allowed:
            raise RuntimeError(
                f"Refusing broker recovery because {record['path']} has unrelated content"
            )
    for value in journal.get("dynamic_paths", []):
        path = Path(value)
        if _hash(path) != checkpoint_hashes.get(value):
            raise RuntimeError(
                f"Refusing broker recovery because {value} has unrelated content"
            )


def _recover_transactions(paths: SecondSelfPaths) -> list[str]:
    root = paths.audit / "transactions"
    if not root.exists():
        return []
    recovered: list[str] = []
    for journal_path in sorted(root.glob("*/journal.json")):
        journal = json.loads(journal_path.read_text(encoding="utf-8"))
        if journal.get("schema") != TRANSACTION_SCHEMA or journal.get("version") != TRANSACTION_VERSION:
            raise RuntimeError("Broker transaction journal is unsupported")
        if journal.get("status") not in {"staging", "applying"}:
            continue
        _assert_recovery_safe(journal)
        _rollback_transaction(journal_path.parent, journal)
        journal["status"] = "rolled-back"
        _write_journal(journal_path, journal)
        recovered.append(str(journal.get("id", journal_path.parent.name)))
    return recovered


def _prune_empty_references_parents(paths: SecondSelfPaths, start: Path) -> None:
    """Prune empty parent directories under 04 References after a move-out."""
    references = (paths.layer1 / "04 References").resolve()
    current = start.resolve()
    try:
        current.relative_to(references)
    except ValueError:
        return
    while current != references:
        try:
            current.rmdir()
        except OSError:
            return
        current = current.parent


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
    from ..wiki.wiki import validate_wiki_change_set

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
        raw_to_references = False
        try:
            source.relative_to(paths.raw.resolve())
            raw_to_references = (
                destination.parent.parent == paths.layer1 / "04 References"
                and destination.parent.name
                in {
                    "01 books",
                    "02 quotes",
                    "03 research",
                    "04 guides",
                    "05 docs",
                    "06 Uncategorized",
                }
            )
        except ValueError:
            pass
        if not raw_to_references:
            raise ValueError(
                "wiki_process moves must be Raw -> 04 References/{subfolder}"
            )
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
        for item in journal["moves"]:
            source = resolve_private_path(paths, item["from"])
            _prune_empty_references_parents(paths, source.parent)
        # Verify source_path consistency for wiki pages pointing to References.
        for record in journal["changes"]:
            target = resolve_private_path(paths, record["path"])
            if (
                target.parent.name == "sources"
                and target.exists()
            ):
                from ..core.frontmatter import read_note
                try:
                    metadata, _ = read_note(target)
                except (OSError, UnicodeError, ValueError):
                    continue
                source_path = str(metadata.get("source_path", ""))
                if source_path.startswith("04 References"):
                    referenced = resolve_private_path(paths, source_path)
                    if not referenced.exists():
                        raise RuntimeError(
                            f"Wiki source page {record['path']} references "
                            f"{source_path} but that path does not exist"
                        )
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


def _wiki_transaction_is_active(paths: SecondSelfPaths) -> bool:
    if not paths.wiki_transactions.exists():
        return False
    for journal_path in paths.wiki_transactions.glob("*/journal.json"):
        journal = json.loads(journal_path.read_text(encoding="utf-8"))
        if journal.get("status") in {"staging", "applying"}:
            return True
    return False


def _acquire_wiki_lock(
    paths: SecondSelfPaths, proposal_id: str
) -> tuple[Path, int]:
    paths.wiki_transactions.mkdir(parents=True, exist_ok=True)
    lock = paths.wiki_transactions / ".processing.lock"
    try:
        handle = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        try:
            payload = json.dumps(
                {
                    "schema": WIKI_LOCK_SCHEMA,
                    "proposal_id": proposal_id,
                    "created_at": datetime.now().astimezone().isoformat(),
                }
            ).encode("utf-8")
            os.write(handle, payload)
            return lock, handle
        except Exception:
            os.close(handle)
            lock.unlink(missing_ok=True)
            raise
    except FileExistsError as exc:
        age = time.time() - lock.stat().st_mtime
        if age <= WIKI_LOCK_STALE_SECONDS or _wiki_transaction_is_active(paths):
            raise RuntimeError(
                "Another wiki transaction is already active"
            ) from exc
        lock.unlink()
        try:
            return lock, os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError as retry_exc:
            raise RuntimeError(
                "Another wiki transaction is already active"
            ) from retry_exc


def _apply(
    paths: SecondSelfPaths,
    specification: dict[str, Any],
    proposal_id: str,
    transaction: dict[str, Any] | None = None,
) -> list[str]:
    operation = specification["operation"]
    changed: list[str] = []
    if operation in {"edit", "migration"}:
        for item in specification["changes"]:
            path = resolve_private_path(paths, item["path"])
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(item["content"], encoding="utf-8")
            if transaction is not None:
                _checkpoint_transaction(
                    _transaction_stage(paths, proposal_id), transaction
                )
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
                if transaction is not None:
                    transaction["dynamic_paths"].append(str(destination))
                    _write_journal(
                        _transaction_stage(paths, proposal_id) / "journal.json",
                        transaction,
                    )
                shutil.move(str(source), destination)
                if transaction is not None:
                    _checkpoint_transaction(
                        _transaction_stage(paths, proposal_id), transaction
                    )
                changed.extend([str(source), str(destination)])
    elif operation == "move":
        for item in specification["moves"]:
            source = resolve_private_path(paths, item["from"])
            destination = resolve_private_path(paths, item["to"])
            destination.parent.mkdir(parents=True, exist_ok=True)
            if destination.exists():
                raise FileExistsError(destination)
            shutil.move(str(source), destination)
            if transaction is not None:
                _checkpoint_transaction(
                    _transaction_stage(paths, proposal_id), transaction
                )
            changed.extend([str(source), str(destination)])
    elif operation == "export":
        destination = Path(specification["destination"]).expanduser().resolve()
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            raise FileExistsError(destination)
        destination.write_text(specification["content"], encoding="utf-8")
        if transaction is not None:
            _checkpoint_transaction(
                _transaction_stage(paths, proposal_id), transaction
            )
        changed.append(str(destination))
    elif operation == "assemble_layer1":
        changed.extend(_assemble_layer1(paths))
    elif operation == "wiki_process":
        changed.extend(_apply_wiki_process(paths, specification, proposal_id))
    elif operation == "link_fix":
        for item in specification["fixes"]:
            path = resolve_private_path(paths, item["path"])
            text = path.read_text(encoding="utf-8") if path.exists() else ""
            for replacement in item.get("replacements", []):
                text = text.replace(replacement["old"], replacement["new"], 1)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
            if transaction is not None:
                _checkpoint_transaction(
                    _transaction_stage(paths, proposal_id), transaction
                )
            changed.append(str(path))
    return changed


def approve(
    paths: SecondSelfPaths, proposal_id: str, confirmation: str, agent: str = "unknown"
) -> dict[str, Any]:
    proposal = load_proposal(paths, proposal_id)
    if proposal["status"] not in APPROVAL_PENDING_STATUSES:
        raise ValueError(f"Proposal status is {proposal['status']}")
    if not _approval_decision(confirmation):
        proposal["status"] = "rejected"
        proposal["rejected"] = datetime.now().astimezone().isoformat()
        _proposal_path(paths, proposal_id).write_text(
            json.dumps(proposal, indent=2) + "\n", encoding="utf-8"
        )
        return proposal
    _recover_transactions(paths)
    proposal_lock = _proposal_lock_path(paths, proposal_id)
    try:
        proposal_lock_handle = os.open(
            proposal_lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY
        )
    except FileExistsError as exc:
        raise RuntimeError(
            "Another approval for this proposal is already active"
        ) from exc
    try:
        proposal = load_proposal(paths, proposal_id)
        if proposal["status"] not in APPROVAL_PENDING_STATUSES:
            raise ValueError(f"Proposal status is {proposal['status']}")
        _validate_proposal_schema(proposal)
        _validate_approval_digest(proposal)
        recomputed_preview = _exact_preview(paths, proposal["specification"])
        _check_stale(paths, proposal)
        if recomputed_preview != proposal.get("exact_preview"):
            raise RuntimeError(
                "Proposal exact preview integrity check failed. "
                "Create a new proposal."
            )
        operation = proposal["specification"]["operation"]
        lock: Path | None = None
        lock_handle: int | None = None
        lock_owned = False
        transaction_stage: Path | None = None
        transaction: dict[str, Any] | None = None
        if operation == "wiki_process":
            lock, lock_handle = _acquire_wiki_lock(paths, proposal_id)
            lock_owned = True
        try:
            transaction_stage, transaction = _begin_transaction(
                paths, proposal_id, proposal["specification"]
            )
            changed = _apply(
                paths,
                proposal["specification"],
                proposal_id,
                transaction,
            )
            transaction["status"] = "committed"
            _write_journal(transaction_stage / "journal.json", transaction)
        except Exception:
            if transaction_stage is not None and transaction is not None:
                _rollback_transaction(transaction_stage, transaction)
                transaction["status"] = "rolled-back"
                _write_journal(transaction_stage / "journal.json", transaction)
            raise
        finally:
            if lock_handle is not None:
                os.close(lock_handle)
            if lock_owned and lock is not None and lock.exists():
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
        audit_log = paths.audit / "agent-edits.jsonl"
        with audit_log.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(event) + "\n")
        return proposal
    finally:
        os.close(proposal_lock_handle)
        if proposal_lock.exists():
            proposal_lock.unlink()
