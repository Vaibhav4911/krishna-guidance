from __future__ import annotations

import json
import math
from typing import Any

import httpx

from app.config import settings

OPENAI_API_URL = "https://api.openai.com/v1"
REQUEST_TIMEOUT_SECONDS = 60.0


class OpenAIConfigurationError(RuntimeError):
    pass


class OpenAIProviderError(RuntimeError):
    pass


def _post(endpoint: str, payload: dict[str, Any]) -> dict[str, Any]:
    if not settings.openai_api_key:
        raise OpenAIConfigurationError(
            "OpenAI is not configured. Set OPENAI_API_KEY in apps/api/.env."
        )

    try:
        response = httpx.post(
            f"{OPENAI_API_URL}/{endpoint}",
            headers={"Authorization": f"Bearer {settings.openai_api_key}"},
            json=payload,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
    except httpx.TimeoutException as error:
        raise OpenAIProviderError("The OpenAI request timed out.") from error
    except httpx.HTTPError as error:
        raise OpenAIProviderError("Unable to reach the OpenAI API.") from error

    if response.is_error:
        raise OpenAIProviderError(
            f"The OpenAI API returned HTTP {response.status_code}."
        )
    try:
        result = response.json()
    except ValueError as error:
        raise OpenAIProviderError("The OpenAI API returned invalid JSON.") from error
    if not isinstance(result, dict):
        raise OpenAIProviderError("The OpenAI API returned an invalid response.")
    return result


def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []

    response = _post(
        "embeddings",
        {
            "model": settings.openai_embedding_model,
            "input": texts,
            "dimensions": settings.openai_embedding_dimensions,
        },
    )
    rows = response.get("data")
    if not isinstance(rows, list) or len(rows) != len(texts):
        raise OpenAIProviderError("The OpenAI API returned an incomplete embedding batch.")

    vectors: list[list[float] | None] = [None] * len(texts)
    for row in rows:
        if not isinstance(row, dict):
            raise OpenAIProviderError("The OpenAI API returned an invalid embedding.")
        index = row.get("index")
        embedding = row.get("embedding")
        if (
            not isinstance(index, int)
            or isinstance(index, bool)
            or not 0 <= index < len(texts)
            or not isinstance(embedding, list)
            or len(embedding) != settings.openai_embedding_dimensions
            or any(
                not isinstance(value, (int, float))
                or isinstance(value, bool)
                or not math.isfinite(value)
                for value in embedding
            )
            or vectors[index] is not None
        ):
            raise OpenAIProviderError("The OpenAI API returned an invalid embedding.")
        vectors[index] = [float(value) for value in embedding]

    if any(vector is None for vector in vectors):
        raise OpenAIProviderError("The OpenAI API returned an incomplete embedding batch.")
    return [vector for vector in vectors if vector is not None]


def generate_json_response(system_prompt: str, user_content: str) -> dict[str, Any]:
    response = _post(
        "chat/completions",
        {
            "model": settings.openai_chat_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.4,
            "max_tokens": 1200,
        },
    )
    choices = response.get("choices")
    if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
        raise OpenAIProviderError("The OpenAI API returned no guidance response.")
    message = choices[0].get("message")
    content = message.get("content") if isinstance(message, dict) else None
    if not isinstance(content, str):
        raise OpenAIProviderError("The OpenAI API returned an invalid guidance response.")
    try:
        result = json.loads(content)
    except ValueError as error:
        raise OpenAIProviderError("The OpenAI API returned malformed guidance JSON.") from error
    if not isinstance(result, dict):
        raise OpenAIProviderError("The OpenAI API returned an invalid guidance response.")
    return result
