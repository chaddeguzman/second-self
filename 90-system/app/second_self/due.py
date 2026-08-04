from __future__ import annotations

from datetime import date

from .dashboard import scan_dashboard
from .paths import SecondSelfPaths


def due_items(
    paths: SecondSelfPaths,
    *,
    overdue_only: bool = False,
    today: date | None = None,
) -> list[dict[str, object]]:
    today = today or date.today()
    snapshot = scan_dashboard(paths, today)
    results: list[dict[str, object]] = []
    for item in [*snapshot.layer1, *snapshot.projects]:
        if item.due is None:
            continue
        days_until_due = (item.due - today).days
        if overdue_only and days_until_due >= 0:
            continue
        results.append(
            {
                "path": f"{'01-strategy-storage' if item.scope == 'layer1' else '02-skills-projects/projects'}/{item.relative_path}",
                "title": item.title,
                "type": item.record_type,
                "status": item.status,
                "due": item.due.isoformat(),
                "days_until_due": days_until_due,
            }
        )
    results.sort(key=lambda entry: (entry["due"], str(entry["title"]).casefold()))
    return results