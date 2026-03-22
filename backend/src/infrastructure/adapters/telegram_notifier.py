"""Telegram notification adapter via Bot API."""

import json
import logging
import urllib.request
import urllib.error

from src.domain.ports.notification_sender import NotificationSender

logger = logging.getLogger(__name__)

_API_BASE = "https://api.telegram.org/bot"


class TelegramNotifier(NotificationSender):
    def __init__(self, bot_token: str, chat_id: str):
        self._token = bot_token
        self._chat_id = chat_id

    @property
    def channel_name(self) -> str:
        return "Telegram"

    def send(self, subject: str, body: str, is_error: bool = False) -> bool:
        if not self._token or not self._chat_id:
            return False

        emoji = "\u274c" if is_error else "\u2705"

        text = (
            f"{emoji} *{self._escape(subject)}*\n\n"
            f"```\n{body}\n```\n\n"
            f"\U0001f6e1 _Sent by Restorex_"
        )

        payload = {
            "chat_id": self._chat_id,
            "text": text,
            "parse_mode": "MarkdownV2" if not self._has_special_chars(text) else "Markdown",
            "disable_web_page_preview": True,
        }

        try:
            url = f"{_API_BASE}{self._token}/sendMessage"
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                result = json.loads(resp.read().decode())
                return result.get("ok", False)
        except Exception as e:
            logger.error("Telegram notification failed: %s", e)
            return False

    def test(self) -> tuple[bool, str]:
        if not self._token:
            return False, "Bot token is empty"
        if not self._chat_id:
            return False, "Chat ID is empty"
        ok = self.send(
            "Restorex Test Notification",
            "If you see this, Telegram notifications are working correctly.",
        )
        return ok, "Message sent successfully" if ok else "Failed to send message"

    @staticmethod
    def _escape(text: str) -> str:
        """Escape special Markdown characters."""
        for ch in ("_", "*", "[", "]", "(", ")", "~", "`", ">", "#", "+", "-", "=", "|", "{", "}", ".", "!"):
            text = text.replace(ch, f"\\{ch}")
        return text

    @staticmethod
    def _has_special_chars(text: str) -> bool:
        """Check if text has chars that break MarkdownV2."""
        return any(ch in text for ch in (".", "-", "(", ")", "+", "="))
