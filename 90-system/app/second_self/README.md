# Second Self Application Package

`second_self` is the Python package that powers the Second Self CLI and local
dashboard. It is grouped into subpackages by responsibility so it is easy to
tell which module does what.

## Top-level entry points

| File / Folder | Purpose |
|---|---|
| `cli.py` | Argparse CLI. Wires every subcommand (`capture`, `journal`, `search`, `broker`, `wiki`, `tags`, `tag-rename`, `web`, etc.). Define new commands here. |
| `web.py` | Flask app for the local dashboard: routes, templates, static assets, Markdown preview rendering, server launcher. |
| `__main__.py` | Allows `python -m second_self`. |
| `templates/` | Jinja HTML templates used by `web.py`. |
| `static/` | CSS/JS assets used by `web.py`. |

## Subpackages

### `core/` — Shared foundations

Low-level utilities almost every module depends on.

| Module | Purpose |
|---|---|
| `paths.py` | `SecondSelfPaths`, config loading, and `resolve_private_path` safety checks. |
| `frontmatter.py` | Parse/serialize YAML front matter and validate required metadata fields. |
| `scaffold.py` | Create the initial private folder structure and wiki scaffold. |

### `broker/` — Protected change approval

| Module | Purpose |
|---|---|
| `broker.py` | `propose()` / `load_proposal()` / `approve()` for protected changes: edits, deletes, moves, exports, wiki transactions, journaling, rollback, audit log. |

### `reads/` — Read models and queries

| Module | Purpose |
|---|---|
| `dashboard.py` | Scans Layer 1 + projects; builds `DashboardSnapshot`, queues, tag index, legacy list. |
| `search.py` | Full-text search over Layer 1. |
| `due.py` | Due-date query. |
| `recent.py` | Recent-items query. |

### `writes/` — Write actions

| Module | Purpose |
|---|---|
| `capture.py` | Create inbox captures. |
| `journal.py` | Create journal entries. |
| `tag_rename.py` | Build a broker `edit` proposal to rename a tag across notes. |

### `wiki/` — LLM Wiki layer

| Module | Purpose |
|---|---|
| `wiki.py` | Wiki status, source units, lint, change-set validation, References subfolders, references destination. |

### `ingest/` — Import processing

| Module | Purpose |
|---|---|
| `ingest.py` | Import PDF/DOCX/XLSX/TXT sources into Raw with immutable provenance. |

### `projects/` — Project registration

| Module | Purpose |
|---|---|
| `projects.py` | Register a local repository as a Second Self project; writes adapters and project record. |

### `maintenance/` — Repository hygiene

| Module | Purpose |
|---|---|
| `indexes.py` | Regenerate generated index notes. |
| `validation.py` | Privacy + tracked-file validation (`second-self validate`). |

## Import conventions

- Top-level entry points (`cli.py`, `web.py`) import from subpackages:
  `from .writes.capture import capture_note`.
- Subpackage modules use relative imports:
  `from ..core.paths import SecondSelfPaths`.
- Sibling imports inside a subpackage stay as `from .dashboard import ...`.