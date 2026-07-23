---
name: second-self-restore
description: Verify and restore an encrypted Second Self snapshot into a new empty directory. Use for a new workstation, recovery test, or explicit disaster recovery request.
---

# Second Self Restore

Version: `1.0.0`

1. Confirm the archive, checksum file, and empty destination.
2. Run `90-system/automation/scripts/restore.ps1 -Archive "<file>" -Destination "<path>"`.
3. Let `age` request the passphrase interactively.
4. Stop on checksum failure, wrong passphrase, or a non-empty destination.
5. Validate restored metadata before changing active configuration.
6. Never merge or overwrite an active private-data directory automatically.
