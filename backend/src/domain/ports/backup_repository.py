"""Port: Persistence for backup history and database stats."""

from abc import ABC, abstractmethod
from datetime import datetime

from src.domain.entities.backup_record import BackupRecord
from src.domain.value_objects.db_change_stats import DbChangeStats


class BackupRepository(ABC):
    @abstractmethod
    def save_record(self, record: BackupRecord) -> None:
        """Persist a single backup record."""

    @abstractmethod
    def save_run_summary(self, summary: dict) -> None:
        """Persist a full backup run summary."""

    @abstractmethod
    def get_history(self, limit: int = 50) -> list[dict]:
        """Retrieve backup run history, most recent first."""

    @abstractmethod
    def get_last_successful_backup(self, db_name: str) -> BackupRecord | None:
        """Find the most recent successful backup for a database."""

    @abstractmethod
    def save_stats(self, db_name: str, stats: DbChangeStats, size_pretty: str = "") -> None:
        """Save current change stats for change detection."""

    @abstractmethod
    def get_saved_stats(self, db_name: str) -> DbChangeStats | None:
        """Retrieve previously saved stats for a database."""

    @abstractmethod
    def get_all_stats(self) -> dict:
        """Retrieve all saved stats as a dict keyed by db_name."""
