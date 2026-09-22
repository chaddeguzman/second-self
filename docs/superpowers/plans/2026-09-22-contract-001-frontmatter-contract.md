# CONTRACT-001 Front-Matter Contract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Establish one versioned front-matter contract that drives runtime validation, JSON schemas, templates, scaffold fixtures, and regression tests without silently changing existing private notes.

**Architecture:** `90-system/docs/frontmatter-contract.json` becomes the reviewable source of truth. A deterministic generator emits the checked-in JSON schemas and a generated Python contract module; `core.frontmatter` consumes that module at runtime, while templates and public scaffolds are checked against the same definitions. CONTRACT-001 must be implemented and validated before WIKI-001 changes generated wiki metadata or links.

**Tech Stack:** Python 3.12, JSON, YAML front matter, `pathlib`, `json`, `pytest`, existing PowerShell privacy validation, and the current `SecondSelfPaths` fixtures.

**Spec:** `log/2026-09-19-systemic-architecture-audit.md` action item CONTRACT-001; `90-system/docs/OPERATING-MODEL.md`; `90-system/docs/SECURITY.md`; `AGENTS.md`.

## Global Constraints

- Markdown remains authoritative; generated schemas and Python constants are derived artifacts and must not become a second source of personal data.
- Preserve the current core required fields `type`, `created`, and `status` unless a compatibility test proves the existing behavior is wrong.
- Preserve the current status values `inbox`, `proposed`, `active`, `superseded`, and `archived`.
- Preserve the current record types, including `capture`, `identity`, `strategy`, `note`, `journal`, `book`, `reference`, `quote`, `lesson`, `review`, `decision`, `conflict`, `import`, `project`, and `handoff`.
- Keep project-only required fields `project_state` and `repository`; `local_path` remains supported but optional.
- Do not read or write live private-vault content during tests; all fixtures use temporary `SecondSelfPaths` roots.
- Do not change `.second-self-schema` data migration behavior in this task; front-matter contract versioning is separate from private vault data versioning.
- Do not commit between CONTRACT-001 and WIKI-001; Charlie will use one final protected delivery after both acceptance gates pass.

## Review Focus

- A note with only the three core fields remains valid, while a missing core field fails with a stable field-specific error; test in `test_frontmatter_contract.py`.
- An unknown status or record type fails consistently in runtime validation and generated JSON schema checks; test the same payload through both paths.
- A project without `project_state` or `repository` fails, while an ordinary note containing project-only fields remains backward-compatible; test the profile matrix.
- YAML scalar/list/type mistakes are rejected without leaking file contents or absolute paths; test malformed metadata and inspect only safe error text.
- Generated artifacts are deterministic and drift detection fails when a schema, template, or generated Python module is manually changed; test generator output in a clean temporary directory.

---

### Task 1: Freeze the contract matrix with failing tests

**Files:**
- Create: `90-system/tests/test_frontmatter_contract.py`
- Modify: `90-system/tests/test_validation.py` only if the shared validator assertion needs a stable error contract
- Read: `90-system/app/second_self/core/frontmatter.py`, `90-system/docs/schemas/note.schema.json`, `90-system/docs/schemas/project.schema.json`, `90-system/docs/templates/*.md`

**Interfaces:**
- Consumes: `split_frontmatter`, `validate_metadata`, current schema files, and temporary `SecondSelfPaths` fixtures.
- Produces: executable examples for the canonical contract and a drift test that later generator work must satisfy.

- [x] **Step 1: Write the failing contract matrix tests.**

  Add tests with explicit fixtures for:

  ```python
  CORE_VALID = {"type": "note", "created": "2026-09-22", "status": "active"}
  PROJECT_VALID = {
      **CORE_VALID,
      "type": "project",
      "project_state": "active",
      "repository": "example/repository",
  }
  ```

  Assert that the core note is valid, a missing `created` field reports exactly `missing required field: created`, invalid status/type values are rejected, project metadata requires `project_state` and `repository`, and optional fields preserve their declared list/string types.

- [x] **Step 2: Run the tests and confirm they fail against the current split definitions.**

  Run:

  ```powershell
  python -m pytest 90-system/tests/test_frontmatter_contract.py -q
  ```

  Expected: the contract-source and generated-artifact tests fail because the canonical contract file and generator do not exist yet; existing compatibility tests must remain green.

- [x] **Step 3: Add schema/template drift assertions.**

  Load `note.schema.json`, `project.schema.json`, and every Markdown template under `90-system/docs/templates`. Extract each template front-matter block with `split_frontmatter`, then compare required fields, allowed statuses, and type-specific requirements against the contract API that Task 2 will provide.

- [x] **Step 4: Keep the red tests focused and synthetic.**

  Verify fixtures contain no private paths, private note text, credentials, or live-vault references. The tests should assert safe error categories and field names, never absolute paths or raw file content.

### Task 2: Create the versioned canonical contract and deterministic generator

**Files:**
- Create: `90-system/docs/frontmatter-contract.json`
- Create: `90-system/automation/scripts/generate-frontmatter-contract.py`
- Create: `90-system/app/second_self/core/frontmatter_contract.py`
- Modify: `90-system/docs/SCHEMA-VERSION` only if generated contract versioning requires an explicit documented value; do not change private `.second-self-schema`
- Test: `90-system/tests/test_frontmatter_contract.py`

**Interfaces:**
- Consumes: the contract matrix from Task 1.
- Produces: `load_contract() -> dict[str, object]`, `field_definition(name: str) -> dict[str, object]`, `profile_definition(record_type: str) -> dict[str, object]`, and a generator command that accepts `--check` and `--write`.

- [x] **Step 1: Define the canonical JSON shape.**

  Store a top-level object with:

  ```json
  {
    "contract": "second-self-frontmatter",
    "version": 1,
    "core_required": ["type", "created", "status"],
    "fields": {
      "type": {"kind": "string", "enum": ["capture", "identity", "strategy", "note", "journal", "book", "reference", "quote", "lesson", "review", "decision", "conflict", "import", "project", "handoff"]},
      "created": {"kind": "date"},
      "status": {"kind": "string", "enum": ["inbox", "proposed", "active", "superseded", "archived"]},
      "updated": {"kind": "date", "required": false},
      "tags": {"kind": "list", "items": "string", "unique": true, "required": false},
      "projects": {"kind": "list", "items": "string", "unique": true, "required": false},
      "related": {"kind": "list", "items": "string", "unique": true, "required": false},
      "source": {"kind": "string-or-list", "required": false}
    },
    "profiles": {
      "project": {"required": ["project_state", "repository"], "type": "project", "project_state": ["idea", "planned", "active", "paused", "completed", "cancelled", "archived"]},
      "wiki-derived": {"required": ["verification"], "verification": "derived"}
    }
  }
  ```

  The exact JSON must include the full current type/status enums and explicit definitions for project, wiki-index, wiki-log, wiki-open-questions, and wiki-source extensions used by the scaffold and WIKI-001.

- [x] **Step 2: Implement the loader and immutable lookup helpers.**

  `frontmatter_contract.py` must resolve the repository-relative contract path from the installed package location, load it once with `json.loads`, validate its own `contract` and integer `version`, and return defensive copies or read-only structures so callers cannot mutate global definitions.

- [x] **Step 3: Implement deterministic generation.**

  The generator must emit, in stable key order and newline format:

  - `90-system/docs/schemas/note.schema.json` from core fields and record types.
  - `90-system/docs/schemas/project.schema.json` from the project profile.
  - `90-system/app/second_self/core/frontmatter_contract.py` from the same source.

  `--check` must exit nonzero and name the first drifted output without printing private paths or contents. `--write` must update only those three generated outputs.

- [x] **Step 4: Run generator tests.**

  Run:

  ```powershell
  python 90-system/automation/scripts/generate-frontmatter-contract.py --check
  python -m pytest 90-system/tests/test_frontmatter_contract.py -q
  ```

  Expected: generated outputs are deterministic, current checked-in schemas match the contract, and the new tests pass.

### Task 3: Route runtime validation and templates through the contract

**Files:**
- Modify: `90-system/app/second_self/core/frontmatter.py`
- Modify: `90-system/app/second_self/core/scaffold.py`
- Modify: `90-system/docs/templates/Note.md`, `Journal.md`, `Project.md`, `Weekly Review.md`, `Monthly Agent Review.md`, `Quarterly Review.md`
- Modify: `90-system/tests/test_frontmatter_contract.py`, `90-system/tests/test_validation.py`, `90-system/tests/test_public_scaffold.py`

**Interfaces:**
- Consumes: generated contract definitions from Task 2.
- Produces: `validate_metadata(data) -> list[str]` driven by contract profiles; scaffold/template fixtures that all satisfy the same required-field rules.

- [x] **Step 1: Replace duplicated runtime constants.**

  Update `frontmatter.py` so `REQUIRED`, `STATUSES`, and type/profile checks come from `frontmatter_contract.py`. Preserve `split_frontmatter` behavior, including UTF-8 BOM handling, malformed YAML errors, and mapping validation.

- [x] **Step 2: Add explicit profile validation.**

  Validate project and wiki-derived fields only when the record type/profile requires them. Return stable errors such as `missing required field: project_state`, `invalid project_state: 'unknown'`, and `verification must be derived`; do not serialize full metadata into errors.

- [x] **Step 3: Align reusable templates and public scaffold content.**

  Add every contract-required field to the matching template and scaffold fixture, preserving the existing body headings. `Project.md` must continue to include `project_state: idea`, `repository: ""`, and `local_path: ""`; derived wiki templates must retain `verification: derived`.

- [x] **Step 4: Run compatibility tests.**

  Run:

  ```powershell
  python -m pytest 90-system/tests/test_frontmatter_contract.py 90-system/tests/test_validation.py 90-system/tests/test_public_scaffold.py -q
  ```

  Expected: old valid notes remain valid, new invalid cases fail safely, generated schema checks pass, and the public scaffold remains privacy-safe.

### Task 4: Validate migration boundaries and delivery readiness

**Files:**
- Modify: `90-system/tests/test_frontmatter_contract.py`
- Modify: `docs/superpowers/plans/2026-09-22-contract-001-frontmatter-contract.md` as task checkboxes are completed
- Do not modify live private notes or `.second-self-schema`

**Interfaces:**
- Consumes: runtime, schema, template, and scaffold behavior from Tasks 1-3.
- Produces: a verified CONTRACT-001 package ready for WIKI-001, with no protected commit yet.

- [x] **Step 1: Add backward-compatibility fixtures.**

  Test minimal existing front matter, existing project records, wiki-derived pages, malformed YAML, duplicate list values, and unknown extra fields. Confirm extra fields remain accepted unless the contract explicitly marks them forbidden.

- [x] **Step 2: Run the repository gates.**

  Run:

  ```powershell
  python 90-system/automation/scripts/generate-frontmatter-contract.py --check
  .\90-system\automation\scripts\second-self.ps1 validate --privacy --tracked-only
  python -m pytest
  git diff --check
  ```

- [x] **Step 3: Review the complete diff.**

  Confirm only public contract, generated schema/runtime artifacts, templates, scaffold fixtures, tests, and plan files changed. Confirm no private note, absolute user path, credential, or runtime journal is staged.

- [x] **Step 4: Hand off to WIKI-001 without committing.**

  Record the generated contract version and the exact helper names consumed by WIKI-001. Keep all changes uncommitted until WIKI-001 completes its own tests and both plans are reviewed together.

## Acceptance Gate

CONTRACT-001 is ready for the shared Charlie delivery only when the contract is the sole definition source, generator `--check` is clean, runtime validation/schema/template/scaffold tests pass, privacy validation passes, the full suite passes, and WIKI-001 can consume the derived-profile names without duplicating metadata rules.

**Execution owner:** Charlie. **Coordinator:** ECHO. **Current state:** implementation validated; protected delivery pending explicit approval.
