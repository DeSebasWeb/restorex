"""Application Service: Generates reports and dashboard data.

Read-only service for the web dashboard and report generation.
Depends only on domain ports, not on infrastructure.
"""

import logging
from datetime import datetime
from pathlib import Path

from src.application.dto.database_status import DatabaseStatusDTO
from src.domain.ports.backup_repository import BackupRepository
from src.domain.ports.filesystem import Filesystem
from src.domain.value_objects.db_change_stats import DbChangeStats

logger = logging.getLogger(__name__)


class ReportService:
    def __init__(
        self,
        repository: BackupRepository,
        filesystem: Filesystem,
        log_file: Path,
        ssh_host: str,
        retention_days: int,
    ):
        self._repo = repository
        self._fs = filesystem
        self._log_file = log_file
        self._ssh_host = ssh_host
        self._retention_days = retention_days

    def get_all_database_statuses(self) -> list[DatabaseStatusDTO]:
        """Build the status list for the dashboard.

        Compares current scan stats vs last backup stats to determine
        if each database needs a new backup.
        """
        stats = self._repo.get_all_stats()
        history = self._repo.get_history(limit=100)

        statuses = []
        for db_name, db_stats in sorted(stats.items()):
            last_backup = self._find_last_backup(db_name, history)

            # Determine if backup is needed by comparing scan vs backup stats
            needs_backup = True  # Default: needs backup
            if last_backup is not None:
                # Has a previous backup — check if stats changed
                saved_stats = self._repo.get_saved_stats(db_name)
                if saved_stats is not None:
                    current_scan = DbChangeStats(
                        inserts=db_stats.get("inserts", 0),
                        updates=db_stats.get("updates", 0),
                        deletes=db_stats.get("deletes", 0),
                        live_rows=db_stats.get("live_rows", 0),
                        table_count=db_stats.get("table_count", 0),
                    )
                    needs_backup = current_scan.has_changed_since(saved_stats)
                # If no saved backup stats, needs_backup stays True

            statuses.append(DatabaseStatusDTO(
                name=db_name,
                size=db_stats.get("size", "Unknown"),
                tables=db_stats.get("table_count", db_stats.get("tables", 0)),
                live_rows=db_stats.get("live_rows", 0),
                inserts=db_stats.get("inserts", 0),
                updates=db_stats.get("updates", 0),
                deletes=db_stats.get("deletes", 0),
                last_checked=db_stats.get("saved_at"),
                last_backup=last_backup,
                needs_backup=needs_backup,
            ))

        return statuses

    def generate_report(self) -> dict:
        """Generate a summary report suitable for presentation."""
        history = self._repo.get_history(limit=1000)
        stats = self._repo.get_all_stats()

        total_backups = sum(h.get("backed_up", 0) for h in history)
        total_failures = sum(h.get("failed", 0) for h in history)
        total_runs = len(history)
        total_attempted = total_backups + total_failures

        databases = []
        for db_name, db_stats in sorted(stats.items()):
            last_bk = self._find_last_backup(db_name, history)
            databases.append({
                "name": db_name,
                "size": db_stats.get("size", "Unknown"),
                "tables": db_stats.get("table_count", db_stats.get("tables", 0)),
                "live_rows": db_stats.get("live_rows", 0),
                "last_backup": last_bk,
            })

        return {
            "generated_at": datetime.now().isoformat(),
            "server": self._ssh_host,
            "total_databases": len(stats),
            "total_backup_runs": total_runs,
            "total_backups_created": total_backups,
            "total_failures": total_failures,
            "success_rate": (
                round((total_backups / total_attempted) * 100, 1)
                if total_attempted > 0 else 0
            ),
            "local_storage_used": self._human_size(self._fs.get_total_local_size()),
            "retention_days": self._retention_days,
            "databases": databases,
        }

    def get_logs(self, lines: int = 100) -> list[str]:
        if not self._log_file.exists():
            return []
        with open(self._log_file, "r", encoding="utf-8") as f:
            all_lines = f.readlines()
        return [line.strip() for line in all_lines[-lines:]]

    @staticmethod
    def _find_last_backup(db_name: str, history: list[dict]) -> dict | None:
        for run in history:
            for result in run.get("results", []):
                if result.get("db_name") == db_name and result.get("status") in ("success", "partial"):
                    return {
                        "timestamp": result.get("timestamp"),
                        "backup_size": result.get("backup_size", 0),
                        "sql_size": result.get("sql_size", 0),
                        "duration": result.get("duration_seconds", 0),
                    }
        return None

    @staticmethod
    def _human_size(n: int) -> str:
        for u in ("B", "KB", "MB", "GB"):
            if n < 1024:
                return f"{n:.1f} {u}"
            n /= 1024
        return f"{n:.1f} TB"
