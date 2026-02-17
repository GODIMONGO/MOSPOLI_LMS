from uuid import uuid4

from flask import Blueprint, current_app, redirect, render_template, request, session, url_for
from loguru import logger

my_curse_bp = Blueprint("my_curse", __name__)


def _error_id_logger(error):
    id_error = str(uuid4())
    logger.error(f"ID: {id_error} Ошибка: {error}")
    return id_error


STATUS_LEGEND = [
    {"text": "Отлично", "class_name": "legend-pill--excellent"},
    {"text": "Хорошо", "class_name": "legend-pill--good"},
    {"text": "Удовлетворительно", "class_name": "legend-pill--satisfactory"},
    {"text": "Неудовл.", "class_name": "legend-pill--poor"},
    {"text": "В процессе", "class_name": "legend-pill--in-progress"},
]

COMPLETION_CLASS_MAP = {
    "Не начато": "status-pill--not-started",
    "В процессе": "status-pill--in-progress",
    "Выполнено": "status-pill--done",
    "Просрочено": "status-pill--overdue",
}

GRADING_CLASS_MAP = {
    "Не оценено": "status-pill--not-graded",
    "Удовлетворительно": "status-pill--satisfactory",
    "Хорошо": "status-pill--good",
    "Отлично": "status-pill--excellent",
    "Неудовл.": "status-pill--poor",
}

GRADING_TEXT_BY_QUERY = {
    "none": "Не оценено",
    "satisfactory": "Удовлетворительно",
    "good": "Хорошо",
    "excellent": "Отлично",
    "poor": "Неудовл.",
}

GRADING_VALUE_BY_TEXT = {
    "Удовлетворительно": 5,
    "Хорошо": 7,
    "Отлично": 10,
    "Неудовл.": 2,
}


CARD_TONE_BY_TYPE = {
    "info": "info",
    "video": "video",
    "assignment": "task",
    "lab": "task",
    "test": "test",
}


def _parse_grade_value(raw_grade):
    if raw_grade in (None, ""):
        return None

    try:
        return int(raw_grade)
    except ValueError:
        return None


def _build_task_detail_data(task_id, course_id):
    normalized_task_id = (task_id or "").lower()
    is_lab_view = "lab" in normalized_task_id or "report" in normalized_task_id or normalized_task_id == "2"

    if is_lab_view:
        return {
            "title": "Лабораторная работа №2. Нормализация структуры базы данных",
            "is_compact": False,
            "completion_status": "Выполнено",
            "grading_status": "Не оценено",
            "grade_value": None,
            "updated_at": "10.11.2025 19:30",
            "answer_files": [
                {
                    "name": "Lab2_Report_Baranova.pdf",
                    "meta": "PDF, 1.6 MB",
                    "href": url_for("input_file.input_file_page", ID_fields="test", course=course_id),
                },
                {
                    "name": "schema_v3.drawio",
                    "meta": "DRAWIO, 428 KB",
                    "href": url_for("input_file.input_file_page", ID_fields="test", course=course_id),
                },
            ],
            "answer_comment": (
                "Добавила пояснения к выбору ключей и обновила диаграмму после замечаний к предыдущей версии."
            ),
            "assignment_brief": (
                "Сформируйте нормализованную структуру таблиц для учебной базы данных и "
                "приложите итоговый отчет."
            ),
            "report_items": [
                "Краткое описание предметной области и сущностей.",
                "ER-модель и обоснование связей.",
                "Переход к 1НФ, 2НФ и 3НФ с комментариями.",
                "Финальная структура таблиц с ключами и типами данных.",
                "Выводы и оценка ограничений решения.",
            ],
            "materials": [
                "Шаблон отчета к лабораторной №2",
                "Методические рекомендации по нормализации",
                "Пример структуры SQL-скрипта",
            ],
        }

    return {
        "title": "Задание. Тема 1. Распределение роли в команде",
        "is_compact": True,
        "completion_status": "Выполнено",
        "grading_status": "Хорошо",
        "grade_value": 7,
        "updated_at": "27.10.2025 14:23",
        "answer_files": [
            {
                "name": "team_roles_v2.docx",
                "meta": "DOCX, 312 KB",
                "href": url_for("input_file.input_file_page", ID_fields="test", course=course_id),
            }
        ],
        "answer_comment": "Роли согласованы внутри команды. Обновила аргументацию по выбранному лидеру.",
        "assignment_brief": (
            "Опишите распределение ролей в проектной команде и приложите краткое обоснование "
            "для каждой роли."
        ),
        "report_items": [],
        "materials": [],
    }


def _apply_task_state_overrides(task_data):
    completion_status = request.args.get("completion")
    if completion_status:
        task_data["completion_status"] = completion_status

    grading_query = (request.args.get("grading") or "").strip().lower()
    if grading_query:
        task_data["grading_status"] = GRADING_TEXT_BY_QUERY.get(grading_query, task_data["grading_status"])

    grade_value = _parse_grade_value(request.args.get("grade"))
    if "grade" in request.args:
        task_data["grade_value"] = grade_value

    files_mode = (request.args.get("files") or "").strip().lower()
    if files_mode == "none":
        task_data["answer_files"] = []

    comment_mode = (request.args.get("comment") or "").strip().lower()
    if comment_mode == "none":
        task_data["answer_comment"] = ""

    view_mode = (request.args.get("view") or "").strip().lower()
    if view_mode == "compact":
        task_data["is_compact"] = True
        task_data["report_items"] = []
    elif view_mode == "full":
        task_data["is_compact"] = False


def _prepare_task_view_model(task_data):
    completion_status = task_data.get("completion_status", "В процессе")
    grading_status = task_data.get("grading_status", "Не оценено")
    grade_value = task_data.get("grade_value")

    task_data["completion_class"] = COMPLETION_CLASS_MAP.get(completion_status, "status-pill--in-progress")
    task_data["grading_class"] = GRADING_CLASS_MAP.get(grading_status, "status-pill--not-graded")
    task_data["is_graded"] = grading_status != "Не оценено" and grade_value is not None

    if task_data["is_graded"] is False and "grade" not in request.args:
        task_data["grade_value"] = GRADING_VALUE_BY_TEXT.get(grading_status)

    task_data["has_files"] = bool(task_data.get("answer_files"))
    task_data["has_comment"] = bool((task_data.get("answer_comment") or "").strip())


def _project_modules_to_legacy_blocks(modules):
    legacy_blocks = []
    for module_index, module in enumerate(modules, start=1):
        module_id = module.get("id") or f"module-{module_index}"
        module_title = module.get("title", f"Модуль {module_index}")

        for theme_index, theme in enumerate(module.get("themes", []), start=1):
            theme_cards = theme.get("cards", [])
            theme_tone = theme.get("tone")
            if not theme_tone and theme_cards:
                theme_tone = CARD_TONE_BY_TYPE.get((theme_cards[0].get("type") or "").lower(), "info")

            legacy_blocks.append(
                {
                    "id": theme.get("id") or f"{module_id}-theme-{theme_index}",
                    "title": theme.get("title", f"Тема {theme_index}"),
                    "collapsed": theme.get("collapsed", False),
                    "cross_icon": theme.get("cross_icon", "my_curse/icons/arrow.svg"),
                    "tone": theme_tone or "info",
                    "module_title": module_title,
                    "items": [
                        {
                            "id": card.get("id") or f"{module_id}-theme-{theme_index}-card-{card_index}",
                            "icon": card.get("icon", "my_curse/icons/todo_list.svg"),
                            "text": card.get("title", "Элемент без названия"),
                            "href": card.get("href", "#"),
                        }
                        for card_index, card in enumerate(theme_cards, start=1)
                    ],
                }
            )

    return legacy_blocks


@my_curse_bp.route("/my_curse/<path:id>")
def my_curse(id):
    try:
        current_app.logger.info(f"Открыт мой курс id={id}")
        if "user" not in session:
            return redirect(url_for("login"))

        # A08: целевая структура module -> theme -> cards.
        # Legacy `blocks` сохраняем как проекцию для обратной совместимости.
        course_data = {
            "id": id,
            "schema_version": "2.1",
            "name": "Основы проектирования БД",
            "pill": {
                "icon": "my_curse/icons/curse-icon.svg",
                "text": "Осн.БД 25",
                "close_icon": "my_curse/icons/cross.svg",
            },
            "modules": [
                {
                    "id": "module-1",
                    "title": "Модуль 1. Основы проектной деятельности",
                    "collapsed": False,
                    "cross_icon": "my_curse/icons/arrow.svg",
                    "themes": [
                        {
                            "id": "module-1-theme-1",
                            "title": "Тема 1. Общая информация",
                            "tone": "info",
                            "collapsed": False,
                            "cross_icon": "my_curse/icons/arrow.svg",
                            "cards": [
                                {
                                    "id": "card-1",
                                    "type": "info",
                                    "icon": "my_curse/icons/info.svg",
                                    "title": "Теоретический материал",
                                    "href": "#",
                                    "collapsed": True,
                                    "completed": False,
                                    "with_grade": False,
                                    "with_comment": False,
                                    "with_files": False,
                                    "meta": {
                                        "author": "Преподаватель",
                                        "date": "17.02.2026",
                                        "period": "Неделя 1",
                                    },
                                },
                                {
                                    "id": "card-2",
                                    "type": "info",
                                    "icon": "my_curse/icons/info.svg",
                                    "title": "Информация",
                                    "href": "#",
                                    "collapsed": True,
                                    "completed": False,
                                    "with_grade": False,
                                    "with_comment": False,
                                    "with_files": False,
                                    "meta": {
                                        "author": "Кафедра",
                                        "date": "18.02.2026",
                                        "period": "Неделя 1",
                                    },
                                },
                            ],
                        },
                        {
                            "id": "module-1-theme-2",
                            "title": "Тема 2. Практические задания",
                            "tone": "task",
                            "collapsed": False,
                            "cross_icon": "my_curse/icons/arrow.svg",
                            "cards": [
                                {
                                    "id": "card-3",
                                    "type": "assignment",
                                    "icon": "my_curse/icons/info.svg",
                                    "title": "Задание. Тема 1 (детали)",
                                    "href": url_for(
                                        "my_curse.task_detail", course_id=id, task_id="assignment-team-roles"
                                    ),
                                    "collapsed": True,
                                    "completed": True,
                                    "with_grade": True,
                                    "with_comment": True,
                                    "with_files": True,
                                    "meta": {
                                        "author": "Преподаватель",
                                        "date": "27.10.2025",
                                        "period": "17.02-23.02",
                                    },
                                },
                                {
                                    "id": "card-4",
                                    "type": "lab",
                                    "icon": "my_curse/icons/todo_list.svg",
                                    "title": "Лабораторная работа №2 (детали)",
                                    "href": url_for("my_curse.task_detail", course_id=id, task_id="lab-2-report"),
                                    "collapsed": False,
                                    "completed": True,
                                    "with_grade": False,
                                    "with_comment": True,
                                    "with_files": True,
                                    "meta": {
                                        "author": "Преподаватель",
                                        "date": "10.11.2025",
                                        "period": "24.02-02.03",
                                    },
                                },
                                {
                                    "id": "card-5",
                                    "type": "video",
                                    "icon": "my_curse/icons/todo_list.svg",
                                    "title": "Видео-урок. Тема 1",
                                    "href": "#",
                                    "collapsed": True,
                                    "completed": False,
                                    "with_grade": False,
                                    "with_comment": False,
                                    "with_files": False,
                                    "meta": {
                                        "author": "Преподаватель",
                                        "date": "19.02.2026",
                                        "period": "Неделя 2",
                                    },
                                },
                            ],
                        },
                    ],
                },
            ],
        }
        course_data["blocks"] = _project_modules_to_legacy_blocks(course_data["modules"])

        return render_template(
            "my_curse/my_curse.html",
            course_id=course_data["id"],
            schema_version=course_data["schema_version"],
            name=course_data["name"],
            course_pill=course_data["pill"],
            modules=course_data["modules"],
            blocks=course_data["blocks"],
        )

    except Exception as e:
        id_error = _error_id_logger(e)
        return render_template("error/error.html", id_error=id_error)


@my_curse_bp.route("/my_curse/<path:course_id>/task/<path:task_id>")
def task_detail(course_id, task_id):
    try:
        current_app.logger.info(f"Открыта детальная страница задания course_id={course_id}, task_id={task_id}")
        if "user" not in session:
            return redirect(url_for("login"))

        task_data = _build_task_detail_data(task_id, course_id)
        _apply_task_state_overrides(task_data)
        _prepare_task_view_model(task_data)
        task_data["action_edit_url"] = url_for("input_file.input_file_page", ID_fields="test", course=course_id)
        task_data["action_delete_available"] = False

        return render_template(
            "my_curse/task_detail.html",
            course_id=course_id,
            task_id=task_id,
            page_title=task_data["title"],
            task=task_data,
            status_legend=STATUS_LEGEND,
        )
    except Exception as e:
        id_error = _error_id_logger(e)
        return render_template("error/error.html", id_error=id_error)
