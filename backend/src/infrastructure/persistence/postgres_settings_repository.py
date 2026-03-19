"""Concrete adapter: PostgreSQL-based settings store.

Stores app settings as key-value pairs in the app_settings table.
Replaces the old JSON file-based settings store.
"""

import logging
from datetime import datetime

from src.infrastructure.database.engine import session_scope
from src.infrastructure.database.models import AppSettingModel

logger = logging.getLogger(__name__)

CONFIGURABLE_FIELDS = {
    "SSH_HOST", "SSH_PORT", "SSH_USER", "SSH_PASSWORD", "SSH_KEY_PATH",
    "PG_HOST", "PG_PORT", "PG_USER", "PG_PASSWORD",
    "BACKUP_LOCAL_DIR", "BACKUP_REMOTE_TMP_DIR",
    "RETENTION_DAYS", "SCHEDULER_HOUR", "SCHEDULER_MINUTE",
}

SENSITIVE_FIELDS = {"SSH_PASSWORD", "PG_PASSWORD"}


class PostgresSettingsRepository:

    def load(self) -> dict:
        """Load all saved settings from the database."""
        with session_scope() as session:
            rows = session.query(AppSettingModel).all()
            return {row.key: row.value for row in rows}

    def save(self, updates: dict) -> dict:
        """Merge updates into saved settings. Only allows configurable fields."""
        with session_scope() as session:
            for key, value in updates.items():
                if key not in CONFIGURABLE_FIELDS:
                    logger.warning("Ignoring non-configurable field: %s", key)
                    continue
                if value == "*****":
                    continue

                existing = session.query(AppSettingModel).filter_by(key=key).first()
                if existing:
                    existing.value = str(value)
                    existing.updated_at = datetime.now()
                else:
                    session.add(AppSettingModel(key=key, value=str(value)))

        logger.info("Settings saved: %s", [k for k in updates if k in CONFIGURABLE_FIELDS])
        return self.load()

    def get(self, key: str, default: str = "") -> str:
        """Get a single setting value."""
        with session_scope() as session:
            row = session.query(AppSettingModel).filter_by(key=key).first()
            return row.value if row else default

    def get_all_masked(self, env_defaults: dict) -> dict:
        """Return all settings with sensitive fields masked."""
        saved = self.load()
        merged = {**env_defaults, **saved}

        result = {}
        for key, value in merged.items():
            if key in SENSITIVE_FIELDS and value:
                result[key] = "*****"
            else:
                result[key] = value

        return result
