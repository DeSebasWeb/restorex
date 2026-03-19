"""Port: Local filesystem operations for backup storage."""

from abc import ABC, abstractmethod
from pathlib import Path


class Filesystem(ABC):
    @abstractmethod
    def ensure_db_directory(self, db_name: str) -> Path:
        """Create and return the local directory for a database's backups."""

    @abstractmethod
    def rotate_old_backups(self) -> int:
        """Delete backups older than retention policy. Returns count removed."""

    @abstractmethod
    def get_total_local_size(self) -> int:
        """Total bytes used by all local backups."""
