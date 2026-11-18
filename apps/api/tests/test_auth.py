from __future__ import annotations

from uuid import uuid4

from app.db.models import AuthSession, User
from app.services import auth_service


def test_signup_creates_hashed_password_and_login_returns_session(test_context):
    client, session_factory = test_context
    email = f"signup-{uuid4().hex}@example.com"
    password = "correct horse battery"

    signup = client.post(
        "/api/v1/auth/signup",
        json={
            "email": email.upper(),
            "password": password,
            "display_name": "Test User",
        },
    )

    assert signup.status_code == 201
    signup_body = signup.json()
    assert signup_body["user"]["email"] == email
    assert signup_body["user"]["name"] == "Test User"
    assert signup_body["access_token"]
    assert signup_body["token_type"] == "bearer"

    with session_factory() as db:
        user = db.query(User).filter(User.email == email).one()
        assert user.password_hash != password
        assert auth_service.verify_password(password, user.password_hash)
        assert db.query(AuthSession).filter(AuthSession.user_id == user.id).count() == 1

    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login.status_code == 200
    assert login.json()["user"]["email"] == email
    assert login.json()["access_token"]


def test_signup_rejects_duplicate_email_and_login_rejects_bad_password(test_context):
    client, _ = test_context
    email = f"duplicate-{uuid4().hex}@example.com"
    password = "correct horse battery"

    first_signup = client.post(
        "/api/v1/auth/signup",
        json={"email": email, "password": password},
    )
    assert first_signup.status_code == 201

    duplicate_signup = client.post(
        "/api/v1/auth/signup",
        json={"email": email.upper(), "password": password},
    )
    assert duplicate_signup.status_code == 409

    bad_login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "incorrect password"},
    )
    assert bad_login.status_code == 401
    assert bad_login.json()["detail"] == "Invalid email or password."


def test_signup_enforces_password_minimum_and_old_auth_routes_are_removed(test_context):
    client, _ = test_context

    short_password = client.post(
        "/api/v1/auth/signup",
        json={"email": f"short-{uuid4().hex}@example.com", "password": "short"},
    )
    assert short_password.status_code == 422

    assert client.post(
        "/api/v1/auth/otp/request",
        json={"email": "person@example.com"},
    ).status_code == 404
    assert client.post(
        "/api/v1/auth/google/verify",
        json={"credential": "unused"},
    ).status_code == 404


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
