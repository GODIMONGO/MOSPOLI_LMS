from flask import jsonify, session


def current_role() -> str:
    role = str(session.get("role") or "").strip().lower()
    if role in {"admin", "student"}:
        return role
    return "student"


def is_admin() -> bool:
    return current_role() == "admin"


def current_user_id() -> int | None:
    value = session.get("user_id")
    if isinstance(value, int):
        return value
    if not isinstance(value, str):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def require_auth_json():
    if "user" not in session:
        return jsonify({"error": "not authenticated"}), 401
    if current_user_id() is None:
        return jsonify({"error": "invalid session"}), 401
    return None


def require_admin_json():
    if "user" not in session:
        return jsonify({"error": "not authenticated"}), 401
    if not is_admin():
        return jsonify({"error": "admin role required"}), 403
    return None
