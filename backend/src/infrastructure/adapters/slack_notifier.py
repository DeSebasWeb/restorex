"""Slack notification adapter via incoming webhooks."""

import json
import logging
import urllib.request
import urllib.error

from src.domain.ports.notification_sender import NotificationSender

logger = logging.getLogger(__name__)


class SlackNotifier(NotificationSender):
    def __init__(self, webhook_url: str):
        self._webhook_url = webhook_url

    @property
    def channel_name(self) -> str:
        return "Slack"

    def send(self, subject: str, body: str, is_error: bool = False) -> bool:
        if not self._webhook_url:
            return False

        color = "#e74c3c" if is_error else "#10b981"
        emoji = ":x:" if is_error else ":white_check_mark:"

        payload = {
            "attachments": [
                {
                    "color": color,
                    "blocks": [
                        {
                            "type": "header",
                            "text": {"type": "plain_text", "text": f"{emoji} {subject}"},
                        },
                        {
                            "type": "section",
                            "text": {"type": "mrkdwn", "text": body},
                        },
                        {
                            "type": "context",
                            "elements": [
                                {"type": "mrkdwn", "text": ":shield: Sent by *Restorex* — Database Backup Engine"},
                            ],
                        },
                    ],
                }
            ]
        }

        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                self._webhook_url,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.status == 200
        except Exception as e:
            logger.error("Slack notification failed: %s", e)
            return False

    def test(self) -> tuple[bool, str]:
        if not self._webhook_url:
            return False, "Webhook URL is empty"
        ok = self.send(
            "Restorex Test Notification",
            "If you see this, Slack notifications are working correctly.",
        )
        return ok, "Message sent successfully" if ok else "Failed to send message"
