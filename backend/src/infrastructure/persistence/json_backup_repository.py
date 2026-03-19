"""Concrete adapter: JSON file-based backup repository.

Implements BackupRepository port using local JSON files for persistence.
"""

import json
import logging
from datetime import datetime, timedelta

from src.domain.entities.backup_record import BackupRecord
from src.domain.ports.backup_repository import BackupRepository
from src.domain.value_objects.db_change_stats import DbChangeStats
from src.infrastructure.config import Settings

logger = logging.getLogger(__name__)


class JsonBackupRepository(BackupRepository):
    def __init__(self):
        Settings.DATA_DIR.mkdir(parents=True, exist_ok=True)

    # ── Records & History ───────────────────────────────────────

    def save_record(self, record: BackupRecord) -> None:
        # Individual records are stored as part of run summaries
        pass

    def save_run_summary(self, summary: dict) -> None:
        history = self._load_history()
        history.append(summary)

        # Keep last 90 days
        cutoff = (datetime.now() - timedelta(days=90)).isoformat()
        history = [h for h in history if h.get("started_at", "") >= cutoff]

        self._write_history(history)

    def get_history(self, limit: int = 50) -> list[dict]:
        history = self._load_history()
        history.reverse()
        return history[:limit]

    def get_last_successful_backup(self, db_name: str) -> BackupRecord | None:
        history = self._load_history()
        for run in reversed(history):
            for result in run.get("results", []):
                if result.get("db_name") == db_name and result.get("status") == "success":
                    return BackupRecord(
                        db_name=db_name,
                        timestamp=datetime.fromisoformat(result["timestamp"])
                        if "T" in result.get("timestamp", "")
                        else datetime.now(),
                        status="success",
                        backup_file=result.get("backup_file"),
                        sql_file=result.get("sql_file"),
                        backup_size_bytes=result.get("backup_size", 0),
                        sql_size_bytes=result.get("sql_size", 0),
                        duration_seconds=result.get("duration_seconds", 0),
                    )
        return None

    # ── Stats (change detection) ────────────────────────────────

    def save_stats(self, db_name: str, stats: DbChangeStats, size_pretty: str = "") -> None:
        all_stats = self._load_stats()
        entry = {
            "inserts": stats.inserts,
            "updates": stats.updates,
            "deletes": stats.deletes,
            "live_rows": stats.live_rows,
            "table_count": stats.table_count,
            "saved_at": datetime.now().isoformat(),
        }
        if size_pretty:
            entry["size"] = size_pretty
        all_stats[db_name] = entry
        self._write_stats(all_stats)

    def get_saved_stats(self, db_name: str) -> DbChangeStats | None:
        all_stats = self._load_stats()
        if db_name not in all_stats:
            return None
        s = all_stats[db_name]
        return DbChangeStats(
            inserts=s.get("inserts", 0),
            updates=s.get("updates", 0),
            deletes=s.get("deletes", 0),
            live_rows=s.get("live_rows", 0),
            table_count=s.get("table_count", 0),
        )

    # ── Private helpers ─────────────────────────────────────────

    def _load_history(self) -> list:
        if not Settings.HISTORY_FILE.exists():
            return []
        with open(Settings.HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

    def _write_history(self, data: list) -> None:
        with open(Settings.HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)

    def _load_stats(self) -> dict:
        if not Settings.STATS_FILE.exists():
            return {}
        with open(Settings.STATS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

    def _write_stats(self, data: dict) -> None:
        with open(Settings.STATS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def get_all_stats(self) -> dict:
        return self._load_stats()
