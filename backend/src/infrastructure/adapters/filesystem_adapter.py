"""Concrete adapter: Local filesystem operations for backup rotation.

Implements the Filesystem port from the domain layer.
"""

import logging
import re
from datetime import datetime, timedelta
from pathlib import Path

from src.domain.ports.filesystem import Filesystem

logger = logging.getLogger(__name__)

# Matches timestamp in backup filenames: dbname_YYYY-MM-DD_HH-MM-SS.backup
_TIMESTAMP_PATTERN = re.compile(r"_(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2})\.")


def _extract_timestamp_prefix(filename: str) -> str | None:
    """Extract the timestamp portion from a backup filename.

    e.g. 'mydb_2026-03-20_10-30-00.backup' → '2026-03-20_10-30-00'
    """
    match = _TIMESTAMP_PATTERN.search(filename)
    return match.group(1) if match else None


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
        """Delete local backups older than retention policy.

        SAFETY: Always keeps the newest backup set per database,
        even if it's older than the retention period. Never leaves
        a database with zero backups.

        Returns count of files removed.
        """
        if not self._backup_dir.exists():
            return 0

        cutoff = datetime.now() - timedelta(days=self._retention_days)
        removed = 0

        for db_dir in self._backup_dir.iterdir():
            if not db_dir.is_dir():
                continue

            # Collect all backup files in this DB directory
            files = sorted(
                [f for f in db_dir.iterdir() if f.is_file()],
                key=lambda f: f.stat().st_mtime,
                reverse=True,  # newest first
            )

            if not files:
                continue  # Empty dir — leave it alone

            # Identify the newest backup set by timestamp prefix
            # A "set" is .backup + .sql.gz with the same timestamp
            newest_prefix = _extract_timestamp_prefix(files[0].name)

            for f in files:
                prefix = _extract_timestamp_prefix(f.name)

                # Always keep the newest set (even if older than cutoff)
                if prefix and prefix == newest_prefix:
                    continue

                # If no prefix match and it's the only file, keep it
                if len(files) - removed <= 1:
                    break

                try:
                    if datetime.fromtimestamp(f.stat().st_mtime) < cutoff:
                        f.unlink()
                        removed += 1
                        logger.info("Rotated: %s", f.name)
                except OSError as e:
                    logger.warning("Could not remove %s: %s", f.name, e)

            # NEVER delete the DB directory — it represents a known database

        if removed:
            logger.info("Rotation complete: removed %d old backup files", removed)
        return removed

    def get_total_local_size(self) -> int:
        """Total bytes used by all local backups."""
        if not self._backup_dir.exists():
            return 0
        return sum(f.stat().st_size for f in self._backup_dir.rglob("*") if f.is_file())
