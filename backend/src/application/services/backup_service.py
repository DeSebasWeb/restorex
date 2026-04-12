"""Application Service: Orchestrates the full backup workflow.

This is the main use case. It depends ONLY on domain ports (interfaces),
never on concrete infrastructure. Dependencies are injected.

Supports parallel backup execution via ThreadPoolExecutor. Each parallel
job gets its own SSH connection (via executor_factory) for thread safety.
"""

import logging
import shlex
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Callable

from src.application.dto.backup_result import BackupResultDTO
from src.application.dto.backup_summary import BackupSummaryDTO
from src.domain.ports.backup_repository import BackupRepository
from src.domain.ports.database_inspector import DatabaseInspector
from src.domain.ports.file_transfer import FileTransfer
from src.domain.ports.filesystem import Filesystem
from src.domain.ports.remote_executor import RemoteExecutor
from src.application.cancellation_token import CancellationToken
from src.domain.exceptions import BackupCancelled
from src.domain.value_objects.backup_format import BackupFormat
from src.domain.value_objects.db_name import DbName

logger = logging.getLogger(__name__)

# Callback types
ProgressCallback = Callable[[str, str, int, int], None]
# Job-level callbacks for parallel mode
JobProgressCallback = Callable[[str, str, int, int], None]
JobDownloadCallback = Callable[[str, int, int], None]

# Factory types: create new instances per thread
ExecutorFactory = Callable[[], RemoteExecutor]
InspectorFactory = Callable[[RemoteExecutor], DatabaseInspector]
TransferFactory = Callable[[RemoteExecutor], FileTransfer]


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
        generate_sql: bool = True,
        parallel_workers: int = 1,
        executor_factory: ExecutorFactory | None = None,
        inspector_factory: InspectorFactory | None = None,
        transfer_factory: TransferFactory | None = None,
        on_progress: ProgressCallback | None = None,
        on_job_progress: JobProgressCallback | None = None,
        on_job_download: JobDownloadCallback | None = None,
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
        self._generate_sql = generate_sql
        self._parallel_workers = max(1, parallel_workers)
        self._executor_factory = executor_factory
        self._inspector_factory = inspector_factory
        self._transfer_factory = transfer_factory
        self._on_progress = on_progress or _noop_progress
        self._on_job_progress = on_job_progress or _noop_progress
        self._on_job_download = on_job_download or (lambda db, t, tot: None)
        self._processed_lock = threading.Lock()
        self._processed_count = 0
        self._cancel_token: CancellationToken | None = None

    def cancel(self) -> None:
        """Signal cancellation of the running backup. Thread-safe."""
        token = self._cancel_token
        if token is not None:
            token.cancel()
            logger.info("Backup cancellation requested.")

    def _check_cancelled(self) -> None:
        """Raise BackupCancelled if cancellation was requested."""
        token = self._cancel_token
        if token is not None:
            token.check()

    def scan_databases(self) -> list[dict]:
        """Scan server for databases and their stats. No backup performed."""
        self._executor.connect()
        try:
            databases = self._inspector.list_databases()
            result = []

            for db_name in databases:
                stats = self._inspector.get_change_stats(db_name)
                size = self._inspector.get_size_pretty(db_name)
                self._repo.save_stats(db_name, stats, size_pretty=size, source="scan")
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
        """Execute the full backup workflow for all databases.

        When parallel_workers > 1 and executor_factory is provided,
        databases are backed up concurrently using a thread pool.
        """
        summary = BackupSummaryDTO(started_at=datetime.now().isoformat())
        self._processed_count = 0
        self._cancel_token = CancellationToken()

        # Phase 1: Scan (sequential — single connection)
        self._executor.connect()
        try:
            databases = self._inspector.list_databases()
            summary.total_dbs = len(databases)
            logger.info("Found %d databases to evaluate.", len(databases))
            self._on_progress("", f"Found {len(databases)} databases", 0, len(databases))

            # Determine which DBs need backup
            dbs_to_backup = []
            dbs_to_skip = []
            for db_name in databases:
                self._check_cancelled()
                current_stats = self._inspector.get_change_stats(db_name)
                size_pretty = self._inspector.get_size_pretty(db_name)
                self._repo.save_stats(db_name, current_stats, size_pretty=size_pretty, source="scan")

                saved_stats = self._repo.get_saved_stats(db_name)
                last_backup = self._repo.get_last_successful_backup(db_name)
                never_backed_up = last_backup is None
                has_changes = saved_stats is None or current_stats.has_changed_since(saved_stats)
                needs_backup = force or never_backed_up or has_changes

                if needs_backup:
                    reason = "forced" if force else ("first backup" if never_backed_up else "changes detected")
                    dbs_to_backup.append((db_name, current_stats, reason))
                else:
                    dbs_to_skip.append(db_name)
        finally:
            self._executor.disconnect()

        # Record skipped DBs
        for db_name in dbs_to_skip:
            summary.skipped += 1
            summary.results.append(
                BackupResultDTO(
                    db_name=db_name,
                    status="skipped",
                    reason="No changes since last backup",
                ).to_dict()
            )

        total_to_process = len(dbs_to_backup)
        total_all = total_to_process + len(dbs_to_skip)
        self._on_progress("", f"{total_to_process} databases need backup, {len(dbs_to_skip)} skipped", 0, total_to_process)

        if not dbs_to_backup:
            summary.finished_at = datetime.now().isoformat()
            self._repo.save_run_summary(summary.to_dict())
            return summary

        # Phase 2: Backup (parallel or sequential)
        use_parallel = (
            self._parallel_workers > 1
            and self._executor_factory is not None
            and len(dbs_to_backup) > 1
        )

        if use_parallel:
            self._run_parallel_backup(dbs_to_backup, total_to_process, summary)
        else:
            self._run_sequential_backup(dbs_to_backup, total_to_process, summary)

        # Phase 3: Cleanup
        try:
            removed = self._fs.rotate_old_backups()
            if removed:
                logger.info("Rotated %d old backup files.", removed)
        except Exception as e:
            logger.warning("Rotation failed: %s", e)

        summary.finished_at = datetime.now().isoformat()
        self._cancel_token = None
        self._repo.save_run_summary(summary.to_dict())

        logger.info(
            "Backup run complete: %d backed up, %d skipped, %d failed.",
            summary.backed_up, summary.skipped, summary.failed,
        )
        return summary

    def _run_sequential_backup(
        self,
        dbs_to_backup: list[tuple],
        total: int,
        summary: BackupSummaryDTO,
    ):
        """Backup databases one by one using the shared connection."""
        self._executor.connect()
        try:
            for i, (db_name, current_stats, reason) in enumerate(dbs_to_backup):
                self._check_cancelled()
                logger.info("Backing up %s — %s.", db_name, reason)
                self._on_progress(db_name, f"Backing up ({reason})...", i, total)
                self._on_job_progress(db_name, f"Backing up ({reason})...", i, total)

                result = self._backup_single_db(
                    db_name, self._executor, self._transfer,
                    download_cb=lambda t, tot: self._on_job_download(db_name, t, tot),
                )
                self._record_result(result, db_name, current_stats, i + 1, total, summary)
        except BackupCancelled:
            logger.info("Sequential backup cancelled by user.")
            raise
        except Exception as e:
            logger.exception("Fatal error during sequential backup.")
            summary.errors.append({"db_name": "GLOBAL", "error": str(e)})
        finally:
            self._executor.disconnect()

    def _run_parallel_backup(
        self,
        dbs_to_backup: list[tuple],
        total: int,
        summary: BackupSummaryDTO,
    ):
        """Backup databases concurrently. Each thread gets its own SSH connection."""
        workers = min(self._parallel_workers, len(dbs_to_backup))
        logger.info("Starting parallel backup with %d workers for %d databases.", workers, len(dbs_to_backup))

        summary_lock = threading.Lock()

        def _backup_worker(db_name: str, current_stats, reason: str) -> tuple[str, BackupResultDTO, object]:
            """Worker function: creates its own SSH connection, runs backup, disconnects."""
            self._check_cancelled()

            executor = self._executor_factory()
            inspector = self._inspector_factory(executor) if self._inspector_factory else None
            transfer = self._transfer_factory(executor) if self._transfer_factory else executor

            self._on_job_progress(db_name, f"Connecting ({reason})...", 0, 0)
            executor.connect()
            try:
                self._check_cancelled()
                self._on_job_progress(db_name, f"Backing up ({reason})...", 0, 0)

                def _download_cb(transferred: int, total_bytes: int):
                    self._on_job_download(db_name, transferred, total_bytes)

                result = self._backup_single_db(db_name, executor, transfer, download_cb=_download_cb)
                return db_name, result, current_stats
            except BackupCancelled:
                logger.info("Worker for %s cancelled.", db_name)
                return db_name, BackupResultDTO(db_name=db_name, status="cancelled", reason="Cancelled by user"), current_stats
            except Exception as e:
                logger.exception("Worker failed for %s", db_name)
                return db_name, BackupResultDTO(db_name=db_name, status="failed", error=str(e)), current_stats
            finally:
                try:
                    executor.disconnect()
                except Exception:
                    pass

        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {}
            for db_name, current_stats, reason in dbs_to_backup:
                future = pool.submit(_backup_worker, db_name, current_stats, reason)
                futures[future] = db_name

            for future in as_completed(futures):
                try:
                    db_name, result, current_stats = future.result()
                except BackupCancelled:
                    db_name = futures[future]
                    result = BackupResultDTO(db_name=db_name, status="cancelled", reason="Cancelled by user")
                    current_stats = None
                except Exception as e:
                    db_name = futures[future]
                    result = BackupResultDTO(db_name=db_name, status="failed", error=str(e))
                    current_stats = None

                with self._processed_lock:
                    self._processed_count += 1
                    processed = self._processed_count

                with summary_lock:
                    self._record_result(result, db_name, current_stats, processed, total, summary)

                # Cancel pending futures if cancellation was requested
                if self._cancel_token and self._cancel_token.is_cancelled:
                    for f in futures:
                        f.cancel()
                    break

    def _record_result(
        self,
        result: BackupResultDTO,
        db_name: str,
        current_stats,
        processed: int,
        total: int,
        summary: BackupSummaryDTO,
    ):
        """Record a backup result into the summary and update progress."""
        summary.results.append(result.to_dict())

        if result.status in ("success", "partial"):
            summary.backed_up += 1
            if current_stats is not None:
                self._repo.save_stats(db_name, current_stats)
            size_label = self._human_size(result.backup_size + result.sql_size)
            status_label = "Done" if result.status == "success" else "Partial"
            self._on_progress(db_name, f"{status_label} ({size_label})", processed, total)
            self._on_job_progress(db_name, f"{status_label} ({size_label})", processed, total)
        elif result.status == "cancelled":
            summary.failed += 1
            self._on_progress(db_name, "Cancelled", processed, total)
            self._on_job_progress(db_name, "Cancelled", processed, total)
        else:
            summary.failed += 1
            summary.errors.append({"db_name": db_name, "error": result.error})
            self._on_progress(db_name, f"Failed: {result.error}", processed, total)
            self._on_job_progress(db_name, f"Failed: {result.error}", processed, total)

    def _backup_single_db(
        self,
        db_name: str,
        executor: RemoteExecutor,
        transfer: FileTransfer,
        download_cb: Callable[[int, int], None] | None = None,
    ) -> BackupResultDTO:
        """Generate .backup + .sql for a single database and download.

        SECURITY: db_name is validated, all shell arguments are quoted.
        Only temporary files in remote_tmp_dir are created/deleted.
        """
        validated_name = DbName(db_name)
        safe_name = validated_name.value

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        remote_dir = self._remote_tmp_dir
        local_dir = self._fs.ensure_db_directory(safe_name)

        result = BackupResultDTO(db_name=safe_name, status="failed", timestamp=timestamp)
        start = time.time()
        remote_files_created: list[str] = []

        _download_cb = download_cb or (lambda t, tot: None)

        try:
            executor.execute(f"mkdir -p {shlex.quote(remote_dir)}")

            backup_size = 0
            sql_size = 0
            local_backup = None
            local_sql = None

            formats = [BackupFormat.CUSTOM]
            if self._generate_sql:
                formats.append(BackupFormat.PLAIN)

            for fmt in formats:
                self._check_cancelled()

                filename = f"{safe_name}_{timestamp}{fmt.file_extension}"
                remote_path = f"{remote_dir}/{filename}"
                local_path = local_dir / filename
                ext = fmt.file_extension

                self._on_job_progress(safe_name, f"Generating {ext}...", 0, 0)
                logger.info("Generating %s for %s...", ext, safe_name)

                try:
                    pg_dump_cmd = (
                        f"pg_dump "
                        f"-h {shlex.quote(self._pg_host)} "
                        f"-p {shlex.quote(str(self._pg_port))} "
                        f"-U {shlex.quote(self._pg_user)} "
                        f"{fmt.pg_dump_flag} "
                        f"{shlex.quote(safe_name)}"
                    )
                    if fmt.needs_pipe_gzip:
                        inner = f"export PGPASSWORD={shlex.quote(self._pg_password)}; {pg_dump_cmd} | gzip > {shlex.quote(remote_path)}"
                    else:
                        inner = f"export PGPASSWORD={shlex.quote(self._pg_password)}; {pg_dump_cmd} -f {shlex.quote(remote_path)}"
                    # Use subshell to hide password from ps aux
                    cmd = f"bash -c {shlex.quote(inner)}"

                    remote_files_created.append(remote_path)
                    _, stderr, code = self._execute_cancellable(executor, cmd)

                    if code != 0:
                        logger.error("pg_dump %s failed for %s: %s", fmt.name, safe_name, stderr)
                        self._safe_cleanup(transfer, remote_path)
                        remote_files_created.remove(remote_path)
                        if fmt == BackupFormat.PLAIN and backup_size > 0:
                            result.error = f".sql generation failed: {stderr}"
                            continue
                        result.error = f"pg_dump {fmt.name} failed: {stderr}"
                        return result

                    self._check_cancelled()
                    remote_size = transfer.get_remote_size(remote_path)
                    self._on_job_progress(safe_name, f"Downloading {ext} ({self._human_size(remote_size)})...", 0, 0)
                    transfer.download(remote_path, local_path, progress_cb=_download_cb)
                    transfer.cleanup_remote(remote_path)
                    remote_files_created.remove(remote_path)

                    size = local_path.stat().st_size
                    if fmt == BackupFormat.CUSTOM:
                        backup_size = size
                        local_backup = str(local_path)
                    else:
                        sql_size = size
                        local_sql = str(local_path)

                except Exception as fmt_err:
                    logger.error("Failed %s for %s: %s", ext, safe_name, fmt_err)
                    if fmt == BackupFormat.PLAIN and backup_size > 0:
                        result.error = f".sql failed: {fmt_err}"
                        continue
                    raise

            duration = round(time.time() - start, 2)

            if backup_size > 0:
                # "partial" only when SQL was requested but failed
                if sql_size == 0 and self._generate_sql:
                    result.status = "partial"
                else:
                    result.status = "success"
            result.backup_file = local_backup
            result.sql_file = local_sql
            result.backup_size = backup_size
            result.sql_size = sql_size
            result.duration_seconds = duration

            logger.info(
                "%s %s (%.1fs) .backup=%s .sql=%s",
                "PARTIAL" if result.status == "partial" else "OK",
                safe_name, duration,
                self._human_size(backup_size),
                self._human_size(sql_size),
            )

        except BackupCancelled:
            result.status = "cancelled"
            result.reason = "Cancelled by user"
            result.duration_seconds = round(time.time() - start, 2)
            logger.info("Backup cancelled for %s", safe_name)
            for rpath in remote_files_created:
                self._safe_cleanup(transfer, rpath)
            raise

        except Exception as e:
            result.error = str(e)
            result.duration_seconds = round(time.time() - start, 2)
            logger.exception("Backup failed for %s", safe_name)
            for rpath in remote_files_created:
                self._safe_cleanup(transfer, rpath)

        return result

    def _execute_cancellable(
        self,
        executor: RemoteExecutor,
        command: str,
    ) -> tuple[str, str, int]:
        """Execute a remote command while polling for cancellation.

        Runs the command in a background thread and checks the cancel
        token every second. If cancelled, the SSH channel is closed
        which terminates the remote process.
        """
        if self._cancel_token is None or not self._cancel_token.is_cancelled:
            result_holder: list = []
            error_holder: list = []

            def _run():
                try:
                    result_holder.append(executor.execute(command))
                except Exception as e:
                    error_holder.append(e)

            t = threading.Thread(target=_run, daemon=True)
            t.start()

            while t.is_alive():
                t.join(timeout=1.0)
                if self._cancel_token and self._cancel_token.is_cancelled:
                    logger.info("Cancelling running remote command...")
                    # Close SSH transport to kill the remote process
                    try:
                        executor.disconnect()
                    except Exception:
                        pass
                    raise BackupCancelled("Backup cancelled by user")

            if error_holder:
                raise error_holder[0]
            if result_holder:
                return result_holder[0]

        raise BackupCancelled("Backup cancelled by user")

    @staticmethod
    def _safe_cleanup(transfer: FileTransfer, remote_path: str) -> None:
        try:
            transfer.cleanup_remote(remote_path)
        except Exception as cleanup_err:
            logger.warning("Could not clean up remote file %s: %s", remote_path, cleanup_err)

    @staticmethod
    def _human_size(n: int) -> str:
        for u in ("B", "KB", "MB", "GB"):
            if n < 1024:
                return f"{n:.1f} {u}"
            n /= 1024
        return f"{n:.1f} TB"
