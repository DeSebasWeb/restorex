"""Authentication and authorization service.

Handles login, JWT creation/verification, refresh token rotation,
and password changes. Uses bcrypt for hashing and PyJWT for tokens.
"""

import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from src.domain.ports.auth_repository import AuthRepository

logger = logging.getLogger(__name__)


class AuthService:

    def __init__(
        self,
        repository: AuthRepository,
        jwt_secret: str,
        access_token_minutes: int = 15,
        refresh_token_days: int = 2,
    ):
        self._repo = repository
        self._jwt_secret = jwt_secret
        self._access_minutes = access_token_minutes
        self._refresh_days = refresh_token_days

    @property
    def refresh_token_days(self) -> int:
        return self._refresh_days

    def get_user(self, user_id: int) -> dict | None:
        """Get user info by ID."""
        return self._repo.get_user_by_id(user_id)

    # ── Authentication ────────────────────────────────────────────

    def authenticate(self, username: str, password: str) -> dict:
        """Validate credentials. Returns user dict or raises ValueError."""
        user = self._repo.get_user_by_username(username)
        if not user:
            raise ValueError("Invalid username or password")

        if not bcrypt.checkpw(password.encode("utf-8"), user["password_hash"].encode("utf-8")):
            raise ValueError("Invalid username or password")

        if not user["is_active"]:
            raise ValueError("Account is disabled")

        logger.info("User '%s' authenticated successfully", username)
        return user

    # ── Access Token (JWT) ────────────────────────────────────────

    def create_access_token(self, user_id: int, role: str) -> str:
        """Create a short-lived JWT access token."""
        payload = {
            "sub": str(user_id),
            "role": role,
            "exp": datetime.now(timezone.utc) + timedelta(minutes=self._access_minutes),
            "iat": datetime.now(timezone.utc),
        }
        return jwt.encode(payload, self._jwt_secret, algorithm="HS256")

    def verify_access_token(self, token: str) -> dict:
        """Decode and verify a JWT. Returns payload dict with sub as int."""
        payload = jwt.decode(token, self._jwt_secret, algorithms=["HS256"])
        payload["sub"] = int(payload["sub"])
        return payload

    # ── Refresh Token ─────────────────────────────────────────────

    @staticmethod
    def _hash_token(raw_token: str) -> str:
        """SHA-256 hash of the raw refresh token for storage."""
        return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

    def create_refresh_token(self, user_id: int) -> str:
        """Generate an opaque refresh token, store its hash, return the raw token."""
        raw_token = secrets.token_urlsafe(48)
        token_hash = self._hash_token(raw_token)
        expires_at = datetime.now() + timedelta(days=self._refresh_days)
        self._repo.save_refresh_token(user_id, token_hash, expires_at)
        return raw_token

    def refresh_access_token(self, raw_refresh_token: str) -> tuple[str, str]:
        """Validate refresh token, rotate it, return (new_access_token, new_refresh_token).

        Raises ValueError if the token is invalid, expired, or revoked.
        """
        token_hash = self._hash_token(raw_refresh_token)
        stored = self._repo.get_refresh_token(token_hash)

        if not stored:
            raise ValueError("Invalid or expired refresh token")

        # Rotate: revoke old, create new
        self._repo.revoke_refresh_token(token_hash)
        user = self._repo.get_user_by_id(stored["user_id"])
        if not user or not user["is_active"]:
            raise ValueError("User not found or disabled")

        new_refresh = self.create_refresh_token(user["id"])
        new_access = self.create_access_token(user["id"], user["role_name"])

        return new_access, new_refresh

    def revoke_refresh_token(self, raw_refresh_token: str) -> None:
        """Revoke a specific refresh token (logout)."""
        token_hash = self._hash_token(raw_refresh_token)
        self._repo.revoke_refresh_token(token_hash)

    # ── Password Change ───────────────────────────────────────────

    def change_password(self, user_id: int, current_password: str, new_password: str) -> dict:
        """Verify current password, set new one, revoke all refresh tokens.

        Returns the updated user dict.
        """
        user = self._repo.get_user_by_id(user_id)
        if not user:
            raise ValueError("User not found")

        if not bcrypt.checkpw(current_password.encode("utf-8"), user["password_hash"].encode("utf-8")):
            raise ValueError("Current password is incorrect")

        if len(new_password) < 8:
            raise ValueError("New password must be at least 8 characters")

        new_hash = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        self._repo.update_password(user_id, new_hash)
        self._repo.revoke_all_user_tokens(user_id)

        logger.info("User '%s' changed password", user["username"])

        # Return updated user
        return self._repo.get_user_by_id(user_id)
