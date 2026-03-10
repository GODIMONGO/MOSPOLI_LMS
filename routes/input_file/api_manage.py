import os

from flask import jsonify, request

from .blueprint import input_file_bp
from .context import error_id_logger, require_request_config, require_upload_context
from .files import build_file_meta, build_file_record, ensure_upload_dir, is_allowed_extension, is_safe_filename
from .indexing import enqueue_index_sync, list_uploaded_files, load_index, save_index


@input_file_bp.route("/input_file/<string:uuid_for_upload>/list", methods=["GET"])
def list_files(uuid_for_upload):
    try:
        config, uuid_for_upload, err = require_request_config(explicit_uuid=uuid_for_upload)
        if err:
            return err

        ctx, err = require_upload_context(config)
        if err:
            return err

        files = list_uploaded_files(ctx["upload_dir"], ctx["upload_index"], ctx["course_id"], uuid_for_upload, config)
        return jsonify({"files": files})
    except Exception as error:
        error_id = error_id_logger(error)
        return jsonify({"error": f"Ошибка списка файлов: {error_id}"}), 500


@input_file_bp.route("/input_file/<string:uuid_for_upload>/upload", methods=["POST"])
def upload_files(uuid_for_upload):
    try:
        config, uuid_for_upload, err = require_request_config(explicit_uuid=uuid_for_upload)
        if err:
            return err

        ctx, err = require_upload_context(config)
        if err:
            return err

        files = request.files.getlist("file")
        if not files:
            return jsonify({"added": [], "errors": ["Файлы не выбраны."]}), 400

        ensure_upload_dir(ctx["upload_dir"])
        index = load_index(ctx["upload_dir"], ctx["upload_index"])
        index_changed = False
        added = []
        errors = []

        for indexed_name in list(index.keys()):
            indexed_path = os.path.join(ctx["upload_dir"], indexed_name)
            if not is_safe_filename(indexed_name) or not os.path.isfile(indexed_path):
                index.pop(indexed_name, None)
                index_changed = True

        current_count = len(index)
        for file in files:
            filename = file.filename or ""
            if not filename:
                errors.append("Пропущен файл без имени.")
                continue
            if not is_safe_filename(filename):
                errors.append(f"Недопустимое имя файла: {filename}")
                continue
            if not is_allowed_extension(filename, config):
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

            record = build_file_record(ctx["upload_dir"], filename, config, index.get(filename), include_hash=False)
            index[filename] = record
            index_changed = True
            if not is_replacement:
                current_count += 1
            added.append(build_file_meta(record, ctx["course_id"], uuid_for_upload, config))

        if index_changed:
            save_index(ctx["upload_dir"], ctx["upload_index"], index)
            enqueue_index_sync(uuid_for_upload, ctx["upload_dir"], ctx["upload_index"])

        return jsonify({"added": added, "errors": errors}), (200 if added else 400)
    except Exception as error:
        error_id = error_id_logger(error)
        return jsonify({"added": [], "errors": [f"Ошибка загрузки: {error_id}"]}), 500


@input_file_bp.route("/input_file/<string:uuid_for_upload>/rename", methods=["POST"])
def rename_file(uuid_for_upload):
    try:
        config, uuid_for_upload, err = require_request_config(explicit_uuid=uuid_for_upload)
        if err:
            return err

        ctx, err = require_upload_context(config)
        if err:
            return err

        data = request.get_json(silent=True) or {}
        old_name = (data.get("from") or data.get("old_name") or data.get("old") or "").strip()
        new_name = (data.get("to") or data.get("new_name") or data.get("new") or "").strip()

        if not is_safe_filename(old_name):
            return jsonify({"ok": False, "error": "Недопустимое имя файла."}), 400
        if not new_name:
            return jsonify({"ok": False, "error": "Новое имя не задано."}), 400
        if not is_safe_filename(new_name):
            return jsonify({"ok": False, "error": "Недопустимое новое имя файла."}), 400
        if not is_allowed_extension(new_name, config):
            return jsonify({"ok": False, "error": "Недопустимое расширение."}), 400

        old_path = os.path.join(ctx["upload_dir"], old_name)
        new_path = os.path.join(ctx["upload_dir"], new_name)
        if not os.path.isfile(old_path):
            return jsonify({"ok": False, "error": "Файл не найден."}), 404

        if old_name == new_name:
            index = load_index(ctx["upload_dir"], ctx["upload_index"])
            record = build_file_record(ctx["upload_dir"], old_name, config, index.get(old_name), include_hash=False)
            index[old_name] = record
            save_index(ctx["upload_dir"], ctx["upload_index"], index)
            enqueue_index_sync(uuid_for_upload, ctx["upload_dir"], ctx["upload_index"])
            file_meta = build_file_meta(record, ctx["course_id"], uuid_for_upload, config)
            return jsonify({"ok": True, "file": file_meta})

        if os.path.exists(new_path):
            return jsonify({"ok": False, "error": "Файл с таким именем уже существует."}), 409

        os.replace(old_path, new_path)
        index = load_index(ctx["upload_dir"], ctx["upload_index"])
        existing = index.pop(old_name, None)
        record = build_file_record(ctx["upload_dir"], new_name, config, existing, include_hash=False)
        index[new_name] = record
        save_index(ctx["upload_dir"], ctx["upload_index"], index)
        enqueue_index_sync(uuid_for_upload, ctx["upload_dir"], ctx["upload_index"])

        return jsonify({"ok": True, "file": build_file_meta(record, ctx["course_id"], uuid_for_upload, config)})
    except Exception as error:
        error_id = error_id_logger(error)
        return jsonify({"ok": False, "error": f"Ошибка переименования: {error_id}"}), 500


@input_file_bp.route("/input_file/<string:uuid_for_upload>/delete", methods=["POST"])
def delete_file(uuid_for_upload):
    try:
        config, _, err = require_request_config(explicit_uuid=uuid_for_upload)
        if err:
            return err

        ctx, err = require_upload_context(config)
        if err:
            return err

        data = request.get_json(silent=True) or {}
        filename = data.get("name", "")
        if not is_safe_filename(filename):
            return jsonify({"ok": False, "error": "Недопустимое имя файла."}), 400

        path = os.path.join(ctx["upload_dir"], filename)
        if not os.path.isfile(path):
            return jsonify({"ok": False, "error": "Файл не найден."}), 404

        os.remove(path)
        index = load_index(ctx["upload_dir"], ctx["upload_index"])
        if filename in index:
            index.pop(filename, None)
            save_index(ctx["upload_dir"], ctx["upload_index"], index)
            enqueue_index_sync(uuid_for_upload, ctx["upload_dir"], ctx["upload_index"])

        return jsonify({"ok": True})
    except Exception as error:
        error_id = error_id_logger(error)
        return jsonify({"ok": False, "error": f"Ошибка удаления: {error_id}"}), 500
