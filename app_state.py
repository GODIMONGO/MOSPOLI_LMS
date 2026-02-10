# Shared in-memory state to avoid circular imports.
from typing import Any

GANTT_STORE: dict[str, dict[str, list[dict[str, Any]]]] = {}
