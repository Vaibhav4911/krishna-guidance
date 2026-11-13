from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.db.models import User
from app.middleware.auth import get_current_user

router = APIRouter(prefix="/api/v1/admin")


@router.get("/overview")
def admin_overview(user: User = Depends(get_current_user)):
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required.")
    return {
        "users": 0,
        "active_conversations": 0,
        "verified_sources": 0,
        "status": "ready",
    }
