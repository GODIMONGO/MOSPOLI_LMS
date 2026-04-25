import hashlib

from semantic_router.catalog import load_route_catalog
from semantic_router.config import SemanticRouterConfig, load_semantic_router_config, resolve_project_path
from semantic_router.embeddings import EmbeddingClient
from semantic_router.vector_store import VectorStoreClient


def index_routes(config: SemanticRouterConfig | None = None) -> dict[str, int | str]:
    resolved_config = config or load_semantic_router_config()
    catalog_path = resolve_project_path(resolved_config.routes_file)
    routes = load_route_catalog(catalog_path)
    texts = [route.embedding_text() for route in routes]
    hashes = {route.id: hashlib.sha256(route.embedding_text().encode("utf-8")).hexdigest() for route in routes}

    vectors = EmbeddingClient(resolved_config).embed(texts)
    if not vectors:
        raise RuntimeError("Infinity returned no vectors.")
    vector_size = len(vectors[0])

    vector_store = VectorStoreClient(resolved_config)
    vector_store.ensure_collection(vector_size)
    vector_store.upsert_routes(routes, vectors, hashes)

    return {
        "routes_file": str(catalog_path),
        "routes_count": len(routes),
        "vector_size": vector_size,
        "collection": resolved_config.qdrant_collection,
    }
