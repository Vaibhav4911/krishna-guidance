from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from app.schemas import Citation

API_ROOT = Path(__file__).resolve().parents[2]
VERSES_PATH = API_ROOT / "data" / "corpora" / "wikisource_sanskrit" / "verses.jsonl"

SOURCE_ID = "wikisource-sa-bhagavad-gita"
SOURCE_TITLE = "Sanskrit Wikisource"
SOURCE_INDEX_TITLE = "भगवद्गीता"
WIKISOURCE_BASE_URL = "https://sa.wikisource.org"
WIKIMEDIA_TERMS_URL = "https://foundation.wikimedia.org/wiki/Policy:Terms_of_Use"
LANGUAGE = "sa"
EXPECTED_VERSE_COUNTS = (
    47, 72, 43, 42, 29, 47, 30, 28, 34,
    42, 55, 20, 34, 27, 20, 24, 28, 78,
)
DEVANAGARI_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")
VERSE_MARKER = re.compile(r"॥\s*([०-९]+)\s*-\s*([०-९]+)\s*॥")
POEM_BLOCK = re.compile(r"<poem>(.*?)</poem>", re.IGNORECASE | re.DOTALL)


@dataclass(frozen=True)
class SanskritVerse:
    verse_id: str
    source_id: str
    language: str
    chapter: int
    verse: int
    text: str
    source_url: str
    revision_id: int


def _clean_verse(raw_text: str) -> str:
    raw_text = re.sub(r"<!--.*?-->", "", raw_text, flags=re.DOTALL)
    raw_text = re.sub(r"<br\s*/?>", "\n", raw_text, flags=re.IGNORECASE)
    raw_text = re.sub(r"<[^>]+>", "", raw_text)
    raw_text = raw_text.replace("'''", "").replace("''", "")
    raw_text = html.unescape(raw_text)

    lines: list[str] = []
    for raw_line in raw_text.splitlines():
        line = " ".join(raw_line.split())
        if not line or line in {"ॐ", "श्रीपरमात्मने नमः"}:
            continue
        if line.endswith("उवाच"):
            continue
        if line == "अध्यायः" or (
            line.startswith("अथ ") and "अध्याय" in line
        ):
            continue
        lines.append(line)

    text = " ".join(lines).strip()
    if not text:
        raise ValueError("A verse marker has no Sanskrit text before it.")
    return f"{text} ॥"


def parse_chapter_wikitext(
    wikitext: str,
    expected_chapter: int | None,
    source_url: str,
    revision_id: int,
) -> list[SanskritVerse]:
    verses: list[SanskritVerse] = []
    for block in POEM_BLOCK.findall(wikitext):
        previous_end = 0
        for marker in VERSE_MARKER.finditer(block):
            chapter, verse = (
                int(value.translate(DEVANAGARI_DIGITS))
                for value in marker.groups()
            )
            if expected_chapter is not None and chapter != expected_chapter:
                raise ValueError(
                    f"Chapter {expected_chapter} page contains a marker for chapter {chapter}."
                )
            verse_text = _clean_verse(block[previous_end:marker.start()])
            verses.append(
                SanskritVerse(
                    verse_id=f"{SOURCE_ID}:{chapter}:{verse}",
                    source_id=SOURCE_ID,
                    language=LANGUAGE,
                    chapter=chapter,
                    verse=verse,
                    text=verse_text,
                    source_url=source_url,
                    revision_id=revision_id,
                )
            )
            previous_end = marker.end()

    chapters = {verse.chapter for verse in verses}
    if len(chapters) != 1:
        raise ValueError(f"Expected one chapter per page, found {sorted(chapters)}.")
    chapter = next(iter(chapters))
    if not 1 <= chapter <= len(EXPECTED_VERSE_COUNTS):
        raise ValueError(f"Unexpected chapter number: {chapter}.")
    expected_count = EXPECTED_VERSE_COUNTS[chapter - 1]
    actual_numbers = [verse.verse for verse in verses]
    if actual_numbers != list(range(1, expected_count + 1)):
        raise ValueError(
            f"Chapter {chapter} expected verses 1-{expected_count} in order; "
            f"found {actual_numbers!r}."
        )
    if expected_chapter is not None and chapter != expected_chapter:
        raise ValueError(
            f"Expected chapter {expected_chapter}, found chapter {chapter}."
        )
    return verses


@lru_cache(maxsize=1)
def load_sanskrit_verses() -> tuple[SanskritVerse, ...]:
    if not VERSES_PATH.is_file():
        raise FileNotFoundError(
            f"Sanskrit verse corpus is missing at {VERSES_PATH}. "
            "Run `python -m app.scripts.ingest_wikisource_sanskrit` from apps/api."
        )
    with VERSES_PATH.open(encoding="utf-8") as corpus_file:
        verses = tuple(
            SanskritVerse(**json.loads(line))
            for line in corpus_file
            if line.strip()
        )

    expected_count = sum(EXPECTED_VERSE_COUNTS)
    if len(verses) != expected_count:
        raise ValueError(
            f"Expected {expected_count} Sanskrit verses, found {len(verses)}."
        )
    return verses


def get_sanskrit_verse(chapter: int, verse: int) -> SanskritVerse | None:
    if not 1 <= chapter <= len(EXPECTED_VERSE_COUNTS):
        return None
    if not 1 <= verse <= EXPECTED_VERSE_COUNTS[chapter - 1]:
        return None
    return load_sanskrit_verses()[
        sum(EXPECTED_VERSE_COUNTS[:chapter - 1]) + verse - 1
    ]


def build_sanskrit_citation(
    verse: SanskritVerse,
    meaning: str | None = None,
    explanation: str | None = None,
) -> Citation:
    return Citation(
        chapter=verse.chapter,
        verse=verse.verse,
        source=SOURCE_TITLE,
        source_url=verse.source_url,
        language=LANGUAGE,
        translation="Original Sanskrit verse",
        quote=verse.text,
        meaning=meaning,
        explanation=explanation,
    )
