"""Entity representing a completed (or failed) backup operation."""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class BackupRecord:
    db_name: str
    timestamp: datetime
    status: str  # "success" | "failed" | "skipped"
    backup_file: str | None = None
    sql_file: str | None = None
    backup_size_bytes: int = 0
    sql_size_bytes: int = 0
    duration_seconds: float = 0.0
    error: str | None = None

    @property
    def is_success(self) -> bool:
        return self.status == "success"

    @property
    def total_size_bytes(self) -> int:
        return self.backup_size_bytes + self.sql_size_bytes
