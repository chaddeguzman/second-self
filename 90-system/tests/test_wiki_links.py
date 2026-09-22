from __future__ import annotations

from pathlib import Path

from second_self.core.paths import SecondSelfPaths
from second_self.wiki.links import format_wikilink, parse_wikilinks, resolve_wiki_target
from second_self.wiki.web_process import _update_log, build_wiki_process_spec
from second_self.wiki.wiki import lint_wiki, validate_wiki_change_set


def _paths(tmp_path: Path) -> SecondSelfPaths:
    data_root = tmp_path / "private"
    layer1 = data_root / "01-strategy-storage"
    projects = data_root / "02-skills-projects" / "projects"
    layer1.mkdir(parents=True)
    projects.mkdir(parents=True)
    return SecondSelfPaths(repo_root=tmp_path / "repo", data_root=data_root)


def _wiki_scaffold(paths: SecondSelfPaths) -> None:
    paths.wiki.mkdir(parents=True, exist_ok=True)
    (paths.wiki / "index.md").write_text(
        "---\ntype: wiki-index\ncreated: 2026-09-22\nstatus: active\nverification: derived\n---\n"
        "# Wiki Index\n<!-- BEGIN GENERATED -->\n<!-- END GENERATED -->\n",
        encoding="utf-8",
    )
    (paths.wiki / "log.md").write_text(
        "---\ntype: wiki-log\ncreated: 2026-09-22\nstatus: active\nverification: derived\n---\n"
        "# Wiki Log\n\n| Date | Operation | Title | Details |\n"
        "|------|-----------|-------|---------|\n",
        encoding="utf-8",
    )


def test_process_raw_generates_canonical_wikilinks(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    _wiki_scaffold(paths)
    source = paths.layer1 / "01 Capture" / "00 Raw" / "How To Build A Wiki.md"
    source.parent.mkdir(parents=True)
    source.write_text("# Guide\n", encoding="utf-8")
    relative = source.relative_to(paths.data_root).as_posix()

    spec = build_wiki_process_spec(paths, {relative: "04 guides"})
    source_page = next(
        item["content"] for item in spec["changes"] if "/sources/" in item["path"]
    )
    index_content = next(
        item["content"] for item in spec["changes"] if item["path"] == "03-wiki/index.md"
    )
    log_content = next(
        item["content"] for item in spec["changes"] if item["path"] == "03-wiki/log.md"
    )

    assert "[[index|Wiki index]]" in source_page
    assert "[[sources/" in index_content
    assert "[[sources/" in log_content
    assert "](" not in index_content


def test_update_log_inserts_rows_after_table_separator() -> None:
    original = "| Date | Operation | Title | Details |\n|------|-----------|-------|---------|\n"

    updated = _update_log(original, "| 2026-09-22 | ingest | Batch | Details |")

    lines = updated.splitlines()
    assert lines[0] == "| Date | Operation | Title | Details |"
    assert lines[1] == "|------|-----------|-------|---------|"
    assert lines[2] == "| 2026-09-22 | ingest | Batch | Details |"


def test_update_log_keeps_repeated_rows_below_separator() -> None:
    original = "| Date | Operation | Title | Details |\n|------|-----------|-------|---------|\n"

    once = _update_log(original, "| 2026-09-22 | ingest | First | Details |")
    twice = _update_log(once, "| 2026-09-22 | ingest | Second | Details |")

    lines = twice.splitlines()
    assert lines[1] == "|------|-----------|-------|---------|"
    assert lines[2:] == [
        "| 2026-09-22 | ingest | Second | Details |",
        "| 2026-09-22 | ingest | First | Details |",
    ]


def test_update_log_repairs_header_without_separator() -> None:
    original = "| Date | Operation | Title | Details |\n"

    updated = _update_log(original, "| 2026-09-22 | ingest | Batch | Details |")

    assert updated.splitlines() == [
        "| Date | Operation | Title | Details |",
        "|------|-----------|-------|---------|",
        "| 2026-09-22 | ingest | Batch | Details |",
    ]


def test_wikilink_formatter_preserves_spaces_and_aliases() -> None:
    assert format_wikilink("topics/Topic Note") == "[[topics/Topic Note]]"
    assert format_wikilink("topics/Topic Note#Heading", "Friendly") == (
        "[[topics/Topic Note#Heading|Friendly]]"
    )


def test_wikilink_parser_ignores_code_and_embeds(tmp_path: Path) -> None:
    text = (
        "[[topics/Topic]] [[topics/Topic#Heading|Alias]] ![[assets/image.png]] "
        "`[[ignored/inline]]`\n```\n[[ignored/fenced]]\n```\n"
    )

    links = parse_wikilinks(text)

    assert [(link.target, link.alias, link.is_embed) for link in links] == [
        ("topics/Topic", None, False),
        ("topics/Topic#Heading", "Alias", False),
        ("assets/image.png", None, True),
    ]


def test_wikilink_resolver_strips_fragments_and_stays_inside_wiki(
    tmp_path: Path,
) -> None:
    paths = _paths(tmp_path)
    page = paths.wiki / "topics" / "Current.md"
    target = paths.wiki / "topics" / "Topic Note.md"
    page.parent.mkdir(parents=True)
    target.write_text("# Topic\n", encoding="utf-8")

    assert resolve_wiki_target(page, "Topic Note#Heading", paths) == target
    assert resolve_wiki_target(page, "../outside", paths) is None


def test_wiki_lint_reports_broken_canonical_wikilinks(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    _wiki_scaffold(paths)
    page = paths.wiki / "topics" / "Broken.md"
    page.parent.mkdir(parents=True)
    page.write_text(
        "---\ntype: wiki-topic\ncreated: 2026-09-22\nstatus: active\nverification: derived\n---\n"
        "# Broken\n\n[[topics/Missing]]\n",
        encoding="utf-8",
    )

    errors = lint_wiki(paths)

    assert any("broken link [[topics/Missing]]" in error for error in errors)


def test_validate_change_set_rejects_missing_canonical_wikilink(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    _wiki_scaffold(paths)
    changes = [
        {
            "path": "03-wiki/topics/New.md",
            "content": "---\ntype: wiki-topic\ncreated: 2026-09-22\nstatus: active\nverification: derived\n---\n"
            "# New\n\n[[topics/Missing]]\n",
        }
    ]

    try:
        validate_wiki_change_set(paths, changes)
    except ValueError as exc:
        assert "broken wiki link topics/Missing" in str(exc)
    else:
        raise AssertionError("missing canonical wikilink was accepted")
