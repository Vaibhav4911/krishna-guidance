from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from urllib.request import Request, urlopen

from app.services.corpus_service import (
    API_ROOT,
    SOURCE_ID,
    SOURCE_URL,
    TRANSLATION_TITLE,
    parse_gutenberg_text,
)

CORPUS_DIR = API_ROOT / "data" / "corpora" / "edwin_arnold"
SOURCE_PATH = CORPUS_DIR / "pg2388.txt"
PASSAGES_PATH = CORPUS_DIR / "passages.jsonl"
MANIFEST_PATH = CORPUS_DIR / "manifest.json"
DOWNLOAD_URL = "https://www.gutenberg.org/cache/epub/2388/pg2388.txt"


def download_source() -> None:
    request = Request(
        DOWNLOAD_URL,
        headers={"User-Agent": "KrishnaGuidanceCorpusIngest/1.0"},
    )
    with urlopen(request, timeout=30) as response:
        content = response.read()
    content.decode("utf-8-sig")
    CORPUS_DIR.mkdir(parents=True, exist_ok=True)
    SOURCE_PATH.write_bytes(content)


def ingest() -> int:
    if not SOURCE_PATH.is_file():
        raise FileNotFoundError(
            f"Source text not found at {SOURCE_PATH}; pass --download to fetch it."
        )

    raw_bytes = SOURCE_PATH.read_bytes()
    source_text = raw_bytes.decode("utf-8-sig")
    passages = parse_gutenberg_text(source_text)
    CORPUS_DIR.mkdir(parents=True, exist_ok=True)

    with PASSAGES_PATH.open("w", encoding="utf-8", newline="\n") as output:
        for passage in passages:
            output.write(
                json.dumps(passage.__dict__, ensure_ascii=False, sort_keys=True) + "\n"
            )

    manifest = {
        "source_id": SOURCE_ID,
        "title": "The Song Celestial; Or, Bhagavad-Gita (from the Mahabharata)",
        "translator": "Sir Edwin Arnold",
        "translation_publication_year": 1885,
        "source_printed_edition_year": 1900,
        "language": "en",
        "source_url": SOURCE_URL,
        "download_url": DOWNLOAD_URL,
        "license_url": "https://www.gutenberg.org/policy/license.html",
        "rights_status": "public_domain_us_verified_other_jurisdictions_unverified",
        "rights_note": (
            "Project Gutenberg identifies this eBook as public domain in the United States. "
            "Verify rights in each deployment jurisdiction before redistribution or production use."
        ),
        "attribution": (
            "The Song Celestial; Or, Bhagavad-Gita, translated by Sir Edwin Arnold; "
            "Project Gutenberg eBook #2388."
        ),
        "citation_granularity": "chapter_only",
        "verse_alignment": "not_provided_by_source",
        "source_sha256": hashlib.sha256(raw_bytes).hexdigest(),
        "passage_count": len(passages),
        "chapter_count": len({passage.chapter for passage in passages}),
    }
    MANIFEST_PATH.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return len(passages)


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest Project Gutenberg eBook #2388.")
    parser.add_argument(
        "--download",
        action="store_true",
        help="Download the source text before generating normalized passages.",
    )
    args = parser.parse_args()
    if args.download:
        download_source()
    passage_count = ingest()
    print(f"Ingested {passage_count} chapter-level passages from {SOURCE_PATH.name}.")


if __name__ == "__main__":
    main()
