from flask import Blueprint, render_template

from routes.admin_utils import log_error_id, require_auth_redirect

grades_bp = Blueprint("grades", __name__)


@grades_bp.route("/admin/grades")
def admin_grades():
    try:
        auth_redirect = require_auth_redirect()
        if auth_redirect:
            return auth_redirect
        return render_template("Admin/Grades.html")
    except Exception as e:
        id_error = log_error_id(e)
        return render_template("error/error.html", id_error=id_error)
