from types import SimpleNamespace

from qdrant_client import QdrantClient

from app.scripts import ingest_sanskrit_embeddings
from app.services import sanskrit_rag_service
from app.services.sanskrit_corpus import get_sanskrit_verse


def test_embedding_ingestion_indexes_verses_for_exact_retrieval(tmp_path, monkeypatch):
    collection_name = "test_bhagavad_gita"
    client = QdrantClient(path=str(tmp_path / "qdrant"))
    settings_stub = SimpleNamespace(
        qdrant_collection=collection_name,
        llm_embedding_dimensions=2,
    )
    monkeypatch.setattr(ingest_sanskrit_embeddings, "settings", settings_stub)
    monkeypatch.setattr(sanskrit_rag_service, "settings", settings_stub)
    monkeypatch.setattr(
        ingest_sanskrit_embeddings, "get_qdrant_client", lambda: client
    )
    monkeypatch.setattr(sanskrit_rag_service, "get_qdrant_client", lambda: client)

    def fake_corpus_embeddings(texts):
        return [
            [1.0, 0.0] if "chapter 2, verse 47." in text else [0.0, 1.0]
            for text in texts
        ]

    monkeypatch.setattr(
        ingest_sanskrit_embeddings, "embed_texts", fake_corpus_embeddings
    )
    monkeypatch.setattr(
        sanskrit_rag_service,
        "embed_texts",
        lambda texts: [[1.0, 0.0] for _ in texts],
    )
    monkeypatch.setattr(
        sanskrit_rag_service, "retrieve_related_passages", lambda query, limit: []
    )

    try:
        assert ingest_sanskrit_embeddings.ingest() == 700
        verse = get_sanskrit_verse(2, 47)
        assert verse is not None
        assert sanskrit_rag_service.retrieve_sanskrit_verses(
            "karma and action", limit=1
        ) == [verse]
    finally:
        client.close()
