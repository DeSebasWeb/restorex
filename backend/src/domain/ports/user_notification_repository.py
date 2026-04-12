"""Port: Per-user notification channel persistence."""

from abc import ABC, abstractmethod


class UserNotificationRepository(ABC):
    """CRUD for user-specific notification channel configurations."""

    @abstractmethod
    def get_user_channels(self, user_id: int) -> list[dict]:
        """Return all channels for a user with decrypted settings."""

    @abstractmethod
    def get_user_channels_masked(self, user_id: int) -> list[dict]:
        """Return all channels for a user with sensitive values masked."""

    @abstractmethod
    def get_user_enabled_channels(self, user_id: int) -> list[dict]:
        """Return only enabled channels for a user with decrypted settings."""

    @abstractmethod
    def save_user_channel(self, user_id: int, channel_name: str, data: dict) -> None:
        """Create or update a channel config for a user."""

    @abstractmethod
    def get_all_users_enabled_channels(self) -> list[dict]:
        """Return enabled channels across ALL users (for broadcast notifications).

        Each dict includes 'user_id' to identify the owner.
        """
