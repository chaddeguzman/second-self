---
name: brain-backup
description: Create a manual dated encrypted Main Brain backup on removable storage. Use when the user connects a backup drive or requests a verified private-data snapshot.
---

# Brain Backup

Version: `1.0.0`

1. Confirm the destination is the intended removable drive.
2. Run `90-system/automation/scripts/backup.ps1 -Destination "<path>"`.
3. Let `age` request the passphrase interactively; never record it.
4. Confirm the encrypted archive, manifest, and SHA-256 file exist.
5. Report verification results without revealing private filenames.
6. Never prune older snapshots automatically.
