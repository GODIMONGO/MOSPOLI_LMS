import argparse
import json
import sys

from semantic_router.benchmark import BenchmarkOptions, benchmark_cases
from semantic_router.catalog import load_route_catalog
from semantic_router.config import load_semantic_router_config, resolve_project_path
from semantic_router.embeddings import EmbeddingClient
from semantic_router.evaluator import evaluate_cases
from semantic_router.indexer import index_routes
from semantic_router.vector_store import VectorStoreClient


def _print_json(payload: dict[str, object]) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def check() -> int:
    config = load_semantic_router_config()
    catalog_path = resolve_project_path(config.routes_file)
    routes = load_route_catalog(catalog_path)
    embedding_probe = EmbeddingClient(config).embed(["semantic router health check"])
    collection_status = VectorStoreClient(config).check()
    _print_json(
        {
            "status": "ok",
            "routes_file": str(catalog_path),
            "routes_count": len(routes),
            "embedding_size": len(embedding_probe[0]) if embedding_probe else 0,
            "qdrant": collection_status,
        }
    )
    return 0


def index() -> int:
    _print_json({"status": "ok", **index_routes()})
    return 0


def evaluate(cases_file: str) -> int:
    config = load_semantic_router_config()
    payload = evaluate_cases(config, cases_file)
    _print_json(payload)
    return 0 if payload["failed"] == 0 else 1


def benchmark(cases_file: str, rounds: int, warmup: int) -> int:
    config = load_semantic_router_config()
    payload = benchmark_cases(config, BenchmarkOptions(cases_file=cases_file, rounds=rounds, warmup=warmup))
    _print_json(payload)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Semantic Router utilities")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("check", help="Check catalog, Infinity and Qdrant availability")
    subparsers.add_parser("index", help="Index semantic routes into Qdrant")
    evaluate_parser = subparsers.add_parser("evaluate", help="Run semantic search scenarios against real services")
    evaluate_parser.add_argument("--cases", default="data/semantic_router_eval.json", help="Evaluation cases JSON file")
    benchmark_parser = subparsers.add_parser("benchmark", help="Measure semantic search latency against real services")
    benchmark_parser.add_argument("--cases", default="data/semantic_router_eval.json", help="Benchmark cases JSON file")
    benchmark_parser.add_argument("--rounds", type=int, default=2, help="Measured rounds")
    benchmark_parser.add_argument("--warmup", type=int, default=1, help="Warmup rounds")
    args = parser.parse_args(argv)

    if args.command == "check":
        return check()
    if args.command == "index":
        return index()
    if args.command == "evaluate":
        return evaluate(args.cases)
    if args.command == "benchmark":
        return benchmark(args.cases, args.rounds, args.warmup)
    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
