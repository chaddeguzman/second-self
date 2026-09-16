"""Single-run scheduler lock with bounded stale recovery."""

from __future__ import annotations

import json
import os
import socket
import time
from dataclasses import dataclass
from pathlib import Path


LOCK_TTL_SECONDS = 15 * 60


class SchedulerLockError(RuntimeError):
    """Lock acquisition failed or lock state could not be inspected."""


@dataclass
class SchedulerLock:
    path: Path
    owner: str = ""
    acquired: bool = False

    def acquire(self, *, now: float | None = None, ttl_seconds: int = LOCK_TTL_SECONDS) -> bool:
        if self.acquired:
            return True
        timestamp = time.time() if now is None else now
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"owner": self.owner or f"{socket.gethostname()}:{os.getpid()}", "acquired_at": timestamp}
        try:
            descriptor = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            if self._is_stale(timestamp, ttl_seconds):
                try:
                    self.path.unlink()
                except FileNotFoundError:
                    return self.acquire(now=timestamp, ttl_seconds=ttl_seconds)
                except OSError:
                    raise SchedulerLockError("scheduler lock is busy") from None
                return self.acquire(now=timestamp, ttl_seconds=ttl_seconds)
            return False
        except OSError:
            raise SchedulerLockError("scheduler lock could not be acquired") from None
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
                json.dump(payload, stream, sort_keys=True)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
        except OSError:
            try:
                self.path.unlink()
            except OSError:
                pass
            raise SchedulerLockError("scheduler lock could not be acquired") from None
        self.owner = payload["owner"]
        self.acquired = True
        return True

    def _is_stale(self, now: float, ttl_seconds: int) -> bool:
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            acquired_at = payload.get("acquired_at") if isinstance(payload, dict) else None
            return isinstance(acquired_at, (int, float)) and now - acquired_at > ttl_seconds
        except (OSError, ValueError, json.JSONDecodeError):
            return False

    def release(self) -> None:
        if not self.acquired:
            return
        try:
            self.path.unlink()
        except FileNotFoundError:
            pass
        except OSError:
            raise SchedulerLockError("scheduler lock could not be released") from None
        self.acquired = False

    def __enter__(self) -> "SchedulerLock":
        if not self.acquire():
            raise SchedulerLockError("scheduler lock is busy")
        return self

    def __exit__(self, _exc_type: object, _exc: object, _tb: object) -> None:
        self.release()
