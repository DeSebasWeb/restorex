"""Concrete adapter: SSH-based remote executor and file transfer.

Implements both RemoteExecutor and FileTransfer ports using paramiko.
"""

import logging
import os
import re
from pathlib import Path, PurePosixPath

import paramiko

from src.domain.ports.file_transfer import FileTransfer, ProgressCallback
from src.domain.ports.remote_executor import RemoteExecutor
from src.infrastructure.config import Settings

logger = logging.getLogger(__name__)

# Only allow cleanup of files inside the configured temp directory
_SAFE_PATH_CHARS = re.compile(r"^[a-zA-Z0-9_/.\-]+$")


class SSHAdapter(RemoteExecutor, FileTransfer):
    """Single SSH connection that serves as both executor and file transfer."""

    _KNOWN_HOSTS_FILE = Path.home() / ".ssh" / "known_hosts"

    def __init__(self):
        self._client: paramiko.SSHClient | None = None
        self._sftp: paramiko.SFTPClient | None = None

    # ── RemoteExecutor ──────────────────────────────────────────

    def connect(self) -> None:
        if self._client is not None:
            return

        self._client = paramiko.SSHClient()

        # Load system known_hosts for host key verification
        known_hosts = self._KNOWN_HOSTS_FILE
        if known_hosts.exists():
            self._client.load_host_keys(str(known_hosts))

        # AutoAddPolicy saves new host keys to known_hosts on first connect.
        # After the first connection, the host key is pinned and future
        # connections will reject if the key changes (MITM detection).
        self._client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        kwargs: dict = {
            "hostname": Settings.SSH_HOST,
            "port": Settings.SSH_PORT,
            "username": Settings.SSH_USER,
        }

        key_path = os.path.expanduser(Settings.SSH_KEY_PATH)
        if Settings.SSH_KEY_PATH and os.path.exists(key_path):
            kwargs["key_filename"] = key_path
        elif Settings.SSH_PASSWORD:
            kwargs["password"] = Settings.SSH_PASSWORD
        else:
            kwargs["look_for_keys"] = True

        kwargs["timeout"] = 15  # 15 second connection timeout
        logger.info("Connecting SSH to %s:%s...", Settings.SSH_HOST, Settings.SSH_PORT)
        self._client.connect(**kwargs)

        # Keep connection alive during long pg_dump operations (every 30s)
        transport = self._client.get_transport()
        if transport:
            transport.set_keepalive(30)

        # Save host key to known_hosts for future MITM detection
        try:
            known_hosts = self._KNOWN_HOSTS_FILE
            known_hosts.parent.mkdir(parents=True, exist_ok=True)
            self._client.save_host_keys(str(known_hosts))
        except Exception as e:
            logger.warning("Could not save host keys: %s", e)

        self._sftp = self._client.open_sftp()
        # Set SFTP channel timeout to None (unlimited) for large file transfers
        self._sftp.get_channel().settimeout(None)
        logger.info("SSH connected.")

    def execute(self, command: str) -> tuple[str, str, int]:
        if self._client is None:
            raise RuntimeError("SSH not connected. Call connect() first.")

        stdin, stdout, stderr = self._client.exec_command(command)
        exit_code = stdout.channel.recv_exit_status()
        return (
            stdout.read().decode().strip(),
            stderr.read().decode().strip(),
            exit_code,
        )

    def disconnect(self) -> None:
        if self._sftp:
            self._sftp.close()
            self._sftp = None
        if self._client:
            self._client.close()
            self._client = None
        logger.info("SSH disconnected.")

    def is_connected(self) -> bool:
        if self._client is None:
            return False
        transport = self._client.get_transport()
        return transport is not None and transport.is_active()

    # ── FileTransfer ────────────────────────────────────────────

    def download(self, remote_path: str, local_path: Path, progress_cb: ProgressCallback = None) -> None:
        if self._sftp is None:
            raise RuntimeError("SFTP not available. Call connect() first.")

        local_path.parent.mkdir(parents=True, exist_ok=True)
        self._sftp.get(remote_path, str(local_path), callback=progress_cb)
        logger.info("Downloaded %s → %s", remote_path, local_path)

    def get_remote_size(self, remote_path: str) -> int:
        if self._sftp is None:
            raise RuntimeError("SFTP not available. Call connect() first.")
        return self._sftp.stat(remote_path).st_size or 0

    def cleanup_remote(self, remote_path: str) -> None:
        """Delete a temporary backup file on the remote server.

        SAFETY: Only deletes files inside BACKUP_REMOTE_TMP_DIR.
        Rejects paths with shell metacharacters.
        """
        # Validate path characters (no semicolons, pipes, backticks, etc.)
        if not _SAFE_PATH_CHARS.match(remote_path):
            logger.error("BLOCKED: cleanup_remote refused unsafe path: %r", remote_path)
            raise ValueError(f"Unsafe remote path rejected: {remote_path!r}")

        # Resolve and verify the file is inside the allowed temp directory
        allowed_dir = PurePosixPath(Settings.BACKUP_REMOTE_TMP_DIR)
        resolved = PurePosixPath(remote_path)

        if not str(resolved).startswith(str(allowed_dir) + "/"):
            logger.error(
                "BLOCKED: cleanup_remote path %r is outside allowed dir %s",
                remote_path, allowed_dir,
            )
            raise ValueError(
                f"Refusing to delete {remote_path!r}: "
                f"not inside {allowed_dir}"
            )

        # Use SFTP remove (not shell rm) — no injection possible
        if self._sftp is None:
            raise RuntimeError("SFTP not available. Call connect() first.")

        self._sftp.remove(remote_path)
        logger.info("Cleaned up remote temp file: %s", remote_path)

    # ── Context manager ─────────────────────────────────────────

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
        return False
