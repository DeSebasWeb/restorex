"""Database models — each model in its own file for modularity."""

from .base import Base
from .backup_run import BackupRunModel
from .backup_result import BackupResultModel
from .db_stats import DbStatsModel
from .app_setting import AppSettingModel
from .backup_progress import BackupProgressModel
from .notification_channel import NotificationChannelModel
from .notification_setting import NotificationSettingModel
from .notification_template import NotificationTemplateModel
from .user_notification_channel import UserNotificationChannelModel
from .user_notification_setting import UserNotificationSettingModel
from .role import RoleModel
from .permission import PermissionModel
from .role_permission import role_permissions
from .user import UserModel
from .refresh_token import RefreshTokenModel

__all__ = [
    "Base",
    "BackupRunModel",
    "BackupResultModel",
    "DbStatsModel",
    "AppSettingModel",
    "BackupProgressModel",
    "NotificationChannelModel",
    "NotificationSettingModel",
    "NotificationTemplateModel",
    "UserNotificationChannelModel",
    "UserNotificationSettingModel",
    "RoleModel",
    "PermissionModel",
    "role_permissions",
    "UserModel",
    "RefreshTokenModel",
]
