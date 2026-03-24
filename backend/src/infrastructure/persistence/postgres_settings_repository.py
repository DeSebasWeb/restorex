"""Concrete adapter: PostgreSQL-based settings store.

Stores app settings as key-value pairs in the app_settings table.
Sensitive fields (passwords) are encrypted at rest using Fernet.
"""

import logging
from datetime import datetime

from src.infrastructure.database.engine import session_scope
from src.infrastructure.database.models import AppSettingModel
from src.infrastructure.security.encryption import encrypt, decrypt, is_encrypted

logger = logging.getLogger(__name__)

CONFIGURABLE_FIELDS = {
    "SSH_HOST", "SSH_PORT", "SSH_USER", "SSH_PASSWORD", "SSH_KEY_PATH",
    "PG_HOST", "PG_PORT", "PG_USER", "PG_PASSWORD",
    "BACKUP_LOCAL_DIR", "BACKUP_REMOTE_TMP_DIR",
    "RETENTION_DAYS", "SCHEDULER_HOUR", "SCHEDULER_MINUTE",
    "GENERATE_SQL", "PARALLEL_WORKERS",
}

SENSITIVE_FIELDS = {"SSH_PASSWORD", "PG_PASSWORD"}


class PostgresSettingsRepository:

    def load(self) -> dict:
        """Load all saved settings, decrypting sensitive fields."""
        with session_scope() as session:
            rows = session.query(AppSettingModel).all()
            result = {}
            for row in rows:
                if row.key in SENSITIVE_FIELDS and is_encrypted(row.value):
                    result[row.key] = decrypt(row.value)
                else:
                    result[row.key] = row.value
            return result

    def save(self, updates: dict) -> dict:
        """Merge updates into saved settings. Encrypts sensitive fields."""
        with session_scope() as session:
            for key, value in updates.items():
                if key not in CONFIGURABLE_FIELDS:
                    continue
                if value == "*****":
                    continue

                # Encrypt sensitive values before storage
                stored_value = encrypt(str(value)) if key in SENSITIVE_FIELDS else str(value)

                existing = session.query(AppSettingModel).filter_by(key=key).first()
                if existing:
                    existing.value = stored_value
                    existing.updated_at = datetime.now()
                else:
                    session.add(AppSettingModel(key=key, value=stored_value))

        logger.info("Settings saved: %s (sensitive fields encrypted)", [k for k in updates if k in CONFIGURABLE_FIELDS])
        return self.load()

    def get(self, key: str, default: str = "") -> str:
        """Get a single setting value, decrypting if sensitive."""
        with session_scope() as session:
            row = session.query(AppSettingModel).filter_by(key=key).first()
            if not row:
                return default
            if key in SENSITIVE_FIELDS and is_encrypted(row.value):
                return decrypt(row.value)
            return row.value

    def get_all_masked(self, env_defaults: dict) -> dict:
        """Return all settings with sensitive fields masked (for API responses)."""
        saved = self.load()
        merged = {**env_defaults, **saved}

        result = {}
        for key, value in merged.items():
            if key in SENSITIVE_FIELDS and value:
                result[key] = "*****"
            else:
                result[key] = value

        return result
