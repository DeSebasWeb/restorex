"""Application Service: Orchestrates notification delivery across channels."""

import logging
from datetime import datetime

from src.domain.ports.notification_sender import NotificationSender
from src.infrastructure.adapters.slack_notifier import SlackNotifier
from src.infrastructure.adapters.email_notifier import EmailNotifier
from src.infrastructure.adapters.telegram_notifier import TelegramNotifier
from src.infrastructure.persistence.notification_repository import NotificationRepository

logger = logging.getLogger(__name__)


def _build_sender(channel_name: str, settings: dict) -> NotificationSender | None:
    """Factory: create a NotificationSender from channel name + settings dict."""
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


class NotificationService:
    def __init__(self, repository: NotificationRepository):
        self._repo = repository

    def notify_backup_result(self, summary: dict) -> list[dict]:
        """Send notifications for a backup run result to all enabled channels.

        Returns a list of {channel, success, error} dicts.
        """
        backed_up = summary.get("backed_up", 0)
        failed = summary.get("failed", 0)
        skipped = summary.get("skipped", 0)
        total = summary.get("total_dbs", 0)
        errors = summary.get("errors", [])

        # Determine result type
        if failed > 0 or errors:
            result_type = "failure"
            is_error = True
        elif any(r.get("status") == "partial" for r in summary.get("results", [])):
            result_type = "partial"
            is_error = False
        elif backed_up == 0 and skipped > 0:
            result_type = "success"
            is_error = False
        elif backed_up > 0:
            result_type = "success"
            is_error = False
        else:
            # No DBs processed and no errors = nothing happened (likely misconfigured)
            result_type = "failure"
            is_error = True

        subject = self._build_subject(backed_up, failed, skipped, total, errors)
        body = self._build_body(summary)

        enabled_channels = self._repo.get_enabled_channels()
        results = []

        for ch_config in enabled_channels:
            channel_name = ch_config["channel"]

            # Check if this channel should receive this type of notification
            if result_type == "success" and not ch_config.get("on_success", True):
                continue
            if result_type == "failure" and not ch_config.get("on_failure", True):
                continue
            if result_type == "partial" and not ch_config.get("on_partial", True):
                continue

            sender = _build_sender(channel_name, ch_config["settings"])
            if not sender:
                logger.warning("Could not build sender for channel: %s", channel_name)
                results.append({"channel": channel_name, "success": False, "error": "Invalid configuration"})
                continue

            try:
                ok = sender.send(subject, body, is_error=is_error)
                results.append({"channel": channel_name, "success": ok, "error": None if ok else "Send failed"})
                if ok:
                    logger.info("Notification sent via %s", channel_name)
                else:
                    logger.warning("Notification failed via %s", channel_name)
            except Exception as e:
                logger.error("Notification error via %s: %s", channel_name, e)
                results.append({"channel": channel_name, "success": False, "error": str(e)})

        return results

    def test_channel(self, channel_name: str) -> tuple[bool, str]:
        """Test a specific notification channel."""
        ch_config = self._repo.get_channel(channel_name)
        if not ch_config:
            return False, f"Channel '{channel_name}' not configured"

        sender = _build_sender(channel_name, ch_config["settings"])
        if not sender:
            return False, f"Invalid configuration for {channel_name}"

        return sender.test()

    @staticmethod
    def _build_subject(backed_up: int, failed: int, skipped: int, total: int, errors: list | None = None) -> str:
        if errors:
            error_msg = errors[0].get("error", "Unknown error") if len(errors) == 1 else f"{len(errors)} error(s)"
            return f"Backup Failed — {error_msg}"
        if failed > 0:
            return f"Backup Failed — {failed} database(s) failed out of {total}"
        if backed_up > 0:
            return f"Backup Complete — {backed_up} backed up, {skipped} skipped"
        if skipped > 0:
            return f"Backup Complete — {skipped} databases unchanged (no backup needed)"
        return "Backup Failed — no databases processed"

    @staticmethod
    def _build_body(summary: dict) -> str:
        backed_up = summary.get("backed_up", 0)
        failed = summary.get("failed", 0)
        skipped = summary.get("skipped", 0)
        total = summary.get("total_dbs", 0)
        started = summary.get("started_at", "")
        finished = summary.get("finished_at", "")
        errors = summary.get("errors", [])

        lines = [
            f"Databases:  {total}",
            f"Backed up:  {backed_up}",
            f"Skipped:    {skipped}",
            f"Failed:     {failed}",
            f"Started:    {started}",
            f"Finished:   {finished}",
        ]

        if errors:
            lines.append("")
            lines.append("Errors:")
            for err in errors[:5]:
                lines.append(f"  - {err.get('db_name', '?')}: {err.get('error', 'Unknown')}")
            if len(errors) > 5:
                lines.append(f"  ... and {len(errors) - 5} more")

        return "\n".join(lines)
