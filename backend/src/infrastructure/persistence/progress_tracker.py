"""Live backup progress tracker. Writes directly to the database.

Supports tracking multiple concurrent backup jobs via the active_jobs JSON column.
All methods are thread-safe (each uses its own session_scope).
"""

import json
import logging
import threading
import time
from datetime import datetime

logger = logging.getLogger(__name__)

from src.infrastructure.database.engine import session_scope
from src.infrastructure.database.models import BackupProgressModel


class ProgressTracker:
    """Updates a single row in backup_progress to track live backup state.

    For parallel backups, active_jobs stores a JSON array of all currently
    running jobs with their individual progress.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._last_download_updates: dict[str, float] = {}

    def start(self, total_dbs: int):
        with session_scope() as session:
            row = session.query(BackupProgressModel).filter_by(id=1).first()
            if row:
                row.running = True
                row.started_at = datetime.now()
                row.current_db = None
                row.current_step = "Starting..."
                row.processed = 0
                row.total = total_dbs
                row.last_completed_db = None
                row.last_completed_status = None
                row.download_bytes = 0
                row.download_total = 0
                row.active_jobs = "[]"
                row.updated_at = datetime.now()
            else:
                session.add(BackupProgressModel(
                    id=1,
                    running=True,
                    started_at=datetime.now(),
                    current_step="Starting...",
                    total=total_dbs,
                    active_jobs="[]",
                ))

    def update(self, current_db: str, step: str, processed: int):
        with session_scope() as session:
            row = session.query(BackupProgressModel).filter_by(id=1).first()
            if row:
                row.current_db = current_db
                row.current_step = step
                row.processed = processed
                row.download_bytes = 0
                row.download_total = 0
                row.updated_at = datetime.now()

    def update_total(self, total: int):
        with session_scope() as session:
            row = session.query(BackupProgressModel).filter_by(id=1).first()
            if row and row.total != total:
                row.total = total
                row.updated_at = datetime.now()

    # ── Parallel job tracking ──────────────────────────────────

    def start_job(self, db_name: str, step: str):
        """Add a database to the list of active parallel jobs."""
        with self._lock:
            try:
                with session_scope() as session:
                    row = session.query(BackupProgressModel).filter_by(id=1).first()
                    if not row:
                        return
                    jobs = self._parse_jobs(row.active_jobs)
                    # Remove existing entry for same db (if restarting)
                    jobs = [j for j in jobs if j["db"] != db_name]
                    jobs.append({
                        "db": db_name,
                        "step": step,
                        "download_bytes": 0,
                        "download_total": 0,
                    })
                    row.active_jobs = json.dumps(jobs)
                    row.current_db = db_name
                    row.current_step = step
                    row.updated_at = datetime.now()
            except Exception:
                pass

    def update_job(self, db_name: str, step: str, download_bytes: int = 0, download_total: int = 0):
        """Update step and progress for a specific parallel job."""
        try:
            with session_scope() as session:
                row = session.query(BackupProgressModel).filter_by(id=1).first()
                if not row:
                    return
                jobs = self._parse_jobs(row.active_jobs)
                found = False
                for job in jobs:
                    if job["db"] == db_name:
                        job["step"] = step
                        job["download_bytes"] = download_bytes
                        job["download_total"] = download_total
                        found = True
                        break
                if not found:
                    logger.warning("update_job called for unknown job '%s', auto-creating.", db_name)
                    jobs.append({"db": db_name, "step": step, "download_bytes": download_bytes, "download_total": download_total})
                row.active_jobs = json.dumps(jobs)
                row.current_db = db_name
                row.current_step = step
                row.updated_at = datetime.now()
        except Exception:
            pass

    def update_job_download(self, db_name: str, download_bytes: int, download_total: int):
        """Update only download progress for a job. Throttled to 1 write/sec per DB."""
        now = time.time()
        with self._lock:
            last = self._last_download_updates.get(db_name, 0.0)
            if now - last < 1.0 and download_bytes < download_total:
                return
            self._last_download_updates[db_name] = now

        try:
            with session_scope() as session:
                row = session.query(BackupProgressModel).filter_by(id=1).first()
                if not row:
                    return
                jobs = self._parse_jobs(row.active_jobs)
                for job in jobs:
                    if job["db"] == db_name:
                        job["download_bytes"] = download_bytes
                        job["download_total"] = download_total
                        break
                row.active_jobs = json.dumps(jobs)
                row.download_bytes = download_bytes
                row.download_total = download_total
                row.updated_at = datetime.now()
        except Exception:
            pass

    def complete_job(self, db_name: str, status: str, processed: int):
        """Remove a database from active jobs and update completion info."""
        with self._lock:
            self._last_download_updates.pop(db_name, None)
        try:
            with session_scope() as session:
                row = session.query(BackupProgressModel).filter_by(id=1).first()
                if not row:
                    return
                jobs = self._parse_jobs(row.active_jobs)
                jobs = [j for j in jobs if j["db"] != db_name]
                row.active_jobs = json.dumps(jobs)
                row.last_completed_db = db_name
                row.last_completed_status = status
                row.processed = processed
                row.download_bytes = 0
                row.download_total = 0
                row.updated_at = datetime.now()
        except Exception:
            pass

    # ── Legacy single-DB methods (kept for backwards compat) ──

    def update_download(self, bytes_transferred: int, total_bytes: int):
        """Update download progress (legacy single-DB mode)."""
        now = time.time()
        with self._lock:
            last = self._last_download_updates.get("__global__", 0.0)
            if now - last < 1.0 and bytes_transferred < total_bytes:
                return
            self._last_download_updates["__global__"] = now
        try:
            with session_scope() as session:
                row = session.query(BackupProgressModel).filter_by(id=1).first()
                if row:
                    row.download_bytes = bytes_transferred
                    row.download_total = total_bytes
                    row.updated_at = datetime.now()
        except Exception:
            pass

    def complete_db(self, db_name: str, status: str, processed: int):
        self.complete_job(db_name, status, processed)

    def cancel(self):
        """Mark the current backup as cancelled by the user."""
        with session_scope() as session:
            row = session.query(BackupProgressModel).filter_by(id=1).first()
            if row:
                row.running = False
                row.current_db = None
                row.current_step = "Cancelled"
                row.download_bytes = 0
                row.download_total = 0
                row.active_jobs = "[]"
                row.updated_at = datetime.now()

    def finish(self):
        with session_scope() as session:
            row = session.query(BackupProgressModel).filter_by(id=1).first()
            if row:
                row.running = False
                row.current_db = None
                row.current_step = "Completed"
                row.download_bytes = 0
                row.download_total = 0
                row.active_jobs = "[]"
                row.updated_at = datetime.now()

    @staticmethod
    def get_progress() -> dict | None:
        try:
            with session_scope() as session:
                row = session.query(BackupProgressModel).filter_by(id=1).first()
                if not row:
                    return None
                try:
                    active_jobs = json.loads(row.active_jobs) if row.active_jobs else []
                except (json.JSONDecodeError, TypeError):
                    active_jobs = []
                return {
                    "running": row.running,
                    "started_at": row.started_at.isoformat() if row.started_at else None,
                    "current_db": row.current_db,
                    "current_step": row.current_step,
                    "processed": row.processed,
                    "total": row.total,
                    "last_completed_db": row.last_completed_db,
                    "last_completed_status": row.last_completed_status,
                    "download_bytes": row.download_bytes,
                    "download_total": row.download_total,
                    "active_jobs": active_jobs,
                    "updated_at": row.updated_at.isoformat() if row.updated_at else None,
                }
        except Exception:
            return None

    @staticmethod
    def _parse_jobs(raw: str | None) -> list[dict]:
        if not raw:
            return []
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return []
