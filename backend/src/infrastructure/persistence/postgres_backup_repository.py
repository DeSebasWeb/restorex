"""Concrete adapter: PostgreSQL-based backup repository.

Implements BackupRepository port using the local PostgreSQL database.
Replaces the old JSON file-based repository.
"""

import logging
from datetime import datetime

from src.domain.entities.backup_record import BackupRecord
from src.domain.ports.backup_repository import BackupRepository
from src.domain.value_objects.db_change_stats import DbChangeStats
from src.infrastructure.database.engine import session_scope
from src.infrastructure.database.models import (
    BackupRunModel, BackupResultModel, DbStatsModel,
)

logger = logging.getLogger(__name__)


class PostgresBackupRepository(BackupRepository):

    # ── Records & History ───────────────────────────────────────

    def save_record(self, record: BackupRecord) -> None:
        # Individual records are saved as part of run summaries
        pass

    def save_run_summary(self, summary: dict) -> None:
        with session_scope() as session:
            run = BackupRunModel(
                started_at=_parse_dt(summary.get("started_at")),
                finished_at=_parse_dt(summary.get("finished_at")),
                total_dbs=summary.get("total_dbs", 0),
                backed_up=summary.get("backed_up", 0),
                skipped=summary.get("skipped", 0),
                failed=summary.get("failed", 0),
            )
            session.add(run)
            session.flush()  # get run.id

            for r in summary.get("results", []):
                result = BackupResultModel(
                    run_id=run.id,
                    db_name=r.get("db_name", ""),
                    status=r.get("status", "unknown"),
                    timestamp=r.get("timestamp"),
                    backup_file=r.get("backup_file"),
                    sql_file=r.get("sql_file"),
                    backup_size=r.get("backup_size", 0),
                    sql_size=r.get("sql_size", 0),
                    duration_seconds=r.get("duration_seconds", 0.0),
                    error=r.get("error"),
                    reason=r.get("reason"),
                )
                session.add(result)

    def get_history(self, limit: int = 50) -> list[dict]:
        with session_scope() as session:
            runs = (
                session.query(BackupRunModel)
                .order_by(BackupRunModel.started_at.desc())
                .limit(limit)
                .all()
            )

            history = []
            for run in runs:
                results = []
                errors = []
                for r in run.results:
                    rd = {
                        "db_name": r.db_name,
                        "status": r.status,
                        "timestamp": r.timestamp,
                        "backup_file": r.backup_file,
                        "sql_file": r.sql_file,
                        "backup_size": r.backup_size,
                        "sql_size": r.sql_size,
                        "duration_seconds": r.duration_seconds,
                        "error": r.error,
                        "reason": r.reason,
                    }
                    results.append(rd)
                    if r.status == "failed" and r.error:
                        errors.append({"db_name": r.db_name, "error": r.error})

                history.append({
                    "started_at": run.started_at.isoformat() if run.started_at else None,
                    "finished_at": run.finished_at.isoformat() if run.finished_at else None,
                    "total_dbs": run.total_dbs,
                    "backed_up": run.backed_up,
                    "skipped": run.skipped,
                    "failed": run.failed,
                    "results": results,
                    "errors": errors,
                })

            return history

    def get_last_successful_backup(self, db_name: str) -> BackupRecord | None:
        with session_scope() as session:
            result = (
                session.query(BackupResultModel)
                .filter(
                    BackupResultModel.db_name == db_name,
                    BackupResultModel.status == "success",
                )
                .order_by(BackupResultModel.id.desc())
                .first()
            )
            if not result:
                return None

            return BackupRecord(
                db_name=result.db_name,
                timestamp=_parse_dt(result.timestamp) or datetime.now(),
                status="success",
                backup_file=result.backup_file,
                sql_file=result.sql_file,
                backup_size_bytes=result.backup_size,
                sql_size_bytes=result.sql_size,
                duration_seconds=result.duration_seconds,
            )

    # ── Stats (change detection) ────────────────────────────────

    def save_stats(self, db_name: str, stats: DbChangeStats, size_pretty: str = "") -> None:
        with session_scope() as session:
            existing = (
                session.query(DbStatsModel)
                .filter(DbStatsModel.db_name == db_name)
                .first()
            )
            if existing:
                existing.inserts = stats.inserts
                existing.updates = stats.updates
                existing.deletes = stats.deletes
                existing.live_rows = stats.live_rows
                existing.table_count = stats.table_count
                existing.saved_at = datetime.now()
                if size_pretty:
                    existing.size_pretty = size_pretty
            else:
                session.add(DbStatsModel(
                    db_name=db_name,
                    inserts=stats.inserts,
                    updates=stats.updates,
                    deletes=stats.deletes,
                    live_rows=stats.live_rows,
                    table_count=stats.table_count,
                    size_pretty=size_pretty or None,
                ))

    def get_saved_stats(self, db_name: str) -> DbChangeStats | None:
        with session_scope() as session:
            row = (
                session.query(DbStatsModel)
                .filter(DbStatsModel.db_name == db_name)
                .first()
            )
            if not row:
                return None
            return DbChangeStats(
                inserts=row.inserts,
                updates=row.updates,
                deletes=row.deletes,
                live_rows=row.live_rows,
                table_count=row.table_count,
            )

    def get_all_stats(self) -> dict:
        """Return all stats as a dict keyed by db_name. Used by ReportService."""
        with session_scope() as session:
            rows = session.query(DbStatsModel).all()
            return {
                row.db_name: {
                    "inserts": row.inserts,
                    "updates": row.updates,
                    "deletes": row.deletes,
                    "live_rows": row.live_rows,
                    "table_count": row.table_count,
                    "size": row.size_pretty or "Unknown",
                    "saved_at": row.saved_at.isoformat() if row.saved_at else None,
                }
                for row in rows
            }


def _parse_dt(value) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value))
    except (ValueError, TypeError):
        return None
