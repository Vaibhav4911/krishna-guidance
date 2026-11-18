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
    meaning: str | None = None
    explanation: str | None = None


class ConversationMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(..., min_length=1, max_length=3000)
    citation_ids: list[str] = Field(default_factory=list, max_length=3)


class ChatMessageRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=3000)
    language: Literal["en", "hi"] = "en"
    history: list[ConversationMessage] = Field(default_factory=list, max_length=8)


class ChatMessageResponse(BaseModel):
    answer: str
    language: str
    citations: list[Citation] = Field(default_factory=list)
    safety_mode: str = "standard"
