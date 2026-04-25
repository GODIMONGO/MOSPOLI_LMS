from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class RouteRecord:
    id: str
    path: str
    title: str
    example_queries: list[str]
    metadata: dict[str, Any] = field(default_factory=dict)

    def embedding_text(self) -> str:
        examples = "\n".join(f"- {query}" for query in self.example_queries)
        metadata_lines = "\n".join(f"{key}: {value}" for key, value in sorted(self.metadata.items()))
        return f"title: {self.title}\npath: {self.path}\nexamples:\n{examples}\n{metadata_lines}".strip()


@dataclass(frozen=True)
class SearchResult:
    id: str
    path: str
    title: str
    score: float
    metadata: dict[str, Any] = field(default_factory=dict)
    example_text: str = ""

    def as_public_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "path": self.path,
            "title": self.title,
            "score": round(self.score, 4),
            "metadata": self.metadata,
        }
