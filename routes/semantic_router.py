from uuid import uuid4

from flask import Blueprint, jsonify, redirect, render_template, request, session, url_for
from loguru import logger

from semantic_router.config import load_semantic_router_config
from semantic_router.service import SemanticRouterError, SemanticRouterService

semantic_router_bp = Blueprint("semantic_router", __name__)
_SEMANTIC_ROUTER_SERVICE: SemanticRouterService | None = None


def _json_error(message: str, status_code: int):
    return jsonify({"status": "error", "message": message}), status_code


def _current_role() -> str:
    return "admin" if session.get("user") == "admin" else "student"


@semantic_router_bp.route("/semantic-router")
def semantic_router_page():
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template("semantic_router/semantic_router.html")


@semantic_router_bp.route("/api/semantic-router/search", methods=["POST"])
def semantic_router_search():
    if "user" not in session:
        return _json_error("Требуется авторизация.", 401)
    if not request.is_json:
        return _json_error("Ожидается JSON-запрос.", 400)

    payload = request.get_json(silent=True) or {}
    query = payload.get("query")
    if not isinstance(query, str):
        return _json_error("Поле query обязательно.", 400)

    try:
        decision = _get_semantic_router_service().search(query, user_role=_current_role())
        response = decision.as_response()
        return jsonify(response)
    except SemanticRouterError as error:
        error_id = str(uuid4())
        logger.warning(f"ID: {error_id} Semantic Router unavailable: {error}")
        return jsonify({"status": "unavailable", "message": "Семантическая навигация временно недоступна.", "error_id": error_id}), 503
    except Exception as error:
        error_id = str(uuid4())
        logger.exception(f"ID: {error_id} Semantic Router unexpected error: {error}")
        return jsonify({"status": "error", "message": "Не удалось обработать запрос.", "error_id": error_id}), 500


def _get_semantic_router_service() -> SemanticRouterService:
    global _SEMANTIC_ROUTER_SERVICE  # noqa: PLW0603
    if _SEMANTIC_ROUTER_SERVICE is None:
        _SEMANTIC_ROUTER_SERVICE = SemanticRouterService(load_semantic_router_config())
    return _SEMANTIC_ROUTER_SERVICE
