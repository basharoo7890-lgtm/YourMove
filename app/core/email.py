import logging
import smtplib
from email.message import EmailMessage

from app.core.config import get_settings

logger = logging.getLogger("yourmove.email")


def send_login_notification(recipient_email: str, recipient_name: str) -> None:
    """
    Sends a login notification email when SMTP is configured.
    Fails safely without breaking authentication flow.
    """
    settings = get_settings()
    if not settings.SMTP_HOST or not settings.SMTP_USERNAME or not settings.SMTP_PASSWORD:
        return

    msg = EmailMessage()
    msg["Subject"] = "YourMove Login Alert"
    msg["From"] = settings.SMTP_FROM_EMAIL or settings.SMTP_USERNAME
    msg["To"] = recipient_email
    msg.set_content(
        f"Hello {recipient_name},\n\n"
        "A new login to your YourMove account was detected.\n"
        "If this was you, no action is required.\n\n"
        "Thank you for using YourMove."
    )

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
            server.starttls()
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.send_message(msg)
    except Exception:
        logger.exception("Failed to send login notification email")
