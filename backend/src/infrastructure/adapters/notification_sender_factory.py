"""Concrete factory: builds NotificationSender instances from config.

This is the only place that knows about concrete sender implementations.
The application layer never imports Slack/Email/Telegram adapters directly.
"""

from src.domain.ports.notification_sender import NotificationSender
from src.domain.ports.notification_sender_factory import NotificationSenderFactory
from src.infrastructure.adapters.email_notifier import EmailNotifier
from src.infrastructure.adapters.slack_notifier import SlackNotifier
from src.infrastructure.adapters.telegram_notifier import TelegramNotifier


class ConcreteNotificationSenderFactory(NotificationSenderFactory):
    """Creates senders based on channel name and settings dict."""

    def create(self, channel_name: str, settings: dict) -> NotificationSender | None:
        if channel_name == "slack":
            url = settings.get("webhook_url", "")
            return SlackNotifier(webhook_url=url) if url else None

        if channel_name == "email":
            host = settings.get("smtp_host", "")
            if not host:
                return None
            return EmailNotifier(
                smtp_host=host,
                smtp_port=int(settings.get("smtp_port", "587")),
                smtp_user=settings.get("smtp_user", ""),
                smtp_password=settings.get("smtp_password", ""),
                from_email=settings.get("from_email", ""),
                to_emails=settings.get("to_emails", ""),
                use_tls=settings.get("use_tls", "true").lower() in ("true", "1"),
            )

        if channel_name == "telegram":
            token = settings.get("bot_token", "")
            chat_id = settings.get("chat_id", "")
            return TelegramNotifier(bot_token=token, chat_id=chat_id) if token and chat_id else None

        return None
