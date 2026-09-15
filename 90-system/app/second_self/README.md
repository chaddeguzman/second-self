# Second Self Application Package

`second_self` is the Python package that powers the Second Self CLI and local
dashboard. It is grouped into subpackages by responsibility so it is easy to
tell which module does what.

## Top-level entry points

| File / Folder | Purpose |
|---|---|
| `cli.py` | Argparse CLI. Wires every subcommand (`doctor`, `route`, `capture`, `journal`, `search`, `recall`, `broker`, `wiki`, `tags`, `tag-rename`, `web`, etc.). Define new commands here. |
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
| `recall.py` | Ranked recall search over Layer 1 (folder priority, recency, tag strength, title match). |
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
| `link_check.py` | Wikilink integrity checker for Layer 1 notes; builds `link_fix` broker proposals. |
| `tag_audit.py` | Tag vocabulary audit against `Tag Registry.md`; builds `edit` broker proposals for near-duplicates. |

### `health/` — Shared health contracts

| Module | Purpose |
|---|---|
| `registry.py` | Ordered health-check registry, redacted failure containment, stable text/JSON rendering, and 0/1/2 exit semantics. |

## Health commands

Use `second-self doctor [--strict] [--json]` for the public, read-only health
surface. It runs the standalone command's seven ECHO checks plus seven
Second Self readiness checks, emits no resolved roots, and has no repair option.
Exit 0 means no failures (and WARN is allowed normally), exit 1 means `--strict`
found a WARN, and exit 2 means FAIL.

| Second Self-only check | Severity rule |
|---|---|
| Private-path resolution | `FAIL` when local configuration is missing/invalid or its data root is unavailable |
| Active Second Self vault | `FAIL` unless the approved vault markers are present |
| Git main alignment | `FAIL` for detached/non-main, divergent, or unverifiable state |
| Privacy validator | `FAIL` when the required validator entry point is missing |
| Ollama readiness | `WARN` when optional configuration/service/model readiness is missing or invalid |
| Evaluation state | `WARN` when optional baseline state is absent or invalid |
| Scheduler state | `WARN` when optional job state is absent or invalid |

`90-system/.echo/scripts/echo-doctor.py` remains the maintenance-compatible
entry point. It preserves `--fix` and `--base-dir` in addition to `--strict` and
`--json`; those extra controls are intentionally not exposed by `second-self`,
and it retains its original seven-check scope.

## Routing diagnostic

`second-self route --operation NAME --sensitivity LEVEL --dry-run [--json]`
validates provider-neutral routing metadata without invoking a provider. LEVEL
is exactly `public`, `ordinary_private`, `sensitive`, or `prohibited`.
`--dry-run` is required. The diagnostic intentionally supplies no provider
capability, so valid non-prohibited requests deny with `no_capable_provider`;
prohibited requests deny with `prohibited_data`, and unknown/malformed metadata
denies with `invalid_request`. A denial exits 2.

The internal routing contract stores only stable operation/origin metadata and
optional SHA-256 approval binding. Raw payloads are not accepted, persisted, or
rendered. Provider capability objects contain descriptive metadata only and
have no invocation callable in this phase.

### Ollama provider

`second_self.providers.ModelProvider` defines replaceable capability, health,
and inference methods. `OllamaProvider` is the first implementation. It reads
its loopback endpoint and model from ignored local configuration, supports only
non-streaming `generate`, and never falls back to another provider. Requests use
a two-second connection timeout, 60-second total timeout, 256 KiB prompt limit,
and 1 MiB response limit by default. Local configuration may tune the timeouts
and response limit within validated bounds.

Doctor readiness calls this provider's health API. Missing configuration,
offline Ollama, malformed responses, or a missing configured model remain a
redacted optional `WARN`; doctor never submits a prompt.

## Import conventions

- Top-level entry points (`cli.py`, `web.py`) import from subpackages:
  `from .writes.capture import capture_note`.
- Subpackage modules use relative imports:
  `from ..core.paths import SecondSelfPaths`.
- Sibling imports inside a subpackage stay as `from .dashboard import ...`.
