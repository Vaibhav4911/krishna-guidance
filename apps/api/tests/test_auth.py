from __future__ import annotations

from uuid import uuid4

from app.db.models import AuthSession, User
from app.services import auth_service


def test_email_otp_is_single_use_and_rate_limited(test_context, monkeypatch):
    _, session_factory = test_context
    sent_codes: list[str] = []
    monkeypatch.setattr(
        auth_service,
        "_send_otp_email",
        lambda email, code: sent_codes.append(code),
    )

    with session_factory() as db:
        email = f"otp-{uuid4().hex}@example.test"
        auth_service.request_email_otp(db, email)
        assert len(sent_codes) == 1

        try:
            auth_service.request_email_otp(db, email)
        except auth_service.OtpRateLimitError:
            pass
        else:
            raise AssertionError("OTP resend should be rate limited.")

        wrong_code = "000000" if sent_codes[0] != "000000" else "000001"
        assert auth_service.verify_email_otp(db, email, wrong_code) is None

        user = auth_service.verify_email_otp(db, email, sent_codes[0])
        assert user is not None
        assert user.email == email
        assert auth_service.verify_email_otp(db, email, sent_codes[0]) is None


def test_access_token_can_be_revoked(test_context):
    client, session_factory = test_context
    with session_factory() as db:
        user = User(email=f"session-{uuid4().hex}@example.test", display_name="Test")
        db.add(user)
        db.commit()
        db.refresh(user)
        token, _ = auth_service.create_user_session(db, user)

    headers = {"Authorization": f"Bearer {token}"}
    assert client.post("/api/v1/journal/entry", json={"body": "private note"}).status_code == 401
    assert client.get("/api/v1/admin/overview", headers=headers).status_code == 403
    profile = client.get("/api/v1/me", headers=headers)
    assert profile.status_code == 200

    logout = client.post("/api/v1/auth/logout", headers=headers)
    assert logout.status_code == 204
    assert client.get("/api/v1/me", headers=headers).status_code == 401
