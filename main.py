import hashlib
import os
import secrets
from uuid import uuid4

from flask import (
    Flask,
    abort,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)
from flask_socketio import SocketIO
from loguru import logger

from config import configure_logger, load_app_config
from routes.admin import admin_bp
from routes.course_builder import course_builder_bp
from routes.gantt import gantt_bp
from routes.grades import grades_bp
from routes.input_file import input_file_bp
from routes.my_curse import my_curse_bp
from tasks import broker_init_check

configure_logger()
config_data = load_app_config()
app = Flask(__name__, static_folder="static", template_folder="templates")
_secret_key = os.getenv("SECRET_KEY")
if not _secret_key:
    _secret_key = secrets.token_hex(32)
    logger.warning("SECRET_KEY not set; generated ephemeral key.")
app.config["SECRET_KEY"] = _secret_key
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

# Регистрация блюпринта
app.register_blueprint(gantt_bp)
app.register_blueprint(my_curse_bp)
app.register_blueprint(input_file_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(course_builder_bp)
app.register_blueprint(grades_bp)

file_map = {}
users = {"admin": "admin", "student": "123"}
# Colors used by Gantt tasks. Keys are safe identifiers used in task.color.
# Values are CSS color strings (hex or any CSS color).
load_files = ""


def error_id_logger(error):
    id_error = str(uuid4())
    logger.error(f"ID: {id_error} Ошибка: {error}")
    return id_error


try:

    @app.route("/favicon.ico")
    def favicon():
        try:
            return redirect("https://e.mospolytech.ru/icon.png")
        except Exception as e:
            logger.error(f"Ошибка при получении favicon: {e}")

    @app.route("/execution-status")
    def execution_status():
        try:
            if "user" in session:
                return redirect(url_for("login"))
            return
        except Exception as e:
            id_error = error_id_logger(e)
            return render_template("error/error.html", id_error=id_error)

    @app.route("/")
    def index():
        try:
            if "user" not in session:
                return redirect(url_for("login"))
            # If logged in, send to the dashboard
            return redirect(url_for("dashboard"))
        except Exception as e:
            id_error = error_id_logger(e)
            return render_template("error/error.html", id_error=id_error)

    @app.route("/comments/<entity_id>", methods=["GET", "POST"])
    def comments(entity_id):
        try:
            if "user" not in session:
                return redirect(url_for("login"))
            success = None
            comment_text = None
            if request.method == "POST":
                comment_text = request.form.get("message")
                received_entity_id = request.form.get("entity_id")
                uuid_input = request.form.get("uuid_input")
                print(comment_text, received_entity_id, uuid_input)
                if received_entity_id != entity_id:
                    success = "Несоответствие entity_id между URL и формой."
                if comment_text and comment_text.strip():
                    success = "Успешно!"
                else:
                    success = None
            return render_template(
                "CommentatorTeacher/CommentatorTeacher.html",
                label_text_comment="Комментарий преподавателя:",
                success=success,
                comment_text=comment_text,
                entity_id=entity_id,
            )
        except Exception as e:
            id_error = error_id_logger(e)
            return render_template("error/error.html", id_error=id_error)

    @app.route("/base")
    def base():
        try:
            if "user" not in session:
                return redirect(url_for("login"))
            return render_template("Base/Base.html")
        except Exception as e:
            id_error = error_id_logger(e)
            return render_template("error/error.html", id_error=id_error)

    @app.route("/blockvideo")
    def blockvideo():
        try:
            if "user" not in session:
                return redirect(url_for("login"))
            return render_template("BlockVideo/BlockVideo.html")
        except Exception as e:
            id_error = error_id_logger(e)
            return render_template("error/error.html", id_error=id_error)

    @app.route("/filesblock")
    def filesblock():
        try:
            if "user" not in session:
                return redirect(url_for("login"))
            files = {
                "test.txt": {"desc": "Тестовый файл", "name": "test.txt", "last_modified": "2024-01-01 19:00:00"},
                "example.pdf": {
                    "desc": "Пример PDF файла",
                    "name": "example.pdf",
                    "last_modified": "2024-01-02 15:30:00",
                },
            }
            files_dir = "kurse1"
            project_uploads = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads", files_dir)
            checked_map = session.get("checked_files", {})
            file_entries = []
            for fname, fileinfo in files.items():
                abs_path = os.path.join(project_uploads, fname)
                if os.path.isfile(abs_path):
                    fid = hashlib.sha1(os.path.abspath(abs_path).encode("utf-8")).hexdigest()
                    file_map[fid] = os.path.abspath(abs_path)
                    file_entries.append(
                        {
                            "name": fileinfo["name"],
                            "desc": fileinfo["desc"],
                            "last_modified": fileinfo["last_modified"],
                            "url": url_for("download_file", fid=fid),
                            "system_path": os.path.abspath(abs_path),
                            "fid": fid,
                            "checked": checked_map.get(fid, False),
                        }
                    )
                else:
                    file_entries.append(
                        {
                            "name": fileinfo["name"],
                            "desc": fileinfo["desc"],
                            "url": None,
                            "system_path": os.path.abspath(abs_path),
                            "fid": None,
                            "checked": checked_map.get(fileinfo["name"], False),
                        }
                    )
            return render_template("BlockFiles/BlockFiles.html", files=file_entries)
        except Exception as e:
            id_error = error_id_logger(e)
            return render_template("error/error.html", id_error=id_error)

    @app.route("/filesblock/toggle", methods=["POST"])
    def toggle_check():
        try:
            fid = request.form.get("fid")
            checked = "checked" in request.form
            print(f"[toggle_check] fid={fid!r}, checked={checked}")
            checked_map = session.get("checked_files", {})
            if fid:
                checked_map[fid] = checked
            else:
                name_key = request.form.get("fid")
                if name_key:
                    checked_map[name_key] = checked
            session["checked_files"] = checked_map
            session.modified = True
            return redirect(url_for("filesblock"))
        except Exception as e:
            id_error = error_id_logger(e)
            return render_template("error/error.html", id_error=id_error)

    @app.route("/dashboard")
    def dashboard():
        try:
            if "user" not in session:
                return redirect(url_for("login"))
            return render_template(
                "./dashboard/dashboard.html",
                username=session["user"],
                lesson_name="Название занятия",
                lesson_lecturer_name="Имя преподавателя",
                lesson_time="с 12:00 до 13:30",
            )
        except Exception as e:
            id_error = error_id_logger(e)
            return render_template("error/error.html", id_error=id_error)

    # Маршруты диаграммы Ганта перемещены в файл `routes/gantt.py` и зарегистрированы как шаблон.

    @app.route("/logout", methods=["GET", "POST"])
    def logout():
        try:
            if request.method == "POST":
                session.pop("user", None)
                return redirect(url_for("login"))
            return render_template("logout.html")
        except Exception as e:
            id_error = error_id_logger(e)
            return render_template("error/error.html", id_error=id_error)

    @app.route("/settings", methods=["GET", "POST"])
    def settings():
        try:
            if "user" not in session:
                return redirect(url_for("login"))
            if request.method == "POST":
                # Получаем данные из формы
                theme = request.form.get("theme")
                session["theme"] = theme
                print(theme)
            return render_template("settings/settings.html")
        except Exception as e:
            id_error = error_id_logger(e)
            return render_template("error/error.html", id_error=id_error)

    # Список курсов для передачи в шаблон
    # count_number_task - 1 ячейка = 1 тема в курсе
    courses_data = [
        {"name": "Основы проектирования БД", "count": 6, "stat": 100, "count_number_task": 12},
        {"name": "Основы программирования", "count": 10, "stat": 80, "count_number_task": 15},
        {"name": "Основы Цифрового дизайна", "count": 3, "stat": 60, "count_number_task": 8},
        {"name": "Основы информационно-коммуникационных технологий", "count": 7, "stat": 40, "count_number_task": 10},
        {"name": "Основы проектирования БД", "count": 6, "stat": 20, "count_number_task": 9},
        {"name": "Основы программирования", "count": 5, "stat": 0, "count_number_task": 0},
        {"name": "Основы проектирования БД", "count": 6, "stat": 100, "count_number_task": 0},
        {"name": "Основы программирования", "count": 11, "stat": 0, "count_number_task": 0},
    ]

    default_logo = "static\\courses\\icons\\logo-4d9aa449.png"

    user_profile = {
        "name": "Баранова София Алексеевна",
        "avatar_text": "БС",
        "logo": default_logo,
        # theme: 'dark' or 'light'
        "theme": "dark",
    }

    @app.route("/courses")
    def courses():
        try:
            return render_template("courses/courses.html", courses=courses_data, user_profile=user_profile)
        except Exception as e:
            id_error = error_id_logger(e)
            return render_template("error/error.html", id_error=id_error)

    @app.route("/ui-ui-a", methods=["GET", "POST"])
    def ui_ui_a():
        try:
            return render_template("ui-ui-a/ui-ui-a.html")
        except Exception as e:
            id_error = error_id_logger(e)
            return render_template("error/error.html", id_error=id_error)

    @app.route("/login", methods=["GET", "POST"])
    def login():
        try:
            error = None
            if request.method == "POST":
                username = request.form.get("username")
                password = request.form.get("password")
                if username in users and users[username] == password:
                    session["user"] = username
                    return redirect(url_for("dashboard"))
                else:
                    error = "Неверное имя пользователя или пароль"
            return render_template("login/login.html", error=error)
        except Exception as e:
            id_error = error_id_logger(e)
            return render_template("error/error.html", id_error=id_error)

    @app.route("/download/<fid>")
    def download_file(fid):
        # Serve a file referenced by the in-memory file_map created in /filesblock.
        if "user" not in session:
            return redirect(url_for("login"))
        path = file_map.get(fid)
        if not path:
            return abort(404)
        if not os.path.isfile(path):
            return abort(404)
        dirpath = os.path.dirname(path)
        filename = os.path.basename(path)
        return send_from_directory(dirpath, filename, as_attachment=True)
except Exception as e:
    id_error = error_id_logger(e)

    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    def catch_all(path):
        return render_template("error/error.html", id_error=id_error)


if __name__ == "__main__":
    broker_init_check.send()

    def _strip_bom(path):
        try:
            with open(path, "rb") as f:
                data = f.read()
            if data.startswith(b"\xef\xbb\xbf"):
                data = data[3:]
                with open(path, "wb") as f:
                    f.write(data)
                logger.info(f"Removed BOM from {path}")
        except Exception as e:
            logger.error(f"Error stripping BOM from {path}: {e}")

    try:
        static_folder = app.static_folder
        if not static_folder:
            raise RuntimeError("App static folder is not configured")
        gantt_dir = os.path.join(static_folder, "gantt")
        if os.path.isdir(gantt_dir):
            for root, _, files in os.walk(gantt_dir):
                for fn in files:
                    if fn.endswith((".css", ".js")):
                        _strip_bom(os.path.join(root, fn))

            def _replace_google_fonts(css_path):
                try:
                    with open(css_path, "r", encoding="utf-8") as f:
                        css = f.read()
                    import re

                    available_fonts = []
                    fonts_dir = os.path.join(gantt_dir, "fonts")
                    if os.path.isdir(fonts_dir):
                        available_fonts = os.listdir(fonts_dir)

                    def repl(m):
                        filename = os.path.basename(m.group(1))
                        if filename in available_fonts:
                            chosen = filename
                        else:
                            chosen = available_fonts[0] if available_fonts else filename
                        local = f"/gantt/static/fonts/{chosen}"
                        return f"url('{local}')"

                    css2 = re.sub(r"url\((https://fonts\.gstatic\.com/s/inter/[^)]+)\)", repl, css)
                    if css2 != css:
                        with open(css_path, "w", encoding="utf-8") as f:
                            f.write(css2)
                        logger.info(f"Replaced Google fonts in {css_path} -> local fonts")
                except Exception as e:
                    logger.error(f"Error replacing google fonts in {css_path}: {e}")

            gantt_css = os.path.join(gantt_dir, "dhtmlxgantt.css")
            if os.path.isfile(gantt_css):
                _replace_google_fonts(gantt_css)
    except Exception as e:
        logger.error(f"Error preparing gantt static files: {e}")

    app.run(debug=True, port=5000)
