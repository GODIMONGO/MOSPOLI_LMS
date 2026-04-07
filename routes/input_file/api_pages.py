from flask import redirect, render_template, session, url_for

from .blueprint import input_file_bp
from .context import error_id_logger, get_course_id_from_request, require_request_config


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

        config, uuid_for_upload, err = require_request_config(explicit_uuid=ID_fields, page_on_missing=True)
        if err:
            return err

        course_id = get_course_id_from_request(config)
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
        error_id = error_id_logger(error)
        return render_template("error/error.html", id_error=error_id)
