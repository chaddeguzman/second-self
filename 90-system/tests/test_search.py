from __future__ import annotations

import json
from pathlib import Path

import pytest

from second_self.cli import main
from second_self.core.paths import SecondSelfPaths
from second_self.reads.search import search_layer1


def _note(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_search_finds_match_in_body(second_self: SecondSelfPaths) -> None:
    _note(
        second_self.layer1 / "01 Capture/02 Notes/Note.md",
        "---\ntype: note\ncreated: 2026-08-01\nstatus: active\n---\n\n# Note\n\nThis is a unique needle in the haystack.\n",
    )
    results = search_layer1(second_self, "unique needle").items
    assert len(results) == 1
    assert results[0]["path"] == "01-strategy-storage/01 Capture/02 Notes/Note.md"
    assert "unique needle" in results[0]["snippet"]
    assert results[0]["matched"] == "unique needle"


def test_search_is_case_insensitive(second_self: SecondSelfPaths) -> None:
    _note(
        second_self.layer1 / "01 Capture/02 Notes/Note.md",
        "---\ntype: note\ncreated: 2026-08-01\nstatus: active\n---\n\n# Note\n\nUPPERCASE CONTENT HERE.\n",
    )
    results = search_layer1(second_self, "uppercase content").items
    assert len(results) == 1
    assert results[0]["matched"] == "UPPERCASE CONTENT"


def test_search_matches_frontmatter(second_self: SecondSelfPaths) -> None:
    _note(
        second_self.layer1 / "01 Capture/02 Notes/Note.md",
        "---\ntype: note\ncreated: 2026-08-01\nstatus: active\ntags: [important-topic]\n---\n\n# Note\n\nBody text.\n",
    )
    results = search_layer1(second_self, "important-topic").items
    assert len(results) == 1
    assert "important-topic" in results[0]["snippet"]


def test_search_skips_trash(second_self: SecondSelfPaths) -> None:
    _note(
        second_self.layer1 / "98-trash/Old Note.md",
        "---\ntype: note\ncreated: 2026-08-01\nstatus: archived\n---\n\n# Old\n\nsecret needle here.\n",
    )
    results = search_layer1(second_self, "secret needle").items
    assert results == []


def test_search_skips_binary(second_self: SecondSelfPaths) -> None:
    binary = second_self.layer1 / "01 Capture/00 Raw/binary.bin"
    binary.parent.mkdir(parents=True, exist_ok=True)
    binary.write_bytes(b"\x00\x01\x02\xff\xfe needle \x00\x01")
    results = search_layer1(second_self, "needle").items
    assert results == []


def test_search_returns_empty_for_blank_query(second_self: SecondSelfPaths) -> None:
    page = search_layer1(second_self, "   ")
    assert page.items == []
    assert page.truncated is False


def test_search_rejects_non_positive_limits(second_self: SecondSelfPaths) -> None:
    _note(
        second_self.layer1 / "01 Capture/02 Notes/Note.md",
        "needle",
    )
    with pytest.raises(ValueError, match="max_results must be positive"):
        search_layer1(second_self, "needle", max_results=0)
    with pytest.raises(ValueError, match="max_results must be positive"):
        search_layer1(second_self, "needle", max_results=-1)


def test_search_exact_limit_is_not_truncated_without_more_matches(
    second_self: SecondSelfPaths,
) -> None:
    _note(second_self.layer1 / "01 Capture/02 Notes/One.md", "exact needle")

    page = search_layer1(second_self, "exact needle", max_results=1)

    assert len(page.items) == 1
    assert page.truncated is False


def test_search_exact_limit_is_truncated_when_more_matches_exist(
    second_self: SecondSelfPaths,
) -> None:
    _note(second_self.layer1 / "01 Capture/02 Notes/One.md", "shared needle")
    _note(second_self.layer1 / "01 Capture/02 Notes/Two.md", "shared needle")

    page = search_layer1(second_self, "shared needle", max_results=1)

    assert len(page.items) == 1
    assert page.truncated is True


def test_search_cli_returns_json(
    second_self: SecondSelfPaths,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _note(
        second_self.layer1 / "01 Capture/02 Notes/Note.md",
        "---\ntype: note\ncreated: 2026-08-01\nstatus: active\n---\n\n# Note\n\nCLI searchable content.\n",
    )
    monkeypatch.setattr("second_self.cli.load_paths", lambda require_config=True: second_self)

    result = main(["search", "CLI searchable"])

    assert result == 0
    output = json.loads(capsys.readouterr().out)
    assert "results" in output
    assert output["truncated"] is False
    assert len(output["results"]) == 1
    assert output["results"][0]["path"].startswith("01-strategy-storage")
    assert str(second_self.data_root) not in capsys.readouterr().out


def test_search_cli_rejects_non_positive_limit(
    second_self: SecondSelfPaths,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr("second_self.cli.load_paths", lambda require_config=True: second_self)

    result = main(["search", "needle", "--max-results", "0"])

    assert result == 2
    assert capsys.readouterr().err.strip() == "error: max_results must be positive"
