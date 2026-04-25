from typing import Any

from semantic_router.config import SemanticRouterConfig
from semantic_router.http import HttpServiceError, request_json


class EmbeddingClient:
    def __init__(self, config: SemanticRouterConfig) -> None:
        self._config = config

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        payload = {"model": self._config.embedding_model, "input": texts}
        errors: list[str] = []
        for suffix in ("/embeddings", "/v1/embeddings"):
            try:
                response = request_json(
                    "POST",
                    f"{self._config.infinity_base_url.rstrip('/')}{suffix}",
                    payload=payload,
                    timeout=self._config.request_timeout,
                )
                return self._parse_embeddings(response)
            except HttpServiceError as exc:
                errors.append(str(exc))
        raise HttpServiceError("; ".join(errors))

    def _parse_embeddings(self, response: dict[str, Any]) -> list[list[float]]:
        data = response.get("data")
        if isinstance(data, list):
            vectors = [item.get("embedding") for item in data if isinstance(item, dict)]
            if vectors and all(_is_vector(vector) for vector in vectors):
                return [list(map(float, vector)) for vector in vectors]

        embeddings = response.get("embeddings")
        if isinstance(embeddings, list) and all(_is_vector(vector) for vector in embeddings):
            return [list(map(float, vector)) for vector in embeddings]

        embedding = response.get("embedding")
        if _is_vector(embedding):
            return [list(map(float, embedding))]

        raise HttpServiceError("Embedding response does not contain vectors.")


def _is_vector(value: Any) -> bool:
    return isinstance(value, list) and bool(value) and all(isinstance(item, int | float) for item in value)
