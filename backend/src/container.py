"""Dependency Injection Container.

Wires all adapters and services together. This is the only place
in the entire application that knows about concrete implementations.
Entry points (web, CLI, scheduler) use this container to get services.
"""

import logging

from src.application.services.backup_service import BackupService
from src.application.services.notification_service import NotificationService
from src.application.services.report_service import ReportService

logger = logging.getLogger(__name__)
from src.infrastructure.adapters.filesystem_adapter import FilesystemAdapter
from src.infrastructure.adapters.postgres_adapter import PostgresAdapter
from src.infrastructure.adapters.ssh_adapter import SSHAdapter
from src.infrastructure.config import Settings
from src.infrastructure.persistence.postgres_backup_repository import PostgresBackupRepository
from src.infrastructure.persistence.notification_repository import NotificationRepository
from src.infrastructure.persistence.postgres_settings_repository import PostgresSettingsRepository
from src.infrastructure.persistence.progress_tracker import ProgressTracker


class Container:
    """Composes the entire dependency graph."""

    def __init__(self):
        # Infrastructure adapters
        self.ssh_adapter = SSHAdapter()
        self.postgres_adapter = PostgresAdapter(executor=self.ssh_adapter)
        self.filesystem_adapter = FilesystemAdapter(
            backup_local_dir=Settings.BACKUP_LOCAL_DIR,
            retention_days=Settings.RETENTION_DAYS,
        )

        # Persistence (PostgreSQL-backed)
        self.backup_repository = PostgresBackupRepository()
        self.settings_repository = PostgresSettingsRepository()
        self.progress_tracker = ProgressTracker()

        # Progress callback: writes to DB so frontend can poll it
        def _on_progress(db: str, step: str, processed: int, total: int):
            try:
                self.progress_tracker.update(db, step, processed)
                if total > 0:
                    self.progress_tracker.update_total(total)
            except Exception as e:
                logger.warning("Progress update failed: %s", e)

        # Download progress callback: writes to DB so frontend can poll it
        def _on_download_progress(transferred: int, total: int):
            try:
                self.progress_tracker.update_download(transferred, total)
            except Exception:
                pass

        # Application services
        self.backup_service = BackupService(
            executor=self.ssh_adapter,
            inspector=self.postgres_adapter,
            transfer=self.ssh_adapter,
            repository=self.backup_repository,
            filesystem=self.filesystem_adapter,
            pg_host=Settings.PG_HOST,
            pg_port=Settings.PG_PORT,
            pg_user=Settings.PG_USER,
            pg_password=Settings.PG_PASSWORD,
            remote_tmp_dir=Settings.BACKUP_REMOTE_TMP_DIR,
            generate_sql=Settings.GENERATE_SQL,
            on_progress=_on_progress,
            on_download_progress=_on_download_progress,
        )

        self.report_service = ReportService(
            repository=self.backup_repository,
            filesystem=self.filesystem_adapter,
            log_file=Settings.LOG_DIR / "app.log",
            ssh_host=Settings.SSH_HOST,
            retention_days=Settings.RETENTION_DAYS,
        )

        # Notifications
        self.notification_repository = NotificationRepository()
        self.notification_service = NotificationService(
            repository=self.notification_repository,
        )


# Will be initialized after DB is ready
container: Container | None = None


def init_container() -> Container:
    """Initialize (or reinitialize) the global container."""
    global container
    Settings.reload()
    container = Container()
    return container
