"""Application Service: Orchestrates notification delivery across channels.

Depends ONLY on domain ports — never on concrete infrastructure adapters.
Supports per-user notification channels and customizable message templates.
"""

import logging
from typing import Callable

from src.application.services.template_renderer import TemplateRenderer
from src.domain.ports.notification_repository import NotificationRepository
from src.domain.ports.notification_sender_factory import NotificationSenderFactory
from src.domain.ports.notification_template_repository import NotificationTemplateRepository
from src.domain.ports.user_notification_repository import UserNotificationRepository

logger = logging.getLogger(__name__)

# Callable that returns True if users without config inherit admin's channels
InheritPolicyFn = Callable[[], bool]

# Maps backup result types to template event types
_RESULT_TYPE_TO_EVENT = {
    "success": "backup_success",
    "failure": "backup_failure",
    "partial": "backup_partial",
}

_EVENT_ICONS = {
    "scheduled_start": "\u23f0",
    "manual_start": "\u25b6\ufe0f",
    "rotation": "\U0001f5d1\ufe0f",
    "backup_cancelled": "\u26d4",
}


class NotificationService:
    def __init__(
        self,
        repository: NotificationRepository,
        sender_factory: NotificationSenderFactory,
        user_repository: UserNotificationRepository | None = None,
        template_repository: NotificationTemplateRepository | None = None,
        inherit_policy: InheritPolicyFn | None = None,
        admin_user_id: int = 1,
    ):
        self._repo = repository
        self._sender_factory = sender_factory
        self._user_repo = user_repository
        self._template_repo = template_repository
        self._inherit_policy = inherit_policy or (lambda: False)
        self._admin_user_id = admin_user_id
        self._renderer = TemplateRenderer()

    # ── Public API ────────────────────────────────────────────────

    def notify_backup_result(self, summary: dict) -> list[dict]:
        """Send backup result notifications to all users with enabled channels."""
        result_type = self._determine_result_type(summary)
        event_type = _RESULT_TYPE_TO_EVENT.get(result_type, "backup_failure")
        is_error = result_type == "failure"
        variables = self._build_variables(summary)

        all_channels = self._collect_all_enabled_channels(result_type)
        results = []

        for ch_entry in all_channels:
            channel_name = ch_entry["channel"]
            user_id = ch_entry.get("user_id")

            subject, body = self._render_templates(event_type, user_id, variables)

            sender = self._sender_factory.create(channel_name, ch_entry["settings"])
            if not sender:
                logger.warning("Could not build sender for channel: %s (user %s)", channel_name, user_id)
                results.append({"channel": channel_name, "user_id": user_id, "success": False, "error": "Invalid configuration"})
                continue

            try:
                ok = sender.send(subject, body, is_error=is_error)
                results.append({"channel": channel_name, "user_id": user_id, "success": ok, "error": None if ok else "Send failed"})
                if ok:
                    logger.info("Notification sent via %s (user %s)", channel_name, user_id)
                else:
                    logger.warning("Notification failed via %s (user %s)", channel_name, user_id)
            except Exception as e:
                logger.error("Notification error via %s (user %s): %s", channel_name, user_id, e)
                results.append({"channel": channel_name, "user_id": user_id, "success": False, "error": str(e)})

        return results

    def notify_event(self, event_type: str, message: str):
        """Send a simple event notification to all users with enabled channels."""
        icon = _EVENT_ICONS.get(event_type, "\u2139\ufe0f")
        variables = {"message": message}

        all_channels = self._collect_all_enabled_channels_for_events()

        for ch_entry in all_channels:
            channel_name = ch_entry["channel"]
            user_id = ch_entry.get("user_id")

            subject_tpl, body_tpl = self._get_templates(event_type, user_id)
            if subject_tpl and body_tpl:
                subject = f"{icon} {self._renderer.render(subject_tpl, variables)}"
                body = self._renderer.render(body_tpl, variables)
            else:
                subject = f"{icon} {message}"
                body = message

            sender = self._sender_factory.create(channel_name, ch_entry["settings"])
            if not sender:
                continue
            try:
                sender.send(subject, body, is_error=False)
            except Exception as e:
                logger.warning("Event notification failed via %s (user %s): %s", channel_name, user_id, e)

    def test_channel(self, channel_name: str, user_id: int | None = None) -> tuple[bool, str]:
        """Test a specific notification channel (global or per-user)."""
        if user_id and self._user_repo:
            channels = self._user_repo.get_user_channels(user_id)
            ch_config = next((c for c in channels if c["channel"] == channel_name), None)
        else:
            ch_config = self._repo.get_channel(channel_name)

        if not ch_config:
            return False, f"Channel '{channel_name}' not configured"

        sender = self._sender_factory.create(channel_name, ch_config["settings"])
        if not sender:
            return False, f"Invalid configuration for {channel_name}"

        return sender.test()

    # ── Channel collection ────────────────────────────────────────

    def _collect_all_enabled_channels(self, result_type: str) -> list[dict]:
        """Collect enabled channels from all users.

        If inherit_policy is ON, users without personal config
        receive notifications through the admin's channels.
        """
        if not self._user_repo:
            return []

        all_user_channels = self._user_repo.get_all_users_enabled_channels()

        channels = []
        users_with_config: set[int] = set()

        for ch in all_user_channels:
            if not self._should_notify(ch, result_type):
                continue
            channels.append(ch)
            users_with_config.add(ch["user_id"])

        # Inheritance: if policy is ON and there are users without config,
        # they inherit the admin's channels (no duplicate for admin)
        # In practice this means: admin's channels are the "global default"
        if not channels and self._inherit_policy():
            admin_channels = self._user_repo.get_user_enabled_channels(self._admin_user_id)
            for ch in admin_channels:
                if not self._should_notify(ch, result_type):
                    continue
                ch["user_id"] = self._admin_user_id
                channels.append(ch)

        return channels

    def _collect_all_enabled_channels_for_events(self) -> list[dict]:
        """Collect all enabled channels for event notifications."""
        if not self._user_repo:
            return []

        channels = self._user_repo.get_all_users_enabled_channels()

        if not channels and self._inherit_policy():
            channels = self._user_repo.get_user_enabled_channels(self._admin_user_id)
            for ch in channels:
                ch["user_id"] = self._admin_user_id

        return channels

    # ── Template resolution ───────────────────────────────────────

    def _render_templates(self, event_type: str, user_id: int | None, variables: dict) -> tuple[str, str]:
        """Resolve and render templates for an event. User template takes priority over system."""
        subject_tpl, body_tpl = self._get_templates(event_type, user_id)

        if subject_tpl and body_tpl:
            return (
                self._renderer.render(subject_tpl, variables),
                self._renderer.render(body_tpl, variables),
            )

        # Fallback to hardcoded (should never happen after seed, but safety)
        return self._fallback_subject(variables), self._fallback_body(variables)

    def _get_templates(self, event_type: str, user_id: int | None) -> tuple[str | None, str | None]:
        """Look up templates via the injected repository."""
        if self._template_repo is None:
            return None, None
        return self._template_repo.get_template(event_type, user_id)

    # ── Helpers ────────────────────────────────────────────────────

    @staticmethod
    def _determine_result_type(summary: dict) -> str:
        failed = summary.get("failed", 0)
        errors = summary.get("errors", [])
        backed_up = summary.get("backed_up", 0)

        if failed > 0 or errors:
            return "failure"
        if any(r.get("status") == "partial" for r in summary.get("results", [])):
            return "partial"
        if backed_up > 0:
            return "success"
        return "success"

    @staticmethod
    def _build_variables(summary: dict) -> dict:
        errors = summary.get("errors", [])
        error_lines = []
        for err in errors[:5]:
            error_lines.append(f"  - {err.get('db_name', '?')}: {err.get('error', 'Unknown')}")
        if len(errors) > 5:
            error_lines.append(f"  ... and {len(errors) - 5} more")

        return {
            "total_dbs": str(summary.get("total_dbs", 0)),
            "backed_up": str(summary.get("backed_up", 0)),
            "skipped": str(summary.get("skipped", 0)),
            "failed": str(summary.get("failed", 0)),
            "started_at": summary.get("started_at", ""),
            "finished_at": summary.get("finished_at", ""),
            "errors": "\n".join(error_lines) if error_lines else "None",
        }

    @staticmethod
    def _should_notify(ch_config: dict, result_type: str) -> bool:
        if result_type == "success" and not ch_config.get("on_success", True):
            return False
        if result_type == "failure" and not ch_config.get("on_failure", True):
            return False
        if result_type == "partial" and not ch_config.get("on_partial", True):
            return False
        return True

    @staticmethod
    def _fallback_subject(variables: dict) -> str:
        failed = int(variables.get("failed", "0"))
        backed_up = int(variables.get("backed_up", "0"))
        skipped = int(variables.get("skipped", "0"))
        if failed > 0:
            return f"Backup Failed — {failed} database(s) failed"
        if backed_up > 0:
            return f"Backup Complete — {backed_up} backed up, {skipped} skipped"
        return "Backup Complete — no changes detected"

    @staticmethod
    def _fallback_body(variables: dict) -> str:
        return (
            f"Databases:  {variables.get('total_dbs', '0')}\n"
            f"Backed up:  {variables.get('backed_up', '0')}\n"
            f"Skipped:    {variables.get('skipped', '0')}\n"
            f"Failed:     {variables.get('failed', '0')}\n"
            f"Started:    {variables.get('started_at', '')}\n"
            f"Finished:   {variables.get('finished_at', '')}"
        )
