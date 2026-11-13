from __future__ import annotations

import hashlib
from functools import lru_cache
from pathlib import Path

from qdrant_client import QdrantClient

from app.config import settings
from app.services.openai_service import embed_texts
from app.services.sanskrit_corpus import (
    API_ROOT,
    VERSES_PATH,
    SanskritVerse,
    load_sanskrit_verses,
)

QDRANT_PATH = API_ROOT / "data" / "qdrant"


class SanskritIndexUnavailableError(RuntimeError):
    pass


def corpus_sha256() -> str:
    return hashlib.sha256(VERSES_PATH.read_bytes()).hexdigest()


@lru_cache(maxsize=1)
def get_qdrant_client() -> QdrantClient:
    if settings.qdrant_url:
        return QdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key,
        )
    Path(QDRANT_PATH).parent.mkdir(parents=True, exist_ok=True)
    return QdrantClient(path=str(QDRANT_PATH))


def retrieve_sanskrit_verses(query: str, limit: int = 8) -> list[SanskritVerse]:
    if limit <= 0 or not query.strip():
        return []

    client = get_qdrant_client()
    if not client.collection_exists(settings.qdrant_collection):
        raise SanskritIndexUnavailableError(
            "The Sanskrit verse index is missing. Run "
            "`python -m app.scripts.ingest_sanskrit_embeddings` from apps/api."
        )

    query_vector = embed_texts([query])[0]
    result = client.query_points(
        collection_name=settings.qdrant_collection,
        query=query_vector,
        limit=limit,
        with_payload=True,
    )
    verses_by_id = {verse.verse_id: verse for verse in load_sanskrit_verses()}
    expected_hash = corpus_sha256()
    verses: list[SanskritVerse] = []
    seen_ids: set[str] = set()

    for point in result.points:
        payload = point.payload or {}
        if payload.get("corpus_sha256") != expected_hash:
            raise SanskritIndexUnavailableError(
                "The Sanskrit verse index is stale. Rebuild it with "
                "`python -m app.scripts.ingest_sanskrit_embeddings --replace`."
            )
        verse_id = payload.get("verse_id")
        if not isinstance(verse_id, str) or verse_id not in verses_by_id:
            raise SanskritIndexUnavailableError(
                "The Sanskrit verse index contains an unrecognized source record."
            )
        if verse_id not in seen_ids:
            verses.append(verses_by_id[verse_id])
            seen_ids.add(verse_id)
    return verses
