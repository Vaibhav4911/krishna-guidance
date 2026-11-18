import json
from types import SimpleNamespace
from uuid import uuid4

from app.db.models import User
from app.routes import chat, rag
from app.schemas import ChatMessageRequest
from app.services import (
    model_service,
    response_service,
    sanskrit_rag_service,
)
from app.services.auth_service import create_user_session
from app.services.model_service import ModelProviderError
from app.scripts import ingest_sanskrit_embeddings
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

    def fake_generate(
        system_prompt: str,
        user_content: str,
        response_schema: dict | None = None,
    ) -> dict:
        captured["system"] = system_prompt
        captured["user"] = user_content
        return {
            "answer": "अपने काम पर ध्यान दें। परिणाम हमेशा आपके वश में नहीं होते।",
            "citation_ids": [verse.verse_id, "invented:99:99"],
            "verse_explanations": [
                {
                    "verse_id": verse.verse_id,
                    "meaning": "कर्म करते रहें, लेकिन फल को अपने नियंत्रण में न मानें।",
                    "explanation": "यह श्लोक प्रयास पर ध्यान देने और परिणामों से अत्यधिक आसक्ति न रखने की सीख देता है।",
                },
                {
                    "verse_id": "invented:99:99",
                    "meaning": "यह स्रोत में नहीं है।",
                    "explanation": "इसे उपयोग नहीं किया जाना चाहिए।",
                },
            ],
        }

    monkeypatch.setattr(
        response_service,
        "retrieve_sanskrit_verses",
        lambda query, limit, language: [verse],
    )
    monkeypatch.setattr(response_service, "generate_json_response", fake_generate)

    response = response_service.build_guidance(
        ChatMessageRequest(message="काम के फल की चिंता है", language="hi")
    )

    prompt_payload = json.loads(captured["user"])
    assert prompt_payload["response_language"] == "Hindi"
    assert prompt_payload["candidate_verses"][0]["verse_id"] == verse.verse_id
    assert "Do not answer in Sanskrit" in captured["system"]
    assert "very simple, everyday words" in captured["system"]
    assert "not authoritative translations" in captured["system"]
    assert response.language == "hi"
    assert response.citations[0].meaning.startswith("आपका अधिकार कर्म करने में है")
    assert response.citations[0].explanation.startswith("यह श्लोक")
    assert len(response.citations) == 1
    assert response.citations[0].quote == verse.text


def test_guidance_without_retrieved_verses_returns_no_scripture_citation(monkeypatch):
    monkeypatch.setattr(
        response_service,         "retrieve_sanskrit_verses", lambda query, limit, language: []
    )
    monkeypatch.setattr(
        response_service,
        "generate_json_response",
        lambda system_prompt, user_content, response_schema=None: {
            "answer": "I could not find a sufficiently relevant source verse.",
            "citation_ids": [],
            "verse_explanations": [],
        },
    )

    response = response_service.build_guidance(
        ChatMessageRequest(message="A question with no matching source")
    )

    assert response.citations == []


def test_emotional_life_confusion_gets_specific_grounded_response(monkeypatch):
    verse = get_sanskrit_verse(2, 7)
    assert verse is not None
    monkeypatch.setattr(
        response_service,
        "retrieve_sanskrit_verses",
        lambda query, limit, language: [verse],
    )
    monkeypatch.setattr(
        response_service,
        "generate_json_response",
        lambda system_prompt, user_content, response_schema=None: {
            "answer": "It's okay to feel this way. Take one small step.",
            "citation_ids": [verse.verse_id],
            "verse_explanations": [],
        },
    )

    response = response_service.build_guidance(
        ChatMessageRequest(
            message="Feeling heavy, frustrated and not having clarity what to do in life."
        )
    )

    assert "heavy and frustrated" in response.answer
    assert "Confused about what is right" in response.answer
    assert "What decision is weighing on you most" in response.answer
    assert "Take one small step" not in response.answer


def test_guidance_uses_recent_history_to_answer_follow_up(monkeypatch):
    captured = {}

    def fake_retrieve(query, limit, language):
        captured["query"] = query
        captured["limit"] = limit
        return []

    def fake_generate(system_prompt, user_content, response_schema=None):
        captured["prompt"] = json.loads(user_content)
        return {
            "answer": "Start with a short, steady practice and build from there.",
            "citation_ids": [],
            "verse_explanations": [],
        }

    monkeypatch.setattr(response_service, "retrieve_sanskrit_verses", fake_retrieve)
    monkeypatch.setattr(response_service, "generate_json_response", fake_generate)

    history = [
        {"role": "user", "content": "I struggle to focus during prayer."},
        {
            "role": "assistant",
            "content": "Try returning to your focus gently.",
            "citation_ids": ["3:17"],
        },
    ]
    response = response_service.build_guidance(
        ChatMessageRequest(
            message="I need more clarity on this.",
            history=history,
        )
    )

    assert "I struggle to focus during prayer." in captured["query"]
    assert "I need more clarity on this." in captured["query"]
    assert captured["limit"] == 24
    assert captured["prompt"]["follow_up_intent"] == "clarification"
    assert "feeling unclear about what to do" in response.answer
    assert "Which part should I clarify first" in response.answer
    assert captured["prompt"]["conversation_history"] == [
        {**message, "citation_ids": message.get("citation_ids", [])}
        for message in history
    ]


def test_vague_follow_up_asks_what_the_user_needs(monkeypatch):
    def unexpected_call(*args, **kwargs):
        raise AssertionError("A vague follow-up should ask for clarification directly.")

    monkeypatch.setattr(response_service, "retrieve_sanskrit_verses", unexpected_call)
    monkeypatch.setattr(response_service, "generate_json_response", unexpected_call)

    response = response_service.build_guidance(
        ChatMessageRequest(
            message="I need for from you",
            history=[
                {"role": "user", "content": "I feel uncertain about my life."},
                {"role": "assistant", "content": "Take one small step."},
            ],
        )
    )

    assert response.citations == []
    assert "instead of guessing" in response.answer
    assert "help thinking through a decision" in response.answer


def test_guidance_cites_top_retrieved_verse_when_model_omits_citation(monkeypatch):
    verse = get_sanskrit_verse(2, 47)
    assert verse is not None
    monkeypatch.setattr(
        response_service,
        "retrieve_sanskrit_verses",
        lambda query, limit, language: [verse],
    )
    def fake_generate(system_prompt, user_content, response_schema=None):
        if response_schema == response_service.EXPLANATION_RESPONSE_SCHEMA:
            return {
                "verse_explanations": [
                    {
                        "verse_id": verse.verse_id,
                        "meaning": "Do your work without depending on its reward.",
                        "explanation": "The verse teaches you to focus on your actions, not to control every result.",
                    }
                ]
            }
        return {
            "answer": "Focus on the work you can do now.",
            "citation_ids": [],
            "verse_explanations": [],
        }
    monkeypatch.setattr(response_service, "generate_json_response", fake_generate)

    response = response_service.build_guidance(
        ChatMessageRequest(message="I worry about the results of my work.")
    )

    assert response.citations[0].verse == verse.verse
    assert response.citations[0].meaning.startswith("Your responsibility is to act")
    assert response.citations[0].explanation.startswith("This verse asks Arjuna")


def test_gita_12_9_uses_curated_plain_language_meaning(monkeypatch):
    verse = get_sanskrit_verse(12, 9)
    assert verse is not None
    monkeypatch.setattr(
        response_service,
        "retrieve_sanskrit_verses",
        lambda query, limit, language: [verse],
    )
    monkeypatch.setattr(
        response_service,
        "generate_json_response",
        lambda system_prompt, user_content, response_schema=None: {
            "answer": "Practice gently and patiently.",
            "citation_ids": [verse.verse_id],
            "verse_explanations": [
                {
                    "verse_id": verse.verse_id,
                    "meaning": "You cannot keep your mind steady.",
                    "explanation": "This verse is about focus.",
                }
            ],
        },
    )

    response = response_service.build_guidance(
        ChatMessageRequest(message="I struggle to focus", language="en")
    )

    assert response.citations[0].meaning == (
        "If you cannot keep your mind steadily fixed on Me, then seek to reach Me "
        "through repeated practice, O Arjuna."
    )
    assert "practice returning the mind" in response.citations[0].explanation

    hindi_response = response_service.build_guidance(
        ChatMessageRequest(message="ध्यान में मन नहीं लगता", language="hi")
    )
    assert hindi_response.citations[0].meaning.startswith(
        "यदि आप अपने मन को मुझ पर स्थिर नहीं कर पाते"
    )


def test_gita_3_17_does_not_equate_self_contentment_with_resolving_confusion(
    monkeypatch,
):
    verse = get_sanskrit_verse(3, 17)
    assert verse is not None
    monkeypatch.setattr(
        response_service,
        "retrieve_sanskrit_verses",
        lambda query, limit, language: [verse],
    )
    monkeypatch.setattr(
        response_service,
        "generate_json_response",
        lambda system_prompt, user_content, response_schema=None: {
            "answer": "Let's take time to identify what feels unclear.",
            "citation_ids": [verse.verse_id],
            "verse_explanations": [
                {
                    "verse_id": verse.verse_id,
                    "meaning": "This verse says there is no confusion about actions.",
                    "explanation": "A calm self always knows the right path.",
                }
            ],
        },
    )

    response = response_service.build_guidance(
        ChatMessageRequest(message="I feel confused about my life.", language="en")
    )

    assert response.citations[0].meaning.startswith(
        "One who delights in the Self"
    )
    assert "no duty to perform" in response.citations[0].meaning
    assert "not an instruction" in response.citations[0].explanation


def test_more_verses_follow_up_excludes_previous_citations(monkeypatch):
    previous = get_sanskrit_verse(3, 17)
    first_new = get_sanskrit_verse(2, 47)
    second_new = get_sanskrit_verse(6, 5)
    assert previous is not None
    assert first_new is not None
    assert second_new is not None
    captured = {}

    def fake_retrieve(query, limit, language):
        captured["query"] = query
        captured["limit"] = limit
        return [previous, first_new, second_new]

    def fake_generate(system_prompt, user_content, response_schema=None):
        payload = json.loads(user_content)
        if response_schema == response_service.EXPLANATION_RESPONSE_SCHEMA:
            missing_verse = payload["verses"][0]
            return {
                "verse_explanations": [
                    {
                        "verse_id": missing_verse["verse_id"],
                        "meaning": "Lift yourself by your own effort.",
                        "explanation": "This verse encourages steady self-effort.",
                    }
                ]
            }
        captured["prompt"] = payload
        return {
            "answer": "Here are two other passages that offer complementary guidance.",
            "citation_ids": [first_new.verse_id],
            "verse_explanations": [
                {
                    "verse_id": first_new.verse_id,
                    "meaning": "Act without attachment to the results.",
                    "explanation": "Focus on the work you can do, not on controlling every outcome.",
                }
            ],
        }

    monkeypatch.setattr(response_service, "retrieve_sanskrit_verses", fake_retrieve)
    monkeypatch.setattr(response_service, "generate_json_response", fake_generate)

    response = response_service.build_guidance(
        ChatMessageRequest(
            message="Can you give me more verses on this?",
            history=[
                {"role": "user", "content": "I feel confused about my life."},
                {
                    "role": "assistant",
                    "content": "Let's clarify what feels uncertain.",
                    "citation_ids": ["3:17"],
                },
            ],
        )
    )

    references = {
        f"{citation.chapter}:{citation.verse}" for citation in response.citations
    }
    assert captured["limit"] == 24
    assert captured["prompt"]["follow_up_intent"] == "more_verses"
    assert "3:17" in captured["prompt"]["previous_citation_ids"]
    assert "3:17" not in {
        f"{candidate['chapter']}:{candidate['verse']}"
        for candidate in captured["prompt"]["candidate_verses"]
    }
    assert references == {"2:47", "6:5"}
    assert "2 different verses" in response.answer


def test_clarification_response_acknowledges_emotion_and_adds_specificity(monkeypatch):
    previous = get_sanskrit_verse(3, 17)
    next_verse = get_sanskrit_verse(2, 7)
    assert previous is not None
    assert next_verse is not None
    monkeypatch.setattr(
        response_service,
        "retrieve_sanskrit_verses",
        lambda query, limit, language: [previous, next_verse],
    )
    monkeypatch.setattr(
        response_service,
        "generate_json_response",
        lambda system_prompt, user_content, response_schema=None: {
            "answer": "Feeling heavy and frustrated? Take one small step today.",
            "citation_ids": [],
            "verse_explanations": [],
        },
    )

    response = response_service.build_guidance(
        ChatMessageRequest(
            message="I need more clarity on this from you.",
            history=[
                {
                    "role": "user",
                    "content": "Feeling heavy, frustrated and not having clarity what to do in life.",
                },
                {
                    "role": "assistant",
                    "content": "Take a small step today.",
                    "citation_ids": ["3:17"],
                },
            ],
        )
    )

    assert response.citations[0].verse == 7
    assert "heavy and frustrated" in response.answer
    assert "Take one small step today" not in response.answer
    assert "Confused about what is right" in response.answer
    assert "What decision is weighing on you most" in response.answer


def test_chat_rejects_excessive_conversation_history(test_context):
    client, session_factory = test_context
    response = client.post(
        "/api/v1/chat/message",
        headers=_create_auth_headers(session_factory),
        json={
            "message": "A follow-up",
            "history": [
                {"role": "user", "content": f"Earlier message {index}"}
                for index in range(9)
            ],
        },
    )

    assert response.status_code == 422


def test_rag_search_returns_original_sanskrit_for_hindi_query(test_context, monkeypatch):
    client, session_factory = test_context
    verse = get_sanskrit_verse(2, 47)
    assert verse is not None
    monkeypatch.setattr(
        rag,
        "retrieve_sanskrit_verses",
        lambda query, limit, language: [verse],
    )

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
        json={"query": "wisdom", "language": "sa"},
    )

    assert response.status_code == 422


def test_chat_reports_unavailable_self_hosted_model(test_context, monkeypatch):
    client, session_factory = test_context

    def raise_configuration_error(payload):
        raise ModelProviderError("Start the local vLLM service.")

    monkeypatch.setattr(chat, "build_guidance", raise_configuration_error)
    response = client.post(
        "/api/v1/chat/message",
        headers=_create_auth_headers(session_factory),
        json={"message": "I feel uncertain", "language": "en"},
    )

    assert response.status_code == 502
    assert response.json()["detail"] == (
        "The self-hosted AI guidance service could not complete the request."
    )


def test_embedding_ingestion_does_not_require_a_paid_api_key(monkeypatch):
    monkeypatch.setattr(
        model_service,
        "settings",
        SimpleNamespace(
            llm_chat_base_url="http://127.0.0.1:8001/v1",
            llm_chat_model="chat-model",
            llm_embeddings_base_url="http://127.0.0.1:8002/v1",
            llm_embedding_model="embedding-model",
            llm_embedding_dimensions=2,
        ),
    )
    monkeypatch.setattr(
        ingest_sanskrit_embeddings,
        "embed_texts",
        lambda texts: [[0.0, 1.0] for _ in texts],
    )
    monkeypatch.setattr(
        ingest_sanskrit_embeddings,
        "VERSES_PATH",
        SimpleNamespace(read_bytes=lambda: b"test-corpus"),
    )

    class FakeClient:
        def collection_exists(self, collection_name):
            return False

        def create_collection(self, **kwargs):
            pass

        def upsert(self, **kwargs):
            pass

    fake_client = FakeClient()
    monkeypatch.setattr(
        ingest_sanskrit_embeddings, "get_qdrant_client", lambda: fake_client
    )

    assert ingest_sanskrit_embeddings.ingest() == 700


def test_model_service_uses_local_embedding_endpoint_without_api_key(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        model_service,
        "settings",
        SimpleNamespace(
            llm_chat_base_url="http://127.0.0.1:8001/v1",
            llm_chat_model="chat-model",
            llm_embeddings_base_url="http://127.0.0.1:8002/v1",
            llm_api_key=None,
            llm_embedding_model="embedding-model",
            llm_embedding_dimensions=2,
        ),
    )

    class FakeResponse:
        is_error = False

        def json(self):
            return {"data": [{"index": 0, "embedding": [0.25, 0.75]}]}

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured.update(kwargs)
        return FakeResponse()

    monkeypatch.setattr(model_service.httpx, "post", fake_post)

    vectors = model_service.embed_texts(["भगवद्गीता"])

    assert vectors == [[0.25, 0.75]]
    assert captured["url"] == "http://127.0.0.1:8002/v1/embeddings"
    assert captured["json"]["model"] == "embedding-model"
    assert captured["headers"] == {"Content-Type": "application/json"}


def test_hindi_retrieval_query_is_translated_before_search(monkeypatch):
    captured = {}

    def fake_generate(system_prompt, user_content):
        captured["system"] = system_prompt
        captured["query"] = json.loads(user_content)["query"]
        return {"answer": "concern about work results", "citation_ids": []}

    monkeypatch.setattr(model_service, "generate_json_response", fake_generate)

    assert model_service.translate_query_to_english(
        "मुझे काम के परिणामों की चिंता है।"
    ) == "concern about work results"
    assert captured["query"] == "मुझे काम के परिणामों की चिंता है।"
    assert "Do not answer the question" in captured["system"]


def test_ollama_embeddings_use_native_endpoint(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        model_service,
        "settings",
        SimpleNamespace(
            llm_provider="ollama",
            llm_chat_base_url="http://127.0.0.1:11434",
            llm_chat_model="qwen3:4b",
            llm_embeddings_base_url="http://127.0.0.1:11434",
            llm_api_key=None,
            llm_embedding_model="bge-m3",
            llm_embedding_dimensions=2,
        ),
    )

    class FakeResponse:
        is_error = False

        def json(self):
            return {"embeddings": [[0.25, 0.75]]}

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured.update(kwargs)
        return FakeResponse()

    monkeypatch.setattr(model_service.httpx, "post", fake_post)

    assert model_service.embed_texts(["गीता"]) == [[0.25, 0.75]]
    assert captured["url"] == "http://127.0.0.1:11434/api/embed"
    assert captured["json"] == {"model": "bge-m3", "input": ["गीता"]}


def test_ollama_chat_disables_thinking_and_uses_constrained_json(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        model_service,
        "settings",
        SimpleNamespace(
            llm_provider="ollama",
            llm_chat_base_url="http://127.0.0.1:11434/v1",
            llm_chat_model="qwen3:4b",
            llm_embeddings_base_url="http://127.0.0.1:11434",
            llm_api_key=None,
            llm_embedding_model="bge-m3",
            llm_embedding_dimensions=2,
        ),
    )

    class FakeResponse:
        is_error = False

        def json(self):
            return {
                "message": {
                    "content": '{"answer":"शांत रहें।","citation_ids":[]}'
                }
            }

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured.update(kwargs)
        return FakeResponse()

    monkeypatch.setattr(model_service.httpx, "post", fake_post)

    result = model_service.generate_json_response("system", "user")

    assert result == {"answer": "शांत रहें।", "citation_ids": []}
    assert captured["url"] == "http://127.0.0.1:11434/api/chat"
    assert captured["json"]["think"] is False
    assert captured["json"]["stream"] is False
    assert captured["json"]["format"]["required"] == ["answer", "citation_ids"]

    model_service.generate_json_response(
        "system",
        "user",
        response_schema=response_service.GUIDANCE_RESPONSE_SCHEMA,
    )
    assert captured["json"]["format"]["required"] == [
        "answer",
        "citation_ids",
        "verse_explanations",
    ]


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
    monkeypatch.setattr(
        sanskrit_rag_service, "retrieve_related_passages", lambda query, limit: []
    )
    monkeypatch.setattr(
        sanskrit_rag_service,
        "embed_texts",
        lambda texts: [[0.1] for _ in texts],
    )
    monkeypatch.setattr(sanskrit_rag_service, "corpus_sha256", lambda: "verified-hash")

    assert sanskrit_rag_service.retrieve_sanskrit_verses("karma", limit=1) == [verse]


def test_chapter_translation_signal_can_retrieve_verse_missing_from_global_hits(
    monkeypatch,
):
    target_verse = get_sanskrit_verse(2, 47)
    global_verse = get_sanskrit_verse(5, 12)
    assert target_verse is not None
    assert global_verse is not None
    payloads = {
        verse.verse_id: {
            "corpus_sha256": "verified-hash",
            "verse_id": verse.verse_id,
            "chapter": verse.chapter,
            "verse": verse.verse,
        }
        for verse in (target_verse, global_verse)
    }

    class FakeQdrantClient:
        def collection_exists(self, collection_name):
            return True

        def query_points(self, **kwargs):
            if "query_filter" in kwargs:
                chapters = kwargs["query_filter"].must[0].match.any
                assert chapters == [2]
                verse_ids = [target_verse.verse_id]
            else:
                verse_ids = [global_verse.verse_id]
            return SimpleNamespace(
                points=[
                    SimpleNamespace(payload=payloads[verse_id])
                    for verse_id in verse_ids
                ]
            )

    monkeypatch.setattr(
        sanskrit_rag_service,
        "get_qdrant_client",
        lambda: FakeQdrantClient(),
    )
    monkeypatch.setattr(
        sanskrit_rag_service,
        "retrieve_related_passages",
        lambda query, limit: [build_sanskrit_citation(target_verse)],
    )
    monkeypatch.setattr(
        sanskrit_rag_service,
        "translate_query_to_english",
        lambda query: "concern about work results",
    )
    monkeypatch.setattr(
        sanskrit_rag_service,
        "embed_texts",
        lambda texts: [[0.1] for _ in texts],
    )
    monkeypatch.setattr(sanskrit_rag_service, "corpus_sha256", lambda: "verified-hash")

    results = sanskrit_rag_service.retrieve_sanskrit_verses(
        "काम के परिणामों की चिंता है",
        limit=2,
        language="hi",
    )

    assert target_verse in results
