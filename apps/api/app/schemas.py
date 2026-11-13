from typing import Literal

from pydantic import BaseModel, Field


class Citation(BaseModel):
    chapter: int
    verse: int | None = None
    source: str = "Bhagavad Gita"
    source_url: str | None = None
    language: str = "en"
    translation: str = "Traditional English"
    quote: str


class ChatMessageRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=3000)
    language: Literal["en", "hi", "sa"] = "en"


class ChatMessageResponse(BaseModel):
    answer: str
    language: str
    citations: list[Citation] = Field(default_factory=list)
    safety_mode: str = "standard"
