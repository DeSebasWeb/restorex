"""Dependency Injection Container.

Wires all adapters and services together. This is the only place
in the entire application that knows about concrete implementations.
Entry points (web, CLI, scheduler) use this container to get services.
"""

import logging

from src.application.services.auth_service import AuthService
from src.application.services.backup_service import BackupService
from src.application.services.user_service import UserService
from src.application.services.notification_service import NotificationService
from src.application.services.report_service import ReportService
from src.infrastructure.adapters.filesystem_adapter import FilesystemAdapter
from src.infrastructure.adapters.notification_sender_factory import ConcreteNotificationSenderFactory
from src.infrastructure.adapters.postgres_adapter import PostgresAdapter, PGConfig
from src.infrastructure.adapters.ssh_adapter import SSHAdapter, SSHConfig
from src.infrastructure.config import Settings
from src.infrastructure.persistence.auth_repository import PostgresAuthRepository
from src.infrastructure.persistence.host_key_store import PostgresHostKeyStore
from src.infrastructure.persistence.user_repository import PostgresUserRepository
from src.infrastructure.persistence.postgres_backup_repository import PostgresBackupRepository
from src.infrastructure.persistence.notification_repository import PostgresNotificationRepository
from src.infrastructure.persistence.notification_template_repository import PostgresNotificationTemplateRepository
from src.infrastructure.persistence.user_notification_repository import PostgresUserNotificationRepository
from src.infrastructure.persistence.postgres_settings_repository import PostgresSettingsRepository
from src.infrastructure.persistence.progress_tracker import ProgressTracker

logger = logging.getLogger(__name__)


class Container:
    """Composes the entire dependency graph."""

    def __init__(self):
        # Configuration objects (immutable, injected into adapters)
        ssh_config = SSHConfig(
            host=Settings.SSH_HOST,
            port=Settings.SSH_PORT,
            user=Settings.SSH_USER,
            password=Settings.SSH_PASSWORD,
            key_path=Settings.SSH_KEY_PATH,
            remote_tmp_dir=Settings.BACKUP_REMOTE_TMP_DIR,
        )
        pg_config = PGConfig(
            host=Settings.PG_HOST,
            port=Settings.PG_PORT,
            user=Settings.PG_USER,
            password=Settings.PG_PASSWORD,
            excluded_dbs=frozenset(Settings.EXCLUDED_DBS),
        )

        # Infrastructure adapters (shared — used for scan, single-DB mode)
        self.host_key_store = PostgresHostKeyStore()
        self.ssh_adapter = SSHAdapter(config=ssh_config, host_key_store=self.host_key_store)
        self.postgres_adapter = PostgresAdapter(executor=self.ssh_adapter, config=pg_config)
        self.filesystem_adapter = FilesystemAdapter(
            backup_local_dir=Settings.BACKUP_LOCAL_DIR,
            retention_days=Settings.RETENTION_DAYS,
        )

        # Persistence (PostgreSQL-backed)
        self.backup_repository = PostgresBackupRepository()
        self.settings_repository = PostgresSettingsRepository()
        self.progress_tracker = ProgressTracker()

        # ── Factories for parallel mode (each thread gets its own SSH) ──

        def _executor_factory() -> SSHAdapter:
            return SSHAdapter(config=ssh_config, host_key_store=self.host_key_store)

        def _inspector_factory(executor):
            return PostgresAdapter(executor=executor, config=pg_config)

        def _transfer_factory(executor):
            """SSHAdapter implements both RemoteExecutor and FileTransfer."""
            return executor

        # ── Progress callbacks ──

        def _on_progress(db: str, step: str, processed: int, total: int):
            try:
                self.progress_tracker.update(db, step, processed)
                if total > 0:
                    self.progress_tracker.update_total(total)
            except Exception as e:
                logger.warning("Progress update failed: %s", e)

        def _on_job_progress(db: str, step: str, processed: int, total: int):
            """Per-job progress for parallel mode — updates active_jobs in tracker."""
            try:
                self.progress_tracker.update_job(db, step)
            except Exception:
                pass

        def _on_job_download(db: str, transferred: int, total: int):
            """Per-job download progress for parallel mode."""
            try:
                self.progress_tracker.update_job_download(db, download_bytes=transferred, download_total=total)
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
            parallel_workers=Settings.PARALLEL_WORKERS,
            executor_factory=_executor_factory,
            inspector_factory=_inspector_factory,
            transfer_factory=_transfer_factory,
            on_progress=_on_progress,
            on_job_progress=_on_job_progress,
            on_job_download=_on_job_download,
        )

        self.report_service = ReportService(
            repository=self.backup_repository,
            filesystem=self.filesystem_adapter,
            log_file=Settings.LOG_DIR / "app.log",
            ssh_host=Settings.SSH_HOST,
            retention_days=Settings.RETENTION_DAYS,
        )

        # Notifications
        self.notification_repository = PostgresNotificationRepository()
        self.user_notification_repository = PostgresUserNotificationRepository()
        self.notification_template_repository = PostgresNotificationTemplateRepository()
        self.sender_factory = ConcreteNotificationSenderFactory()

        def _inherit_policy() -> bool:
            """Read the notification inheritance setting from DB."""
            try:
                repo = PostgresSettingsRepository()
                settings = repo.load()
                return settings.get("NOTIFICATION_INHERIT_GLOBAL", "true").lower() in ("true", "1")
            except Exception:
                return True  # Default: inherit

        self.notification_service = NotificationService(
            repository=self.notification_repository,
            sender_factory=self.sender_factory,
            user_repository=self.user_notification_repository,
            template_repository=self.notification_template_repository,
            inherit_policy=_inherit_policy,
        )

        # Authentication
        self.auth_repository = PostgresAuthRepository()
        self.auth_service = AuthService(
            repository=self.auth_repository,
            jwt_secret=Settings.JWT_SECRET_KEY,
            access_token_minutes=Settings.ACCESS_TOKEN_MINUTES,
            refresh_token_days=Settings.REFRESH_TOKEN_DAYS,
        )

        # User management
        self.user_repository = PostgresUserRepository()
        self.user_service = UserService(
            repository=self.user_repository,
            auth_repository=self.auth_repository,
        )


# Will be initialized after DB is ready
container: Container | None = None


def init_container() -> Container:
    """Initialize (or reinitialize) the global container."""
    global container
    Settings.reload()
    container = Container()
    return container
