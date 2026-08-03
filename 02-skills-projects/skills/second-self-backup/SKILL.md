---
name: second-self-backup
description: Create a manual dated encrypted Second Self backup on removable storage. Use when the user connects a backup drive or requests a verified private-data snapshot.
---
# Second Self Backup

Version: `1.0.0`

## Encrypted backup (disaster recovery)

1. Confirm the destination is the intended removable drive or path.
2. Run `90-system/automation/scripts/backup.ps1 -Destination "<path>"`.
3. Let `age` request the passphrase interactively; never record it.
4. Confirm the encrypted archive, manifest, and SHA-256 file exist.
5. Report verification results without revealing private filenames.
6. Never prune older snapshots automatically.

## Obsidian-readable sync backup (portable copy)

Use this when you want a plain folder you can open in Obsidian, copy to another
machine, or push to GitHub.

1. Run `90-system/automation/scripts/backup.ps1 -SyncTo "<parent-folder>"`.
   Example: `-SyncTo "%USERPROFILE%\Downloads\<your-folder>"`
2. The script creates `"<parent-folder>\second-self\"` with a full mirror of
   your private data root.
3. `.git` is included; caches like `node_modules`, `__pycache__`,
   `.second-self-cache`, `.pytest_cache`, `.next`, `.turbo`, and `.cache`
   are excluded.
4. If previous sync backups exist in the parent folder (`second-self-2`,
   `second-self-3`, etc.), only the 5 newest are kept; older ones are deleted.
5. After creation, point Obsidian at the new folder or copy it to another
   machine. Update `.second-self.local.json` if the data root path changes.

**Privacy note:** The sync backup contains full Layer 1 private data. Push to
GitHub only if you intend to share it. Treat it like any other Git repo.