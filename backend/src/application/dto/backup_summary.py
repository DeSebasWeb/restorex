"""DTO for a complete backup run summary."""

from dataclasses import dataclass, field


@dataclass
class BackupSummaryDTO:
    started_at: str
    finished_at: str | None = None
    total_dbs: int = 0
    backed_up: int = 0
    skipped: int = 0
    failed: int = 0
    results: list[dict] = field(default_factory=list)
    errors: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "total_dbs": self.total_dbs,
            "backed_up": self.backed_up,
            "skipped": self.skipped,
            "failed": self.failed,
            "results": self.results,
            "errors": self.errors,
        }
