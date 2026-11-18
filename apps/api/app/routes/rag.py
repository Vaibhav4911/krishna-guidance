from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.db.models import User
from app.middleware.auth import get_current_user
from app.services.model_service import ModelConfigurationError, ModelProviderError
from app.services.sanskrit_corpus import build_sanskrit_citation
from app.services.sanskrit_rag_service import (
    SanskritIndexUnavailableError,
    retrieve_sanskrit_verses,
)


router = APIRouter(prefix="/api/v1")


class RetrievalRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=3000)
    language: Literal["en", "hi"] = "en"


@router.post("/rag/search")
def search_corpus(
    payload: RetrievalRequest,
    _current_user: User = Depends(get_current_user),
):
    try:
        verses = retrieve_sanskrit_verses(
            payload.query,
            limit=5,
            language=payload.language,
        )
    except (ModelConfigurationError, SanskritIndexUnavailableError) as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except ModelProviderError as error:
        raise HTTPException(
            status_code=502,
            detail="The self-hosted AI retrieval service could not complete the request.",
        ) from error
    citations = [build_sanskrit_citation(verse) for verse in verses]
    return {
        "query": payload.query,
        "language": payload.language,
        "citations": [c.model_dump() for c in citations],
    }
