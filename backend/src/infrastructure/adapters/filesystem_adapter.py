"""Concrete adapter: Local filesystem operations for backup rotation.

Implements the Filesystem port from the domain layer.
"""

import logging
from datetime import datetime, timedelta
from pathlib import Path

from src.domain.ports.filesystem import Filesystem

logger = logging.getLogger(__name__)


class FilesystemAdapter(Filesystem):
    """Handles local backup directory management and rotation."""

    def __init__(self, backup_local_dir: Path, retention_days: int):
        self._backup_dir = backup_local_dir
        self._retention_days = retention_days

    def ensure_db_directory(self, db_name: str) -> Path:
        path = self._backup_dir / db_name
        path.mkdir(parents=True, exist_ok=True)
        return path

    def rotate_old_backups(self) -> int:
        """Delete local backups older than retention policy. Returns count removed."""
        if not self._backup_dir.exists():
            return 0

        cutoff = datetime.now() - timedelta(days=self._retention_days)
        removed = 0

        for db_dir in self._backup_dir.iterdir():
            if not db_dir.is_dir():
                continue
            for f in db_dir.iterdir():
                try:
                    if f.is_file() and datetime.fromtimestamp(f.stat().st_mtime) < cutoff:
                        f.unlink()
                        removed += 1
                        logger.info("Rotated: %s", f.name)
                except OSError as e:
                    logger.warning("Could not remove %s: %s", f.name, e)

            try:
                if db_dir.is_dir() and not any(db_dir.iterdir()):
                    db_dir.rmdir()
            except OSError:
                pass

        if removed:
            logger.info("Rotation complete: removed %d files", removed)
        return removed

    def get_total_local_size(self) -> int:
        """Total bytes used by all local backups."""
        if not self._backup_dir.exists():
            return 0
        return sum(f.stat().st_size for f in self._backup_dir.rglob("*") if f.is_file())
