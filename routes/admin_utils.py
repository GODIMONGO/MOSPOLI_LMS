from uuid import uuid4

from flask import redirect, session, url_for
from loguru import logger


def require_auth_redirect():
    if "user" not in session:
        return redirect(url_for("login"))
    return None


def log_error_id(error):
    id_error = str(uuid4())
    logger.error(f"ID: {id_error} Ошибка: {error}")
    return id_error
