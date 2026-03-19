"""Port: File transfer interface between remote and local systems."""

from abc import ABC, abstractmethod
from pathlib import Path


class FileTransfer(ABC):
    @abstractmethod
    def download(self, remote_path: str, local_path: Path) -> None:
        """Download a file from the remote server to local disk."""

    @abstractmethod
    def cleanup_remote(self, remote_path: str) -> None:
        """Delete a file on the remote server."""
