import os

from flask import redirect, render_template, send_from_directory, session, url_for

from .blueprint import input_file_bp
from .context import error_id_logger, require_request_config, require_upload_context
from .files import is_safe_filename


def _resolve_context_or_status(uuid_for_upload):
    config, _, err = require_request_config(explicit_uuid=uuid_for_upload)
    if err:
        _, status = err
        return None, status

    ctx, err = require_upload_context(config)
    if err:
        _, status = err
        return None, status
    return ctx, None


@input_file_bp.route("/input_file/file/<uuid_for_upload>/<path:filename>", methods=["GET"])
def get_file(uuid_for_upload, filename):
    try:
        if "user" not in session:
            return redirect(url_for("login"))

        ctx, status = _resolve_context_or_status(uuid_for_upload)
        if status:
            return "", status
        if not is_safe_filename(filename):
            return "", 400
        if not os.path.isdir(ctx["upload_dir"]):
            return "", 404

        return send_from_directory(ctx["upload_dir"], filename, as_attachment=False)
    except Exception as error:
        error_id = error_id_logger(error)
        return render_template("error/error.html", id_error=error_id)


@input_file_bp.route("/input_file/download/<uuid_for_upload>/<path:filename>", methods=["GET"])
def download_file(uuid_for_upload, filename):
    try:
        if "user" not in session:
            return redirect(url_for("login"))

        ctx, status = _resolve_context_or_status(uuid_for_upload)
        if status:
            return "", status
        if not is_safe_filename(filename):
            return "", 400
        if not os.path.isdir(ctx["upload_dir"]):
            return "", 404

        return send_from_directory(ctx["upload_dir"], filename, as_attachment=True)
    except Exception as error:
        error_id = error_id_logger(error)
        return render_template("error/error.html", id_error=error_id)
