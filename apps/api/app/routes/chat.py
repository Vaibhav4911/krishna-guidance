from datetime import date

from fastapi import APIRouter, Depends, HTTPException

from app.db.models import User
from app.middleware.auth import get_current_user
from app.schemas import ChatMessageRequest, ChatMessageResponse
from app.services.openai_service import OpenAIConfigurationError, OpenAIProviderError
from app.services.response_service import build_guidance
from app.services.sanskrit_corpus import build_sanskrit_citation, load_sanskrit_verses
from app.services.sanskrit_rag_service import SanskritIndexUnavailableError

router = APIRouter(prefix="/api/v1")


@router.get("/health")
def health():
    return {"status": "ok", "service": "krishna-guidance-api"}


@router.post("/chat/message", response_model=ChatMessageResponse)
def generate_response(payload: ChatMessageRequest, user: User = Depends(get_current_user)):
    try:
        return build_guidance(payload)
    except (OpenAIConfigurationError, SanskritIndexUnavailableError) as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except OpenAIProviderError as error:
        raise HTTPException(
            status_code=502,
            detail="The AI guidance provider could not complete the request.",
        ) from error


@router.get("/daily-wisdom")
def daily_wisdom():
    verses = load_sanskrit_verses()
    verse = verses[(date.today().toordinal() - 1) % len(verses)]
    return {
        "passage": build_sanskrit_citation(verse).model_dump(),
        "reflection": (
            "This is the original Sanskrit source text. Its meaning is not included "
            "because a reviewed translation has not yet been configured."
        ),
    }
