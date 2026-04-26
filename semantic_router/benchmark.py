import statistics
from dataclasses import dataclass
from typing import Any

from semantic_router.config import SemanticRouterConfig
from semantic_router.evaluator import load_evaluation_cases
from semantic_router.service import SemanticRouterService


@dataclass(frozen=True)
class BenchmarkOptions:
    cases_file: str
    rounds: int
    warmup: int


def benchmark_cases(config: SemanticRouterConfig, options: BenchmarkOptions) -> dict[str, Any]:
    cases = load_evaluation_cases(config_path(options.cases_file))
    service = SemanticRouterService(config)

    for _ in range(options.warmup):
        for case in cases:
            service.search(case.query, user_role=case.role)

    rows: list[dict[str, Any]] = []
    for round_index in range(options.rounds):
        for case in cases:
            decision = service.search(case.query, user_role=case.role)
            timings = decision.timings_ms or {}
            rows.append(
                {
                    "round": round_index + 1,
                    "case": case.id,
                    "status": decision.status,
                    "path": decision.best.path if decision.best else None,
                    "reranker_used": decision.reranker_used,
                    "embed_ms": timings.get("embed"),
                    "qdrant_ms": timings.get("qdrant"),
                    "rerank_ms": timings.get("rerank"),
                    "total_ms": timings.get("total"),
                }
            )

    totals = [row["total_ms"] for row in rows if isinstance(row.get("total_ms"), int | float)]
    reranks = [row["rerank_ms"] for row in rows if isinstance(row.get("rerank_ms"), int | float) and row["rerank_ms"] >= 0]
    return {
        "status": "ok",
        "rounds": options.rounds,
        "warmup": options.warmup,
        "cases": len(cases),
        "summary": {
            "total_p50_ms": _percentile(totals, 50),
            "total_p95_ms": _percentile(totals, 95),
            "total_min_ms": min(totals) if totals else None,
            "total_max_ms": max(totals) if totals else None,
            "rerank_p50_ms": _percentile(reranks, 50),
            "rerank_used": sum(1 for row in rows if row["reranker_used"]),
            "requests": len(rows),
        },
        "rows": rows,
    }


def config_path(path: str):
    from semantic_router.config import resolve_project_path

    return resolve_project_path(path)


def _percentile(values: list[float], percentile: int) -> float | None:
    if not values:
        return None
    if len(values) == 1:
        return round(values[0], 1)
    ordered = sorted(values)
    if percentile == 50:
        return round(statistics.median(ordered), 1)
    index = round((len(ordered) - 1) * (percentile / 100))
    return round(ordered[index], 1)
