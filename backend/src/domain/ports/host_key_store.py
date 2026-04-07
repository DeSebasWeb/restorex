"""Port: SSH host key fingerprint storage for TOFU verification."""

from abc import ABC, abstractmethod


class HostKeyStore(ABC):

    @abstractmethod
    def get_fingerprint(self, hostname: str) -> str | None:
        """Return the stored fingerprint for a hostname, or None if not pinned."""

    @abstractmethod
    def save_fingerprint(self, hostname: str, fingerprint: str) -> None:
        """Store (or update) the fingerprint for a hostname."""
