import os
from uuid import uuid4

from flask import (
    Blueprint,
    abort,
    current_app,
    jsonify,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)
from loguru import logger

from app_state import GANTT_STORE

gantt_bp = Blueprint("gantt", __name__)


def _error_id_logger(error):
    id_error = str(uuid4())
    logger.error(f"ID: {id_error} Ошибка: {error}")
    return id_error


@gantt_bp.route("/gantt/<path:id>")
def gantt(id):
    try:
        current_app.logger.info(f"Открыта диаграмма Ганта id={id}")
        if "user" not in session:
            return redirect(url_for("login"))
        editable = request.args.get("editable", "1").lower() in ("1", "true", "yes")
        mobile_timeline_first = request.args.get("mobile_timeline_first", "1").lower() in (
            "1",
            "true",
            "yes",
        )
        gantt_id = request.args.get("id", id)

        def _color_meta(hexcol):
            c = hexcol.lstrip("#")
            r, g, b = int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)
            lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
            text = "#111827" if lum > 170 else "#ffffff"
            overlay = "rgba(255,255,255,0.32)" if lum <= 170 else "rgba(17,24,39,0.16)"
            border = "rgba(17,24,39,0.12)"
            return {"bg": hexcol, "text": text, "overlay": overlay, "border": border}

        GANTT_COLORS = {
            "group": _color_meta("#111827"),
            "task": _color_meta("#2563EB"),
            "done": _color_meta("#9CA3AF"),
            "muted": _color_meta("#E5E7EB"),
            # Backward compatibility with previously saved tasks.
            "pink": _color_meta("#2563EB"),
            "red": _color_meta("#111827"),
            "blue": _color_meta("#2563EB"),
            "cyan": _color_meta("#9CA3AF"),
        }
        gantt_legend = [
            {"name": "Группы", "color_key": "group"},
            {"name": "Задачи", "color_key": "task"},
            {"name": "Завершено", "color_key": "done"},
        ]
        return render_template(
            "gantt/gantt_dhtmlx.html",
            editable=editable,
            name="Панель Ганта",
            subtitle="Календарный план курса и контроль дедлайнов",
            colors=GANTT_COLORS,
            legend=gantt_legend,
            gantt_id=gantt_id,
            mobile_timeline_first=mobile_timeline_first,
        )
    except Exception as e:
        id_error = _error_id_logger(e)
        return render_template("error/error.html", id_error=id_error)


@gantt_bp.route("/gantt")
def gantt_root():
    return redirect(url_for("gantt.gantt", id="default"))


@gantt_bp.route("/api/gantt_tasks")
def gantt_tasks_default():
    query_id = request.args.get("id", "default")
    return gantt_tasks(query_id)


@gantt_bp.route("/api/gantt_tasks/<path:id>")
def gantt_tasks(id):
    try:
        current_app.logger.info(f"Запрошены задачи для диаграммы Ганта id={id}")
        if id in GANTT_STORE:
            store = GANTT_STORE[id]
            return jsonify({"data": store.get("data", []), "links": store.get("links", [])})

        if id == "kurse1":
            tasks = [
                {
                    "id": 1,
                    "text": "Курс 1: Планирование",
                    "start_date": "2025-11-01",
                    "duration": 3,
                    "open": True,
                    "progress": 0.3,
                    "color": "group",
                },
                {
                    "id": 2,
                    "text": "Курс 1: Сбор требований",
                    "start_date": "2025-11-01",
                    "duration": 1,
                    "parent": 1,
                    "progress": 1,
                    "color": "done",
                },
            ]
        else:
            tasks = [
                {
                    "id": 1,
                    "text": "Планирование",
                    "start_date": "2025-11-01",
                    "duration": 3,
                    "open": True,
                    "progress": 0.3,
                    "color": "group",
                },
                {
                    "id": 2,
                    "text": "Сбор требований",
                    "start_date": "2025-11-01",
                    "duration": 1,
                    "parent": 1,
                    "progress": 1,
                    "color": "done",
                },
                {
                    "id": 3,
                    "text": "Определение объема",
                    "start_date": "2025-11-02",
                    "duration": 2,
                    "parent": 1,
                    "progress": 0.4,
                    "color": "task",
                },
                {
                    "id": 4,
                    "text": "Разработка",
                    "start_date": "2025-11-05",
                    "duration": 9,
                    "open": True,
                    "progress": 0.2,
                    "color": "group",
                },
                {
                    "id": 5,
                    "text": "Бэкенд",
                    "start_date": "2025-11-05",
                    "duration": 4,
                    "parent": 4,
                    "progress": 0.2,
                    "color": "task",
                },
                {
                    "id": 6,
                    "text": "Фронтенд",
                    "start_date": "2025-11-09",
                    "duration": 5,
                    "parent": 4,
                    "progress": 0.1,
                    "color": "task",
                },
            ]
        links = [
            {"id": 1, "source": 2, "target": 3, "type": "0"},
            {"id": 2, "source": 3, "target": 4, "type": "0"},
            {"id": 3, "source": 5, "target": 6, "type": "0"},
        ]

        def _short_label(text, limit=28):
            if not text:
                return ""
            txt = str(text)
            return txt if len(txt) <= limit else txt[: limit - 3] + "..."

        for t in tasks:
            t.setdefault("label", _short_label(t.get("text")))
        GANTT_STORE[id] = {"data": tasks.copy(), "links": links.copy()}
        return jsonify({"data": tasks, "links": links})
    except Exception as e:
        id_error = _error_id_logger(e)
        return jsonify({"error": str(e), "id_error": id_error}), 500


@gantt_bp.route("/api/gantt_tasks/<path:id>", methods=["POST", "PUT", "DELETE"])
def gantt_tasks_modify(id):
    try:
        if "user" not in session:
            return jsonify({"error": "not authenticated"}), 401
        payload = request.get_json(force=True, silent=True) or {}
        action = payload.get("action") or payload.get("type")
        data = payload.get("data") or payload.get("task") or payload.get("link") or payload

        store = GANTT_STORE.setdefault(id, {"data": [], "links": []})

        def _as_int(value):
            try:
                return int(value)
            except (TypeError, ValueError):
                return None

        def _next_task_id():
            existing = [int(t["id"]) for t in store["data"] if isinstance(t.get("id"), int)]
            return (max(existing) + 1) if existing else 1

        def _next_link_id():
            existing = [int(l["id"]) for l in store["links"] if isinstance(l.get("id"), int)]
            return (max(existing) + 1) if existing else 1

        if request.method == "POST" or action in ("inserted", "add_task", "add_link"):
            if "source" in data and "target" in data:
                new_id = _next_link_id()
                new_link = {
                    "id": new_id,
                    "source": int(data["source"]),
                    "target": int(data["target"]),
                    "type": data.get("type", "0"),
                }
                store["links"].append(new_link)
                logger.info(f"Добавлена ссылка в GANTT {id}: {new_link}")
                return jsonify({"action": "inserted", "id": new_id}), 201
            else:
                new_id = _next_task_id()
                new_task = data.copy() if isinstance(data, dict) else {}
                new_task["id"] = new_id
                store["data"].append(new_task)
                logger.info(f"Добавлена задача в GANTT {id}: {new_task}")
                return jsonify({"action": "inserted", "id": new_id}), 201

        if request.method == "PUT" or action in ("updated", "update_task", "update_link"):
            if "source" in data and "target" in data:
                lid = _as_int(data.get("id"))
                if lid is None:
                    return jsonify({"error": "link id is required"}), 400
                found = next((l for l in store["links"] if _as_int(l.get("id")) == lid), None)
                if not found:
                    return jsonify({"error": "link not found"}), 404
                found.update(data)
                logger.info(f"Обновлена ссылка в GANTT {id}: {found}")
                return jsonify({"action": "updated", "id": lid})
            else:
                tid = _as_int(data.get("id"))
                if tid is None:
                    return jsonify({"error": "task id is required"}), 400
                found = next((t for t in store["data"] if _as_int(t.get("id")) == tid), None)
                if not found:
                    return jsonify({"error": "task not found"}), 404
                found.update(data)
                logger.info(f"Обновлена задача в GANTT {id}: {found}")
                return jsonify({"action": "updated", "id": tid})

        if request.method == "DELETE" or action in ("deleted", "delete_task", "delete_link"):
            # Delete task or link
            if "id" in data and "source" in data and "target" in data:
                lid = _as_int(data.get("id"))
                if lid is None:
                    return jsonify({"error": "link id is required"}), 400
                store["links"] = [l for l in store["links"] if _as_int(l.get("id")) != lid]
                logger.info(f"Удалена ссылка {lid} из GANTT {id}")
                return jsonify({"action": "deleted", "id": lid})
            if "id" in data:
                tid = _as_int(data.get("id"))
                if tid is None:
                    return jsonify({"error": "task id is required"}), 400
                store["data"] = [t for t in store["data"] if _as_int(t.get("id")) != tid]
                logger.info(f"Удалена задача {tid} из GANTT {id}")
                return jsonify({"action": "deleted", "id": tid})

        return jsonify({"error": "Unsupported operation", "payload": payload}), 400
    except Exception as e:
        id_error = _error_id_logger(e)
        return jsonify({"error": str(e), "id_error": id_error}), 500


@gantt_bp.route("/gantt/static/<path:filename>")
def gantt_static(filename):
    try:
        safe = os.path.normpath(filename)
        if safe.startswith(".."):
            return abort(403)
        static_folder = current_app.static_folder
        if not static_folder:
            return abort(404)
        file_path = os.path.join(static_folder, "gantt", safe)
        if not os.path.isfile(file_path):
            return abort(404)
        if file_path.endswith(".css"):
            mimetype = "text/css; charset=utf-8"
        elif file_path.endswith(".js"):
            mimetype = "application/javascript; charset=utf-8"
        else:
            mimetype = None
        if mimetype:
            return send_from_directory(os.path.dirname(file_path), os.path.basename(file_path), mimetype=mimetype)
        if file_path.endswith(".ttf"):
            return send_from_directory(os.path.dirname(file_path), os.path.basename(file_path), mimetype="font/ttf")
        if file_path.endswith(".woff"):
            return send_from_directory(os.path.dirname(file_path), os.path.basename(file_path), mimetype="font/woff")
        if file_path.endswith(".woff2"):
            return send_from_directory(os.path.dirname(file_path), os.path.basename(file_path), mimetype="font/woff2")
        return send_from_directory(os.path.dirname(file_path), os.path.basename(file_path))
    except Exception as e:
        id_error = _error_id_logger(e)
        # Fix endpoint name in url_for: use 'gantt.gantt_static' instead of 'gantt_static'
        return render_template("error/error.html", id_error=id_error)
