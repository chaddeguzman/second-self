from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import pytest

from second_self.capture import capture_note
from second_self.cli import main
from second_self.frontmatter import read_note
from second_self.paths import SecondSelfPaths


def test_capture_is_structured_and_preserves_body(second_self: SecondSelfPaths) -> None:
    body = "First line.\n\nSecond line with **original wording**."
    captured = capture_note(
        second_self,
        "A useful thought",
        body,
        source="dashboard",
        require_body=True,
        now=datetime(2026, 7, 23, 9, 30, tzinfo=timezone.utc),
    )
    metadata, content = read_note(captured.path)
    assert metadata["type"] == "capture"
    assert metadata["status"] == "inbox"
    assert metadata["source"] == "dashboard"
    assert content.endswith(body + "\n")
    assert captured.path.parent == second_self.layer1 / "00-inbox"


def test_capture_rejects_invalid_web_input(second_self: SecondSelfPaths) -> None:
    with pytest.raises(ValueError, match="Title is required"):
        capture_note(second_self, " ", "body", require_body=True)
    with pytest.raises(ValueError, match="Body is required"):
        capture_note(second_self, "Title", " ", require_body=True)
    with pytest.raises(ValueError, match="single line"):
        capture_note(second_self, "Bad\nTitle", "body", require_body=True)


def test_concurrent_captures_never_overwrite(second_self: SecondSelfPaths) -> None:
    now = datetime(2026, 7, 23, 9, 30, tzinfo=timezone.utc)

    def create(index: int) -> Path:
        return capture_note(
            second_self,
            "Same title",
            f"Body {index}",
            require_body=True,
            now=now,
        ).path

    with ThreadPoolExecutor(max_workers=8) as pool:
        paths = list(pool.map(create, range(12)))
    assert len(set(paths)) == 12
    assert {read_note(path)[1].strip().splitlines()[-1] for path in paths} == {
        f"Body {index}" for index in range(12)
    }


def test_failed_link_leaves_no_partial_capture(
    second_self: SecondSelfPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    import second_self.capture as capture_module

    def fail_link(source: Path, destination: Path) -> None:
        raise OSError("simulated link failure")

    monkeypatch.setattr(capture_module.os, "link", fail_link)
    with pytest.raises(OSError, match="simulated"):
        capture_note(second_self, "Title", "Body", require_body=True)
    inbox = second_self.layer1 / "00-inbox"
    assert not list(inbox.glob("*.md"))
    assert not list(inbox.glob(".capture-*.tmp"))


def test_failed_verification_removes_final_capture(
    second_self: SecondSelfPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    import second_self.capture as capture_module

    monkeypatch.setattr(
        capture_module,
        "validate_metadata",
        lambda metadata: ["simulated verification failure"],
    )
    with pytest.raises(RuntimeError, match="verification failed"):
        capture_note(second_self, "Title", "Body", require_body=True)
    inbox = second_self.layer1 / "00-inbox"
    assert not list(inbox.glob("*.md"))
    assert not list(inbox.glob(".capture-*.tmp"))


def test_cli_capture_uses_shared_service_without_printing_private_root(
    second_self: SecondSelfPaths,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr("second_self.cli.load_paths", lambda require_config=True: second_self)

    result = main(["capture", "--title", "CLI note", "--body", "CLI body"])

    output = capsys.readouterr().out.strip()
    assert result == 0
    assert output.startswith("01-strategy-storage")
    assert str(second_self.data_root) not in output
    note = second_self.data_root / output
    assert read_note(note)[0]["source"] == "cli"
