import json
from pathlib import Path
from typing import Any

from semantic_router.models import RouteRecord


class RouteCatalogError(ValueError):
    """Raised when the semantic route catalog is invalid."""


def _require_string(value: Any, field_name: str, record_id: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RouteCatalogError(f"Route {record_id!r} has invalid {field_name}.")
    return value.strip()


def _safe_internal_path(path: str) -> str:
    if not path.startswith("/") or path.startswith("//") or "://" in path:
        raise RouteCatalogError(f"Route path {path!r} must be an internal relative path.")
    return path


def load_route_catalog(path: Path) -> list[RouteRecord]:
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    raw_routes = data.get("routes") if isinstance(data, dict) else data
    if not isinstance(raw_routes, list):
        raise RouteCatalogError("Route catalog must be a list or an object with a 'routes' list.")

    records: list[RouteRecord] = []
    seen_ids: set[str] = set()
    for raw in raw_routes:
        if not isinstance(raw, dict):
            raise RouteCatalogError("Every route catalog item must be an object.")

        route_id = _require_string(raw.get("id"), "id", "<unknown>")
        if route_id in seen_ids:
            raise RouteCatalogError(f"Duplicate route id {route_id!r}.")
        seen_ids.add(route_id)

        path_value = _safe_internal_path(_require_string(raw.get("path"), "path", route_id))
        title = _require_string(raw.get("title"), "title", route_id)
        examples = raw.get("example_queries")
        if not isinstance(examples, list) or not all(isinstance(item, str) and item.strip() for item in examples):
            raise RouteCatalogError(f"Route {route_id!r} must define non-empty example_queries.")

        metadata = raw.get("metadata", {})
        if not isinstance(metadata, dict):
            raise RouteCatalogError(f"Route {route_id!r} metadata must be an object.")

        records.append(
            RouteRecord(
                id=route_id,
                path=path_value,
                title=title,
                example_queries=[item.strip() for item in examples],
                metadata=metadata,
            )
        )
    return records
