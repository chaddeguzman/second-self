# WIKI-001 Canonical Wikilinks And Wiki Log Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reconcile generated wiki pages and linting with the repository’s canonical Obsidian `[[wikilink]]` contract and fix wiki log insertion so generated rows remain valid and readable.

**Architecture:** WIKI-001 consumes CONTRACT-001’s derived metadata profiles but owns link serialization, wiki-target resolution, index generation, source-page provenance links, and log-table insertion. A shared wiki-link parser/resolver will replace the current Markdown-link-only checks for generated wiki content; generation will use `[[target|alias]]` while preserving fragments and safe aliases. All changes remain broker-proposal-compatible and are tested with temporary synthetic vaults.

**Tech Stack:** Python 3.12, `pathlib`, regular expressions, Markdown, Obsidian wikilinks, existing `SecondSelfPaths`, broker `wiki_process`, Flask Process Raw flow, and pytest.

**Spec:** `log/2026-09-19-systemic-architecture-audit.md` action item WIKI-001; `AGENTS.md`; `90-system/docs/OPERATING-MODEL.md`; `90-system/docs/SECURITY.md`; `2026-09-22-contract-001-frontmatter-contract.md`.

## Global Constraints

- Canonical generated internal links use standard Obsidian `[[wikilink]]` syntax, with `[[target|display text]]` only when an alias is needed.
- Link validation must ignore fenced code blocks, inline code spans, image embeds, external URLs, and Markdown links that are not generated canonical wiki links unless a compatibility test explicitly covers them.
- Generated wiki pages remain derived and must preserve provenance through `source_id`, `source_path`, and `source_sha256`.
- Wiki processing remains one approval-gated `wiki_process` proposal containing page changes, index/log changes, and Raw-to-References moves.
- The existing valid References subfolders and source filename collision behavior remain unchanged.
- Log rows must be inserted after the table separator, match the declared operation vocabulary, and remain parseable by `lint_wiki` after one or repeated Process Raw runs.
- Do not read or write live private-vault data during tests; use temporary `SecondSelfPaths` fixtures and synthetic Markdown.
- CONTRACT-001 must be implemented and locally validated before WIKI-001 implementation begins; both feature sets remain uncommitted until the combined delivery gate.

## Review Focus

- A generated source link with spaces, punctuation, or an alias resolves to the intended page and does not create malformed brackets; test canonical serialization and target resolution.
- A wiki link with `#heading`, `^block`, or `|alias` validates the target while ignoring only the display fragment; test all three forms.
- A fenced code block, inline code span, image embed, or external URL is not reported as a broken internal link; test each input class.
- A log row is inserted below the table separator rather than between the header and separator, and a second update does not corrupt the table; test repeated `_update_log` calls.
- A generated page points to the post-move References path and the broker still rejects stale source hashes or missing destinations; test the full synthetic Process Raw proposal.

---

### Task 1: Freeze canonical link and log behavior with failing tests

**Files:**
- Modify: `90-system/tests/test_wiki.py`
- Modify: `90-system/tests/test_web_process_raw.py`
- Create: `90-system/tests/test_wiki_links.py`
- Read: `90-system/app/second_self/wiki/wiki.py`, `90-system/app/second_self/wiki/web_process.py`, `90-system/app/second_self/maintenance/link_check.py`

**Interfaces:**
- Consumes: current `lint_wiki`, `validate_wiki_change_set`, `build_wiki_process_spec`, and temporary vault fixtures.
- Produces: red tests defining canonical link output, fragment/alias behavior, ignored code/embed inputs, and valid log-table row placement.

- [x] **Step 1: Write canonical output tests.**

  Build a synthetic Raw source named `How To Build A Wiki.md`, call `build_wiki_process_spec`, and assert generated content contains forms like:

  ```python
  assert "[[sources/" in source_page
  assert "[[sources/" in index_content
  assert "[How To Build A Wiki]" not in index_content
  ```

  Assert that the source page’s archived-source reference uses a code literal for the post-move References path, because References are outside the wiki root, while wiki-page navigation uses a canonical wikilink. The generated content must not use a Markdown-only internal link.

- [x] **Step 2: Write parser and resolver tests.**

  Create wiki pages that contain `[[topics/Topic]]`, `[[topics/Topic#Heading]]`, `[[topics/Topic^block-id]]`, `[[topics/Topic|friendly name]]`, `![[assets/image.png]]`, `` `[[not-a-link]]` ``, a fenced block, and `https://example.test`. Assert only the real internal page target is resolved and broken-target errors identify a safe relative target.

- [x] **Step 3: Write log insertion regression tests.**

  Given:

  ```text
  | Date | Operation | Title | Details |
  |------|-----------|-------|---------|
  ```

  assert `_update_log` returns the header, separator, then the new row. Call it twice and assert both rows remain below the separator, with no row inserted between the header and separator and no malformed row reported by `lint_wiki`.

- [x] **Step 4: Run the focused tests and confirm current failures.**

  Run:

  ```powershell
  python -m pytest 90-system/tests/test_wiki.py 90-system/tests/test_web_process_raw.py -k "wikilink or log or process" -q
  ```

  Expected: canonical output and log-position assertions fail against the current Markdown-link generation and `_update_log` insertion order; unrelated existing tests remain green.

### Task 2: Add one canonical wiki-link serializer and resolver

**Files:**
- Create: `90-system/app/second_self/wiki/links.py`
- Modify: `90-system/app/second_self/wiki/wiki.py`
- Modify: `90-system/app/second_self/maintenance/link_check.py` only if the shared resolver can preserve Layer 1 behavior without broadening scope
- Test: `90-system/tests/test_wiki_links.py`, `90-system/tests/test_link_check.py`

**Interfaces:**
- Consumes: `SecondSelfPaths`, existing wiki-relative paths, and the repository’s `[[wikilink]]` rules.
- Produces:

  ```python
  def format_wikilink(target: str, alias: str | None = None) -> str: ...
  def parse_wikilinks(text: str) -> list[WikiLink]: ...
  def resolve_wiki_target(page: Path, target: str, paths: SecondSelfPaths) -> Path | None: ...
  def iter_wiki_links(text: str) -> Iterator[WikiLink]: ...
  ```

  `WikiLink` must expose the raw target, optional alias, line/column, and whether the match was an embed or occurred in ignored code.

- [x] **Step 1: Implement safe serialization.**

  Normalize `/` separators, reject empty targets and bracket/control characters, preserve valid `#heading` and `^block-id` suffixes, and emit `[[target]]` or `[[target|alias]]`. Do not URL-encode canonical wikilinks; Obsidian paths may contain spaces.

- [x] **Step 2: Implement code-aware parsing.**

  Reuse the existing fence/inline-code behavior from `maintenance.link_check` or move it into `links.py`. Skip `![[...]]` embeds for page-link validation while leaving a typed `is_embed=True` record available to callers that need asset validation.

- [x] **Step 3: Implement wiki-root resolution.**

  Resolve targets relative to the linking page, then relative to `paths.wiki`, append `.md` only when no extension is supplied, strip only `#heading` and `^block-id` for filesystem lookup, and retain aliases for display only. Never resolve outside `paths.wiki`.

- [x] **Step 4: Run parser/resolver tests.**

  Run:

  ```powershell
  python -m pytest 90-system/tests/test_wiki_links.py 90-system/tests/test_link_check.py -q
  ```

  Expected: all canonical syntax, alias/fragment, ignored-code, embed, and traversal-boundary tests pass without changing existing Layer 1 link-check results.

### Task 3: Update wiki generation and validation to canonical links

**Files:**
- Modify: `90-system/app/second_self/wiki/web_process.py`
- Modify: `90-system/app/second_self/wiki/wiki.py`
- Modify: `90-system/tests/test_wiki.py`
- Modify: `90-system/tests/test_web_process_raw.py`

**Interfaces:**
- Consumes: `format_wikilink`, `parse_wikilinks`, and `resolve_wiki_target` from Task 2; derived metadata profiles from CONTRACT-001.
- Produces: Process Raw-generated source pages, index rows, and provenance references using canonical wikilinks; `validate_wiki_change_set` and `lint_wiki` that validate those links.

- [x] **Step 1: Replace generated Markdown internal links.**

  Update `_source_page` and `_update_index` so a source page target uses `format_wikilink(page_relative, title)` and index rows use the same serializer. Keep external URLs, code literals, and source-path provenance text distinct from internal navigation links.

- [x] **Step 2: Validate changed and existing wiki pages with the shared parser.**

  Replace the Markdown-only `LINK` checks in `validate_wiki_change_set` and `lint_wiki` with `parse_wikilinks` plus `resolve_wiki_target`. Resolve links against both existing pages and pages in the current `changes` map so a new source page can link to another page in the same proposal.

- [x] **Step 3: Preserve derived metadata and safe boundaries.**

  Continue requiring `verification: derived` and source provenance fields. Reject a change whose wikilink target escapes `03-wiki`, whose target is missing, or whose source page points to a References path that the broker move did not create.

- [x] **Step 4: Run Process Raw integration tests.**

  Run:

  ```powershell
  python -m pytest 90-system/tests/test_wiki.py 90-system/tests/test_web_process_raw.py -q
  ```

  Expected: generated specs contain canonical wikilinks, proposal validation accepts new pages in the same batch, stale Raw hashes still fail, and successful broker application preserves source moves and provenance.

### Task 4: Fix log-table insertion and idempotent linting

**Files:**
- Modify: `90-system/app/second_self/wiki/web_process.py`
- Modify: `90-system/app/second_self/wiki/wiki.py`
- Modify: `90-system/tests/test_wiki.py`
- Modify: `90-system/tests/test_web_process_raw.py`

**Interfaces:**
- Consumes: canonical row format and operation vocabulary from existing `LOG_TABLE_HEADER`, `LOG_TABLE_ROW`, and Process Raw specs.
- Produces: `_update_log(log_content: str, entry_row: str) -> str` that inserts after the separator and preserves valid table structure.

- [x] **Step 1: Implement separator-aware insertion.**

  Find the exact header row and immediately following separator row. Insert new rows after the separator; if the table is absent, return the original content plus a complete header, separator, and row. Do not insert rows merely because a line contains `--`.

- [x] **Step 2: Keep rows lint-compatible.**

  Ensure generated operation is `ingest`, title is non-empty, details escape raw pipe characters that would create extra cells, and multi-source details use `<br>` without introducing a newline inside the table row.

- [x] **Step 3: Test repeated generation.**

  Process two synthetic batches and run `lint_wiki` after each. Assert the table remains valid, rows remain below the separator, source/index links resolve, and the second batch does not rewrite or delete the first row.

- [x] **Step 4: Run wiki lint and focused tests.**

  Run:

  ```powershell
  python -m second_self wiki lint
  python -m pytest 90-system/tests/test_wiki.py 90-system/tests/test_web_process_raw.py 90-system/tests/test_wiki_links.py -q
  ```

### Task 5: Validate both feature plans and prepare one delivery

**Files:**
- Modify: `90-system/tests/test_frontmatter_contract.py` and wiki tests as needed for final regressions
- Modify: `docs/superpowers/plans/2026-09-22-contract-001-frontmatter-contract.md`
- Modify: `docs/superpowers/plans/2026-09-22-wiki-001-canonical-wikilinks.md`
- Modify: `90-system/.echo/subagents/charlie/log.md`
- Modify: `log/2026-09-19-systemic-architecture-audit.md` only after acceptance and protected delivery; it is ignored local audit state

**Interfaces:**
- Consumes: completed CONTRACT-001 and WIKI-001 behavior.
- Produces: one reviewed, uncommitted implementation ready for the Second Self commit workflow.

- [x] **Step 1: Run all required validation in dependency order.**

  Run:

  ```powershell
  python 90-system/automation/scripts/generate-frontmatter-contract.py --check
  python -m second_self wiki lint
  .\90-system\automation\scripts\second-self.ps1 validate --privacy --tracked-only
  python -m pytest
  git diff --check
  ```

- [x] **Step 2: Review the complete diff and task boundary.**

  Confirm the diff contains only contract source/generated artifacts, runtime validation, templates/scaffold fixtures, wiki link generation/resolution/linting, tests, plans, and Charlie’s assignment log. Confirm no private vault content, absolute user path, secret, runtime journal, or unrelated feature is staged.

- [x] **Step 3: Update assignment and audit state without committing early.**

  Mark both plan checklists complete, mark Charlie’s combined assignment `Done` only after both features pass validation, and set CONTRACT-001/WIKI-001 to `ready-for-validation` until the single protected commit/PR/merge is complete.

- [ ] **Step 4: Deliver once through the protected workflow.**

  Use `02-skills-projects/skills/second-self-commit/SKILL.md` for one coherent commit, one automation PR, CI, merge commit, pull, and final `main...origin/main == 0 0` plus clean-tree verification. Do not create a checkpoint or status-only closeout commit.

## Acceptance Gate

The combined assignment is ready for protected delivery only when CONTRACT-001’s contract generator is deterministic and all runtime/schema/template tests pass, WIKI-001 emits and validates canonical Obsidian wikilinks, log rows are structurally valid after repeated updates, privacy validation and full pytest pass, and the complete diff has been reviewed.

**Execution owner:** Charlie. **Coordinator:** ECHO. **Current state:** implementation validated; protected delivery pending explicit approval.
