from numbers import Integral
from typing import Any

from semantic_router.config import SemanticRouterConfig
from semantic_router.http import HttpServiceError, request_json
from semantic_router.models import SearchResult


class RerankerClient:
    def __init__(self, config: SemanticRouterConfig) -> None:
        self._config = config

    def rerank(self, query: str, candidates: list[SearchResult]) -> list[SearchResult]:
        if not candidates:
            return []

        documents = [candidate.example_text or f"{candidate.title}\n{candidate.path}" for candidate in candidates]
        payload = {
            "model": self._config.reranker_model,
            "query": query,
            "documents": documents,
            "top_n": len(documents),
        }

        errors: list[str] = []
        for suffix in ("/rerank", "/v1/rerank"):
            try:
                response = request_json(
                    "POST",
                    f"{self._config.infinity_base_url.rstrip('/')}{suffix}",
                    payload=payload,
                    timeout=self._config.request_timeout,
                )
                return self._parse_rerank(response, candidates)
            except HttpServiceError as exc:
                errors.append(str(exc))
        if self._config.reranker_model == "jina-reranker-v3":
            local_results = _rerank_with_local_jina_v3(query, candidates)
            if local_results:
                return local_results
        raise HttpServiceError("; ".join(errors))

    def _parse_rerank(self, response: dict[str, Any], candidates: list[SearchResult]) -> list[SearchResult]:
        raw_results = response.get("results") or response.get("data")
        if not isinstance(raw_results, list):
            raise HttpServiceError("Reranker response does not contain results.")

        reranked: list[SearchResult] = []
        used_indexes: set[int] = set()
        for item in raw_results:
            if not isinstance(item, dict):
                continue
            index = item.get("index")
            if not isinstance(index, int) or index < 0 or index >= len(candidates):
                continue
            score = item.get("relevance_score", item.get("score", candidates[index].score))
            candidate = candidates[index]
            reranked.append(_merge_scores(candidate, float(score)))
            used_indexes.add(index)

        for index, candidate in enumerate(candidates):
            if index not in used_indexes:
                reranked.append(candidate)
        return sorted(reranked, key=lambda result: result.score, reverse=True)


_LOCAL_JINA_V3_MODEL = None


def _rerank_with_local_jina_v3(query: str, candidates: list[SearchResult]) -> list[SearchResult]:
    global _LOCAL_JINA_V3_MODEL  # noqa: PLW0603
    try:
        if _LOCAL_JINA_V3_MODEL is None:
            from transformers import AutoModel

            _LOCAL_JINA_V3_MODEL = AutoModel.from_pretrained(
                "jinaai/jina-reranker-v3",
                dtype="auto",
                trust_remote_code=True,
            )
            _LOCAL_JINA_V3_MODEL.eval()

        documents = [candidate.example_text or f"{candidate.title}\n{candidate.path}" for candidate in candidates]
        raw_results = _LOCAL_JINA_V3_MODEL.rerank(query, documents, top_n=len(documents))
    except Exception as exc:
        raise HttpServiceError(f"Local jina-reranker-v3 fallback failed: {exc}") from exc

    reranked: list[SearchResult] = []
    for item in raw_results:
        if not isinstance(item, dict):
            continue
        index = item.get("index")
        if not isinstance(index, Integral) or index < 0 or index >= len(candidates):
            continue
        candidate = candidates[int(index)]
        score = item.get("relevance_score", candidate.score)
        reranked.append(_merge_scores(candidate, float(score)))
    return reranked


def _merge_scores(candidate: SearchResult, reranker_score: float) -> SearchResult:
    vector_score = candidate.vector_score if candidate.vector_score is not None else candidate.score
    combined_score = (0.35 * vector_score) + (0.65 * reranker_score)
    metadata = dict(candidate.metadata)
    diagnostics = dict(metadata.get("diagnostics", {})) if isinstance(metadata.get("diagnostics"), dict) else {}
    diagnostics.update({"vector_score": round(vector_score, 6), "reranker_score": round(reranker_score, 6)})
    metadata["diagnostics"] = diagnostics
    return SearchResult(
        id=candidate.id,
        path=candidate.path,
        title=candidate.title,
        score=combined_score,
        metadata=metadata,
        example_text=candidate.example_text,
        vector_score=vector_score,
        reranker_score=reranker_score,
    )
