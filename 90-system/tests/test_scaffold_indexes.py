from pathlib import Path

from second_self.maintenance.indexes import generate_indexes
from second_self.core.paths import SecondSelfPaths
from second_self.core.scaffold import scaffold
from second_self.maintenance.validation import validate


def test_scaffold_is_idempotent(second_self: SecondSelfPaths) -> None:
    identity = second_self.layer1 / "01 Notes/01 Current" / "Current Identity.md"
    original = identity.read_text(encoding="utf-8")
    assert scaffold(second_self) == []
    assert identity.read_text(encoding="utf-8") == original
    assert validate(second_self) == []


def test_indexes_preserve_manual_text(second_self: SecondSelfPaths) -> None:
    note = second_self.layer1 / "01 Notes/02 Notes" / "Decision Context.md"
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
    index = second_self.layer1 / "99-audit/indexes" / "Content Index.md"
    index.write_text(
        index.read_text(encoding="utf-8") + "\nManual navigation note.\n",
        encoding="utf-8",
    )
    result = generate_indexes(second_self)
    content = index.read_text(encoding="utf-8")
    assert result["notes"] >= 1
    assert "Decision%20Context.md" in content
    assert "Manual navigation note." in content


def test_validation_reports_missing_metadata(second_self: SecondSelfPaths) -> None:
    bad = second_self.layer1 / "01 Notes/02 Notes" / "Bad.md"
    bad.write_text("# Missing metadata\n", encoding="utf-8")
    errors = validate(second_self)
    assert any("missing required field: type" in error for error in errors)

