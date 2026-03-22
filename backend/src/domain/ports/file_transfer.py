"""Port: File transfer interface between remote and local systems."""

from abc import ABC, abstractmethod
from collections.abc import Callable
from pathlib import Path

# callback(bytes_transferred, total_bytes)
ProgressCallback = Callable[[int, int], None] | None


class FileTransfer(ABC):
    @abstractmethod
    def download(self, remote_path: str, local_path: Path, progress_cb: ProgressCallback = None) -> None:
        """Download a file from the remote server to local disk."""

    @abstractmethod
    def get_remote_size(self, remote_path: str) -> int:
        """Get file size on remote server in bytes."""

    @abstractmethod
    def cleanup_remote(self, remote_path: str) -> None:
        """Delete a file on the remote server."""
