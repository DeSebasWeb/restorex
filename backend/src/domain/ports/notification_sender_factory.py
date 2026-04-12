"""Port: Factory for creating notification senders.

The application layer depends on this interface, never on
concrete sender implementations (Slack, Email, Telegram).
"""

from abc import ABC, abstractmethod

from src.domain.ports.notification_sender import NotificationSender


class NotificationSenderFactory(ABC):
    """Creates NotificationSender instances from channel configuration."""

    @abstractmethod
    def create(self, channel_name: str, settings: dict) -> NotificationSender | None:
        """Build a sender for the given channel and settings.

        Returns None if the configuration is incomplete or invalid.
        """
