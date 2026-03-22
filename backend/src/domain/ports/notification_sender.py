"""Port: Notification delivery interface."""

from abc import ABC, abstractmethod


class NotificationSender(ABC):
    """Sends notifications through a specific channel (Slack, Email, Telegram)."""

    @abstractmethod
    def send(self, subject: str, body: str, is_error: bool = False) -> bool:
        """Send a notification. Returns True if delivered successfully."""

    @abstractmethod
    def test(self) -> tuple[bool, str]:
        """Test the connection. Returns (success, message)."""

    @property
    @abstractmethod
    def channel_name(self) -> str:
        """Human-readable channel name (e.g., 'Slack', 'Email', 'Telegram')."""
