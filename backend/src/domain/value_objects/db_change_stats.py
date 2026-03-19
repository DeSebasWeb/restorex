"""Value object for database change statistics (immutable)."""

from dataclasses import dataclass


@dataclass(frozen=True)
class DbChangeStats:
    inserts: int
    updates: int
    deletes: int
    live_rows: int
    table_count: int

    @property
    def total_changes(self) -> int:
        return self.inserts + self.updates + self.deletes

    def has_changed_since(self, previous: "DbChangeStats") -> bool:
        return (
            self.inserts != previous.inserts
            or self.updates != previous.updates
            or self.deletes != previous.deletes
        )
