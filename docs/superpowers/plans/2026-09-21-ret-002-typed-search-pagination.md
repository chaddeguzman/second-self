# RET-002 Typed Search Pagination Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Owner:** Charlie (Development/Coding)

**Coordinator:** ECHO

**Goal:** Replace the search result list’s illegal dynamic `truncated` attribute with a typed paginated result and make result-limit behavior deterministic across the Python API, CLI, and web dashboard.

**Architecture:** `search_layer1()` will return a typed `SearchPage` containing `items` and an explicit `truncated` flag. The search function will reject non-positive limits before scanning, stop only after determining that an additional matching item exists, and preserve the current matching, ordering, snippet, path, and privacy behavior. CLI and web callers will consume the explicit page fields instead of treating a list as both data and pagination metadata.

**Tech Stack:** Python 3.12, dataclasses, Flask/Jinja, argparse, JSON, and pytest.

**Spec:** `log/2026-09-19-systemic-architecture-audit.md`, action item RET-002.

## Global Constraints

- Preserve case-insensitive body/front-matter matching, skipped directories, binary/oversized-file handling, snippets, matched text, and relative paths.
- Do not expose private absolute paths in CLI JSON, web HTML, errors, or tests.
- `max_results` must be a positive integer for the search API and CLI.
- Exact-limit results must be returned without exceptions; `truncated` is true only when another matching result exists beyond the returned page.
- Keep the public CLI payload stable for existing consumers by retaining `results` as a list and adding an explicit boolean `truncated` field.
- Keep the web template’s `results` iterable as a list and pass the explicit page flag separately.
- Use tests-first development, then run focused tests, privacy validation, and the full suite.
- Update the audit queue only after the acceptance gate and protected Git delivery are complete.

## Review Focus

- `max_results=0` and negative limits must raise deterministic `ValueError`s from the Python API and produce a deterministic CLI error/exit without an `AttributeError`.
- An exact-limit result set with no additional match must have `truncated == False`.
- An exact-limit result set with an additional match must return exactly the limit and `truncated == True`.
- A blank query still returns an empty page, while invalid limits are rejected consistently before scanning.
- CLI JSON and web rendering must not leak the private data root or break because the result is no longer a list subclass.

---

### Task 1: Define the typed page and write boundary regression tests

**Files:**
- Modify: `90-system/app/second_self/reads/search.py:1-70`
- Modify: `90-system/tests/test_search.py`
- Read: `90-system/app/second_self/cli.py:361-364, 658-661`
- Read: `90-system/app/second_self/web.py:503-529`

**Interfaces:**
- Consumes: current `search_layer1()` result fields and the existing CLI/web call sites.
- Produces: `SearchPage` with `items: list[dict[str, str]]`, `truncated: bool`, and an explicit serialization shape for callers.

- [ ] **Step 1: Add the `SearchPage` contract.**

  Define:

  ```python
  @dataclass(frozen=True, slots=True)
  class SearchPage:
      items: list[dict[str, str]]
      truncated: bool = False

      def as_dict(self) -> dict[str, object]:
          return {"results": self.items, "truncated": self.truncated}
  ```

  Keep `items` as the existing result dictionaries; do not add private source text or absolute paths.

- [ ] **Step 2: Write failing API tests for invalid and exact limits.**

  Add tests in `90-system/tests/test_search.py` that assert:

  ```python
  with pytest.raises(ValueError, match="max_results must be positive"):
      search_layer1(second_self, "needle", max_results=0)

  with pytest.raises(ValueError, match="max_results must be positive"):
      search_layer1(second_self, "needle", max_results=-1)
  ```

  Add one test with exactly one matching file and `max_results=1` asserting `page.items` contains one item and `page.truncated is False`; add another with two matching files and `max_results=1` asserting one item and `page.truncated is True`.

- [ ] **Step 3: Run the new tests and confirm the expected red failure.**

  Run:

  ```powershell
  python -m pytest 90-system/tests/test_search.py -q
  ```

  Expected: the new tests fail because the current function returns a raw list, mutates `results.truncated`, and accepts non-positive limits until the scan reaches the mutation.

### Task 2: Implement deterministic search pagination and update consumers

**Files:**
- Modify: `90-system/app/second_self/reads/search.py:22-70`
- Modify: `90-system/app/second_self/cli.py:361-364`
- Modify: `90-system/app/second_self/web.py:503-529`
- Modify: `90-system/tests/test_search.py`
- Modify: any additional test call sites identified by `rg -n "search_layer1" 90-system`

**Interfaces:**
- Consumes: `SearchPage.items`, `SearchPage.truncated`, and `SearchPage.as_dict()` from Task 1.
- Produces: A stable Python, CLI, and web search flow with no list-attribute mutation.

- [ ] **Step 1: Validate `max_results` at the search boundary.**

  At the beginning of `search_layer1()`, raise `ValueError("max_results must be positive")` when `max_results <= 0`, before checking the query or filesystem. For a blank query with a valid limit, return `SearchPage([], truncated=False)`.

- [ ] **Step 2: Replace the list mutation with explicit pagination state.**

  Accumulate matching dictionaries in a normal list. When the next matching file would exceed `max_results`, set a local `truncated = True` and stop scanning. Return `SearchPage(results, truncated=truncated)`. Do not set arbitrary attributes on `list` and do not mark a page truncated merely because its length equals the limit.

- [ ] **Step 3: Update the CLI payload and invalid-limit behavior.**

  In `_command_search()`, serialize the page as:

  ```python
  page = search_layer1(paths, args.query, max_results=args.max_results)
  _print(page.as_dict())
  ```

  Catch `ValueError` at the command boundary using the repository’s existing CLI error convention, emit a path-free deterministic error, and return exit code `2`. Add a CLI test for zero and negative limits.

- [ ] **Step 4: Update web rendering to use explicit fields.**

  In the web route, keep `results = page.items`, pass `truncated=page.truncated`, and leave preview URLs, highlighting, and template inputs unchanged. Add or update a web test proving an exact-limit page renders and that a truncated page exposes the existing template state without leaking the private root.

- [ ] **Step 5: Update existing tests to assert the explicit page contract.**

  Change direct API tests from list assumptions to `page.items` and `page.truncated`; retain all existing matching, case, front-matter, skipped-trash, binary, blank-query, CLI JSON, and privacy assertions.

- [ ] **Step 6: Run focused tests and confirm green behavior.**

  Run:

  ```powershell
  python -m pytest 90-system/tests/test_search.py -q
  python -m pytest 90-system/tests/test_web.py -k search -q
  ```

  Expected: all search and search-web tests pass with deterministic limit handling and no `AttributeError`.

### Task 3: Validate, review, and finalize RET-002

**Files:**
- Modify: `log/2026-09-19-systemic-architecture-audit.md` (ignored local audit log)
- Modify: `90-system/.echo/subagents/charlie/log.md`

- [ ] **Step 1: Run the complete test and privacy gates.**

  Run:

  ```powershell
  .\90-system\automation\scripts\second-self.ps1 validate --privacy --tracked-only
  python -m pytest
  git diff --check
  ```

  Expected: privacy validation passes, the full suite passes, and the diff has no whitespace errors.

- [ ] **Step 2: Review the complete diff and staged paths.**

  Confirm only the typed search implementation, consumer adaptations, tests, plan/status records, and intended documentation changed. Confirm no private Layer 1 content, runtime cache, or unrelated files are staged.

- [ ] **Step 3: Update status only after delivery succeeds.**

  Set Charlie’s task to `Done`, record the test evidence, and change RET-002 from `queued` to `done` only after the protected Second Self commit, PR, CI, merge, and final repository verification succeed. If implementation is validated but delivery is awaiting approval, use `ready-for-validation` with that reason.

- [ ] **Step 4: Finalize through `02-skills-projects/skills/second-self-commit/SKILL.md`.**

  Charlie must produce one coherent commit, one PR, and one merge. Do not create a status-only closeout commit.

## Charlie endorsement

Charlie is endorsed to implement RET-002 after Chad approves this plan. ECHO owns coordination, scope protection, and status reporting; Charlie owns the code, tests, self-review, validation, and final delivery workflow. No implementation has started from this plan.
