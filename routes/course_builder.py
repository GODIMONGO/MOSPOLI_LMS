import json

from flask import Blueprint, render_template, url_for

from routes.admin_utils import log_error_id, require_auth_redirect

course_builder_bp = Blueprint("course_builder", __name__)


@course_builder_bp.route("/admin/course-builder")
def admin_course_builder():
    try:
        auth_redirect = require_auth_redirect()
        if auth_redirect:
            return auth_redirect
        # Временный "слепок БД": backend отдает JSON-строку с доступными блоками.
        blocks_catalog_json = json.dumps(
            [
                {
                    "id": "theory",
                    "title": "Информация",
                    "caption": "Теоретический материал",
                    "tag": "Блок",
                    "tone": "mint",
                    "icon": url_for("static", filename="admin/CourseBuilder/icons/todo_list.svg"),
                    "item_icon": url_for("static", filename="admin/CourseBuilder/icons/todo_list.svg"),
                    "template_url": url_for("base"),
                    "root_selector": ".base-container",
                    "styles": [url_for("static", filename="Base/Base.css")],
                },
                {
                    "id": "video",
                    "title": "Видео",
                    "caption": "Видео-лекция",
                    "tag": "Блок",
                    "tone": "lilac",
                    "icon": url_for("static", filename="admin/CourseBuilder/icons/video.svg"),
                    "item_icon": url_for("static", filename="admin/CourseBuilder/icons/video.svg"),
                    "template_url": url_for("blockvideo"),
                    "root_selector": ".base-container",
                    "styles": [url_for("static", filename="Blockvideo/BlockVideo.css")],
                },
                {
                    "id": "assignment",
                    "title": "Лабораторная работа",
                    "caption": "Практическое задание",
                    "tag": "Блок",
                    "tone": "cyan",
                    "icon": url_for("static", filename="admin/CourseBuilder/icons/assessments.svg"),
                    "item_icon": url_for("static", filename="admin/CourseBuilder/icons/todo_list.svg"),
                    "template_url": url_for("base"),
                    "root_selector": ".base-container",
                    "styles": [url_for("static", filename="Base/Base.css")],
                },
                {
                    "id": "text-answer",
                    "title": "Текстовый ответ",
                    "caption": "Ответ в текстовом поле",
                    "tag": "Блок",
                    "tone": "amber",
                    "icon": url_for("static", filename="admin/CourseBuilder/icons/participants.svg"),
                    "item_icon": url_for("static", filename="admin/CourseBuilder/icons/todo_list.svg"),
                    "template_url": url_for("base"),
                    "root_selector": ".base-container",
                    "styles": [url_for("static", filename="Base/Base.css")],
                },
                {
                    "id": "quiz",
                    "title": "Тест",
                    "caption": "Контрольные вопросы",
                    "tag": "Блок",
                    "tone": "violet",
                    "icon": url_for("static", filename="admin/CourseBuilder/icons/assessments.svg"),
                    "item_icon": url_for("static", filename="admin/CourseBuilder/icons/assessments.svg"),
                    "template_url": "",
                    "root_selector": "",
                    "styles": [],
                },
            ],
            ensure_ascii=False,
        )
        return render_template("Admin/CourseBuilder.html", blocks_catalog_json=blocks_catalog_json)
    except Exception as e:
        id_error = log_error_id(e)
        return render_template("error/error.html", id_error=id_error)
