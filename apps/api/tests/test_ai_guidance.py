import json
from types import SimpleNamespace
from uuid import uuid4

from app.db.models import User
from app.routes import chat, rag
from app.schemas import ChatMessageRequest
from app.services import response_service, sanskrit_rag_service
from app.services.auth_service import create_user_session
from app.services.openai_service import OpenAIConfigurationError
from app.services.sanskrit_corpus import (
    build_sanskrit_citation,
    get_sanskrit_verse,
)


def _create_auth_headers(session_factory):
    with session_factory() as db:
        user = User(email=f"ai-{uuid4().hex}@example.test", display_name="Test")
        db.add(user)
        db.commit()
        db.refresh(user)
        token, _ = create_user_session(db, user)
    return {"Authorization": f"Bearer {token}"}


def test_multilingual_guidance_only_cites_retrieved_source_verses(monkeypatch):
    verse = get_sanskrit_verse(2, 47)
    assert verse is not None
    captured: dict[str, str] = {}

    def fake_generate(system_prompt: str, user_content: str) -> dict:
        captured["system"] = system_prompt
        captured["user"] = user_content
        return {
            "answer": "कर्मण्येवाधिकारस्ते इति श्लोकस्य अर्थः AI-निर्मितः विचारः।",
            "citation_ids": [verse.verse_id, "invented:99:99"],
        }

    monkeypatch.setattr(
        response_service, "retrieve_sanskrit_verses", lambda query, limit: [verse]
    )
    monkeypatch.setattr(response_service, "generate_json_response", fake_generate)

    response = response_service.build_guidance(
        ChatMessageRequest(message="काम के फल की चिंता है", language="hi")
    )

    prompt_payload = json.loads(captured["user"])
    assert prompt_payload["response_language"] == "Hindi"
    assert prompt_payload["candidate_verses"][0]["verse_id"] == verse.verse_id
    assert response.language == "hi"
    assert response.citations == [build_sanskrit_citation(verse)]
    assert response.citations[0].quote == verse.text


def test_guidance_without_retrieved_verses_returns_no_scripture_citation(monkeypatch):
    monkeypatch.setattr(
        response_service, "retrieve_sanskrit_verses", lambda query, limit: []
    )
    monkeypatch.setattr(
        response_service,
        "generate_json_response",
        lambda system_prompt, user_content: {
            "answer": "I could not find a sufficiently relevant source verse.",
            "citation_ids": [],
        },
    )

    response = response_service.build_guidance(
        ChatMessageRequest(message="A question with no matching source")
    )

    assert response.citations == []


def test_rag_search_returns_original_sanskrit_for_hindi_query(test_context, monkeypatch):
    client, session_factory = test_context
    verse = get_sanskrit_verse(2, 47)
    assert verse is not None
    monkeypatch.setattr(rag, "retrieve_sanskrit_verses", lambda query, limit: [verse])

    response = client.post(
        "/api/v1/rag/search",
        headers=_create_auth_headers(session_factory),
        json={"query": "कर्म का फल", "language": "hi"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["language"] == "hi"
    assert body["citations"][0]["chapter"] == 2
    assert body["citations"][0]["verse"] == 47
    assert body["citations"][0]["language"] == "sa"


def test_rag_search_requires_authentication(test_context):
    client, _ = test_context

    response = client.post(
        "/api/v1/rag/search",
        json={"query": "wisdom", "language": "en"},
    )

    assert response.status_code == 401


def test_rag_endpoint_rejects_unsupported_language(test_context):
    client, session_factory = test_context

    response = client.post(
        "/api/v1/rag/search",
        headers=_create_auth_headers(session_factory),
        json={"query": "wisdom", "language": "fr"},
    )

    assert response.status_code == 422


def test_chat_reports_missing_openai_configuration(test_context, monkeypatch):
    client, session_factory = test_context

    def raise_configuration_error(payload):
        raise OpenAIConfigurationError("Set OPENAI_API_KEY.")

    monkeypatch.setattr(chat, "build_guidance", raise_configuration_error)
    response = client.post(
        "/api/v1/chat/message",
        headers=_create_auth_headers(session_factory),
        json={"message": "I feel uncertain", "language": "en"},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "Set OPENAI_API_KEY."


def test_vector_retrieval_resolves_qdrant_hits_to_local_corpus_verses(monkeypatch):
    verse = get_sanskrit_verse(2, 47)
    assert verse is not None
    payload = {
        "corpus_sha256": "verified-hash",
        "verse_id": verse.verse_id,
    }

    class FakeQdrantClient:
        def collection_exists(self, collection_name):
            return True

        def query_points(self, **kwargs):
            assert kwargs["limit"] == 1
            return SimpleNamespace(points=[SimpleNamespace(payload=payload)])

    monkeypatch.setattr(
        sanskrit_rag_service, "get_qdrant_client", lambda: FakeQdrantClient()
    )
    monkeypatch.setattr(sanskrit_rag_service, "embed_texts", lambda texts: [[0.1]])
    monkeypatch.setattr(sanskrit_rag_service, "corpus_sha256", lambda: "verified-hash")

    assert sanskrit_rag_service.retrieve_sanskrit_verses("karma", limit=1) == [verse]
