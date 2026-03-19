"""Application configuration.

Priority: database (app_settings table) > .env > defaults.
The Settings class exposes class-level attributes that are refreshed
when the user saves new values from the dashboard.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Internal paths (not user-configurable)
DATA_DIR = Path(os.getenv("DATA_DIR", str(BASE_DIR / "data")))
LOG_DIR = Path(os.getenv("LOG_DIR", str(BASE_DIR / "logs")))

# Local database URL for app metadata (history, settings, stats)
LOCAL_DB_URL = os.getenv(
    "LOCAL_DB_URL",
    "postgresql://postgres:postgres@host.docker.internal:5432/pg_backup_manager"
)


def _load_db_settings() -> dict:
    """Load user-saved settings from the database (if available)."""
    try:
        from src.infrastructure.database.engine import get_engine
        if get_engine() is None:
            return {}
        from src.infrastructure.persistence.postgres_settings_repository import PostgresSettingsRepository
        return PostgresSettingsRepository().load()
    except Exception:
        return {}


def _get(key: str, default: str = "") -> str:
    """Get config value: database > .env > default."""
    saved = _load_db_settings()
    if key in saved and saved[key] not in (None, "", "*****"):
        return str(saved[key])
    return os.getenv(key, default)


class Settings:
    """Application settings. Call Settings.reload() after saving new values."""

    # PostgreSQL (remote server to backup)
    PG_HOST: str = ""
    PG_PORT: int = 5432
    PG_USER: str = ""
    PG_PASSWORD: str = ""

    # SSH
    SSH_HOST: str = ""
    SSH_PORT: int = 22
    SSH_USER: str = ""
    SSH_KEY_PATH: str = ""
    SSH_PASSWORD: str = ""

    # Backup
    BACKUP_LOCAL_DIR: Path = Path("/backups/databases")
    BACKUP_REMOTE_TMP_DIR: str = "/tmp/pg_backups"
    RETENTION_DAYS: int = 7

    # Scheduler
    SCHEDULER_HOUR: int = 23
    SCHEDULER_MINUTE: int = 0

    # System databases to always exclude
    EXCLUDED_DBS: set[str] = {"template0", "template1", "postgres"}

    # Flask
    FLASK_PORT: int = int(os.getenv("FLASK_PORT", "5000"))
    FLASK_SECRET_KEY: str = os.getenv("FLASK_SECRET_KEY", "dev-secret-change-me")

    # Internal paths
    DATA_DIR: Path = DATA_DIR
    LOG_DIR: Path = LOG_DIR
    LOCAL_DB_URL: str = LOCAL_DB_URL
    HISTORY_FILE: Path = DATA_DIR / "backup_history.json"  # Legacy, kept for migration
    STATS_FILE: Path = DATA_DIR / "db_stats.json"          # Legacy, kept for migration

    @classmethod
    def reload(cls):
        """Reload all settings from database + .env."""
        cls.PG_HOST = _get("PG_HOST", "localhost")
        cls.PG_PORT = int(_get("PG_PORT", "5432"))
        cls.PG_USER = _get("PG_USER", "postgres")
        cls.PG_PASSWORD = _get("PG_PASSWORD", "")

        cls.SSH_HOST = _get("SSH_HOST", _get("PG_HOST", "localhost"))
        cls.SSH_PORT = int(_get("SSH_PORT", "22"))
        cls.SSH_USER = _get("SSH_USER", "root")
        cls.SSH_KEY_PATH = _get("SSH_KEY_PATH", "")
        cls.SSH_PASSWORD = _get("SSH_PASSWORD", "")

        cls.BACKUP_LOCAL_DIR = Path(_get("BACKUP_LOCAL_DIR", "/backups/databases"))
        cls.BACKUP_REMOTE_TMP_DIR = _get("BACKUP_REMOTE_TMP_DIR", "/tmp/pg_backups")
        cls.RETENTION_DAYS = int(_get("RETENTION_DAYS", "7"))

        cls.SCHEDULER_HOUR = int(_get("SCHEDULER_HOUR", "23"))
        cls.SCHEDULER_MINUTE = int(_get("SCHEDULER_MINUTE", "0"))

    @classmethod
    def get_env_defaults(cls) -> dict:
        """Return current values for all configurable fields."""
        return {
            "SSH_HOST": cls.SSH_HOST,
            "SSH_PORT": cls.SSH_PORT,
            "SSH_USER": cls.SSH_USER,
            "SSH_PASSWORD": cls.SSH_PASSWORD,
            "SSH_KEY_PATH": cls.SSH_KEY_PATH,
            "PG_HOST": cls.PG_HOST,
            "PG_PORT": cls.PG_PORT,
            "PG_USER": cls.PG_USER,
            "PG_PASSWORD": cls.PG_PASSWORD,
            "BACKUP_LOCAL_DIR": str(cls.BACKUP_LOCAL_DIR),
            "BACKUP_REMOTE_TMP_DIR": cls.BACKUP_REMOTE_TMP_DIR,
            "RETENTION_DAYS": cls.RETENTION_DAYS,
            "SCHEDULER_HOUR": cls.SCHEDULER_HOUR,
            "SCHEDULER_MINUTE": cls.SCHEDULER_MINUTE,
        }

    @classmethod
    def is_configured(cls) -> bool:
        """Check if minimum required settings are present."""
        return bool(cls.SSH_HOST and cls.PG_USER and cls.PG_PASSWORD)


# Initial load from .env only (DB not ready yet at import time)
Settings.reload()
