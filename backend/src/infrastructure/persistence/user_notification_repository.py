"""Per-user notification channel persistence with Fernet encryption.

Same encryption pattern as NotificationRepository but scoped per user.
"""

import logging
from datetime import datetime

from src.domain.ports.user_notification_repository import (
    UserNotificationRepository as UserNotificationRepositoryPort,
)
from src.infrastructure.database.engine import session_scope
from src.infrastructure.database.models import (
    UserNotificationChannelModel,
    UserNotificationSettingModel,
)
from src.infrastructure.security.encryption import decrypt, encrypt, is_encrypted

logger = logging.getLogger(__name__)

_SENSITIVE_KEYS = {"webhook_url", "bot_token", "smtp_password"}


class PostgresUserNotificationRepository(UserNotificationRepositoryPort):
    """PostgreSQL-backed per-user notification config with encryption."""

    @staticmethod
    def _decrypt_settings(settings_rows) -> dict:
        result = {}
        for s in settings_rows:
            if s.key in _SENSITIVE_KEYS and is_encrypted(s.value):
                result[s.key] = decrypt(s.value)
            else:
                result[s.key] = s.value
        return result

    @staticmethod
    def _mask_settings(settings_rows) -> dict:
        result = {}
        for s in settings_rows:
            if s.key in _SENSITIVE_KEYS and s.value:
                result[s.key] = "*****"
            else:
                result[s.key] = s.value
        return result

    @staticmethod
    def _to_dict(ch, settings: dict) -> dict:
        return {
            "channel": ch.channel,
            "enabled": ch.enabled,
            "on_success": ch.on_success,
            "on_failure": ch.on_failure,
            "on_partial": ch.on_partial,
            "settings": settings,
        }

    def get_user_channels(self, user_id: int) -> list[dict]:
        with session_scope() as session:
            channels = (
                session.query(UserNotificationChannelModel)
                .filter(UserNotificationChannelModel.user_id == user_id)
                .all()
            )
            return [self._to_dict(ch, self._decrypt_settings(ch.settings)) for ch in channels]

    def get_user_channels_masked(self, user_id: int) -> list[dict]:
        with session_scope() as session:
            channels = (
                session.query(UserNotificationChannelModel)
                .filter(UserNotificationChannelModel.user_id == user_id)
                .all()
            )
            return [self._to_dict(ch, self._mask_settings(ch.settings)) for ch in channels]

    def get_user_enabled_channels(self, user_id: int) -> list[dict]:
        with session_scope() as session:
            channels = (
                session.query(UserNotificationChannelModel)
                .filter(
                    UserNotificationChannelModel.user_id == user_id,
                    UserNotificationChannelModel.enabled == True,
                )
                .all()
            )
            return [self._to_dict(ch, self._decrypt_settings(ch.settings)) for ch in channels]

    def save_user_channel(self, user_id: int, channel_name: str, data: dict) -> None:
        with session_scope() as session:
            ch = (
                session.query(UserNotificationChannelModel)
                .filter(
                    UserNotificationChannelModel.user_id == user_id,
                    UserNotificationChannelModel.channel == channel_name,
                )
                .first()
            )

            if not ch:
                ch = UserNotificationChannelModel(user_id=user_id, channel=channel_name)
                session.add(ch)
                session.flush()

            ch.enabled = data.get("enabled", ch.enabled)
            ch.on_success = data.get("on_success", ch.on_success)
            ch.on_failure = data.get("on_failure", ch.on_failure)
            ch.on_partial = data.get("on_partial", ch.on_partial)
            ch.updated_at = datetime.now()

            settings_data = data.get("settings", {})
            for key, value in settings_data.items():
                if value == "*****":
                    continue

                stored_value = encrypt(str(value)) if key in _SENSITIVE_KEYS else str(value)

                existing = (
                    session.query(UserNotificationSettingModel)
                    .filter(
                        UserNotificationSettingModel.user_channel_id == ch.id,
                        UserNotificationSettingModel.key == key,
                    )
                    .first()
                )
                if existing:
                    existing.value = stored_value
                    existing.updated_at = datetime.now()
                else:
                    session.add(UserNotificationSettingModel(
                        user_channel_id=ch.id,
                        key=key,
                        value=stored_value,
                    ))

        logger.info("Saved user %d notification config for %s", user_id, channel_name)

    def get_all_users_enabled_channels(self) -> list[dict]:
        with session_scope() as session:
            channels = (
                session.query(UserNotificationChannelModel)
                .filter(UserNotificationChannelModel.enabled == True)
                .all()
            )
            result = []
            for ch in channels:
                d = self._to_dict(ch, self._decrypt_settings(ch.settings))
                d["user_id"] = ch.user_id
                result.append(d)
            return result
