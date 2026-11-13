from __future__ import annotations

import argparse
import hashlib
from uuid import NAMESPACE_URL, uuid5

from qdrant_client.models import Distance, PointStruct, VectorParams

from app.config import settings
from app.services.openai_service import embed_texts
from app.services.sanskrit_corpus import VERSES_PATH, load_sanskrit_verses
from app.services.sanskrit_rag_service import get_qdrant_client

EMBEDDING_BATCH_SIZE = 64


def ingest(replace_existing: bool = False) -> int:
    verses = load_sanskrit_verses()
    client = get_qdrant_client()
    collection_exists = client.collection_exists(settings.qdrant_collection)
    if collection_exists and not replace_existing:
        raise ValueError(
            f"Qdrant collection {settings.qdrant_collection!r} already exists. "
            "Pass --replace to rebuild it."
        )

    vectors: list[list[float]] = []
    for offset in range(0, len(verses), EMBEDDING_BATCH_SIZE):
        batch = verses[offset : offset + EMBEDDING_BATCH_SIZE]
        inputs = [
            f"Bhagavad Gita chapter {verse.chapter}, verse {verse.verse}. "
            f"Sanskrit: {verse.text}"
            for verse in batch
        ]
        vectors.extend(embed_texts(inputs))

    if len(vectors) != len(verses):
        raise ValueError(
            f"Expected {len(verses)} embeddings, received {len(vectors)}."
        )

    if collection_exists:
        client.delete_collection(settings.qdrant_collection)
    client.create_collection(
        collection_name=settings.qdrant_collection,
        vectors_config=VectorParams(
            size=settings.openai_embedding_dimensions,
            distance=Distance.COSINE,
        ),
    )
    source_hash = hashlib.sha256(VERSES_PATH.read_bytes()).hexdigest()
    points = [
        PointStruct(
            id=str(uuid5(NAMESPACE_URL, verse.verse_id)),
            vector=vector,
            payload={
                "verse_id": verse.verse_id,
                "chapter": verse.chapter,
                "verse": verse.verse,
                "language": verse.language,
                "corpus_sha256": source_hash,
            },
        )
        for verse, vector in zip(verses, vectors)
    ]
    client.upsert(
        collection_name=settings.qdrant_collection,
        points=points,
        wait=True,
    )
    return len(points)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create multilingual OpenAI embeddings for the Sanskrit Gita in Qdrant."
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Replace the configured collection after all new embeddings are created.",
    )
    args = parser.parse_args()
    count = ingest(replace_existing=args.replace)
    print(f"Indexed {count} Sanskrit verses in Qdrant collection {settings.qdrant_collection}.")


if __name__ == "__main__":
    main()
