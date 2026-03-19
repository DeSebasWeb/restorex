"""Application Service: Orchestrates the full backup workflow.

This is the main use case. It depends ONLY on domain ports (interfaces),
never on concrete infrastructure. Dependencies are injected.
"""

import logging
import shlex
import time
from datetime import datetime
from typing import Callable

from src.application.dto.backup_result import BackupResultDTO
from src.application.dto.backup_summary import BackupSummaryDTO
from src.domain.ports.backup_repository import BackupRepository
from src.domain.ports.database_inspector import DatabaseInspector
from src.domain.ports.file_transfer import FileTransfer
from src.domain.ports.filesystem import Filesystem
from src.domain.ports.remote_executor import RemoteExecutor
from src.domain.value_objects.backup_format import BackupFormat
from src.domain.value_objects.db_name import DbName

logger = logging.getLogger(__name__)

# Progress callback type: (current_db, step_description, processed_count, total_count) -> None
ProgressCallback = Callable[[str, str, int, int], None]


def _noop_progress(db: str, step: str, processed: int, total: int) -> None:
    pass


class BackupService:
    def __init__(
        self,
        executor: RemoteExecutor,
        inspector: DatabaseInspector,
        transfer: FileTransfer,
        repository: BackupRepository,
        filesystem: Filesystem,
        pg_host: str,
        pg_port: int,
        pg_user: str,
        pg_password: str,
        remote_tmp_dir: str,
        on_progress: ProgressCallback | None = None,
    ):
        self._executor = executor
        self._inspector = inspector
        self._transfer = transfer
        self._repo = repository
        self._fs = filesystem
        self._pg_host = pg_host
        self._pg_port = pg_port
        self._pg_user = pg_user
        self._pg_password = pg_password
        self._remote_tmp_dir = remote_tmp_dir
        self._on_progress = on_progress or _noop_progress

    def scan_databases(self) -> list[dict]:
        """Scan server for databases and their stats. No backup performed."""
        self._executor.connect()
        try:
            databases = self._inspector.list_databases()
            result = []

            for db_name in databases:
                stats = self._inspector.get_change_stats(db_name)
                size = self._inspector.get_size_pretty(db_name)

                self._repo.save_stats(db_name, stats, size_pretty=size)

                result.append({
                    "name": db_name,
                    "size": size,
                    "tables": stats.table_count,
                    "live_rows": stats.live_rows,
                    "inserts": stats.inserts,
                    "updates": stats.updates,
                    "deletes": stats.deletes,
                    "last_checked": datetime.now().isoformat(),
                })

            return result
        finally:
            self._executor.disconnect()

    def run_full_backup(self, force: bool = False) -> BackupSummaryDTO:
        """Execute the full backup workflow for all databases."""
        summary = BackupSummaryDTO(started_at=datetime.now().isoformat())

        self._executor.connect()
        try:
            databases = self._inspector.list_databases()
            summary.total_dbs = len(databases)
            logger.info("Found %d databases to evaluate.", len(databases))
            self._on_progress("", f"Found {len(databases)} databases", 0, len(databases))

            processed = 0
            for db_name in databases:
                self._on_progress(db_name, "Checking for changes...", processed, len(databases))

                current_stats = self._inspector.get_change_stats(db_name)
                saved_stats = self._repo.get_saved_stats(db_name)
                last_backup = self._repo.get_last_successful_backup(db_name)

                never_backed_up = last_backup is None
                has_changes = saved_stats is None or current_stats.has_changed_since(saved_stats)

                needs_backup = force or never_backed_up or has_changes

                if not needs_backup:
                    logger.info("Skipping %s — no changes since last backup.", db_name)
                    processed += 1
                    summary.skipped += 1
                    summary.results.append(
                        BackupResultDTO(
                            db_name=db_name,
                            status="skipped",
                            reason="No changes since last backup",
                        ).to_dict()
                    )
                    self._on_progress(db_name, "Skipped (no changes)", processed, len(databases))
                    continue

                reason = "forced" if force else ("first backup" if never_backed_up else "changes detected")
                logger.info("Backing up %s — %s.", db_name, reason)
                self._on_progress(db_name, f"Backing up ({reason})...", processed, len(databases))

                result = self._backup_single_db(db_name)
                processed += 1
                summary.results.append(result.to_dict())

                if result.status == "success":
                    summary.backed_up += 1
                    self._repo.save_stats(db_name, current_stats)
                    self._on_progress(db_name, f"Done ({self._human_size(result.backup_size + result.sql_size)})", processed, len(databases))
                else:
                    summary.failed += 1
                    summary.errors.append({"db_name": db_name, "error": result.error})
                    self._on_progress(db_name, f"Failed: {result.error}", processed, len(databases))

            removed = self._fs.rotate_old_backups()
            if removed:
                logger.info("Rotated %d old backup files.", removed)

        except Exception as e:
            logger.exception("Fatal error during backup run.")
            summary.errors.append({"db_name": "GLOBAL", "error": str(e)})

        finally:
            self._executor.disconnect()

        summary.finished_at = datetime.now().isoformat()
        self._repo.save_run_summary(summary.to_dict())

        logger.info(
            "Backup run complete: %d backed up, %d skipped, %d failed.",
            summary.backed_up, summary.skipped, summary.failed,
        )
        return summary

    def _backup_single_db(self, db_name: str) -> BackupResultDTO:
        """Generate .backup + .sql for a single database and download.

        SECURITY: db_name is validated, all shell arguments are quoted.
        Only temporary files in remote_tmp_dir are created/deleted.
        """
        # Validate database name (defense in depth — already validated by inspector)
        validated_name = DbName(db_name)
        safe_name = validated_name.value

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        remote_dir = self._remote_tmp_dir
        local_dir = self._fs.ensure_db_directory(safe_name)

        result = BackupResultDTO(db_name=safe_name, status="failed", timestamp=timestamp)
        start = time.time()

        try:
            # Ensure remote temp dir (path comes from config, not user input)
            self._executor.execute(f"mkdir -p {shlex.quote(remote_dir)}")

            backup_size = 0
            sql_size = 0
            local_backup = None
            local_sql = None

            for fmt in (BackupFormat.CUSTOM, BackupFormat.PLAIN):
                filename = f"{safe_name}_{timestamp}{fmt.file_extension}"
                remote_path = f"{remote_dir}/{filename}"
                local_path = local_dir / filename

                ext = fmt.file_extension
                self._on_progress(safe_name, f"Generating {ext}...", 0, 0)
                logger.info("Generating %s for %s...", ext, safe_name)

                cmd = (
                    f"PGPASSWORD={shlex.quote(self._pg_password)} pg_dump "
                    f"-h {shlex.quote(self._pg_host)} "
                    f"-p {shlex.quote(str(self._pg_port))} "
                    f"-U {shlex.quote(self._pg_user)} "
                    f"{fmt.pg_dump_flag} "
                    f"-f {shlex.quote(remote_path)} "
                    f"{shlex.quote(safe_name)}"
                )
                _, stderr, code = self._executor.execute(cmd)

                if code != 0:
                    result.error = f"pg_dump {fmt.name} failed: {stderr}"
                    logger.error(result.error)
                    return result

                self._on_progress(safe_name, f"Downloading {ext}...", 0, 0)
                self._transfer.download(remote_path, local_path)
                self._transfer.cleanup_remote(remote_path)

                size = local_path.stat().st_size
                if fmt == BackupFormat.CUSTOM:
                    backup_size = size
                    local_backup = str(local_path)
                else:
                    sql_size = size
                    local_sql = str(local_path)

            duration = round(time.time() - start, 2)

            result.status = "success"
            result.backup_file = local_backup
            result.sql_file = local_sql
            result.backup_size = backup_size
            result.sql_size = sql_size
            result.duration_seconds = duration

            logger.info(
                "OK %s (%.1fs) .backup=%s .sql=%s",
                safe_name, duration,
                self._human_size(backup_size),
                self._human_size(sql_size),
            )

        except Exception as e:
            result.error = str(e)
            result.duration_seconds = round(time.time() - start, 2)
            logger.exception("Backup failed for %s", safe_name)

        return result

    @staticmethod
    def _human_size(n: int) -> str:
        for u in ("B", "KB", "MB", "GB"):
            if n < 1024:
                return f"{n:.1f} {u}"
            n /= 1024
        return f"{n:.1f} TB"
