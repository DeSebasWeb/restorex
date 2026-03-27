"""User management service — CRUD operations with soft delete."""

import logging

import bcrypt

from src.domain.ports.auth_repository import AuthRepository
from src.domain.ports.user_repository import UserRepository

logger = logging.getLogger(__name__)


def _strip_hash(user: dict) -> dict:
    """Remove password_hash from user dict before returning to routes."""
    result = {k: v for k, v in user.items() if k != "password_hash"}
    return result


class UserService:

    def __init__(self, repository: UserRepository, auth_repository: AuthRepository):
        self._repo = repository
        self._auth_repo = auth_repository

    def list_users(self, include_deleted: bool = False) -> list[dict]:
        users = self._repo.list_users(include_deleted=include_deleted)
        return [_strip_hash(u) for u in users]

    def get_user(self, user_id: int) -> dict:
        user = self._repo.get_user_by_id(user_id)
        if not user:
            raise ValueError("User not found")
        return _strip_hash(user)

    def create_user(self, username: str, email: str | None, password: str, role_id: int) -> dict:
        if not username or not username.strip():
            raise ValueError("Username is required")
        if not password or len(password) < 8:
            raise ValueError("Password must be at least 8 characters")

        existing = self._repo.get_user_by_username(username.strip())
        if existing:
            raise ValueError("Username already exists")

        password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        user = self._repo.create_user(username.strip(), email, password_hash, role_id)
        logger.info("User '%s' created by admin", username.strip())
        return _strip_hash(user)

    def update_user(self, user_id: int, updates: dict) -> dict:
        if "username" in updates and updates["username"]:
            existing = self._repo.get_user_by_username(updates["username"].strip())
            if existing and existing["id"] != user_id:
                raise ValueError("Username already exists")

        user = self._repo.update_user(user_id, updates)
        if not user:
            raise ValueError("User not found")
        logger.info("User #%d updated", user_id)
        return _strip_hash(user)

    def soft_delete(self, user_id: int, current_user_id: int) -> None:
        if user_id == current_user_id:
            raise ValueError("Cannot delete your own account")

        success = self._repo.soft_delete(user_id)
        if not success:
            raise ValueError("User not found")

        self._auth_repo.revoke_all_user_tokens(user_id)
        logger.info("User #%d soft-deleted", user_id)

    def restore(self, user_id: int) -> dict:
        user = self._repo.restore(user_id)
        if not user:
            raise ValueError("User not found or not deleted")
        logger.info("User #%d restored", user_id)
        return _strip_hash(user)

    def admin_reset_password(self, user_id: int, new_password: str) -> None:
        if not new_password or len(new_password) < 8:
            raise ValueError("Password must be at least 8 characters")

        password_hash = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        success = self._repo.admin_reset_password(user_id, password_hash)
        if not success:
            raise ValueError("User not found")

        self._auth_repo.revoke_all_user_tokens(user_id)
        logger.info("Password reset for user #%d by admin", user_id)

    def list_roles(self) -> list[dict]:
        return self._repo.list_roles()
