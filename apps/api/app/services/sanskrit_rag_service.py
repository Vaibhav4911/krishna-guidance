from __future__ import annotations

import hashlib
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from qdrant_client import QdrantClient
from qdrant_client.models import FieldCondition, Filter, MatchAny

from app.config import settings
from app.services.corpus_service import (
    expand_retrieval_query,
    retrieve_related_passages,
)
from app.services.model_service import embed_texts, translate_query_to_english
from app.services.sanskrit_corpus import (
    API_ROOT,
    EXPECTED_VERSE_COUNTS,
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


def retrieve_sanskrit_verses(
    query: str,
    limit: int = 8,
    language: Literal["en", "hi"] = "en",
) -> list[SanskritVerse]:
    if limit <= 0 or not query.strip():
        return []
    if language == "hi":
        search_query = translate_query_to_english(query)
    elif language == "en":
        search_query = query
    else:
        raise ValueError(f"Unsupported retrieval language: {language!r}.")

    client = get_qdrant_client()
    if not client.collection_exists(settings.qdrant_collection):
        raise SanskritIndexUnavailableError(
            "The Sanskrit verse index is missing. Run "
            "`python -m app.scripts.ingest_sanskrit_embeddings` after starting the "
            "self-hosted embedding server."
        )

    related_passages = retrieve_related_passages(search_query, limit=8)
    chapter_query = expand_retrieval_query(search_query)
    queries_to_embed = [search_query]
    if chapter_query != search_query:
        queries_to_embed.append(chapter_query)
    query_vectors = embed_texts(queries_to_embed)
    query_vector = query_vectors[0]
    chapter_query_vector = (
        query_vector
        if chapter_query == search_query
        else query_vectors[1]
    )
    verses_by_id = {verse.verse_id: verse for verse in load_sanskrit_verses()}
    expected_hash = corpus_sha256()
    reciprocal_rank_scores: dict[str, float] = {}

    def validate_point(point: Any) -> str:
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
        return verse_id

    global_result = client.query_points(
        collection_name=settings.qdrant_collection,
        query=query_vector,
        limit=limit,
        with_payload=True,
    )
    for rank, point in enumerate(global_result.points, start=1):
        verse_id = validate_point(point)
        reciprocal_rank_scores[verse_id] = 1 / (60 + rank)

    chapter_ids = [passage.chapter for passage in related_passages]
    if chapter_ids:
        chapter_result = client.query_points(
            collection_name=settings.qdrant_collection,
            query=chapter_query_vector,
            query_filter=Filter(
                must=[
                    FieldCondition(
                        key="chapter",
                        match=MatchAny(any=chapter_ids),
                    )
                ]
            ),
            limit=sum(EXPECTED_VERSE_COUNTS[chapter - 1] for chapter in chapter_ids),
            with_payload=True,
        )
        chapter_ranks = {
            chapter: rank for rank, chapter in enumerate(chapter_ids, start=1)
        }
        seen_chapters: set[int] = set()
        for point in chapter_result.points:
            payload = point.payload or {}
            verse_id = validate_point(point)
            chapter = payload.get("chapter")
            if not isinstance(chapter, int) or chapter not in chapter_ranks:
                raise SanskritIndexUnavailableError(
                    "The Sanskrit verse index contains an unrecognized chapter."
                )
            if chapter in seen_chapters:
                continue
            seen_chapters.add(chapter)
            reciprocal_rank_scores[verse_id] = (
                reciprocal_rank_scores.get(verse_id, 0)
                + 1 / (60 + chapter_ranks[chapter])
                + 1 / (60 + 1)
            )

    verses: list[SanskritVerse] = []
    ranked_verse_ids = sorted(
        reciprocal_rank_scores,
        key=lambda verse_id: reciprocal_rank_scores[verse_id],
        reverse=True,
    )
    for verse_id in ranked_verse_ids:
        verses.append(verses_by_id[verse_id])
        if len(verses) == limit:
            break
    return verses
