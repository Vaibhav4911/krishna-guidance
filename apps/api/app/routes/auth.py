from __future__ import annotations

from datetime import datetime, timezone

import google.auth.exceptions
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2 import id_token
from jwt import InvalidTokenError
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.config import settings
from app.core.security import decode_access_token
from app.db.models import AuthSession
from app.db.session import get_db
from app.services.auth_service import (
    OtpDeliveryError,
    OtpRateLimitError,
    create_user_session,
    request_email_otp,
    upsert_google_user,
    verify_email_otp,
)

router = APIRouter(prefix="/api/v1/auth")
bearer = HTTPBearer(auto_error=False)


class GoogleCredentialRequest(BaseModel):
    credential: str = Field(min_length=1, max_length=8192)


class OtpRequest(BaseModel):
    email: EmailStr


class OtpVerifyRequest(BaseModel):
    email: EmailStr
    otp: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")


def _session_response(db: Session, user) -> dict:
    token, expires_at = create_user_session(db, user)
    return {
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.display_name,
        },
        "access_token": token,
        "token_type": "bearer",
        "expires_at": expires_at.isoformat(),
    }


@router.post("/google/verify")
def google_verify(payload: GoogleCredentialRequest, db: Session = Depends(get_db)):
    if not settings.google_client_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google sign-in is not configured.",
        )

    try:
        claims = id_token.verify_oauth2_token(
            payload.credential,
            GoogleRequest(),
            audience=settings.google_client_id,
        )
    except (ValueError, google.auth.exceptions.GoogleAuthError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Google sign-in credential.",
        ) from exc

    email = claims.get("email")
    subject = claims.get("sub")
    if not email or not subject or claims.get("email_verified") is not True:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google account does not provide a verified email.",
        )

    try:
        user = upsert_google_user(db, subject, email, claims.get("name"))
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This email is already linked to a different Google account.",
        ) from exc
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account unavailable.")
    return _session_response(db, user)


@router.post("/otp/request", status_code=status.HTTP_202_ACCEPTED)
def otp_request(payload: OtpRequest, db: Session = Depends(get_db)):
    try:
        request_email_otp(db, str(payload.email))
    except OtpRateLimitError as exc:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(exc)) from exc
    except OtpDeliveryError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Sign-in email could not be sent. Please try again later.",
        ) from exc
    return {"message": "If the address can receive sign-in mail, a code has been sent."}


@router.post("/otp/verify")
def otp_verify(payload: OtpVerifyRequest, db: Session = Depends(get_db)):
    user = verify_email_otp(db, str(payload.email), payload.otp)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired sign-in code.")
    return _session_response(db, user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
):
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")
    try:
        claims = decode_access_token(credentials.credentials)
    except InvalidTokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token.") from exc

    session_id = claims.get("jti")
    if not session_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session.")
    session = db.query(AuthSession).filter(AuthSession.id == session_id).first()
    if session and session.revoked_at is None:
        session.revoked_at = datetime.now(timezone.utc)
        db.commit()
