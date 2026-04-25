from dataclasses import dataclass
from typing import Any

from semantic_router.config import SemanticRouterConfig, load_semantic_router_config
from semantic_router.embeddings import EmbeddingClient
from semantic_router.http import HttpServiceError
from semantic_router.models import SearchResult
from semantic_router.reranker import RerankerClient
from semantic_router.vector_store import VectorStoreClient

_ADMIN_INTENT_MARKERS = (
    "админ",
    "администратор",
    "административ",
    "управление системой",
    "управление пользователями",
)


class SemanticRouterError(RuntimeError):
    """Raised when semantic routing cannot be completed."""


@dataclass(frozen=True)
class SemanticRouterDecision:
    status: str
    best: SearchResult | None
    options: list[SearchResult]
    reranker_used: bool

    def as_response(self) -> dict[str, Any]:
        if self.status == "success" and self.best is not None:
            return {"status": "success", **self.best.as_public_dict()}

        return {
            "status": "clarify",
            "message": "Уточните, какой раздел нужен",
            "options": [option.as_public_dict() for option in self.options],
        }


class SemanticRouterService:
    def __init__(self, config: SemanticRouterConfig | None = None) -> None:
        self._config = config or load_semantic_router_config()
        self._embeddings = EmbeddingClient(self._config)
        self._vector_store = VectorStoreClient(self._config)
        self._reranker = RerankerClient(self._config)

    def search(self, query: str, *, user_role: str | None = None) -> SemanticRouterDecision:
        cleaned_query = query.strip()
        if not cleaned_query:
            raise SemanticRouterError("Запрос не может быть пустым.")
        if len(cleaned_query) > self._config.query_max_length:
            raise SemanticRouterError(f"Запрос длиннее {self._config.query_max_length} символов.")
        if not self._config.enabled:
            raise SemanticRouterError("Semantic Router отключен.")

        try:
            query_vector = self._embeddings.embed([cleaned_query])[0]
            candidates = self._vector_store.search(query_vector, self._config.top_k)
        except (HttpServiceError, IndexError) as exc:
            raise SemanticRouterError(str(exc)) from exc

        candidates = _filter_by_role(candidates, user_role)
        if _contains_restricted_admin_intent(cleaned_query, user_role):
            return SemanticRouterDecision(
                status="clarify", best=None, options=candidates[: self._config.clarify_limit], reranker_used=False
            )
        if not candidates:
            return SemanticRouterDecision(status="clarify", best=None, options=[], reranker_used=False)

        reranker_used = True
        try:
            ranked = self._reranker.rerank(cleaned_query, candidates)
        except HttpServiceError:
            reranker_used = False
            ranked = sorted(candidates, key=lambda result: result.score, reverse=True)

        best = ranked[0]
        options = ranked[: self._config.clarify_limit]
        status = "success" if _is_confident(best, options, self._config) and _is_safe_path(best.path) else "clarify"
        return SemanticRouterDecision(
            status=status, best=best if status == "success" else None, options=options, reranker_used=reranker_used
        )


def _filter_by_role(candidates: list[SearchResult], user_role: str | None) -> list[SearchResult]:
    if not user_role:
        return candidates
    allowed: list[SearchResult] = []
    for candidate in candidates:
        role = candidate.metadata.get("role")
        if role in (None, "", user_role, "all"):
            allowed.append(candidate)
    return allowed


def _is_safe_path(path: str) -> bool:
    return path.startswith("/") and not path.startswith("//") and "://" not in path


def _is_confident(best: SearchResult, options: list[SearchResult], config: SemanticRouterConfig) -> bool:
    if best.score < config.score_threshold:
        return False
    if len(options) < 2:
        return True
    second = options[1]
    if best.id == second.id:
        return True
    return (best.score - second.score) >= config.ambiguity_margin


def _contains_restricted_admin_intent(query: str, user_role: str | None) -> bool:
    if user_role == "admin":
        return False
    lowered = query.casefold()
    return any(marker in lowered for marker in _ADMIN_INTENT_MARKERS)
