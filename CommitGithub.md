# Editing and Publishing from VS Code

Use this sequence whenever you change Second Self in VS Code.

## Normal workflow

1. Make and review your changes in VS Code.
2. Open **Source Control** and confirm that no private memory, journal, note,
   project, or local-configuration files are included.
3. Enter a clear commit message and select **Commit**.
4. Do not select **Push** or **Sync Changes**. The repository's Git hook pushes
   the commit to `automation/main`, and GitHub Actions opens or updates the pull
   request automatically.
5. Open the repository on GitHub and select **Pull requests**.
6. Open the pull request from `automation/main` into `main`.
7. Wait for the required `test` check to pass. Do not merge while a required
   check is pending or failing.
8. Select **Rebase and merge**, then confirm the merge.
9. Return to VS Code.
10. In **Source Control**, select **...** and then **Pull** to update local
    `main`. It is normal for VS Code to report that the branch is already up to
    date.

## Important choices

- Use **Commit**, not **Commit & Push** or **Sync Changes**.
- Use **Rebase and merge** for the automated pull request.
- Do not use **Create a merge commit** or **Squash and merge** for this
  workflow.
- You do not need to manually create a pull request.
- Additional commits made while the automated pull request is open update that
  same pull request.

## If something goes wrong

- If the `test` check fails, open the failed check and fix the reported problem
  before merging.
- If no pull request appears, inspect the latest GitHub Actions run for
  **Validate and open pull request**.
- If VS Code tries to push directly to `main`, cancel it. Protected `main`
  accepts changes only through a pull request.
- Before every commit, run:

  ```powershell
  .\90-system\automation\scripts\second-self.ps1 validate --privacy --tracked-only
  ```
