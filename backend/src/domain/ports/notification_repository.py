"""Port: Global notification channel persistence."""

from abc import ABC, abstractmethod


class NotificationRepository(ABC):
    """CRUD operations for global notification channel configurations."""

    @abstractmethod
    def get_all_channels(self) -> list[dict]:
        """Return all channels with decrypted settings."""

    @abstractmethod
    def get_all_channels_masked(self) -> list[dict]:
        """Return all channels with sensitive values masked (for API responses)."""

    @abstractmethod
    def get_channel(self, channel_name: str) -> dict | None:
        """Return a single channel config with decrypted settings."""

    @abstractmethod
    def get_enabled_channels(self) -> list[dict]:
        """Return only enabled channels with decrypted settings."""

    @abstractmethod
    def save_channel(self, channel_name: str, data: dict) -> None:
        """Create or update a channel configuration."""
