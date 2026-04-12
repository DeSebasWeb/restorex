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
    NotificationTemplateModel,
    NotificationChannelModel,
    NotificationSettingModel,
    UserNotificationChannelModel,
    UserNotificationSettingModel,
    AppSettingModel,
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

    # 5. Default notification templates
    _seed_notification_templates()

    # 6. Migrate global notifications to admin (one-time)
    _migrate_global_notifications_to_admin()

    # 7. Seed default notification policy
    _seed_notification_policy()


# ── Notification templates ────────────────────────────────────────

DEFAULT_TEMPLATES = [
    (
        "backup_success",
        "Backup Complete — {backed_up} backed up, {skipped} skipped",
        "Databases:  {total_dbs}\nBacked up:  {backed_up}\nSkipped:    {skipped}\nFailed:     {failed}\nStarted:    {started_at}\nFinished:   {finished_at}",
    ),
    (
        "backup_failure",
        "Backup Failed — {failed} database(s) failed out of {total_dbs}",
        "Databases:  {total_dbs}\nBacked up:  {backed_up}\nSkipped:    {skipped}\nFailed:     {failed}\nStarted:    {started_at}\nFinished:   {finished_at}\n\nErrors:\n{errors}",
    ),
    (
        "backup_partial",
        "Backup Partial — {backed_up} OK, {failed} failed",
        "Databases:  {total_dbs}\nBacked up:  {backed_up}\nSkipped:    {skipped}\nFailed:     {failed}\nStarted:    {started_at}\nFinished:   {finished_at}\n\nErrors:\n{errors}",
    ),
    (
        "backup_cancelled",
        "Backup Cancelled",
        "The backup was cancelled by user.\nStarted:  {started_at}\nStopped:  {finished_at}",
    ),
    (
        "rotation",
        "Retention Applied",
        "{message}",
    ),
    (
        "manual_start",
        "Manual Backup Started",
        "{message}",
    ),
    (
        "scheduled_start",
        "Scheduled Backup Started",
        "{message}",
    ),
]


def _seed_notification_templates() -> None:
    """Create default system notification templates if they don't exist."""
    with session_scope() as session:
        existing = {
            t.event_type
            for t in session.query(NotificationTemplateModel)
            .filter(NotificationTemplateModel.is_system == True)
            .all()
        }

        for event_type, subject, body in DEFAULT_TEMPLATES:
            if event_type not in existing:
                session.add(NotificationTemplateModel(
                    user_id=None,
                    event_type=event_type,
                    subject_template=subject,
                    body_template=body,
                    is_system=True,
                ))
                logger.info("Created system notification template: %s", event_type)

    logger.info("Notification templates verified.")


def _migrate_global_notifications_to_admin() -> None:
    """One-time migration: copy global notification channels to the admin user.

    After migration, removes the global channels so only per-user config exists.
    Idempotent: skips if admin already has per-user channels or no global channels exist.
    """
    with session_scope() as session:
        # Find admin user
        admin = session.query(UserModel).filter_by(username="admin").first()
        if not admin:
            return

        # Check if admin already has per-user channels (already migrated)
        existing = (
            session.query(UserNotificationChannelModel)
            .filter(UserNotificationChannelModel.user_id == admin.id)
            .count()
        )
        if existing > 0:
            return  # Already migrated

        # Get global channels
        global_channels = session.query(NotificationChannelModel).all()
        if not global_channels:
            return

        migrated = 0
        for gch in global_channels:
            # Create per-user channel for admin
            user_ch = UserNotificationChannelModel(
                user_id=admin.id,
                channel=gch.channel,
                enabled=gch.enabled,
                on_success=gch.on_success,
                on_failure=gch.on_failure,
                on_partial=gch.on_partial,
            )
            session.add(user_ch)
            session.flush()

            # Copy settings (already encrypted — copy as-is)
            for gs in gch.settings:
                session.add(UserNotificationSettingModel(
                    user_channel_id=user_ch.id,
                    key=gs.key,
                    value=gs.value,  # Already encrypted, no need to re-encrypt
                ))

            migrated += 1

        # Remove global channels (migration complete)
        for gch in global_channels:
            session.delete(gch)

        if migrated:
            logger.info("Migrated %d global notification channel(s) to admin user.", migrated)


def _seed_notification_policy() -> None:
    """Seed the default notification inheritance policy setting."""
    with session_scope() as session:
        existing = (
            session.query(AppSettingModel)
            .filter(AppSettingModel.key == "NOTIFICATION_INHERIT_GLOBAL")
            .first()
        )
        if not existing:
            session.add(AppSettingModel(
                key="NOTIFICATION_INHERIT_GLOBAL",
                value="true",
            ))
            logger.info("Created notification inheritance policy setting (default: on).")
