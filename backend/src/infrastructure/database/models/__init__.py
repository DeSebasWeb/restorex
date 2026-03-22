"""Database models — each model in its own file for modularity."""

from .base import Base
from .backup_run import BackupRunModel
from .backup_result import BackupResultModel
from .db_stats import DbStatsModel
from .app_setting import AppSettingModel
from .backup_progress import BackupProgressModel
from .notification_channel import NotificationChannelModel
from .notification_setting import NotificationSettingModel

__all__ = [
    "Base",
    "BackupRunModel",
    "BackupResultModel",
    "DbStatsModel",
    "AppSettingModel",
    "BackupProgressModel",
    "NotificationChannelModel",
    "NotificationSettingModel",
]
