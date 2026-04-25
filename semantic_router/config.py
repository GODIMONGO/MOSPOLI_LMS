import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from config import load_app_config


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


@dataclass(frozen=True)
class SemanticRouterConfig:
    enabled: bool = True
    routes_file: str = "data/semantic_routes.json"
    score_threshold: float = 0.60
    top_k: int = 20
    clarify_limit: int = 5
    query_max_length: int = 512
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "routes"
    infinity_base_url: str = "http://localhost:7997"
    embedding_model: str = "jina-embeddings-v5-text-small"
    reranker_model: str = "jina-reranker-v3"
    request_timeout: float = 20.0


def load_semantic_router_config(config_path: str = "config.json") -> SemanticRouterConfig:
    app_config = load_app_config(config_path)
    raw_section = app_config.get("semantic_router", {})
    section: dict[str, Any] = raw_section if isinstance(raw_section, dict) else {}

    return SemanticRouterConfig(
        enabled=_env_bool("SEMANTIC_ROUTER_ENABLED", bool(section.get("enabled", True))),
        routes_file=os.getenv("SEMANTIC_ROUTER_ROUTES_FILE", str(section.get("routes_file", "data/semantic_routes.json"))),
        score_threshold=_env_float("SEMANTIC_ROUTER_SCORE_THRESHOLD", float(section.get("score_threshold", 0.60))),
        top_k=_env_int("SEMANTIC_ROUTER_TOP_K", int(section.get("top_k", 20))),
        clarify_limit=_env_int("SEMANTIC_ROUTER_CLARIFY_LIMIT", int(section.get("clarify_limit", 5))),
        query_max_length=_env_int("SEMANTIC_ROUTER_QUERY_MAX_LENGTH", int(section.get("query_max_length", 512))),
        qdrant_url=os.getenv("QDRANT_URL", str(section.get("qdrant_url", "http://localhost:6333"))),
        qdrant_collection=os.getenv("QDRANT_COLLECTION", str(section.get("qdrant_collection", "routes"))),
        infinity_base_url=os.getenv("INFINITY_BASE_URL", str(section.get("infinity_base_url", "http://localhost:7997"))),
        embedding_model=os.getenv("INFINITY_EMBEDDING_MODEL", str(section.get("embedding_model", "jina-embeddings-v5-text-small"))),
        reranker_model=os.getenv("INFINITY_RERANKER_MODEL", str(section.get("reranker_model", "jina-reranker-v3"))),
        request_timeout=_env_float("SEMANTIC_ROUTER_REQUEST_TIMEOUT", float(section.get("request_timeout", 20.0))),
    )


def resolve_project_path(path: str) -> Path:
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate
    return Path.cwd() / candidate
