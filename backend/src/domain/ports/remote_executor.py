"""Port: Remote command execution interface.

Any adapter that can run commands on a remote server must implement this.
"""

from abc import ABC, abstractmethod


class RemoteExecutor(ABC):
    @abstractmethod
    def connect(self) -> None:
        """Establish connection to the remote server."""

    @abstractmethod
    def execute(self, command: str) -> tuple[str, str, int]:
        """Execute a command remotely.

        Returns:
            (stdout, stderr, exit_code)
        """

    @abstractmethod
    def disconnect(self) -> None:
        """Close the remote connection."""

    @abstractmethod
    def is_connected(self) -> bool:
        """Check if the connection is active."""
