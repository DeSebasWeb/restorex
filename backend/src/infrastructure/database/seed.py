"""Seed auth data — creates default roles, permissions, and admin user.

Idempotent: safe to call on every startup. Uses check-before-insert
so existing data is never duplicated or overwritten.
"""

import logging

import bcrypt

from src.infrastructure.database.engine import session_scope
from src.infrastructure.database.models import (
    RoleModel,
    PermissionModel,
    UserModel,
    role_permissions,
)

logger = logging.getLogger(__name__)

# ── Role definitions ──────────────────────────────────────────────

ROLES = [
    {"name": "admin", "description": "Full access — users, settings, backups, everything"},
    {"name": "operator", "description": "Run backups, scan databases, view dashboards"},
    {"name": "viewer", "description": "Read-only — view status, history, logs, reports"},
]

# ── Permission definitions (resource:action) ─────────────────────

PERMISSIONS = [
    # Settings & storage (admin only)
    {"name": "settings:read", "resource": "settings", "action": "read"},
    {"name": "settings:write", "resource": "settings", "action": "write"},
    {"name": "storage:read", "resource": "storage", "action": "read"},
    {"name": "storage:write", "resource": "storage", "action": "write"},
    # Notifications (admin only)
    {"name": "notifications:read", "resource": "notifications", "action": "read"},
    {"name": "notifications:write", "resource": "notifications", "action": "write"},
    {"name": "notifications:test", "resource": "notifications", "action": "test"},
    # Backup operations (operator+)
    {"name": "backup:run", "resource": "backup", "action": "run"},
    {"name": "scan:run", "resource": "scan", "action": "run"},
    # Read-only (viewer+)
    {"name": "status:read", "resource": "status", "action": "read"},
    {"name": "history:read", "resource": "history", "action": "read"},
    {"name": "backup_status:read", "resource": "backup_status", "action": "read"},
    {"name": "report:read", "resource": "report", "action": "read"},
    {"name": "logs:read", "resource": "logs", "action": "read"},
    # User management (admin only)
    {"name": "users:read", "resource": "users", "action": "read"},
    {"name": "users:write", "resource": "users", "action": "write"},
]

# ── Role → permission mapping ────────────────────────────────────

ROLE_PERMISSIONS = {
    "admin": [p["name"] for p in PERMISSIONS],  # All permissions
    "operator": [
        "backup:run", "scan:run",
        "status:read", "history:read", "backup_status:read",
        "report:read", "logs:read",
    ],
    "viewer": [
        "status:read", "history:read", "backup_status:read",
        "report:read", "logs:read",
    ],
}

# ── Default admin ─────────────────────────────────────────────────

DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_PASSWORD = "admin123"


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def seed_auth_data() -> None:
    """Create default roles, permissions, and admin user if they don't exist."""
    with session_scope() as session:
        # 1. Roles
        existing_roles = {r.name: r for r in session.query(RoleModel).all()}
        for role_def in ROLES:
            if role_def["name"] not in existing_roles:
                role = RoleModel(**role_def)
                session.add(role)
                logger.info("Created role: %s", role_def["name"])
        session.flush()

        # Re-fetch after flush
        roles_by_name = {r.name: r for r in session.query(RoleModel).all()}

        # 2. Permissions
        existing_perms = {p.name: p for p in session.query(PermissionModel).all()}
        for perm_def in PERMISSIONS:
            if perm_def["name"] not in existing_perms:
                perm = PermissionModel(**perm_def)
                session.add(perm)
                logger.info("Created permission: %s", perm_def["name"])
        session.flush()

        perms_by_name = {p.name: p for p in session.query(PermissionModel).all()}

        # 3. Role-permission assignments
        from sqlalchemy import select
        existing_rp = set(session.execute(select(role_permissions)).fetchall())

        for role_name, perm_names in ROLE_PERMISSIONS.items():
            role = roles_by_name.get(role_name)
            if not role:
                continue
            for perm_name in perm_names:
                perm = perms_by_name.get(perm_name)
                if not perm:
                    continue
                if (role.id, perm.id) not in existing_rp:
                    session.execute(
                        role_permissions.insert().values(role_id=role.id, permission_id=perm.id)
                    )

        # 4. Default admin user
        admin_exists = session.query(UserModel).filter_by(username=DEFAULT_ADMIN_USERNAME).first()
        if not admin_exists:
            admin_role = roles_by_name.get("admin")
            if admin_role:
                admin_user = UserModel(
                    username=DEFAULT_ADMIN_USERNAME,
                    password_hash=_hash_password(DEFAULT_ADMIN_PASSWORD),
                    is_active=True,
                    force_password_change=True,
                    role_id=admin_role.id,
                )
                session.add(admin_user)
                logger.info("Created default admin user (username: %s) — must change password on first login",
                            DEFAULT_ADMIN_USERNAME)

    logger.info("Auth seed data verified.")
