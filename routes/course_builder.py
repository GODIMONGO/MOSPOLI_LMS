from flask import Blueprint, render_template

from routes.admin_utils import log_error_id, require_auth_redirect

course_builder_bp = Blueprint("course_builder", __name__)


@course_builder_bp.route("/admin/course-builder")
def admin_course_builder():
    try:
        auth_redirect = require_auth_redirect()
        if auth_redirect:
            return auth_redirect
        return render_template("Admin/CourseBuilder.html")
    except Exception as e:
        id_error = log_error_id(e)
        return render_template("error/error.html", id_error=id_error)
