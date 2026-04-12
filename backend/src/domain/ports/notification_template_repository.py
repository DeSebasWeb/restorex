"""Port: Notification template persistence and resolution."""

from abc import ABC, abstractmethod


class NotificationTemplateRepository(ABC):
    """Resolves notification templates: user-specific first, then system default."""

    @abstractmethod
    def get_template(self, event_type: str, user_id: int | None = None) -> tuple[str | None, str | None]:
        """Look up templates for an event.

        Priority: user-specific > system default.
        Returns (subject_template, body_template) or (None, None) if not found.
        """
