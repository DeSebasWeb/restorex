"""Entity representing a PostgreSQL database on the server."""

from dataclasses import dataclass, field
from datetime import datetime

from src.domain.value_objects.db_change_stats import DbChangeStats


@dataclass
class DatabaseInfo:
    name: str
    size_pretty: str = "Unknown"
    stats: DbChangeStats = field(
        default_factory=lambda: DbChangeStats(0, 0, 0, 0, 0)
    )
    last_checked: datetime | None = None
    last_backup_at: datetime | None = None
    needs_backup: bool = True

    def mark_checked(self, stats: DbChangeStats, size: str):
        self.stats = stats
        self.size_pretty = size
        self.last_checked = datetime.now()

    def mark_backed_up(self):
        self.last_backup_at = datetime.now()
        self.needs_backup = False
