"""Persistence for notification channel configurations.

Sensitive fields (tokens, passwords, webhook URLs) are encrypted at rest
using Fernet (AES-128-CBC + HMAC-SHA256).
"""

import logging
from datetime import datetime

from src.infrastructure.database.engine import session_scope
from src.infrastructure.database.models import NotificationChannelModel, NotificationSettingModel
from src.infrastructure.security.encryption import encrypt, decrypt, is_encrypted

logger = logging.getLogger(__name__)

# Fields that contain sensitive data — encrypted at rest, masked in API responses
_SENSITIVE_KEYS = {"webhook_url", "bot_token", "smtp_password"}


class NotificationRepository:
    """CRUD operations for notification channel configs with encryption."""

    def _decrypt_settings(self, settings_rows) -> dict:
        """Read settings from DB, decrypting sensitive values."""
        result = {}
        for s in settings_rows:
            if s.key in _SENSITIVE_KEYS and is_encrypted(s.value):
                result[s.key] = decrypt(s.value)
            else:
                result[s.key] = s.value
        return result

    def get_all_channels(self) -> list[dict]:
        """Return all channels with decrypted settings."""
        with session_scope() as session:
            channels = session.query(NotificationChannelModel).all()
            result = []
            for ch in channels:
                result.append({
                    "channel": ch.channel,
                    "enabled": ch.enabled,
                    "on_success": ch.on_success,
                    "on_failure": ch.on_failure,
                    "on_partial": ch.on_partial,
                    "settings": self._decrypt_settings(ch.settings),
                })
            return result

    def get_all_channels_masked(self) -> list[dict]:
        """Return all channels with sensitive values masked (for API responses)."""
        with session_scope() as session:
            channels = session.query(NotificationChannelModel).all()
            result = []
            for ch in channels:
                settings = {}
                for s in ch.settings:
                    if s.key in _SENSITIVE_KEYS and s.value:
                        settings[s.key] = "*****"
                    else:
                        settings[s.key] = s.value
                result.append({
                    "channel": ch.channel,
                    "enabled": ch.enabled,
                    "on_success": ch.on_success,
                    "on_failure": ch.on_failure,
                    "on_partial": ch.on_partial,
                    "settings": settings,
                })
            return result

    def get_channel(self, channel_name: str) -> dict | None:
        """Return a single channel config with decrypted settings."""
        with session_scope() as session:
            ch = (
                session.query(NotificationChannelModel)
                .filter(NotificationChannelModel.channel == channel_name)
                .first()
            )
            if not ch:
                return None
            return {
                "channel": ch.channel,
                "enabled": ch.enabled,
                "on_success": ch.on_success,
                "on_failure": ch.on_failure,
                "on_partial": ch.on_partial,
                "settings": self._decrypt_settings(ch.settings),
            }

    def get_enabled_channels(self) -> list[dict]:
        """Return only enabled channels with decrypted settings (for sending)."""
        with session_scope() as session:
            channels = (
                session.query(NotificationChannelModel)
                .filter(NotificationChannelModel.enabled == True)
                .all()
            )
            result = []
            for ch in channels:
                result.append({
                    "channel": ch.channel,
                    "enabled": ch.enabled,
                    "on_success": ch.on_success,
                    "on_failure": ch.on_failure,
                    "on_partial": ch.on_partial,
                    "settings": self._decrypt_settings(ch.settings),
                })
            return result

    def save_channel(self, channel_name: str, data: dict) -> None:
        """Create or update a channel. Sensitive settings are encrypted before storage."""
        with session_scope() as session:
            ch = (
                session.query(NotificationChannelModel)
                .filter(NotificationChannelModel.channel == channel_name)
                .first()
            )

            if not ch:
                ch = NotificationChannelModel(channel=channel_name)
                session.add(ch)
                session.flush()

            ch.enabled = data.get("enabled", ch.enabled)
            ch.on_success = data.get("on_success", ch.on_success)
            ch.on_failure = data.get("on_failure", ch.on_failure)
            ch.on_partial = data.get("on_partial", ch.on_partial)
            ch.updated_at = datetime.now()

            settings_data = data.get("settings", {})
            for key, value in settings_data.items():
                # Skip masked values (user didn't change them)
                if value == "*****":
                    continue

                # Encrypt sensitive values before storage
                stored_value = encrypt(str(value)) if key in _SENSITIVE_KEYS else str(value)

                existing = (
                    session.query(NotificationSettingModel)
                    .filter(
                        NotificationSettingModel.channel_id == ch.id,
                        NotificationSettingModel.key == key,
                    )
                    .first()
                )
                if existing:
                    existing.value = stored_value
                    existing.updated_at = datetime.now()
                else:
                    session.add(NotificationSettingModel(
                        channel_id=ch.id,
                        key=key,
                        value=stored_value,
                    ))

        logger.info("Saved notification config for channel: %s (sensitive fields encrypted)", channel_name)
