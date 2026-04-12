"""Thread-safe cancellation token for long-running application operations.

Lives in the application layer because it coordinates service-level
workflows (backup orchestration). Uses only Python stdlib (threading.Event).
"""

import threading

from src.domain.exceptions import BackupCancelled


class CancellationToken:
    """Cooperative cancellation token.

    Call cancel() from one thread, and other threads can poll
    is_cancelled or call check() at cancellation points.
    """

    def __init__(self):
        self._event = threading.Event()

    def cancel(self) -> None:
        """Signal cancellation. Thread-safe, idempotent."""
        self._event.set()

    @property
    def is_cancelled(self) -> bool:
        return self._event.is_set()

    def check(self) -> None:
        """Raise BackupCancelled if the token has been cancelled.

        Insert at every cancellation point in the backup workflow.
        """
        if self._event.is_set():
            raise BackupCancelled("Backup cancelled by user")
