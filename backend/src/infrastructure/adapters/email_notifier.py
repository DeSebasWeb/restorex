"""Email notification adapter via SMTP."""

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from src.domain.ports.notification_sender import NotificationSender

logger = logging.getLogger(__name__)


class EmailNotifier(NotificationSender):
    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        smtp_user: str,
        smtp_password: str,
        from_email: str,
        to_emails: str,
        use_tls: bool = True,
    ):
        self._host = smtp_host
        self._port = smtp_port
        self._user = smtp_user
        self._password = smtp_password
        self._from = from_email
        self._to = [e.strip() for e in to_emails.split(",") if e.strip()]
        self._use_tls = use_tls

    @property
    def channel_name(self) -> str:
        return "Email"

    def send(self, subject: str, body: str, is_error: bool = False) -> bool:
        if not self._host or not self._to:
            return False

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"{'[FAIL]' if is_error else '[OK]'} Restorex: {subject}"
            msg["From"] = self._from or self._user
            msg["To"] = ", ".join(self._to)

            status_color = "#e74c3c" if is_error else "#10b981"
            status_icon = "&#10060;" if is_error else "&#9989;"

            html = f"""
            <div style="font-family: -apple-system, sans-serif; max-width: 600px; margin: 0 auto;">
                <div style="background: #0a0b14; color: white; padding: 20px 24px; border-radius: 12px 12px 0 0;">
                    <h2 style="margin: 0; font-size: 18px;">
                        &#128737; Restorex Backup Report
                    </h2>
                </div>
                <div style="border: 1px solid #e5e7eb; border-top: 3px solid {status_color}; padding: 24px; border-radius: 0 0 12px 12px;">
                    <h3 style="margin-top: 0;">{status_icon} {subject}</h3>
                    <pre style="background: #f3f4f6; padding: 16px; border-radius: 8px; font-size: 13px; overflow-x: auto; white-space: pre-wrap;">{body}</pre>
                    <p style="color: #9ca3af; font-size: 11px; margin-bottom: 0;">
                        Sent by Restorex — Database Backup Engine
                    </p>
                </div>
            </div>
            """

            msg.attach(MIMEText(body, "plain"))
            msg.attach(MIMEText(html, "html"))

            with smtplib.SMTP(self._host, self._port, timeout=10) as server:
                if self._use_tls:
                    server.starttls()
                if self._user and self._password:
                    server.login(self._user, self._password)
                server.sendmail(self._from or self._user, self._to, msg.as_string())

            return True
        except Exception as e:
            logger.error("Email notification failed: %s", e)
            return False

    def test(self) -> tuple[bool, str]:
        if not self._host:
            return False, "SMTP host is empty"
        if not self._to:
            return False, "No recipient emails configured"
        ok = self.send(
            "Test Notification",
            "If you see this, email notifications are working correctly.",
        )
        return ok, "Email sent successfully" if ok else "Failed to send email"
