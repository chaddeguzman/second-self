---
name: second-self-tag-rename
description: Rename a tag across all notes via a broker proposal. Use when the user asks to rename, retag, or migrate a tag across Second Self notes.
---
# Second Self Tag Rename

Rename a tag across Layer 1 and project notes. This is a protected change because it edits multiple existing files. Always use the Second Self edit broker and obtain one explicit approval.

## Workflow

1. Confirm the exact old tag and new tag with the user.
2. Run `python -m second_self tags` to see current usage of the old tag.
3. If more than 100 notes would be affected, warn the user and confirm before proceeding.
4. Build a broker `edit` proposal that replaces the old tag with the new tag in every affected note's YAML frontmatter. Preserve tag order and remove duplicates.
5. Include exact unified diffs for every file in `exact_preview`.
6. Save the proposal JSON and submit it:
   ```powershell
   python -m second_self broker propose .\tag-rename-proposal.json
   ```
7. Show the exact preview to the user. Apply after one `Y` or `Yes`:
   ```powershell
   python -m second_self broker approve <proposal-id> --confirm Y --agent <agent-name>
   ```
8. Report the changed paths or any error. Do not rename tags without a reviewed broker proposal.

## Notes

- Only rename tags that already exist. Creating a new tag should use capture or frontmatter edits.
- Keep the operation idempotent: if the old tag does not appear in a file, do not include that file.
- Respect privacy: never expose private paths or personal content outside the local session.