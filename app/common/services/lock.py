"""Single-instance lock file handling.

Locking is only enforced in production so dev runs (e.g. from VS Code) never
get blocked by a stale lock. The environment string is passed in by the
caller — this module never reads the environment itself.
"""

from pathlib import Path

from app.common.config.constants import ENVIRONMENT_PRODUCTION


def is_already_running(lock_path: Path, environment: str) -> bool:
    """Return True if a lock file already exists and we're in production."""
    if lock_path.exists() and (environment or "").lower() == ENVIRONMENT_PRODUCTION:
        print("Another instance is already running. Exiting.")
        return True

    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.touch()
    return False


def release_lock(lock_path: Path) -> None:
    """Remove the lock file if present; safe to call unconditionally on shutdown."""
    try:
        if lock_path.exists():
            lock_path.unlink()
    except Exception:
        pass
