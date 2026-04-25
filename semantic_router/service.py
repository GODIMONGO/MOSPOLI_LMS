import re
from dataclasses import dataclass
from time import perf_counter
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
_FILE_INTENT_MARKERS = ("файл", "документ", "pdf", "материал")
_FILE_ACTION_MARKERS = ("скач", "загруз", "прикреп", "сдать", "отправ", "материал", "преподав")
_TOKEN_RE = re.compile(r"[0-9A-Za-zА-Яа-яЁё]+")


class SemanticRouterError(RuntimeError):
    """Raised when semantic routing cannot be completed."""


@dataclass(frozen=True)
class SemanticRouterDecision:
    status: str
    best: SearchResult | None
    options: list[SearchResult]
    reranker_used: bool
    timings_ms: dict[str, float] | None = None

    def as_response(self) -> dict[str, Any]:
        if self.status == "success" and self.best is not None:
            response = {"status": "success", **self.best.as_public_dict()}
            if self.timings_ms is not None:
                response["timings_ms"] = self.timings_ms
            return response

        response = {
            "status": "clarify",
            "message": "Уточните, какой раздел нужен",
            "options": [option.as_public_dict() for option in self.options],
        }
        if self.timings_ms is not None:
            response["timings_ms"] = self.timings_ms
        return response


class SemanticRouterService:
    def __init__(self, config: SemanticRouterConfig | None = None) -> None:
        self._config = config or load_semantic_router_config()
        self._embeddings = EmbeddingClient(self._config)
        self._vector_store = VectorStoreClient(self._config)
        self._reranker = RerankerClient(self._config)

    def search(self, query: str, *, user_role: str | None = None) -> SemanticRouterDecision:
        total_started = perf_counter()
        timings_ms: dict[str, float] = {}
        cleaned_query = query.strip()
        if not cleaned_query:
            raise SemanticRouterError("Запрос не может быть пустым.")
        if len(cleaned_query) > self._config.query_max_length:
            raise SemanticRouterError(f"Запрос длиннее {self._config.query_max_length} символов.")
        if not self._config.enabled:
            raise SemanticRouterError("Semantic Router отключен.")

        try:
            embed_started = perf_counter()
            query_vector = self._embeddings.embed([cleaned_query])[0]
            timings_ms["embed"] = _elapsed_ms(embed_started)
            qdrant_started = perf_counter()
            candidates = self._vector_store.search(query_vector, self._config.top_k)
            timings_ms["qdrant"] = _elapsed_ms(qdrant_started)
        except (HttpServiceError, IndexError) as exc:
            raise SemanticRouterError(str(exc)) from exc

        candidates = _filter_by_role(candidates, user_role)
        if _contains_restricted_admin_intent(cleaned_query, user_role):
            timings_ms["total"] = _elapsed_ms(total_started)
            return SemanticRouterDecision(
                status="clarify",
                best=None,
                options=candidates[: self._config.clarify_limit],
                reranker_used=False,
                timings_ms=timings_ms,
            )
        if not candidates:
            timings_ms["total"] = _elapsed_ms(total_started)
            return SemanticRouterDecision(status="clarify", best=None, options=[], reranker_used=False, timings_ms=timings_ms)

        lexical_started = perf_counter()
        lexical_ranked = _rank_by_lexical_match(cleaned_query, candidates)
        timings_ms["lexical"] = _elapsed_ms(lexical_started)
        if _is_lexical_fast_path(cleaned_query, lexical_ranked, self._config):
            ranked = lexical_ranked
            reranker_used = False
            timings_ms["rerank"] = 0.0
        else:
            ranked, reranker_used = self._rank_with_reranker(cleaned_query, candidates, timings_ms)

        best = ranked[0]
        options = ranked[: self._config.clarify_limit]
        status = "success" if _is_confident(best, options, self._config) and _is_safe_path(best.path) else "clarify"
        timings_ms["total"] = _elapsed_ms(total_started)
        return SemanticRouterDecision(
            status=status,
            best=best if status == "success" else None,
            options=options,
            reranker_used=reranker_used,
            timings_ms=timings_ms,
        )

    def _rank_with_reranker(
        self, cleaned_query: str, candidates: list[SearchResult], timings_ms: dict[str, float]
    ) -> tuple[list[SearchResult], bool]:
        reranker_used = False
        try:
            if _should_skip_rerank(candidates, self._config):
                ranked = sorted(candidates, key=lambda result: result.score, reverse=True)
                timings_ms["rerank"] = 0.0
            else:
                rerank_started = perf_counter()
                rerank_candidates = candidates[: max(1, min(self._config.rerank_top_k, len(candidates)))]
                reranked_head = self._reranker.rerank(cleaned_query, rerank_candidates)
                timings_ms["rerank"] = _elapsed_ms(rerank_started)
                ranked = _merge_reranked_head(reranked_head, candidates)
                reranker_used = True
        except HttpServiceError:
            ranked = sorted(candidates, key=lambda result: result.score, reverse=True)
            timings_ms["rerank"] = -1.0
        return ranked, reranker_used


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


def _should_skip_rerank(candidates: list[SearchResult], config: SemanticRouterConfig) -> bool:
    if len(candidates) < 2:
        return True
    if config.rerank_top_k <= 0:
        return True
    best, second = candidates[0], candidates[1]
    return best.score >= config.score_threshold and (best.score - second.score) >= config.rerank_skip_margin


def _merge_reranked_head(reranked_head: list[SearchResult], candidates: list[SearchResult]) -> list[SearchResult]:
    reranked_ids = {candidate.id for candidate in reranked_head}
    tail = [candidate for candidate in candidates if candidate.id not in reranked_ids]
    return [*reranked_head, *tail]


def _elapsed_ms(started: float) -> float:
    return round((perf_counter() - started) * 1000, 1)


def _rank_by_lexical_match(query: str, candidates: list[SearchResult]) -> list[SearchResult]:
    query_tokens = _tokens(query)
    if not query_tokens:
        return candidates

    ranked: list[SearchResult] = []
    for candidate in candidates:
        lexical_score = _lexical_score(query_tokens, candidate)
        combined_score = (candidate.score * 0.55) + (lexical_score * 0.45)
        metadata = dict(candidate.metadata)
        diagnostics = dict(metadata.get("diagnostics", {})) if isinstance(metadata.get("diagnostics"), dict) else {}
        diagnostics["lexical_score"] = round(lexical_score, 6)
        metadata["diagnostics"] = diagnostics
        ranked.append(
            SearchResult(
                id=candidate.id,
                path=candidate.path,
                title=candidate.title,
                score=combined_score,
                metadata=metadata,
                example_text=candidate.example_text,
                vector_score=candidate.vector_score,
                reranker_score=candidate.reranker_score,
            )
        )
    return sorted(ranked, key=lambda result: result.score, reverse=True)


def _lexical_score(query_tokens: set[str], candidate: SearchResult) -> float:
    text_tokens = _tokens(f"{candidate.title}\n{candidate.example_text}")
    if not text_tokens:
        return 0.0
    matched = sum(1 for token in query_tokens if _token_matches(token, text_tokens))
    return matched / len(query_tokens)


def _token_matches(token: str, text_tokens: set[str]) -> bool:
    if token in text_tokens:
        return True
    if len(token) < 4:
        return False
    prefix = token[:4]
    return any(text_token.startswith(prefix) or prefix.startswith(text_token[:4]) for text_token in text_tokens if len(text_token) >= 4)


def _tokens(text: str) -> set[str]:
    return {token.casefold() for token in _TOKEN_RE.findall(text) if len(token) >= 3}


def _is_lexical_fast_path(query: str, ranked: list[SearchResult], config: SemanticRouterConfig) -> bool:
    if len(ranked) < 2:
        return True
    if _is_ambiguous_file_intent(query):
        return False
    best = ranked[0]
    best_lexical = _diagnostic_score(best, "lexical_score")
    competing_lexical = max((_diagnostic_score(candidate, "lexical_score") for candidate in ranked[1:]), default=0.0)
    return (
        best_lexical >= config.lexical_fast_path_min_score
        and (best_lexical - competing_lexical) >= config.lexical_fast_path_margin
        and _is_safe_path(best.path)
    )


def _diagnostic_score(candidate: SearchResult, key: str) -> float:
    diagnostics = candidate.metadata.get("diagnostics")
    if not isinstance(diagnostics, dict):
        return 0.0
    value = diagnostics.get(key)
    return float(value) if isinstance(value, int | float) else 0.0


def _is_ambiguous_file_intent(query: str) -> bool:
    lowered = query.casefold()
    return any(marker in lowered for marker in _FILE_INTENT_MARKERS) and not any(marker in lowered for marker in _FILE_ACTION_MARKERS)
