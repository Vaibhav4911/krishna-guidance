from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.core.security import create_access_token
from app.db.models import AuthSession, User

PASSWORD_HASH_N = 2**14
PASSWORD_HASH_R = 8
PASSWORD_HASH_P = 1
PASSWORD_HASH_LENGTH = 64
PASSWORD_SALT_LENGTH = 16
_DUMMY_SALT = b"krishna-guidance-dummy-salt"
_DUMMY_PASSWORD_HASH = hashlib.scrypt(
    b"not-a-real-user-password",
    salt=_DUMMY_SALT,
    n=PASSWORD_HASH_N,
    r=PASSWORD_HASH_R,
    p=PASSWORD_HASH_P,
    dklen=PASSWORD_HASH_LENGTH,
).hex()


class EmailAlreadyRegisteredError(Exception):
    pass


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(PASSWORD_SALT_LENGTH)
    password_digest = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=PASSWORD_HASH_N,
        r=PASSWORD_HASH_R,
        p=PASSWORD_HASH_P,
        dklen=PASSWORD_HASH_LENGTH,
    )
    return (
        f"scrypt${PASSWORD_HASH_N}${PASSWORD_HASH_R}${PASSWORD_HASH_P}"
        f"${salt.hex()}${password_digest.hex()}"
    )


def verify_password(password: str, encoded_hash: str | None) -> bool:
    if not encoded_hash:
        return False
    try:
        algorithm, n, r, p, salt_hex, digest_hex = encoded_hash.split("$")
        if (
            algorithm != "scrypt"
            or int(n) != PASSWORD_HASH_N
            or int(r) != PASSWORD_HASH_R
            or int(p) != PASSWORD_HASH_P
        ):
            return False
        salt = bytes.fromhex(salt_hex)
        expected_digest = bytes.fromhex(digest_hex)
    except (ValueError, TypeError):
        return False
    if (
        len(salt) != PASSWORD_SALT_LENGTH
        or len(expected_digest) != PASSWORD_HASH_LENGTH
    ):
        return False
    actual_digest = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=PASSWORD_HASH_N,
        r=PASSWORD_HASH_R,
        p=PASSWORD_HASH_P,
        dklen=PASSWORD_HASH_LENGTH,
    )
    return hmac.compare_digest(actual_digest, expected_digest)


def register_user(
    db: Session,
    email: str,
    password: str,
    display_name: str | None = None,
) -> User:
    normalized_email = _normalize_email(email)
    if db.query(User).filter(User.email == normalized_email).first():
        raise EmailAlreadyRegisteredError

    user = User(
        email=normalized_email,
        password_hash=hash_password(password),
        display_name=(display_name or "").strip() or normalized_email.split("@")[0],
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        if db.query(User).filter(User.email == normalized_email).first():
            raise EmailAlreadyRegisteredError from error
        raise
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    normalized_email = _normalize_email(email)
    user = db.query(User).filter(User.email == normalized_email).first()
    stored_hash = (
        user.password_hash
        if user and user.password_hash
        else _DUMMY_PASSWORD_HASH
    )
    password_matches = verify_password(password, stored_hash)
    if user is None or not user.is_active or not password_matches:
        return None
    return user


def create_user_session(db: Session, user: User) -> tuple[str, datetime]:
    session_id = str(uuid4())
    token, expires_at = create_access_token(str(user.id), session_id)
    db.add(AuthSession(id=session_id, user_id=user.id, expires_at=expires_at))
    db.commit()
    return token, expires_at
