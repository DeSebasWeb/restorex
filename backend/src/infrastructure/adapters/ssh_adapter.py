"""Concrete adapter: SSH-based remote executor and file transfer.

Implements both RemoteExecutor and FileTransfer ports using paramiko.
All configuration is injected via constructor — no direct Settings access.
"""

import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

import paramiko

from src.domain.ports.file_transfer import FileTransfer, ProgressCallback
from src.domain.ports.host_key_store import HostKeyStore
from src.domain.ports.remote_executor import RemoteExecutor

logger = logging.getLogger(__name__)

# Only allow cleanup of files inside the configured temp directory
_SAFE_PATH_CHARS = re.compile(r"^[a-zA-Z0-9_/.\-]+$")


@dataclass(frozen=True)
class SSHConfig:
    """Immutable SSH connection parameters — injected into SSHAdapter."""
    host: str
    port: int
    user: str
    password: str = ""
    key_path: str = ""
    remote_tmp_dir: str = "/tmp/pg_backups"


class PinnedKeyPolicy(paramiko.MissingHostKeyPolicy):
    """Trust On First Use (TOFU) with persistent fingerprint pinning.

    First connection: accepts the key and stores its fingerprint via HostKeyStore.
    Subsequent connections: rejects if the fingerprint doesn't match (MITM detection).
    """

    def __init__(self, store: HostKeyStore):
        self._store = store

    def missing_host_key(self, client, hostname, key):
        fingerprint = key.get_fingerprint().hex()
        stored = self._store.get_fingerprint(hostname)

        if stored is None:
            self._store.save_fingerprint(hostname, fingerprint)
            logger.info("SSH host key pinned for %s: %s", hostname, fingerprint)
        elif stored != fingerprint:
            raise paramiko.SSHException(
                f"SSH host key CHANGED for {hostname}! "
                f"Expected {stored}, got {fingerprint}. "
                f"Possible MITM attack. If the server was reinstalled, "
                f"clear the stored fingerprint in Settings to re-trust."
            )
        else:
            logger.debug("SSH host key verified for %s", hostname)


class SSHAdapter(RemoteExecutor, FileTransfer):
    """Single SSH connection that serves as both executor and file transfer."""

    _KNOWN_HOSTS_FILE = Path.home() / ".ssh" / "known_hosts"

    def __init__(self, config: SSHConfig, host_key_store: HostKeyStore | None = None):
        self._client: paramiko.SSHClient | None = None
        self._sftp: paramiko.SFTPClient | None = None
        self._config = config
        self._host_key_store = host_key_store

    # ── RemoteExecutor ──────────────────────────────────────────

    def connect(self) -> None:
        if self._client is not None:
            return

        self._client = paramiko.SSHClient()

        # Load system known_hosts for host key verification
        known_hosts = self._KNOWN_HOSTS_FILE
        if known_hosts.exists():
            self._client.load_host_keys(str(known_hosts))

        # TOFU: accept on first connect, reject if key changes (MITM detection).
        if self._host_key_store:
            self._client.set_missing_host_key_policy(PinnedKeyPolicy(self._host_key_store))
        else:
            self._client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        kwargs: dict = {
            "hostname": self._config.host,
            "port": self._config.port,
            "username": self._config.user,
        }

        key_path = os.path.expanduser(self._config.key_path)
        if self._config.key_path and os.path.exists(key_path):
            kwargs["key_filename"] = key_path
        elif self._config.password:
            kwargs["password"] = self._config.password
        else:
            kwargs["look_for_keys"] = True

        kwargs["timeout"] = 15
        logger.info("Connecting SSH to %s:%s...", self._config.host, self._config.port)
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

        SAFETY: Only deletes files inside the configured remote_tmp_dir.
        Rejects paths with shell metacharacters.
        """
        if not _SAFE_PATH_CHARS.match(remote_path):
            logger.error("BLOCKED: cleanup_remote refused unsafe path: %r", remote_path)
            raise ValueError(f"Unsafe remote path rejected: {remote_path!r}")

        allowed_dir = PurePosixPath(self._config.remote_tmp_dir)
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
