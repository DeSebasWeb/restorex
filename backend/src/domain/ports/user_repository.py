"""Port (interface) for user management persistence."""

from abc import ABC, abstractmethod


class UserRepository(ABC):

    @abstractmethod
    def list_users(self, include_deleted: bool = False) -> list[dict]:
        """Return all users. If include_deleted, include soft-deleted users."""

    @abstractmethod
    def get_user_by_id(self, user_id: int) -> dict | None:
        """Return active (non-deleted) user by ID, or None."""

    @abstractmethod
    def get_user_by_username(self, username: str) -> dict | None:
        """Return active (non-deleted) user by username, or None."""

    @abstractmethod
    def create_user(self, username: str, email: str | None, password_hash: str, role_id: int) -> dict:
        """Create a new user and return its dict."""

    @abstractmethod
    def update_user(self, user_id: int, updates: dict) -> dict | None:
        """Update allowed fields on an active user. Returns updated dict or None."""

    @abstractmethod
    def soft_delete(self, user_id: int) -> bool:
        """Set deleted_at on the user. Returns True if found and deleted."""

    @abstractmethod
    def restore(self, user_id: int) -> dict | None:
        """Clear deleted_at. Returns restored user dict or None."""

    @abstractmethod
    def admin_reset_password(self, user_id: int, password_hash: str) -> bool:
        """Update password and set force_password_change=True. Returns True if found."""

    @abstractmethod
    def list_roles(self) -> list[dict]:
        """Return all available roles."""
