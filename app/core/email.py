"""
Numina AI — SMTP Email Service

Handles transactional email delivery (e.g., password reset).
"""

import asyncio
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Final

from app.core.config import settings

logger = logging.getLogger(__name__)

_PLACEHOLDER_HOSTS: Final[frozenset[str]] = frozenset(
    {"smtp.example.com", "localhost", ""}
)


def _email_configured() -> bool:
    host = (settings.smtp_host or "").strip().lower()
    return all(
        [
            host,
            host not in _PLACEHOLDER_HOSTS,
            settings.smtp_username,
            settings.smtp_password,
        ]
    )


def is_email_configured() -> bool:
    return _email_configured()


def send_email_sync(to_email: str, subject: str, body_plain: str) -> None:
    if not _email_configured():
        raise RuntimeError(
            "SMTP is not configured. Set SMTP_HOST, SMTP_USERNAME, and SMTP_PASSWORD."
        )

    from_addr = (settings.smtp_from_email or settings.smtp_username).strip()

    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = from_addr
    message["To"] = to_email
    message.attach(MIMEText(body_plain, "plain", "utf-8"))

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as server:
            server.starttls()
            server.login(settings.smtp_username, settings.smtp_password)
            server.sendmail(from_addr, [to_email], message.as_string())

        logger.info("Email sent to %s | subject=%s", to_email, subject)

    except smtplib.SMTPException:
        logger.exception(
            "SMTP error | host=%s port=%s",
            settings.smtp_host,
            settings.smtp_port,
        )
        raise
    except Exception:
        logger.exception("Unexpected email delivery failure")
        raise


async def send_password_reset_email(to_email: str, reset_link: str) -> None:
    subject = "Reset your Numina AI password"

    body_plain = (
        "You requested a password reset for your Numina AI account.\n\n"
        "Click the link below to set a new password (expires in 1 hour):\n\n"
        f"{reset_link}\n\n"
        "If you did not request this, you can safely ignore this email.\n\n"
        "— Numina AI Security Team"
    )

    body_html = f"""
        <!DOCTYPE html>
        <html>
        <body style="margin:0;padding:0;background-color:#f4f6f8;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">
            <table width="100%" cellpadding="0" cellspacing="0" style="padding:40px 0;background-color:#f4f6f8;">
                <tr>
                    <td align="center">
                        <table width="600" cellpadding="0" cellspacing="0" 
                            style="background:#ffffff;border-radius:12px;padding:40px;box-shadow:0 4px 12px rgba(0,0,0,0.05);">
                            
                            <tr>
                                <td align="center" style="padding-bottom:24px;">
                                    <h1 style="margin:0;font-size:24px;color:#111827;">
                                        Numina AI
                                    </h1>
                                </td>
                            </tr>

                            <tr>
                                <td style="color:#374151;font-size:16px;line-height:1.6;">
                                    <p style="margin:0 0 16px 0;">
                                        You requested a password reset for your Numina AI account.
                                    </p>

                                    <p style="margin:0 0 24px 0;">
                                        Click the button below to set a new password.
                                        This link will expire in <strong>1 hour</strong>.
                                    </p>

                                    <div style="text-align:center;margin:32px 0;">
                                        <a href="{reset_link}" 
                                        style="background-color:#111827;
                                                color:#ffffff;
                                                text-decoration:none;
                                                padding:14px 28px;
                                                border-radius:8px;
                                                font-weight:600;
                                                display:inline-block;">
                                            Reset Password
                                        </a>
                                    </div>

                                    <p style="margin:24px 0 12px 0;font-size:14px;color:#6b7280;">
                                        If the button doesn’t work, copy and paste this link into your browser:
                                    </p>

                                    <p style="word-break:break-all;font-size:13px;color:#2563eb;">
                                        {reset_link}
                                    </p>

                                    <hr style="border:none;border-top:1px solid #e5e7eb;margin:32px 0;" />

                                    <p style="margin:0;font-size:13px;color:#6b7280;">
                                        If you did not request a password reset, you can safely ignore this email.
                                        Your account remains secure.
                                    </p>

                                    <p style="margin-top:24px;font-size:13px;color:#9ca3af;">
                                        Numina AI
                                    </p>
                                </td>
                            </tr>

                        </table>
                    </td>
                </tr>
            </table>
        </body>
        </html>
    """

    def send():
        if not _email_configured():
            raise RuntimeError("SMTP is not configured.")

        from_addr = (settings.smtp_from_email or settings.smtp_username).strip()

        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = from_addr
        message["To"] = to_email

        message.attach(MIMEText(body_plain, "plain", "utf-8"))
        message.attach(MIMEText(body_html, "html", "utf-8"))

        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as server:
            server.starttls()
            server.login(settings.smtp_username, settings.smtp_password)
            server.sendmail(from_addr, [to_email], message.as_string())

    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, send)