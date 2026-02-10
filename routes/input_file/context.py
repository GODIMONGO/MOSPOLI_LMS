import os
from uuid import uuid4

from flask import jsonify, render_template, request, session
from loguru import logger

from .config import load_input_file_config
from .files import is_safe_filename


def error_id_logger(error):
    error_id = str(uuid4())
    logger.error(f"ID: {error_id} Ошибка: {error}")
    return error_id


def get_current_username():
    username = session.get("user")
    if not username:
        return None
    if not is_safe_filename(username) or len(username) > 128:
        return None
    return username


def get_uuid_for_upload_from_request(explicit_uuid=None):
    if explicit_uuid is not None:
        uuid_for_upload = str(explicit_uuid).strip()
        if uuid_for_upload:
            return uuid_for_upload

    route_uuid = ""
    if request.view_args:
        route_uuid = str(request.view_args.get("uuid_for_upload") or request.view_args.get("ID_fields") or "").strip()

    uuid_for_upload = route_uuid or (request.args.get("uuid_for_upload") or request.form.get("uuid_for_upload") or "").strip()
    if not uuid_for_upload and request.is_json:
        data = request.get_json(silent=True) or {}
        uuid_for_upload = str(data.get("uuid_for_upload") or "").strip()
    return uuid_for_upload or None


def require_request_config(explicit_uuid=None, page_on_missing=False):
    uuid_for_upload = get_uuid_for_upload_from_request(explicit_uuid=explicit_uuid)
    if not uuid_for_upload:
        if page_on_missing:
            return None, None, (render_template("input_file/not_found.html", uuid_for_upload=None), 404)
        return None, None, (jsonify({"error": "Не передан обязательный параметр uuid_for_upload."}), 400)

    config = load_input_file_config(uuid_for_upload)
    if config is None:
        error_message = f"Не удалось найти поле вставки файлов: {uuid_for_upload}"
        if page_on_missing:
            return None, uuid_for_upload, (render_template("input_file/not_found.html", uuid_for_upload=uuid_for_upload), 404)
        return None, uuid_for_upload, (jsonify({"error": error_message}), 404)
    return config, uuid_for_upload, None


def get_course_id_from_request(config):
    course_id = (request.args.get("course") or config["course_id"]).strip()
    if not course_id:
        course_id = config["course_id"]
    if not config["course_id_re"].fullmatch(course_id):
        return None
    return course_id


def require_upload_context(config):
    username = get_current_username()
    if not username:
        return None, (jsonify({"error": "Требуется авторизация."}), 401)

    course_id = get_course_id_from_request(config)
    if not course_id:
        return None, (jsonify({"error": "Некорректный курс."}), 400)

    upload_dir = os.path.join(config["uploads_root"], course_id, username)
    upload_index = os.path.join(upload_dir, ".index.json")
    return {
        "username": username,
        "course_id": course_id,
        "upload_dir": upload_dir,
        "upload_index": upload_index,
    }, None
