from __future__ import annotations

import hashlib
import hmac
import secrets
import smtplib
import ssl
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from uuid import uuid4

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import settings
from app.core.security import create_access_token
from app.db.models import AuthSession, OtpChallenge, User

OTP_TTL_MINUTES = 10
OTP_RESEND_SECONDS = 60
OTP_MAX_ATTEMPTS = 5
OTP_MAX_REQUESTS_PER_HOUR = 5


def _ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


class OtpRateLimitError(Exception):
    pass


class OtpDeliveryError(Exception):
    pass


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _otp_digest(email: str, code: str) -> str:
    message = f"{_normalize_email(email)}:{code}".encode()
    return hmac.new(settings.jwt_secret.encode(), message, hashlib.sha256).hexdigest()


def _send_otp_email(email: str, code: str) -> None:
    if not settings.smtp_host or not settings.smtp_from_email:
        raise OtpDeliveryError("Email delivery is not configured.")

    message = EmailMessage()
    message["Subject"] = "Your Krishna Guidance sign-in code"
    message["From"] = settings.smtp_from_email
    message["To"] = email
    message.set_content(
        f"Your sign-in code is {code}. It expires in {OTP_TTL_MINUTES} minutes. "
        "If you did not request this code, you can ignore this email."
    )

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
            smtp.starttls(context=ssl.create_default_context())
            if settings.smtp_username:
                smtp.login(settings.smtp_username, settings.smtp_password or "")
            smtp.send_message(message)
    except (OSError, smtplib.SMTPException) as exc:
        raise OtpDeliveryError("Unable to deliver sign-in email.") from exc


def request_email_otp(db: Session, email: str) -> None:
    normalized_email = _normalize_email(email)
    now = datetime.now(timezone.utc)
    latest = (
        db.query(OtpChallenge)
        .filter(OtpChallenge.email == normalized_email)
        .order_by(OtpChallenge.created_at.desc())
        .with_for_update()
        .first()
    )

    if latest and (now - _ensure_utc(latest.created_at)).total_seconds() < OTP_RESEND_SECONDS:
        raise OtpRateLimitError("Please wait before requesting another code.")

    request_count = (
        db.query(func.count(OtpChallenge.id))
        .filter(
            OtpChallenge.email == normalized_email,
            OtpChallenge.created_at >= now - timedelta(hours=1),
        )
        .scalar()
    )
    if request_count >= OTP_MAX_REQUESTS_PER_HOUR:
        raise OtpRateLimitError("Too many sign-in code requests. Try again later.")

    code = f"{secrets.randbelow(1_000_000):06d}"
    challenge = OtpChallenge(
        email=normalized_email,
        code_digest=_otp_digest(normalized_email, code),
        expires_at=now + timedelta(minutes=OTP_TTL_MINUTES),
    )
    db.add(challenge)
    db.commit()
    db.refresh(challenge)

    try:
        _send_otp_email(normalized_email, code)
    except OtpDeliveryError:
        db.delete(challenge)
        db.commit()
        raise


def verify_email_otp(db: Session, email: str, code: str) -> User | None:
    normalized_email = _normalize_email(email)
    now = datetime.now(timezone.utc)
    challenge = (
        db.query(OtpChallenge)
        .filter(
            OtpChallenge.email == normalized_email,
            OtpChallenge.consumed_at.is_(None),
        )
        .order_by(OtpChallenge.created_at.desc())
        .with_for_update()
        .first()
    )

    if (
        challenge is None
        or _ensure_utc(challenge.expires_at) <= now
        or challenge.attempts >= OTP_MAX_ATTEMPTS
        or len(code) != 6
        or not code.isdigit()
    ):
        return None

    challenge.attempts += 1
    if not hmac.compare_digest(challenge.code_digest, _otp_digest(normalized_email, code)):
        if challenge.attempts >= OTP_MAX_ATTEMPTS:
            challenge.consumed_at = now
        db.commit()
        return None

    challenge.consumed_at = now
    user = db.query(User).filter(User.email == normalized_email).first()
    if user is None:
        user = User(email=normalized_email, display_name=normalized_email.split("@")[0])
        db.add(user)
    db.commit()
    db.refresh(user)
    return user


def upsert_google_user(db: Session, subject: str, email: str, name: str | None) -> User:
    normalized_email = _normalize_email(email)
    user = db.query(User).filter(User.google_subject == subject).first()
    if user is None:
        user = db.query(User).filter(User.email == normalized_email).first()
    if user is None:
        user = User(email=normalized_email, display_name=name, google_subject=subject)
        db.add(user)
    else:
        if user.google_subject not in (None, subject):
            raise ValueError("This email is already linked to a different Google account.")
        user.google_subject = subject
        if name:
            user.display_name = name
    db.commit()
    db.refresh(user)
    return user


def create_user_session(db: Session, user: User) -> tuple[str, datetime]:
    session_id = str(uuid4())
    token, expires_at = create_access_token(str(user.id), session_id)
    db.add(AuthSession(id=session_id, user_id=user.id, expires_at=expires_at))
    db.commit()
    return token, expires_at
