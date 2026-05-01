import json
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

from filelock import FileLock
from rich.console import Console
from rich.progress import Progress

from m3.types import RateState

WINDOW_SECONDS = 3600


class RateLimiter:
    def __init__(self, limit: int, state_file: Path, lock_file: Path) -> None:
        self._limit = limit
        self._state_file = state_file
        self._lock_file = lock_file
        self._file_lock: FileLock = FileLock(str(lock_file))

    def _load(self) -> list[datetime]:
        if not self._state_file.exists():
            return []
        try:
            data: RateState = json.loads(self._state_file.read_text())
            return [datetime.fromisoformat(ts) for ts in data.get("calls", [])]
        except (json.JSONDecodeError, ValueError):
            return []

    def _save(self, calls: list[datetime]) -> None:
        self._state_file.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._state_file.with_suffix(".tmp")
        state: RateState = {"calls": [ts.isoformat() for ts in calls]}
        tmp.write_text(json.dumps(state))
        tmp.replace(self._state_file)

    def _prune(self, calls: list[datetime]) -> list[datetime]:
        cutoff = datetime.now(UTC) - timedelta(seconds=WINDOW_SECONDS)
        return [c for c in calls if c > cutoff]

    def _try_acquire(self) -> float | None:
        """Try to claim a rate-limit slot. Returns None on success, seconds-to-wait otherwise."""
        with self._file_lock:
            calls = self._prune(self._load())

            # Enforce minimum interval between consecutive calls
            min_interval = WINDOW_SECONDS / self._limit
            if calls:
                elapsed = (datetime.now(UTC) - calls[-1]).total_seconds()
                if elapsed < min_interval:
                    return min_interval - elapsed

            # Check hourly quota
            if len(calls) >= self._limit:
                sleep_until = calls[0] + timedelta(seconds=WINDOW_SECONDS)
                wait = (sleep_until - datetime.now(UTC)).total_seconds()
                return max(1.0, wait)

            calls.append(datetime.now(UTC))
            self._save(calls)
            return None

    def acquire(self, console: Console, progress: Progress | None = None) -> None:
        """Block until a rate-limit slot is available, then claim it."""
        while True:
            wait = self._try_acquire()
            if wait is None:
                return

            msg = f"[yellow]Rate limit — waiting {wait:.0f}s for quota to refresh…[/yellow]"
            if progress:
                # Add a transient task to the existing progress bar
                # We use total=None to show a pulsing bar/spinner
                # To hide the "0/?" counter, we would need to modify the Progress columns.
                # Instead, we'll use progress.console.status which works with the active Live display.
                with progress.console.status(msg):
                    time.sleep(wait)
            else:
                # Fallback to console.status if no progress bar is active
                with console.status(msg):
                    time.sleep(wait)

    def status(self) -> tuple[int, int]:
        """Return (used, remaining) calls in the current sliding hour."""
        with self._file_lock:
            calls = self._prune(self._load())
            used = len(calls)
            return used, self._limit - used
