"""PostgreSQL implementation of the auth repository."""

from datetime import datetime

from sqlalchemy.orm import joinedload

from src.domain.ports.auth_repository import AuthRepository
from src.infrastructure.database.engine import session_scope
from src.infrastructure.database.models import UserModel, RefreshTokenModel


class PostgresAuthRepository(AuthRepository):

    def _user_to_dict(self, user: UserModel) -> dict:
        return {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "password_hash": user.password_hash,
            "is_active": user.is_active,
            "force_password_change": user.force_password_change,
            "role_id": user.role_id,
            "role_name": user.role.name,
            "created_at": user.created_at.isoformat() if user.created_at else None,
        }

    def get_user_by_username(self, username: str) -> dict | None:
        with session_scope() as session:
            user = session.query(UserModel).options(joinedload(UserModel.role)).filter_by(username=username).first()
            if not user:
                return None
            return self._user_to_dict(user)

    def get_user_by_id(self, user_id: int) -> dict | None:
        with session_scope() as session:
            user = session.query(UserModel).options(joinedload(UserModel.role)).filter_by(id=user_id).first()
            if not user:
                return None
            return self._user_to_dict(user)

    def update_password(self, user_id: int, password_hash: str) -> None:
        with session_scope() as session:
            user = session.query(UserModel).filter_by(id=user_id).first()
            if user:
                user.password_hash = password_hash
                user.force_password_change = False

    def save_refresh_token(self, user_id: int, token_hash: str, expires_at: datetime) -> None:
        with session_scope() as session:
            token = RefreshTokenModel(
                user_id=user_id,
                token_hash=token_hash,
                expires_at=expires_at,
            )
            session.add(token)

    def get_refresh_token(self, token_hash: str) -> dict | None:
        with session_scope() as session:
            token = (
                session.query(RefreshTokenModel)
                .filter_by(token_hash=token_hash, revoked=False)
                .first()
            )
            if not token or token.expires_at < datetime.now():
                return None
            return {
                "id": token.id,
                "user_id": token.user_id,
                "token_hash": token.token_hash,
                "expires_at": token.expires_at,
            }

    def revoke_refresh_token(self, token_hash: str) -> None:
        with session_scope() as session:
            token = session.query(RefreshTokenModel).filter_by(token_hash=token_hash).first()
            if token:
                token.revoked = True

    def revoke_all_user_tokens(self, user_id: int) -> None:
        with session_scope() as session:
            session.query(RefreshTokenModel).filter_by(
                user_id=user_id, revoked=False
            ).update({"revoked": True})
