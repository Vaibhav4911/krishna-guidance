from __future__ import annotations

from dataclasses import dataclass


@dataclass
class JournalEntry:
    title: str | None
    body: str
    mood: str | None = None


def create_prompt_from_journal(entry: JournalEntry) -> str:
    title = entry.title or "Daily reflection"
    mood = f" Mood: {entry.mood}." if entry.mood else ""
    return f"{title}.{mood} Content: {entry.body}"
