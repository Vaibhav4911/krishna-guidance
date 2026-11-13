from __future__ import annotations

from fastapi import APIRouter, Depends

from app.db.models import User
from app.middleware.auth import get_current_user

router = APIRouter(prefix="/api/v1")


@router.get("/me")
def get_me(user: User = Depends(get_current_user)):
    return {
        "id": user.id,
        "email": user.email,
        "display_name": user.display_name,
        "locale": user.locale,
        "role": user.role,
    }
