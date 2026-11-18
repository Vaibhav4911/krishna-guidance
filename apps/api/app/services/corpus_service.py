from __future__ import annotations

import json
import math
import re
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from app.schemas import Citation

API_ROOT = Path(__file__).resolve().parents[2]
PASSAGES_PATH = API_ROOT / "data" / "corpora" / "edwin_arnold" / "passages.jsonl"

SOURCE_ID = "gutenberg-2388-edwin-arnold"
SOURCE_TITLE = "Project Gutenberg eBook #2388"
TRANSLATION_TITLE = "The Song Celestial, translated by Sir Edwin Arnold (1885)"
SOURCE_URL = "https://www.gutenberg.org/ebooks/2388"
LANGUAGE = "en"
ROMAN_CHAPTERS = (
    "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX",
    "X", "XI", "XII", "XIII", "XIV", "XV", "XVI", "XVII", "XVIII",
)
HEADING_PATTERN = re.compile(
    r"(?im)^[ \t]*CHAPTER[ \t]+(XVIII|XVII|XVI|XV|XIV|XIII|XII|XI|X|IX|VIII|VII|VI|V|IV|III|II|I)[ \t]*$"
)
ENDING_PATTERN = re.compile(
    r"(?im)^[ \t]*HERE[ \t]+(?:ENDETH|ENDS)[ \t]+CHAPTER[ \t]+"
    r"(XVIII|XVII|XVI|XV|XIV|XIII|XII|XI|X|IX|VIII|VII|VI|V|IV|III|II|I)\b.*$"
    r"|^[ \t]*HERE[ \t]+ENDS,[ \t]+WITH[ \t]+CHAPTER[ \t]+(XVIII)\b.*$"
)
TOKEN_PATTERN = re.compile(r"[a-z]{2,}")
STOPWORDS = {
    "about", "after", "again", "also", "and", "are", "because", "been",
    "being", "but", "can", "could", "did", "does", "for", "from", "had",
    "has", "have", "her", "here", "him", "his", "how", "into", "its",
    "may", "might", "more", "most", "not", "our", "out", "shall", "should",
    "some", "such", "than", "that", "the", "their", "them", "then", "there",
    "these", "they", "this", "those", "through", "was", "were", "what",
    "when", "where", "which", "who", "will", "with", "would", "you", "your",
    "a", "an", "as", "at", "by", "he", "i", "in", "is", "it", "me", "my",
    "of", "on", "or", "she", "to", "we", "us",
}
RESULT_TERMS = {
    "result", "results", "outcome", "outcomes", "reward", "rewards",
}
ACTION_TERMS = {
    "action", "actions", "deed", "deeds", "duty", "effort", "efforts",
    "job", "jobs", "karma", "work", "works",
}


@dataclass(frozen=True)
class CorpusPassage:
    passage_id: str
    source_id: str
    language: str
    chapter: int
    verse: int | None
    text: str


def _chunk_lines(text: str, max_characters: int = 1000) -> list[str]:
    chunks: list[str] = []
    current: list[str] = []
    current_length = 0

    def flush() -> None:
        nonlocal current, current_length
        if current:
            chunks.append("\n".join(current))
            current = []
            current_length = 0

    for raw_line in text.splitlines():
        line = " ".join(raw_line.split())
        if not line:
            flush()
            continue

        words = line.split()
        segment: list[str] = []
        segment_length = 0
        for word in words:
            added_length = len(word) + (1 if segment else 0)
            if segment and segment_length + added_length > max_characters:
                segment_text = " ".join(segment)
                if current and current_length + len(segment_text) + 1 > max_characters:
                    flush()
                current.append(segment_text)
                current_length += len(segment_text) + (1 if current_length else 0)
                segment = []
                segment_length = 0
                added_length = len(word)
            segment.append(word)
            segment_length += added_length

        if segment:
            segment_text = " ".join(segment)
            if current and current_length + len(segment_text) + 1 > max_characters:
                flush()
            current.append(segment_text)
            current_length += len(segment_text) + (1 if current_length else 0)

    flush()
    return chunks


def parse_gutenberg_text(text: str) -> list[CorpusPassage]:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if "Project Gutenberg" not in text or "*** START OF THE PROJECT GUTENBERG EBOOK" not in text:
        raise ValueError("The downloaded text is not the expected Project Gutenberg eBook.")

    headings = list(HEADING_PATTERN.finditer(text))
    found_chapters = [match.group(1) for match in headings]
    if found_chapters != list(ROMAN_CHAPTERS):
        raise ValueError(
            "Expected one ordered heading for each of the 18 Bhagavad Gita chapters; "
            f"found {found_chapters!r}."
        )

    passages: list[CorpusPassage] = []
    for index, heading in enumerate(headings):
        end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
        chapter_number = index + 1
        chapter_body = text[heading.end():end]
        ending = ENDING_PATTERN.search(chapter_body)
        if ending is None:
            raise ValueError(f"Could not verify the end of chapter {chapter_number}.")
        ending_chapter = next(group for group in ending.groups() if group is not None)
        if ROMAN_CHAPTERS.index(ending_chapter) + 1 != chapter_number:
            raise ValueError(f"Chapter ending does not match chapter {chapter_number}.")

        chapter_body = chapter_body[:ending.start()]
        chapter_body = re.sub(r"\[FN#\d+\]", "", chapter_body)
        chapter_chunks = _chunk_lines(chapter_body)
        if not chapter_chunks:
            raise ValueError(f"Chapter {chapter_number} contains no text.")

        for passage_number, passage_text in enumerate(chapter_chunks, start=1):
            passages.append(
                CorpusPassage(
                    passage_id=f"{SOURCE_ID}:ch{chapter_number:02}:p{passage_number:03}",
                    source_id=SOURCE_ID,
                    language=LANGUAGE,
                    chapter=chapter_number,
                    verse=None,
                    text=passage_text,
                )
            )

    return passages


@lru_cache(maxsize=1)
def load_passages() -> tuple[CorpusPassage, ...]:
    if not PASSAGES_PATH.is_file():
        raise FileNotFoundError(
            f"Corpus passages are missing at {PASSAGES_PATH}. "
            "Run `python -m app.scripts.ingest_gutenberg_2388` from apps/api."
        )
    with PASSAGES_PATH.open(encoding="utf-8") as corpus_file:
        passages = tuple(
            CorpusPassage(**json.loads(line))
            for line in corpus_file
            if line.strip()
        )
    if not passages:
        raise ValueError(f"Corpus passages file is empty: {PASSAGES_PATH}")
    return passages


def _tokens(text: str) -> list[str]:
    return [
        token
        for token in TOKEN_PATTERN.findall(text.lower())
        if token not in STOPWORDS
    ]


def expand_retrieval_query(query: str) -> str:
    query_terms = set(_tokens(query))
    concepts: list[str] = []
    if query_terms & RESULT_TERMS:
        concepts.append("fruit")
    if query_terms & ACTION_TERMS:
        concepts.append("action")
    return " ".join(concepts) or query


def retrieve_related_passages(
    query: str,
    language: str = LANGUAGE,
    limit: int = 3,
) -> list[Citation]:
    if language != LANGUAGE:
        raise ValueError(f"No approved corpus is configured for language {language!r}.")
    if limit <= 0:
        return []

    query_terms = set(_tokens(query))
    if query_terms & RESULT_TERMS:
        query_terms.add("fruit")
    if query_terms & ACTION_TERMS:
        query_terms.add("action")
    if not query_terms:
        return []

    passages = load_passages()
    document_tokens = [_tokens(passage.text) for passage in passages]
    document_frequencies: Counter[str] = Counter(
        term
        for tokens in document_tokens
        for term in set(tokens)
    )
    document_count = len(passages)
    average_length = sum(map(len, document_tokens)) / document_count
    scored: list[tuple[float, CorpusPassage]] = []
    k1 = 1.5
    b = 0.75

    for passage, tokens in zip(passages, document_tokens):
        frequencies = Counter(tokens)
        score = 0.0
        for term in query_terms:
            term_frequency = frequencies[term]
            if not term_frequency:
                continue
            document_frequency = document_frequencies[term]
            inverse_document_frequency = math.log(
                1 + (document_count - document_frequency + 0.5) / (document_frequency + 0.5)
            )
            denominator = term_frequency + k1 * (
                1 - b + b * len(tokens) / average_length
            )
            score += inverse_document_frequency * (
                term_frequency * (k1 + 1) / denominator
            )
        if score > 0:
            scored.append((score, passage))

    scored.sort(key=lambda result: (-result[0], result[1].passage_id))
    citations: list[Citation] = []
    seen_chapters: set[int] = set()
    for _, passage in scored:
        if passage.chapter in seen_chapters:
            continue
        citations.append(
            Citation(
                chapter=passage.chapter,
                verse=None,
                source=SOURCE_TITLE,
                source_url=SOURCE_URL,
                language=LANGUAGE,
                translation=TRANSLATION_TITLE,
                quote=passage.text,
            )
        )
        seen_chapters.add(passage.chapter)
        if len(citations) >= limit:
            break
    return citations
