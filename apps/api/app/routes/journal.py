from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.db.models import User
from app.middleware.auth import get_current_user
from app.services.journal_service import JournalEntry, create_prompt_from_journal

router = APIRouter(prefix="/api/v1")


class JournalRequest(BaseModel):
    title: str | None = None
    body: str
    mood: str | None = None


@router.post("/journal/entry")
def save_journal_entry(payload: JournalRequest, user: User = Depends(get_current_user)):
    entry = JournalEntry(title=payload.title, body=payload.body, mood=payload.mood)
    prompt = create_prompt_from_journal(entry)
    return {"status": "saved", "summary": prompt[:200]}
