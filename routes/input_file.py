"""Роутер управления файлами пользователя."""

import hashlib
import json
import os
import re
from datetime import datetime
from uuid import uuid4

import dramatiq
from flask import (
    Blueprint,
    jsonify,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)
from loguru import logger

from broker import broker as _dramatiq_broker

_ = _dramatiq_broker

input_file_bp = Blueprint("input_file", __name__)

APP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _normalize_exts(values, fallback):
    if not isinstance(values, list):
        values = fallback
    prepared = {str(ext).strip().lstrip(".").lower() for ext in values if str(ext).strip()}
    return prepared or set(fallback)


def _to_positive_int(value, fallback):
    try:
        value = int(value)
    except (TypeError, ValueError):
        return fallback
    return value if value > 0 else fallback


def fetch_input_file_config_from_db(uuid_for_upload: str):
    default_input_file_config = {
        "test": {
            "uploads_root": "uploads",
            "image_exts": ["jpg", "jpeg", "png", "gif"],
            "allowed_exts": ["jpg", "jpeg", "png", "gif", "pdf", "doc", "docx", "txt"],
            "max_file_size_mb": 500,
            "max_attached_files": 20,
            "hash_chunk_size": 1048576,
            "course_id": "test",
            "course_id_pattern": "^[a-zA-Z0-9_-]+$",
        }
    }
    return default_input_file_config.get(uuid_for_upload)


def load_input_file_config(uuid_for_upload: str):
    config = fetch_input_file_config_from_db(uuid_for_upload)
    if config is None:
        return None
    if isinstance(config, str):
        try:
            config = json.loads(config)
        except json.JSONDecodeError as error:
            logger.warning(f"Некорректный JSON конфига из БД: {error}")
            return None
    if not isinstance(config, dict):
        return None
    input_file_config = config

    uploads_root_raw = input_file_config.get("uploads_root", "uploads")
    uploads_root_name = uploads_root_raw.strip() if isinstance(uploads_root_raw, str) else "uploads"
    if not uploads_root_name:
        uploads_root_name = "uploads"

    image_exts = _normalize_exts(input_file_config.get("image_exts"), ["jpg", "jpeg", "png", "gif"])
    allowed_exts = _normalize_exts(
        input_file_config.get("allowed_exts"),
        ["jpg", "jpeg", "png", "gif", "pdf", "doc", "docx", "txt"],
    )

    max_file_size_mb = _to_positive_int(input_file_config.get("max_file_size_mb"), 500)
    max_attached_files = _to_positive_int(input_file_config.get("max_attached_files"), 20)
    hash_chunk_size = _to_positive_int(input_file_config.get("hash_chunk_size"), 1024 * 1024)

    course_id_raw = input_file_config.get("course_id", "default")
    course_id = course_id_raw.strip() if isinstance(course_id_raw, str) else "default"
    if not course_id:
        course_id = "default"

    course_id_pattern_raw = input_file_config.get("course_id_pattern", r"^[a-zA-Z0-9_-]+$")
    course_id_pattern = course_id_pattern_raw if isinstance(course_id_pattern_raw, str) else r"^[a-zA-Z0-9_-]+$"
    try:
        course_id_re = re.compile(course_id_pattern)
    except re.error:
        course_id_re = re.compile(r"^[a-zA-Z0-9_-]+$")

    if os.path.isabs(uploads_root_name):
        uploads_root = uploads_root_name
    else:
        uploads_root = os.path.join(APP_ROOT, uploads_root_name)

    return {
        "uploads_root": uploads_root,
        "image_exts": image_exts,
        "allowed_exts": allowed_exts,
        "max_file_size_mb": max_file_size_mb,
        "max_file_size_bytes": max_file_size_mb * 1024 * 1024,
        "max_attached_files": max_attached_files,
        "hash_chunk_size": hash_chunk_size,
        "course_id": course_id,
        "course_id_re": course_id_re,
    }


def _error_id_logger(error):
    error_id = str(uuid4())
    logger.error(f"ID: {error_id} Ошибка: {error}")
    return error_id


def _ensure_upload_dir(upload_dir):
    os.makedirs(upload_dir, exist_ok=True)


def _is_allowed_extension(filename, config):
    ext = os.path.splitext(filename)[1].lstrip(".").lower()
    return ext in config["allowed_exts"]


def _is_safe_filename(filename):
    if not filename:
        return False
    if "/" in filename or "\\" in filename:
        return False
    if ".." in filename:
        return False
    if filename != os.path.basename(filename):
        return False
    return True


def _format_size(size_bytes):
    size = float(size_bytes)
    units = ["B", "KB", "MB", "GB", "TB"]
    for unit in units:
        if size < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(size)} {unit}"
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size_bytes} B"


def _compute_file_hash(path, config):
    hasher = hashlib.sha256()
    with open(path, "rb") as file:
        for chunk in iter(lambda: file.read(config["hash_chunk_size"]), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _sync_upload_index(upload_dir, upload_index, config, include_hash=True):
    _ensure_upload_dir(upload_dir)
    index = _load_index(upload_dir, upload_index)
    changed = False

    if not index:
        for filename in os.listdir(upload_dir):
            if filename.startswith("."):
                continue
            path = os.path.join(upload_dir, filename)
            if not os.path.isfile(path) or not _is_safe_filename(filename):
                continue
            index[filename] = _build_file_record(upload_dir, filename, config, include_hash=include_hash)
            changed = True
    else:
        for filename in list(index.keys()):
            if not _is_safe_filename(filename):
                index.pop(filename, None)
                changed = True
                continue
            path = os.path.join(upload_dir, filename)
            if not os.path.isfile(path):
                index.pop(filename, None)
                changed = True
                continue
            record = _build_file_record(
                upload_dir,
                filename,
                config,
                index.get(filename),
                include_hash=include_hash,
            )
            if record != index.get(filename):
                index[filename] = record
                changed = True

    if changed:
        _save_index(upload_dir, upload_index, index)
    return index


@dramatiq.actor(queue_name="input_file")
def sync_upload_index_actor(uuid_for_upload: str, upload_dir: str, upload_index: str):
    config = load_input_file_config(uuid_for_upload)
    if config is None:
        logger.warning(f"sync_upload_index_actor: не найден конфиг для uuid_for_upload={uuid_for_upload}")
        return
    _sync_upload_index(upload_dir, upload_index, config)


def _enqueue_index_sync(uuid_for_upload, upload_dir, upload_index):
    try:
        sync_upload_index_actor.send(uuid_for_upload, upload_dir, upload_index)
    except Exception as enqueue_error:
        logger.warning(f"Не удалось отправить задачу sync_upload_index_actor: {enqueue_error}")


def _load_index(upload_dir, upload_index):
    _ensure_upload_dir(upload_dir)
    if not os.path.isfile(upload_index):
        return {}
    try:
        with open(upload_index, "r", encoding="utf-8") as file:
            data = json.load(file)
    except (json.JSONDecodeError, OSError):
        return {}
    if isinstance(data, dict):
        files_data = data.get("files")
        if isinstance(files_data, dict):
            return files_data
        return data
    return {}


def _save_index(upload_dir, upload_index, index):
    _ensure_upload_dir(upload_dir)
    temp_path = f"{upload_index}.tmp"
    with open(temp_path, "w", encoding="utf-8") as file:
        json.dump({"files": index}, file, ensure_ascii=True, indent=2)
    os.replace(temp_path, upload_index)


def _build_file_record(upload_dir, filename, config, existing=None, include_hash=True):
    if not isinstance(existing, dict):
        existing = None
    path = os.path.join(upload_dir, filename)
    size_bytes = os.path.getsize(path)
    modified_ts = os.path.getmtime(path)
    ext = os.path.splitext(filename)[1].lstrip(".").lower()
    is_image = ext in config["image_exts"]

    file_hash = None
    if existing and existing.get("size_bytes") == size_bytes and existing.get("modified_ts") == modified_ts and existing.get("hash"):
        file_hash = existing.get("hash")
    if include_hash and not file_hash:
        file_hash = _compute_file_hash(path, config)

    return {
        "name": filename,
        "size_bytes": size_bytes,
        "modified_ts": modified_ts,
        "hash": file_hash,
        "ext": ext,
        "is_image": is_image,
    }


def _build_file_meta(record, course_id, uuid_for_upload, config):
    filename = record.get("name", "")
    size_bytes = record.get("size_bytes", 0)
    ext = record.get("ext") or os.path.splitext(filename)[1].lstrip(".").lower()
    is_image = record.get("is_image", ext in config["image_exts"])
    modified_ts = record.get("modified_ts", 0)
    modified = datetime.fromtimestamp(modified_ts).strftime("%Y-%m-%d %H:%M") if modified_ts else ""

    preview_url = url_for(
        "input_file.get_file",
        filename=filename,
        course=course_id,
        uuid_for_upload=uuid_for_upload,
    )
    download_url = url_for(
        "input_file.download_file",
        filename=filename,
        course=course_id,
        uuid_for_upload=uuid_for_upload,
    )
    file_hash = record.get("hash")

    return {
        "name": filename,
        "size_bytes": size_bytes,
        "size_label": _format_size(size_bytes),
        "ext": ext or "file",
        "modified": modified,
        "modified_ts": modified_ts,
        "is_image": is_image,
        "preview_url": preview_url if is_image else None,
        "download_url": download_url,
        "hash": file_hash,
        "hash_short": file_hash[:12] if file_hash else None,
    }


def _list_uploaded_files(upload_dir, upload_index, course_id, uuid_for_upload, config):
    index = _sync_upload_index(upload_dir, upload_index, config, include_hash=False)

    entries = []
    for filename, record in index.items():
        if not _is_safe_filename(filename):
            continue
        if record.get("name") != filename:
            record = {**record, "name": filename}
        entries.append(_build_file_meta(record, course_id, uuid_for_upload, config))

    entries.sort(key=lambda item: item["modified_ts"], reverse=True)
    for item in entries:
        item.pop("modified_ts", None)
    return entries


def _get_current_username():
    username = session.get("user")
    if not username:
        return None
    if not _is_safe_filename(username) or len(username) > 128:
        return None
    return username


def _get_uuid_for_upload_from_request(explicit_uuid=None):
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


def _require_request_config(explicit_uuid=None, page_on_missing=False):
    uuid_for_upload = _get_uuid_for_upload_from_request(explicit_uuid=explicit_uuid)
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


def _get_course_id_from_request(config):
    course_id = (request.args.get("course") or config["course_id"]).strip()
    if not course_id:
        course_id = config["course_id"]
    if not config["course_id_re"].fullmatch(course_id):
        return None
    return course_id


def _require_upload_context(config):
    username = _get_current_username()
    if not username:
        return None, (jsonify({"error": "Требуется авторизация."}), 401)

    course_id = _get_course_id_from_request(config)
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


@input_file_bp.route("/input_file", methods=["GET"])
def input_file_page_without_id():
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template("input_file/not_found.html", uuid_for_upload=None), 404


@input_file_bp.route("/input_file/<string:ID_fields>", methods=["GET"])
def input_file_page(ID_fields):
    try:
        if "user" not in session:
            return redirect(url_for("login"))

        config, uuid_for_upload, err = _require_request_config(explicit_uuid=ID_fields, page_on_missing=True)
        if err:
            return err

        course_id = _get_course_id_from_request(config)
        if not course_id:
            return "", 400

        return render_template(
            "input_file/input.html",
            course_id=course_id,
            uuid_for_upload=uuid_for_upload,
            max_file_size_mb=config["max_file_size_mb"],
            max_attached_files=config["max_attached_files"],
            allowed_exts=sorted(config["allowed_exts"]),
        )
    except Exception as error:
        error_id = _error_id_logger(error)
        return render_template("error/error.html", id_error=error_id)


@input_file_bp.route("/input_file/<string:uuid_for_upload>/list", methods=["GET"])
def list_files(uuid_for_upload):
    try:
        config, uuid_for_upload, err = _require_request_config(explicit_uuid=uuid_for_upload)
        if err:
            return err

        ctx, err = _require_upload_context(config)
        if err:
            return err

        files = _list_uploaded_files(
            ctx["upload_dir"],
            ctx["upload_index"],
            ctx["course_id"],
            uuid_for_upload,
            config,
        )
        return jsonify({"files": files})
    except Exception as error:
        error_id = _error_id_logger(error)
        return jsonify({"error": f"Ошибка списка файлов: {error_id}"}), 500


@input_file_bp.route("/input_file/<string:uuid_for_upload>/upload", methods=["POST"])
def upload_files(uuid_for_upload):
    try:
        config, uuid_for_upload, err = _require_request_config(explicit_uuid=uuid_for_upload)
        if err:
            return err

        ctx, err = _require_upload_context(config)
        if err:
            return err

        files = request.files.getlist("file")
        if not files:
            return jsonify({"added": [], "errors": ["Файлы не выбраны."]}), 400

        _ensure_upload_dir(ctx["upload_dir"])

        index = _load_index(ctx["upload_dir"], ctx["upload_index"])
        index_changed = False
        added = []
        errors = []

        for indexed_name in list(index.keys()):
            indexed_path = os.path.join(ctx["upload_dir"], indexed_name)
            if not _is_safe_filename(indexed_name) or not os.path.isfile(indexed_path):
                index.pop(indexed_name, None)
                index_changed = True

        current_count = len(index)

        for file in files:
            filename = file.filename or ""
            if not filename:
                errors.append("Пропущен файл без имени.")
                continue
            if not _is_safe_filename(filename):
                errors.append(f"Недопустимое имя файла: {filename}")
                continue
            if not _is_allowed_extension(filename, config):
                errors.append(f"Недопустимое расширение: {filename}")
                continue

            is_replacement = filename in index
            if not is_replacement and current_count >= config["max_attached_files"]:
                errors.append(f"Превышено максимальное количество файлов: {config['max_attached_files']}.")
                continue

            target_path = os.path.join(ctx["upload_dir"], filename)
            file.save(target_path)

            size_bytes = os.path.getsize(target_path)
            if size_bytes > config["max_file_size_bytes"]:
                os.remove(target_path)
                errors.append(f"Файл слишком большой: {filename}")
                continue

            record = _build_file_record(
                ctx["upload_dir"],
                filename,
                config,
                index.get(filename),
                include_hash=False,
            )
            index[filename] = record
            index_changed = True
            if not is_replacement:
                current_count += 1
            added.append(_build_file_meta(record, ctx["course_id"], uuid_for_upload, config))

        if index_changed:
            _save_index(ctx["upload_dir"], ctx["upload_index"], index)
            _enqueue_index_sync(uuid_for_upload, ctx["upload_dir"], ctx["upload_index"])

        return jsonify({"added": added, "errors": errors}), (200 if added else 400)
    except Exception as error:
        error_id = _error_id_logger(error)
        return jsonify({"added": [], "errors": [f"Ошибка загрузки: {error_id}"]}), 500


@input_file_bp.route("/input_file/<string:uuid_for_upload>/rename", methods=["POST"])
def rename_file(uuid_for_upload):
    try:
        config, uuid_for_upload, err = _require_request_config(explicit_uuid=uuid_for_upload)
        if err:
            return err

        ctx, err = _require_upload_context(config)
        if err:
            return err

        data = request.get_json(silent=True) or {}
        old_name = (data.get("from") or data.get("old_name") or data.get("old") or "").strip()
        new_name = (data.get("to") or data.get("new_name") or data.get("new") or "").strip()

        if not _is_safe_filename(old_name):
            return jsonify({"ok": False, "error": "Недопустимое имя файла."}), 400
        if not new_name:
            return jsonify({"ok": False, "error": "Новое имя не задано."}), 400
        if not _is_safe_filename(new_name):
            return jsonify({"ok": False, "error": "Недопустимое новое имя файла."}), 400
        if not _is_allowed_extension(new_name, config):
            return jsonify({"ok": False, "error": "Недопустимое расширение."}), 400

        old_path = os.path.join(ctx["upload_dir"], old_name)
        new_path = os.path.join(ctx["upload_dir"], new_name)
        if not os.path.isfile(old_path):
            return jsonify({"ok": False, "error": "Файл не найден."}), 404

        if old_name == new_name:
            index = _load_index(ctx["upload_dir"], ctx["upload_index"])
            record = _build_file_record(
                ctx["upload_dir"],
                old_name,
                config,
                index.get(old_name),
                include_hash=False,
            )
            index[old_name] = record
            _save_index(ctx["upload_dir"], ctx["upload_index"], index)
            _enqueue_index_sync(uuid_for_upload, ctx["upload_dir"], ctx["upload_index"])
            return jsonify({"ok": True, "file": _build_file_meta(record, ctx["course_id"], uuid_for_upload, config)})

        if os.path.exists(new_path):
            return jsonify({"ok": False, "error": "Файл с таким именем уже существует."}), 409

        os.replace(old_path, new_path)

        index = _load_index(ctx["upload_dir"], ctx["upload_index"])
        existing = index.pop(old_name, None)
        record = _build_file_record(
            ctx["upload_dir"],
            new_name,
            config,
            existing,
            include_hash=False,
        )
        index[new_name] = record
        _save_index(ctx["upload_dir"], ctx["upload_index"], index)
        _enqueue_index_sync(uuid_for_upload, ctx["upload_dir"], ctx["upload_index"])

        return jsonify({"ok": True, "file": _build_file_meta(record, ctx["course_id"], uuid_for_upload, config)})
    except Exception as error:
        error_id = _error_id_logger(error)
        return jsonify({"ok": False, "error": f"Ошибка переименования: {error_id}"}), 500


@input_file_bp.route("/input_file/<string:uuid_for_upload>/delete", methods=["POST"])
def delete_file(uuid_for_upload):
    try:
        config, _, err = _require_request_config(explicit_uuid=uuid_for_upload)
        if err:
            return err

        ctx, err = _require_upload_context(config)
        if err:
            return err

        data = request.get_json(silent=True) or {}
        filename = data.get("name", "")

        if not _is_safe_filename(filename):
            return jsonify({"ok": False, "error": "Недопустимое имя файла."}), 400

        path = os.path.join(ctx["upload_dir"], filename)
        if not os.path.isfile(path):
            return jsonify({"ok": False, "error": "Файл не найден."}), 404

        os.remove(path)
        index = _load_index(ctx["upload_dir"], ctx["upload_index"])
        if filename in index:
            index.pop(filename, None)
            _save_index(ctx["upload_dir"], ctx["upload_index"], index)
            _enqueue_index_sync(uuid_for_upload, ctx["upload_dir"], ctx["upload_index"])

        return jsonify({"ok": True})
    except Exception as error:
        error_id = _error_id_logger(error)
        return jsonify({"ok": False, "error": f"Ошибка удаления: {error_id}"}), 500


@input_file_bp.route("/input_file/file/<uuid_for_upload>/<path:filename>", methods=["GET"])
def get_file(uuid_for_upload, filename):
    try:
        if "user" not in session:
            return redirect(url_for("login"))

        config, _, err = _require_request_config(explicit_uuid=uuid_for_upload)
        if err:
            _, status = err
            return "", status

        ctx, err = _require_upload_context(config)
        if err:
            _, status = err
            return "", status

        if not _is_safe_filename(filename):
            return "", 400
        if not os.path.isdir(ctx["upload_dir"]):
            return "", 404

        return send_from_directory(ctx["upload_dir"], filename, as_attachment=False)
    except Exception as error:
        error_id = _error_id_logger(error)
        return render_template("error/error.html", id_error=error_id)


@input_file_bp.route("/input_file/download/<uuid_for_upload>/<path:filename>", methods=["GET"])
def download_file(uuid_for_upload, filename):
    try:
        if "user" not in session:
            return redirect(url_for("login"))

        config, _, err = _require_request_config(explicit_uuid=uuid_for_upload)
        if err:
            _, status = err
            return "", status

        ctx, err = _require_upload_context(config)
        if err:
            _, status = err
            return "", status

        if not _is_safe_filename(filename):
            return "", 400
        if not os.path.isdir(ctx["upload_dir"]):
            return "", 404

        return send_from_directory(ctx["upload_dir"], filename, as_attachment=True)
    except Exception as error:
        error_id = _error_id_logger(error)
        return render_template("error/error.html", id_error=error_id)
