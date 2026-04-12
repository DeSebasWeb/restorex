"""Concrete adapter: notification template persistence in PostgreSQL.

Resolves templates with priority: user-specific > system default.
"""

import logging

from src.domain.ports.notification_template_repository import (
    NotificationTemplateRepository as NotificationTemplateRepositoryPort,
)
from src.infrastructure.database.engine import session_scope
from src.infrastructure.database.models import NotificationTemplateModel

logger = logging.getLogger(__name__)


class PostgresNotificationTemplateRepository(NotificationTemplateRepositoryPort):
    """PostgreSQL-backed template resolution."""

    def get_template(self, event_type: str, user_id: int | None = None) -> tuple[str | None, str | None]:
        try:
            with session_scope() as session:
                # User-specific template first
                if user_id:
                    user_tpl = (
                        session.query(NotificationTemplateModel)
                        .filter(
                            NotificationTemplateModel.user_id == user_id,
                            NotificationTemplateModel.event_type == event_type,
                        )
                        .first()
                    )
                    if user_tpl:
                        return user_tpl.subject_template, user_tpl.body_template

                # System default
                system_tpl = (
                    session.query(NotificationTemplateModel)
                    .filter(
                        NotificationTemplateModel.is_system == True,
                        NotificationTemplateModel.event_type == event_type,
                    )
                    .first()
                )
                if system_tpl:
                    return system_tpl.subject_template, system_tpl.body_template

        except Exception as e:
            logger.warning("Failed to load template for %s: %s", event_type, e)

        return None, None
