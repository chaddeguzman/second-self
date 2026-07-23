from pathlib import Path

from main_brain.indexes import generate_indexes
from main_brain.paths import BrainPaths
from main_brain.scaffold import scaffold
from main_brain.validation import validate


def test_scaffold_is_idempotent(brain: BrainPaths) -> None:
    identity = brain.layer1 / "10-current" / "Current Identity.md"
    original = identity.read_text(encoding="utf-8")
    assert scaffold(brain) == []
    assert identity.read_text(encoding="utf-8") == original
    assert validate(brain) == []


def test_indexes_preserve_manual_text(brain: BrainPaths) -> None:
    note = brain.layer1 / "20-notes" / "Decision Context.md"
    note.write_text(
        """---
type: note
created: 2026-07-23
status: active
---

# Decision Context
""",
        encoding="utf-8",
    )
    index = brain.layer1 / "90-indexes" / "Content Index.md"
    index.write_text(
        index.read_text(encoding="utf-8") + "\nManual navigation note.\n",
        encoding="utf-8",
    )
    result = generate_indexes(brain)
    content = index.read_text(encoding="utf-8")
    assert result["notes"] >= 1
    assert "Decision%20Context.md" in content
    assert "Manual navigation note." in content


def test_validation_reports_missing_metadata(brain: BrainPaths) -> None:
    bad = brain.layer1 / "20-notes" / "Bad.md"
    bad.write_text("# Missing metadata\n", encoding="utf-8")
    errors = validate(brain)
    assert any("missing required field: type" in error for error in errors)

