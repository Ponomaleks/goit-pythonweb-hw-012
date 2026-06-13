from typing import Any, Dict, List

from fastapi_mail import (
    FastMail,
    MessageSchema,
    ConnectionConfig,
    MessageType,
    NameEmail,
)

from app.config import get_settings
from pathlib import Path


def get_mail_config() -> ConnectionConfig:
    settings = get_settings()
    return ConnectionConfig(
        MAIL_USERNAME=settings.mail_username,
        MAIL_PASSWORD=settings.mail_password,
        MAIL_FROM=settings.mail_from or settings.email_from,
        MAIL_PORT=int(settings.mail_port or settings.smtp_port or 25),
        MAIL_SERVER=settings.mail_server or settings.smtp_host or "localhost",
        MAIL_STARTTLS=settings.mail_start_tls,
        MAIL_SSL_TLS=settings.mail_ssl_tls,
        USE_CREDENTIALS=bool(settings.mail_username or settings.smtp_user),
        TEMPLATE_FOLDER=Path(__file__).parent.parent / "templates" / "email",
    )


async def send_verification_email(
    to: NameEmail,
    subject: str,
    template_data: Dict[str, Any],
    template_name: str = "verification.html",
) -> None:
    try:
        conf = get_mail_config()
        message = MessageSchema(
            subject=subject,
            recipients=[to],
            template_body=template_data,
            subtype=MessageType.html,
        )
        fm = FastMail(conf)
        await fm.send_message(message, template_name=template_name)
    except Exception as exc:
        print(f"Error sending email: {exc}")
