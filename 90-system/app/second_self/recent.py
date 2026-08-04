from __future__ import annotations

from datetime import date
from typing import Any

from .dashboard import scan_dashboard
from .paths import SecondSelfPaths


def recent_items(
    paths: SecondSelfPaths,
    *,
    days: int = 7,
    today: date | None = None,
) -> list[dict[str, Any]]:
    today = today or date.today()
    snapshot = scan_dashboard(paths, today)
    results: list[dict[str, Any]] = []
    for item in [*snapshot.layer1, *snapshot.projects]:
        if item.created is None:
            continue
        age_days = (today - item.created).days
        if age_days < 0 or age_days > days:
            continue
        results.append(
            {
                "path": f"{'01-strategy-storage' if item.scope == 'layer1' else '02-skills-projects/projects'}/{item.relative_path}",
                "title": item.title,
                "type": item.record_type,
                "status": item.status,
                "created": item.created.isoformat(),
                "age_days": age_days,
            }
        )
    results.sort(
        key=lambda entry: (entry["created"], str(entry["title"]).casefold()),
        reverse=True,
    )
    return results