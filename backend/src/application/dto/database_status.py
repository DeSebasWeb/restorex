"""DTO for database status displayed on the dashboard."""

from dataclasses import dataclass


@dataclass
class DatabaseStatusDTO:
    name: str
    size: str
    tables: int
    live_rows: int
    inserts: int
    updates: int
    deletes: int
    last_checked: str | None
    last_backup: dict | None

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "size": self.size,
            "tables": self.tables,
            "live_rows": self.live_rows,
            "inserts": self.inserts,
            "updates": self.updates,
            "deletes": self.deletes,
            "last_checked": self.last_checked,
            "last_backup": self.last_backup,
        }
