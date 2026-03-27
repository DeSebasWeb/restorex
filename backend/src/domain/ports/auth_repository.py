"""Port (interface) for authentication persistence."""

from abc import ABC, abstractmethod
from datetime import datetime


class AuthRepository(ABC):

    @abstractmethod
    def get_user_by_username(self, username: str) -> dict | None:
        """Return user dict with role info, or None."""

    @abstractmethod
    def get_user_by_id(self, user_id: int) -> dict | None:
        """Return user dict with role info, or None."""

    @abstractmethod
    def update_password(self, user_id: int, password_hash: str) -> None:
        """Update user password hash and clear force_password_change flag."""

    @abstractmethod
    def save_refresh_token(self, user_id: int, token_hash: str, expires_at: datetime) -> None:
        """Persist a hashed refresh token."""

    @abstractmethod
    def get_refresh_token(self, token_hash: str) -> dict | None:
        """Return valid (non-revoked, non-expired) refresh token info, or None."""

    @abstractmethod
    def revoke_refresh_token(self, token_hash: str) -> None:
        """Mark a refresh token as revoked."""

    @abstractmethod
    def revoke_all_user_tokens(self, user_id: int) -> None:
        """Revoke all refresh tokens for a user (e.g. on password change)."""
