import hashlib
import logging
import random
import smtplib
from datetime import timedelta
from email.message import EmailMessage

import bcrypt
from django.utils import timezone

from accounts.models import OTPLog

from ..config import get_settings

logger = logging.getLogger(__name__)


def _hash_otp(otp: str) -> str:
    return bcrypt.hashpw(otp.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _verify_otp(otp: str, otp_hash: str) -> bool:
    return bcrypt.checkpw(otp.encode("utf-8"), otp_hash.encode("utf-8"))


def generate_otp() -> str:
    settings = get_settings()
    return "".join(str(random.randint(0, 9)) for _ in range(settings.otp_length))


def create_otp_log(identifier: str, purpose: str) -> tuple[OTPLog, str]:
    settings = get_settings()
    identifier = identifier.strip().lower()
    otp = generate_otp()
    expires_at = timezone.now() + timedelta(minutes=settings.otp_expire_minutes)
    log = OTPLog.objects.create(
        identifier=identifier,
        otp_hash=_hash_otp(otp),
        purpose=purpose,
        expires_at=expires_at,
    )
    return log, otp


def send_otp(identifier: str, otp: str) -> None:
    settings = get_settings()
    message = f"Your LMS verification code is: {otp}. It expires in {settings.otp_expire_minutes} minutes."

    if settings.smtp_host and settings.smtp_user:
        if "@" not in identifier:
            logger.warning("SMTP configured but identifier is not an email: %s", identifier)
            print(f"[OTP] {identifier}: {otp}")
            return
        msg = EmailMessage()
        msg["Subject"] = "LMS verification code"
        msg["From"] = settings.smtp_from_email
        msg["To"] = identifier
        msg.set_content(message)
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
            server.starttls()
            server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(msg)
        return

    print(f"[OTP] {identifier}: {otp}")


def verify_otp(identifier: str, otp: str, purpose: str) -> OTPLog:
    settings = get_settings()
    identifier = identifier.strip().lower()
    log = (
        OTPLog.objects.filter(identifier=identifier, purpose=purpose, is_verified=False)
        .order_by("-created_at")
        .first()
    )
    if not log:
        raise ValueError("No active OTP found. Request a new code.")

    if timezone.now() > log.expires_at:
        raise ValueError("OTP has expired. Request a new code.")

    if log.attempts >= settings.otp_max_attempts:
        raise ValueError("Maximum verification attempts exceeded. Request a new code.")

    log.attempts += 1
    log.save(update_fields=["attempts"])

    if not _verify_otp(otp, log.otp_hash):
        raise ValueError("Invalid OTP.")

    log.is_verified = True
    log.verified_at = timezone.now()
    log.save(update_fields=["is_verified", "verified_at"])
    return log
