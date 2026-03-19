"""Live backup progress tracker. Writes directly to the database."""

from datetime import datetime

from src.infrastructure.database.engine import session_scope
from src.infrastructure.database.models import BackupProgressModel


class ProgressTracker:
    """Updates a single row in backup_progress to track live backup state."""

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
                row.updated_at = datetime.now()
            else:
                session.add(BackupProgressModel(
                    id=1,
                    running=True,
                    started_at=datetime.now(),
                    current_step="Starting...",
                    total=total_dbs,
                ))

    def update(self, current_db: str, step: str, processed: int):
        with session_scope() as session:
            row = session.query(BackupProgressModel).filter_by(id=1).first()
            if row:
                row.current_db = current_db
                row.current_step = step
                row.processed = processed
                row.updated_at = datetime.now()

    def complete_db(self, db_name: str, status: str, processed: int):
        with session_scope() as session:
            row = session.query(BackupProgressModel).filter_by(id=1).first()
            if row:
                row.last_completed_db = db_name
                row.last_completed_status = status
                row.processed = processed
                row.updated_at = datetime.now()

    def finish(self):
        with session_scope() as session:
            row = session.query(BackupProgressModel).filter_by(id=1).first()
            if row:
                row.running = False
                row.current_db = None
                row.current_step = "Completed"
                row.updated_at = datetime.now()

    @staticmethod
    def get_progress() -> dict | None:
        try:
            with session_scope() as session:
                row = session.query(BackupProgressModel).filter_by(id=1).first()
                if not row:
                    return None
                return {
                    "running": row.running,
                    "started_at": row.started_at.isoformat() if row.started_at else None,
                    "current_db": row.current_db,
                    "current_step": row.current_step,
                    "processed": row.processed,
                    "total": row.total,
                    "last_completed_db": row.last_completed_db,
                    "last_completed_status": row.last_completed_status,
                    "updated_at": row.updated_at.isoformat() if row.updated_at else None,
                }
        except Exception:
            return None
