import hashlib
import json
import os
import re
import secrets
from datetime import datetime
from uuid import uuid4
from flask_socketio import SocketIO
from loguru import logger

from routes.gantt import gantt_bp
from routes.my_curse import my_curse_bp
from flask import (
    Flask,
    abort,
    jsonify,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)

with open("config.json", "r") as file:
    config_data = json.load(file)
app = Flask(__name__, static_folder="static", template_folder="templates")
_secret_key = os.getenv("SECRET_KEY")
if not _secret_key:
    _secret_key = secrets.token_hex(32)
    logger.warning("SECRET_KEY not set; generated ephemeral key.")
app.config["SECRET_KEY"] = _secret_key
socketio = SocketIO(app, cors_allowed_origins="*")

# Регистрация блюпринта
app.register_blueprint(gantt_bp)
app.register_blueprint(my_curse_bp)

file_map = {}
users = {"admin": "admin", "student": "123"}
# Colors used by Gantt tasks. Keys are safe identifiers used in task.color.
# Values are CSS color strings (hex or any CSS color).
load_files = ""
APP_ROOT = os.path.dirname(os.path.abspath(__file__))
UPLOADS_ROOT = os.path.join(APP_ROOT, "uploads")
DEFAULT_COURSE_ID = "kurse1"
COURSE_ID_RE = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")
ALLOWED_EXTS = {"jpg", "jpeg", "png", "gif", "pdf", "doc", "docx", "txt"}
IMAGE_EXTS = {"jpg", "jpeg", "png", "gif"}
MAX_FILE_SIZE_MB = 500
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
MAX_ATTACHED_FILES = 20
HASH_CHUNK_SIZE = 1024 * 1024


def error_id_logger(error):
    id_error = str(uuid4())
    logger.error(f"ID: {id_error} Ошибка: {error}")
    return id_error


def ensure_upload_dir(upload_dir):
    os.makedirs(upload_dir, exist_ok=True)


def is_allowed_extension(filename):
    ext = os.path.splitext(filename)[1].lstrip(".").lower()
    return ext in ALLOWED_EXTS


def is_safe_filename(filename):
    if not filename:
        return False
    if "/" in filename or "\\" in filename:
        return False
    if ".." in filename:
        return False
    if filename != os.path.basename(filename):
        return False
    return True


def format_size(size_bytes):
    size = float(size_bytes)
    units = ["B", "KB", "MB", "GB", "TB"]
    for unit in units:
        if size < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(size)} {unit}"
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size_bytes} B"


def load_upload_index(upload_dir, upload_index):
    ensure_upload_dir(upload_dir)
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


def save_upload_index(upload_dir, upload_index, index):
    ensure_upload_dir(upload_dir)
    temp_path = f"{upload_index}.tmp"
    payload = {"files": index}
    with open(temp_path, "w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=True, indent=2)
    os.replace(temp_path, upload_index)


def compute_file_hash(path):
    hasher = hashlib.sha256()
    with open(path, "rb") as file:
        for chunk in iter(lambda: file.read(HASH_CHUNK_SIZE), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def build_file_record(upload_dir, filename, existing=None):
    if not isinstance(existing, dict):
        existing = None
    path = os.path.join(upload_dir, filename)
    size_bytes = os.path.getsize(path)
    modified_ts = os.path.getmtime(path)
    ext = os.path.splitext(filename)[1].lstrip(".").lower()
    is_image = ext in IMAGE_EXTS
    file_hash = None
    if existing:
        if (
            existing.get("size_bytes") == size_bytes
            and existing.get("modified_ts") == modified_ts
            and existing.get("hash")
        ):
            file_hash = existing.get("hash")
    if not file_hash:
        file_hash = compute_file_hash(path)
    return {
        "name": filename,
        "size_bytes": size_bytes,
        "modified_ts": modified_ts,
        "hash": file_hash,
        "ext": ext,
        "is_image": is_image,
    }


def build_file_meta(record, course_id):
    filename = record.get("name", "")
    size_bytes = record.get("size_bytes", 0)
    ext = record.get("ext") or os.path.splitext(filename)[1].lstrip(".").lower()
    is_image = record.get("is_image", ext in IMAGE_EXTS)
    modified_ts = record.get("modified_ts", 0)
    modified = datetime.fromtimestamp(modified_ts).strftime("%Y-%m-%d %H:%M") if modified_ts else ""
    file_url = url_for("input_file_file", filename=filename, course=course_id)
    file_hash = record.get("hash")
    hash_short = file_hash[:12] if file_hash else None
    return {
        "name": filename,
        "size_bytes": size_bytes,
        "size_label": format_size(size_bytes),
        "ext": ext or "file",
        "modified": modified,
        "modified_ts": modified_ts,
        "is_image": is_image,
        "preview_url": file_url if is_image else None,
        "download_url": file_url,
        "hash": file_hash,
        "hash_short": hash_short,
    }


def list_uploaded_files(upload_dir, upload_index, course_id):
    ensure_upload_dir(upload_dir)
    index = load_upload_index(upload_dir, upload_index)
    changed = False

    if not index:
        for filename in os.listdir(upload_dir):
            if filename.startswith("."):
                continue
            path = os.path.join(upload_dir, filename)
            if not os.path.isfile(path):
                continue
            if not is_safe_filename(filename):
                continue
            index[filename] = build_file_record(upload_dir, filename)
            changed = True
    else:
        for filename in list(index.keys()):
            if not is_safe_filename(filename):
                index.pop(filename, None)
                changed = True
                continue
            path = os.path.join(upload_dir, filename)
            if not os.path.isfile(path):
                index.pop(filename, None)
                changed = True
                continue
            record = build_file_record(upload_dir, filename, index.get(filename))
            if record != index.get(filename):
                index[filename] = record
                changed = True

    if changed:
        save_upload_index(upload_dir, upload_index, index)

    entries = []
    for filename, record in index.items():
        if not is_safe_filename(filename):
            continue
        record_name = record.get("name")
        if record_name != filename:
            record = {**record, "name": filename}
        entries.append(build_file_meta(record, course_id))

    entries.sort(key=lambda item: item["modified_ts"], reverse=True)
    for item in entries:
        item.pop("modified_ts", None)
    return entries


def get_course_id_from_request():
    course_id = (request.args.get("course") or DEFAULT_COURSE_ID).strip()
    if not course_id:
        course_id = DEFAULT_COURSE_ID
    if not COURSE_ID_RE.fullmatch(course_id):
        return None
    return course_id


def get_current_username():
    username = session.get("user")
    if not username:
        return None
    if not is_safe_filename(username) or len(username) > 128:
        return None
    return username


def require_upload_context():
    username = get_current_username()
    if not username:
        return None, (jsonify({"error": "Требуется авторизация."}), 401)

    course_id = get_course_id_from_request()
    if not course_id:
        return None, (jsonify({"error": "Некорректный курс."}), 400)

    upload_dir = os.path.join(UPLOADS_ROOT, course_id, username)
    upload_index = os.path.join(upload_dir, ".index.json")

    return (
        {
            "username": username,
            "course_id": course_id,
            "upload_dir": upload_dir,
            "upload_index": upload_index,
        },
        None,
    )


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
            status_dir = "static/execution-status/status.json"
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
            key = fid or request.form.get("fid") or ""
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

    # Gantt routes have been moved to `routes/gantt.py` and are registered as a blueprint.

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

    @app.route("/input_file", methods=["GET"])
    def input_file():
        try:
            if "user" not in session:
                return redirect(url_for("login"))

            course_id = get_course_id_from_request()
            if not course_id:
                return "", 400
            return render_template(
                "input_file/input.html",
                course_id=course_id,
                max_file_size_mb=MAX_FILE_SIZE_MB,
                max_attached_files=MAX_ATTACHED_FILES,
                allowed_exts=sorted(ALLOWED_EXTS),
            )
        except Exception as e:
            id_error = error_id_logger(e)
            return render_template("error/error.html", id_error=id_error)

    @app.route("/input_file/list", methods=["GET"])
    def input_file_list():
        try:
            ctx, err = require_upload_context()
            if err:
                return err

            files = list_uploaded_files(ctx["upload_dir"], ctx["upload_index"], ctx["course_id"])
            return jsonify({"files": files})
        except Exception as e:
            id_error = error_id_logger(e)
            return jsonify({"error": f"Ошибка списка файлов: {id_error}"}), 500

    @app.route("/input_file/upload", methods=["POST"])
    def input_file_upload():
        try:
            ctx, err = require_upload_context()
            if err:
                return err

            ensure_upload_dir(ctx["upload_dir"])
            # Ensure the index is synced with the upload dir so limits are accurate.
            list_uploaded_files(ctx["upload_dir"], ctx["upload_index"], ctx["course_id"])
            index = load_upload_index(ctx["upload_dir"], ctx["upload_index"])
            index_changed = False
            files = request.files.getlist("file")
            if not files:
                return jsonify({"added": [], "errors": ["Файлы не выбраны."]}), 400
            added = []
            errors = []
            current_count = len(index)
            for file in files:
                filename = file.filename or ""
                if not filename:
                    errors.append("Пропущен файл без имени.")
                    continue
                if not is_safe_filename(filename):
                    errors.append(f"Недопустимое имя файла: {filename}")
                    continue
                if not is_allowed_extension(filename):
                    errors.append(f"Недопустимое расширение: {filename}")
                    continue
                is_replacement = filename in index
                if not is_replacement and current_count >= MAX_ATTACHED_FILES:
                    errors.append(
                        f"Превышено максимальное количество файлов: {MAX_ATTACHED_FILES}."
                    )
                    continue
                target_path = os.path.join(ctx["upload_dir"], filename)
                file.save(target_path)
                size_bytes = os.path.getsize(target_path)
                if size_bytes > MAX_FILE_SIZE_BYTES:
                    os.remove(target_path)
                    errors.append(f"Файл слишком большой: {filename}")
                    continue
                record = build_file_record(ctx["upload_dir"], filename, index.get(filename))
                index[filename] = record
                index_changed = True
                if not is_replacement:
                    current_count += 1
                added.append(build_file_meta(record, ctx["course_id"]))
            if index_changed:
                save_upload_index(ctx["upload_dir"], ctx["upload_index"], index)
            status_code = 200 if added else 400
            return jsonify({"added": added, "errors": errors}), status_code
        except Exception as e:
            id_error = error_id_logger(e)
            return jsonify({"added": [], "errors": [f"Ошибка загрузки: {id_error}"]}), 500

    @app.route("/input_file/rename", methods=["POST"])
    def input_file_rename():
        try:
            ctx, err = require_upload_context()
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
            if not is_allowed_extension(new_name):
                return jsonify({"ok": False, "error": "Недопустимое расширение."}), 400

            old_path = os.path.join(ctx["upload_dir"], old_name)
            new_path = os.path.join(ctx["upload_dir"], new_name)
            if not os.path.isfile(old_path):
                return jsonify({"ok": False, "error": "Файл не найден."}), 404

            if old_name == new_name:
                index = load_upload_index(ctx["upload_dir"], ctx["upload_index"])
                record = build_file_record(ctx["upload_dir"], old_name, index.get(old_name))
                index[old_name] = record
                save_upload_index(ctx["upload_dir"], ctx["upload_index"], index)
                return jsonify({"ok": True, "file": build_file_meta(record, ctx["course_id"])})

            if os.path.exists(new_path):
                return (
                    jsonify({"ok": False, "error": "Файл с таким именем уже существует."}),
                    409,
                )

            os.replace(old_path, new_path)

            index = load_upload_index(ctx["upload_dir"], ctx["upload_index"])
            existing = index.pop(old_name, None)
            record = build_file_record(ctx["upload_dir"], new_name, existing)
            index[new_name] = record
            save_upload_index(ctx["upload_dir"], ctx["upload_index"], index)

            return jsonify({"ok": True, "file": build_file_meta(record, ctx["course_id"])})
        except Exception as e:
            id_error = error_id_logger(e)
            return jsonify({"ok": False, "error": f"Ошибка переименования: {id_error}"}), 500

    @app.route("/input_file/delete", methods=["POST"])
    def input_file_delete():
        try:
            ctx, err = require_upload_context()
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
            index = load_upload_index(ctx["upload_dir"], ctx["upload_index"])
            if filename in index:
                index.pop(filename, None)
                save_upload_index(ctx["upload_dir"], ctx["upload_index"], index)
            return jsonify({"ok": True})
        except Exception as e:
            id_error = error_id_logger(e)
            return jsonify({"ok": False, "error": f"Ошибка удаления: {id_error}"}), 500

    @app.route("/input_file/file/<path:filename>", methods=["GET"])
    def input_file_file(filename):
        try:
            if "user" not in session:
                return redirect(url_for("login"))

            ctx, err = require_upload_context()
            if err:
                _, status = err
                return "", status

            if not is_safe_filename(filename):
                return "", 400
            if not os.path.isdir(ctx["upload_dir"]):
                return "", 404
            return send_from_directory(ctx["upload_dir"], filename, as_attachment=False)
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
    # Ensure local DHTMLX static assets don't include BOM or wrong encoding
    def _strip_bom(path):
        try:
            with open(path, "rb") as f:
                data = f.read()
            # if file starts with UTF-8 BOM (EF BB BF), remove it
            if data.startswith(b"\xef\xbb\xbf"):
                data = data[3:]
                with open(path, "wb") as f:
                    f.write(data)
                logger.info(f"Removed BOM from {path}")
        except Exception as e:
            logger.error(f"Error stripping BOM from {path}: {e}")

    try:
        gantt_dir = os.path.join(app.static_folder, "gantt")
        if os.path.isdir(gantt_dir):
            for root, _, files in os.walk(gantt_dir):
                for fn in files:
                    if fn.endswith((".css", ".js")):
                        _strip_bom(os.path.join(root, fn))

            # Replace remote Google fonts in dhtmlx CSS with local fonts if available
            def _replace_google_fonts(css_path):
                try:
                    with open(css_path, "r", encoding="utf-8") as f:
                        css = f.read()
                    # Replace any Google fonts Inter URL with local font path under /gantt/static/fonts
                    import re

                    available_fonts = []
                    fonts_dir = os.path.join(gantt_dir, "fonts")
                    if os.path.isdir(fonts_dir):
                        available_fonts = os.listdir(fonts_dir)

                    def repl(m):
                        filename = os.path.basename(m.group(1))
                        # If the remote filename exists locally, keep it; otherwise fall back to first available local font
                        if filename in available_fonts:
                            chosen = filename
                        else:
                            chosen = available_fonts[0] if available_fonts else filename
                        # Construct local path that gantt_static will serve
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
