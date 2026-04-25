from typing import Any
from urllib import parse
from uuid import NAMESPACE_URL, uuid5

from semantic_router.config import SemanticRouterConfig
from semantic_router.http import HttpServiceError, request_json
from semantic_router.models import RouteRecord, SearchResult


class VectorStoreClient:
    def __init__(self, config: SemanticRouterConfig) -> None:
        self._config = config
        self._base_url = config.qdrant_url.rstrip("/")
        self._collection = parse.quote(config.qdrant_collection, safe="")

    def check(self) -> dict[str, Any]:
        response = request_json("GET", f"{self._base_url}/collections/{self._collection}", timeout=self._config.request_timeout)
        result = response.get("result", {})
        if not isinstance(result, dict):
            return {"exists": True, "points_count": None}
        return {
            "exists": True,
            "points_count": result.get("points_count"),
            "vectors_count": result.get("vectors_count"),
            "status": result.get("status"),
        }

    def ensure_collection(self, vector_size: int) -> None:
        try:
            self.check()
            return
        except HttpServiceError:
            pass

        payload = {"vectors": {"size": vector_size, "distance": "Cosine"}}
        request_json("PUT", f"{self._base_url}/collections/{self._collection}", payload=payload, timeout=self._config.request_timeout)

    def upsert_routes(self, routes: list[RouteRecord], vectors: list[list[float]], hashes: dict[str, str]) -> None:
        if len(routes) != len(vectors):
            raise ValueError("Routes and vectors length mismatch.")

        points = []
        for route, vector in zip(routes, vectors, strict=True):
            points.append(
                {
                    "id": str(uuid5(NAMESPACE_URL, f"mospoli-lms-route:{route.id}")),
                    "vector": vector,
                    "payload": {
                        "route_id": route.id,
                        "path": route.path,
                        "title": route.title,
                        "example_text": route.embedding_text(),
                        "metadata": route.metadata,
                        "content_hash": hashes[route.id],
                    },
                }
            )

        request_json(
            "PUT",
            f"{self._base_url}/collections/{self._collection}/points?wait=true",
            payload={"points": points},
            timeout=self._config.request_timeout,
        )

    def search(self, vector: list[float], limit: int) -> list[SearchResult]:
        payload = {"vector": vector, "limit": limit, "with_payload": True}
        response = request_json(
            "POST",
            f"{self._base_url}/collections/{self._collection}/points/search",
            payload=payload,
            timeout=self._config.request_timeout,
        )
        raw_results = response.get("result", [])
        if not isinstance(raw_results, list):
            raise HttpServiceError("Qdrant search returned invalid result.")

        results: list[SearchResult] = []
        for item in raw_results:
            if not isinstance(item, dict):
                continue
            payload_data = item.get("payload", {})
            if not isinstance(payload_data, dict):
                payload_data = {}
            metadata = payload_data.get("metadata", {})
            if not isinstance(metadata, dict):
                metadata = {}
            path = payload_data.get("path")
            title = payload_data.get("title")
            if not isinstance(path, str) or not isinstance(title, str):
                continue
            results.append(
                SearchResult(
                    id=str(payload_data.get("route_id") or item.get("id")),
                    path=path,
                    title=title,
                    score=float(item.get("score", 0.0)),
                    metadata=metadata,
                    example_text=str(payload_data.get("example_text", "")),
                )
            )
        return results
