from __future__ import annotations

import argparse
import hashlib
import json
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.services.sanskrit_corpus import (
    API_ROOT,
    EXPECTED_VERSE_COUNTS,
    SOURCE_ID,
    SOURCE_INDEX_TITLE,
    WIKIMEDIA_TERMS_URL,
    WIKISOURCE_BASE_URL,
    SanskritVerse,
    parse_chapter_wikitext,
)

CORPUS_DIR = API_ROOT / "data" / "corpora" / "wikisource_sanskrit"
VERSES_PATH = CORPUS_DIR / "verses.jsonl"
MANIFEST_PATH = CORPUS_DIR / "manifest.json"
USER_AGENT = "KrishnaGuidance/0.1 (Sanskrit corpus ingestion; https://sa.wikisource.org)"


def _fetch_json(url: str) -> dict:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(5):
        try:
            with urlopen(request, timeout=90) as response:
                return json.load(response)
        except HTTPError as error:
            if error.code != 429 or attempt == 4:
                raise
            retry_after = error.headers.get("Retry-After")
            try:
                delay = float(retry_after) if retry_after else 5.0 * (attempt + 1)
            except ValueError:
                delay = max(
                    1.0,
                    (parsedate_to_datetime(retry_after) - datetime.now(timezone.utc)).total_seconds(),
                )
            time.sleep(min(max(delay, 1.0), 120.0))


def _chapter_titles() -> list[str]:
    url = f"{WIKISOURCE_BASE_URL}/w/api.php?{urlencode({
        'action': 'query',
        'titles': SOURCE_INDEX_TITLE,
        'prop': 'links',
        'plnamespace': 0,
        'pllimit': 'max',
        'format': 'json',
        'formatversion': 2,
    })}"
    result = _fetch_json(url)
    pages = result.get("query", {}).get("pages", [])
    if len(pages) != 1:
        raise ValueError("Wikisource did not return the expected Gita index page.")
    titles = [
        link["title"]
        for link in pages[0].get("links", [])
        if link["title"].startswith(f"{SOURCE_INDEX_TITLE}/")
    ]
    if len(titles) != len(EXPECTED_VERSE_COUNTS):
        raise ValueError(
            f"Expected 18 chapter pages from Wikisource, found {len(titles)}."
        )
    return titles


def _fetch_page_revision(title: str) -> tuple[str, int, str, str, str]:
    url = f"{WIKISOURCE_BASE_URL}/w/api.php?{urlencode({
        'action': 'query',
        'titles': title,
        'redirects': 1,
        'prop': 'revisions',
        'rvprop': 'ids|timestamp|content',
        'rvslots': 'main',
        'format': 'json',
        'formatversion': 2,
    })}"
    result = _fetch_json(url)
    pages = result.get("query", {}).get("pages", [])
    if len(pages) != 1 or "missing" in pages[0]:
        raise ValueError(f"Wikisource chapter page is missing: {title}")

    page = pages[0]
    revisions = page.get("revisions", [])
    if not revisions:
        raise ValueError(f"Wikisource chapter page has no revisions: {title}")
    revision = revisions[0]
    content = revision.get("slots", {}).get("main", {}).get("content")
    if not isinstance(content, str):
        raise ValueError(f"Wikisource did not return chapter text for {title}.")

    page_url = (
        f"{WIKISOURCE_BASE_URL}/w/index.php?"
        f"{urlencode({'title': page['title'], 'oldid': revision['revid']})}"
    )
    return page["title"], revision["revid"], revision["timestamp"], content, page_url


def ingest() -> int:
    titles = _chapter_titles()
    all_verses: list[SanskritVerse] = []
    chapter_sources: dict[str, dict[str, object]] = {}
    seen_chapters: set[int] = set()

    for title in titles:
        resolved_title, revision_id, revision_timestamp, wikitext, page_url = (
            _fetch_page_revision(title)
        )
        verse_markers = parse_chapter_wikitext(
            wikitext,
            expected_chapter=None,
            source_url=page_url,
            revision_id=revision_id,
        )
        chapter = verse_markers[0].chapter
        if chapter in seen_chapters:
            raise ValueError(f"Duplicate Wikisource page for chapter {chapter}.")
        seen_chapters.add(chapter)
        all_verses.extend(verse_markers)
        chapter_sources[str(chapter)] = {
            "title": resolved_title,
            "revision_id": revision_id,
            "revision_timestamp": revision_timestamp,
            "source_url": page_url,
            "wikitext_sha256": hashlib.sha256(wikitext.encode("utf-8")).hexdigest(),
            "verse_count": len(verse_markers),
        }
        time.sleep(1.0)

    if seen_chapters != set(range(1, len(EXPECTED_VERSE_COUNTS) + 1)):
        raise ValueError(f"Expected all 18 chapters; found {sorted(seen_chapters)}.")
    all_verses.sort(key=lambda verse: (verse.chapter, verse.verse))
    expected_count = sum(EXPECTED_VERSE_COUNTS)
    if len(all_verses) != expected_count:
        raise ValueError(f"Expected {expected_count} verses, found {len(all_verses)}.")

    CORPUS_DIR.mkdir(parents=True, exist_ok=True)
    with VERSES_PATH.open("w", encoding="utf-8", newline="\n") as output:
        for verse in all_verses:
            output.write(
                json.dumps(verse.__dict__, ensure_ascii=False, sort_keys=True) + "\n"
            )

    manifest = {
        "source_id": SOURCE_ID,
        "title": "Bhagavad Gita (Sanskrit mūlapāṭha)",
        "language": "sa",
        "source_index_url": f"{WIKISOURCE_BASE_URL}/wiki/{SOURCE_INDEX_TITLE}",
        "license": "CC BY-SA 4.0 for Wikimedia contributor content",
        "license_url": WIKIMEDIA_TERMS_URL,
        "attribution": (
            "Sanskrit text transcribed from Sanskrit Wikisource. Attribute Wikisource "
            "contributors and link to each source page/revision. Share derivatives of "
            "the transcribed corpus under CC BY-SA 4.0."
        ),
        "citation_granularity": "chapter_and_verse",
        "chapter_count": len(seen_chapters),
        "verse_count": len(all_verses),
        "chapter_verse_counts": list(EXPECTED_VERSE_COUNTS),
        "downloaded_at": datetime.now(timezone.utc).isoformat(),
        "chapter_sources": chapter_sources,
    }
    MANIFEST_PATH.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return len(all_verses)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download and validate the Sanskrit Bhagavad Gita from Wikisource."
    )
    parser.parse_args()
    count = ingest()
    print(f"Ingested {count} source-versioned Sanskrit verses from Wikisource.")


if __name__ == "__main__":
    main()
