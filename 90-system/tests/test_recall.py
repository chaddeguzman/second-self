from __future__ import annotations

from datetime import date

from second_self.core.paths import SecondSelfPaths
from second_self.reads.recall import recall_layer1


def _note(
    root: SecondSelfPaths,
    relative: str,
    *,
    created: str = "2026-08-01",
    tags: list[str] | None = None,
    body: str = "",
) -> str:
    path = root.layer1 / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    tag_line = f"tags: [{', '.join(tags)}]\n" if tags else ""
    path.write_text(
        f"---\ntype: note\ncreated: {created}\nstatus: active\n{tag_line}---\n\n# {path.stem}\n\n{body}\n",
        encoding="utf-8",
    )
    return str(path.relative_to(root.data_root).as_posix())


def test_folder_priority_ranks_references_higher(second_self: SecondSelfPaths) -> None:
    _note(second_self, "04 References/03 research/Note.md", body="discuss the topic")
    _note(second_self, "00 Memory/Profile.md", body="discuss the topic")
    results = recall_layer1(second_self, "discuss")
    assert len(results) == 2
    assert results[0]["path"].startswith("01-strategy-storage/04 References")
    assert results[0]["score"] > results[1]["score"]


def test_recency_ranks_newer_higher(second_self: SecondSelfPaths) -> None:
    _note(second_self, "02 Journal/Old.md", created="2025-01-01", body="discuss the topic")
    _note(second_self, "02 Journal/New.md", created="2026-08-01", body="discuss the topic")
    results = recall_layer1(second_self, "discuss", today=date(2026, 8, 5))
    assert len(results) == 2
    assert results[0]["path"].endswith("New.md")
    assert results[0]["score"] > results[1]["score"]


def test_exact_tag_match_scores_higher(second_self: SecondSelfPaths) -> None:
    _note(second_self, "02 Journal/Tagged.md", tags=["weekly-review"], body="discuss the topic")
    _note(second_self, "02 Journal/Untagged.md", body="discuss the weekly-review topic")
    results = recall_layer1(second_self, "weekly-review")
    assert len(results) == 2
    assert results[0]["path"].endswith("Tagged.md")
    assert results[0]["score_breakdown"]["tag"] == 20


def test_body_inline_tag_mention(second_self: SecondSelfPaths) -> None:
    _note(second_self, "02 Journal/Inline.md", body="discuss #weekly-review topic")
    results = recall_layer1(second_self, "weekly-review")
    assert len(results) == 1
    assert results[0]["score_breakdown"]["tag"] == 5


def test_title_match_bonus(second_self: SecondSelfPaths) -> None:
    _note(second_self, "02 Journal/Weekly Review.md", body="discuss the topic")
    _note(second_self, "02 Journal/Other.md", body="discuss the weekly review topic")
    results = recall_layer1(second_self, "weekly review")
    assert len(results) == 2
    assert results[0]["path"].endswith("Weekly Review.md")
    assert results[0]["score_breakdown"]["title"] == 10


def test_min_score_filters(second_self: SecondSelfPaths) -> None:
    _note(second_self, "02 Journal/Note.md", body="discuss the topic")
    results = recall_layer1(second_self, "discuss", min_score=100)
    assert results == []


def test_max_results_limits(second_self: SecondSelfPaths) -> None:
    for i in range(5):
        _note(second_self, f"02 Journal/Note{i}.md", body="discuss the topic")
    results = recall_layer1(second_self, "discuss", max_results=2)
    assert len(results) == 2


def test_empty_query_returns_empty(second_self: SecondSelfPaths) -> None:
    assert recall_layer1(second_self, "  ") == []
