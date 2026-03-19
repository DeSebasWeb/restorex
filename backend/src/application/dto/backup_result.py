"""DTO for a single database backup result."""

from dataclasses import dataclass


@dataclass
class BackupResultDTO:
    db_name: str
    status: str
    timestamp: str | None = None
    backup_file: str | None = None
    sql_file: str | None = None
    backup_size: int = 0
    sql_size: int = 0
    duration_seconds: float = 0.0
    error: str | None = None
    reason: str | None = None

    def to_dict(self) -> dict:
        return {
            "db_name": self.db_name,
            "status": self.status,
            "timestamp": self.timestamp,
            "backup_file": self.backup_file,
            "sql_file": self.sql_file,
            "backup_size": self.backup_size,
            "sql_size": self.sql_size,
            "duration_seconds": self.duration_seconds,
            "error": self.error,
            "reason": self.reason,
        }
