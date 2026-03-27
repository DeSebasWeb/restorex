"""PostgreSQL implementation of the user management repository."""

from datetime import datetime

from sqlalchemy.orm import joinedload

from src.domain.ports.user_repository import UserRepository
from src.infrastructure.database.engine import session_scope
from src.infrastructure.database.models import UserModel, RoleModel


class PostgresUserRepository(UserRepository):

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
            "updated_at": user.updated_at.isoformat() if user.updated_at else None,
            "deleted_at": user.deleted_at.isoformat() if user.deleted_at else None,
        }

    def list_users(self, include_deleted: bool = False) -> list[dict]:
        with session_scope() as session:
            query = session.query(UserModel).options(joinedload(UserModel.role))
            if not include_deleted:
                query = query.filter(UserModel.deleted_at.is_(None))
            users = query.order_by(UserModel.id).all()
            return [self._user_to_dict(u) for u in users]

    def get_user_by_id(self, user_id: int) -> dict | None:
        with session_scope() as session:
            user = (session.query(UserModel).options(joinedload(UserModel.role))
                    .filter_by(id=user_id).filter(UserModel.deleted_at.is_(None)).first())
            return self._user_to_dict(user) if user else None

    def get_user_by_username(self, username: str) -> dict | None:
        with session_scope() as session:
            user = (session.query(UserModel).options(joinedload(UserModel.role))
                    .filter_by(username=username).filter(UserModel.deleted_at.is_(None)).first())
            return self._user_to_dict(user) if user else None

    def create_user(self, username: str, email: str | None, password_hash: str, role_id: int) -> dict:
        with session_scope() as session:
            user = UserModel(
                username=username,
                email=email or None,
                password_hash=password_hash,
                role_id=role_id,
                is_active=True,
                force_password_change=True,
            )
            session.add(user)
            session.flush()
            # Reload with role relationship
            session.refresh(user)
            user.role  # trigger load
            return self._user_to_dict(user)

    def update_user(self, user_id: int, updates: dict) -> dict | None:
        allowed = {"username", "email", "role_id", "is_active"}
        with session_scope() as session:
            user = (session.query(UserModel).options(joinedload(UserModel.role))
                    .filter_by(id=user_id).filter(UserModel.deleted_at.is_(None)).first())
            if not user:
                return None
            for key, value in updates.items():
                if key in allowed:
                    setattr(user, key, value)
            session.flush()
            session.refresh(user)
            return self._user_to_dict(user)

    def soft_delete(self, user_id: int) -> bool:
        with session_scope() as session:
            user = (session.query(UserModel)
                    .filter_by(id=user_id).filter(UserModel.deleted_at.is_(None)).first())
            if not user:
                return False
            user.deleted_at = datetime.now()
            return True

    def restore(self, user_id: int) -> dict | None:
        with session_scope() as session:
            user = (session.query(UserModel).options(joinedload(UserModel.role))
                    .filter_by(id=user_id).filter(UserModel.deleted_at.isnot(None)).first())
            if not user:
                return None
            user.deleted_at = None
            session.flush()
            session.refresh(user)
            return self._user_to_dict(user)

    def admin_reset_password(self, user_id: int, password_hash: str) -> bool:
        with session_scope() as session:
            user = (session.query(UserModel)
                    .filter_by(id=user_id).filter(UserModel.deleted_at.is_(None)).first())
            if not user:
                return False
            user.password_hash = password_hash
            user.force_password_change = True
            return True

    def list_roles(self) -> list[dict]:
        with session_scope() as session:
            roles = session.query(RoleModel).order_by(RoleModel.id).all()
            return [{"id": r.id, "name": r.name, "description": r.description} for r in roles]
