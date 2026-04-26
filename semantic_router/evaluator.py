import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from semantic_router.config import SemanticRouterConfig, resolve_project_path
from semantic_router.service import SemanticRouterDecision, SemanticRouterService


@dataclass(frozen=True)
class EvaluationCase:
    id: str
    query: str
    role: str
    expected_status: str
    expected_path: str | None = None
    expected_options: list[str] | None = None


def load_evaluation_cases(path: Path) -> list[EvaluationCase]:
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    raw_cases = data.get("cases") if isinstance(data, dict) else data
    if not isinstance(raw_cases, list):
        raise ValueError("Evaluation file must be a list or an object with a 'cases' list.")

    cases: list[EvaluationCase] = []
    for raw in raw_cases:
        if not isinstance(raw, dict):
            raise ValueError("Every evaluation case must be an object.")
        case_id = _require_text(raw, "id")
        query = _require_text(raw, "query")
        role = _require_text(raw, "role")
        expected_status = _require_text(raw, "expected_status")
        expected_path = raw.get("expected_path")
        expected_options = raw.get("expected_options")
        if expected_path is not None and not isinstance(expected_path, str):
            raise ValueError(f"Evaluation case {case_id!r} has invalid expected_path.")
        if expected_options is not None and not all(isinstance(item, str) for item in expected_options):
            raise ValueError(f"Evaluation case {case_id!r} has invalid expected_options.")
        cases.append(
            EvaluationCase(
                id=case_id,
                query=query,
                role=role,
                expected_status=expected_status,
                expected_path=expected_path,
                expected_options=expected_options,
            )
        )
    return cases


def evaluate_cases(config: SemanticRouterConfig, cases_file: str) -> dict[str, Any]:
    cases_path = resolve_project_path(cases_file)
    cases = load_evaluation_cases(cases_path)
    service = SemanticRouterService(config)
    results = [_evaluate_case(service, case) for case in cases]
    passed = sum(1 for result in results if result["passed"])
    return {
        "status": "ok" if passed == len(results) else "failed",
        "cases_file": str(cases_path),
        "passed": passed,
        "failed": len(results) - passed,
        "total": len(results),
        "results": results,
    }


def _evaluate_case(service: SemanticRouterService, case: EvaluationCase) -> dict[str, Any]:
    decision = service.search(case.query, user_role=case.role)
    response = decision.as_response()
    actual_path = response.get("path") if isinstance(response.get("path"), str) else None
    actual_options = [option.path for option in decision.options]
    failures = _case_failures(case, decision, actual_path, actual_options)
    return {
        "id": case.id,
        "query": case.query,
        "role": case.role,
        "expected_status": case.expected_status,
        "expected_path": case.expected_path,
        "actual_status": decision.status,
        "actual_path": actual_path,
        "actual_options": actual_options,
        "score": round(decision.best.score, 4) if decision.best else None,
        "reranker_used": decision.reranker_used,
        "passed": not failures,
        "failures": failures,
    }


def _case_failures(case: EvaluationCase, decision: SemanticRouterDecision, actual_path: str | None, actual_options: list[str]) -> list[str]:
    failures: list[str] = []
    if decision.status != case.expected_status:
        failures.append(f"status expected {case.expected_status!r}, got {decision.status!r}")
    if case.expected_path and actual_path != case.expected_path:
        failures.append(f"path expected {case.expected_path!r}, got {actual_path!r}")
    if case.expected_options:
        missing = [path for path in case.expected_options if path not in actual_options and path != actual_path]
        if missing:
            failures.append(f"missing expected options: {missing}")
    return failures


def _require_text(raw: dict[str, Any], field_name: str) -> str:
    value = raw.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Evaluation case has invalid {field_name}.")
    return value.strip()
