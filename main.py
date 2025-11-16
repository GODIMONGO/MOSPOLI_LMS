from flask import Flask, render_template, request, redirect, session, url_for, jsonify, send_from_directory, abort
import os
from flask_socketio import SocketIO
from werkzeug.utils import secure_filename
from loguru import logger
from uuid import uuid4
import hashlib
import json
import os

with open("config.json", "r") as file:
    config_data = json.load(file)
app = Flask(__name__, static_folder='static', template_folder='templates')
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins='*')
# In-memory map of file id -> absolute path for downloads
file_map = {}

# Простые пользователи
users = {
    'admin': 'admin',
    'student': '123' 
}
load_files = ''

def error_id_logger(error):
    id_error = str(uuid4())
    logger.error(f"ID: {id_error} Ошибка: {error}")
    return id_error
try:
    @app.route('/favicon.ico')
    def favicon():
        try:
            return redirect('https://e.mospolytech.ru/icon.png')
        except Exception as e:
            logger.error(f"Ошибка при получении favicon: {e}")

    @app.route('/execution-status')
    def index():
        try:
            if 'user' in session:
                return redirect(url_for('login'))
            status_dir = 'static/execution-status/status.json'
            return render_template('execution-status/execution-status.html', status=)
        except Exception as e:
            id_error = error_id_logger(e)
            return render_template('error/error.html', id_error=id_error)

    @app.route('/')
    def index():
        try:
            if 'user' not in session:
                return redirect(url_for('login'))
        except Exception as e:
            id_error = error_id_logger(e)
            return render_template('error/error.html', id_error=id_error)

    @app.route('/comments/<entity_id>', methods=['GET', 'POST'])
    def comments(entity_id):
        try:
            if 'user' not in session:
                return redirect(url_for('login'))
            success = None
            comment_text = None
            if request.method == 'POST':
                comment_text = request.form.get('message')
                received_entity_id = request.form.get('entity_id')
                uuid_input = request.form.get('uuid_input')
                print(comment_text, received_entity_id, uuid_input)
                if received_entity_id != entity_id:
                    success = "Несоответствие entity_id между URL и формой."
                if comment_text and comment_text.strip():
                    success = 'Успешно!'
                else:
                    success = None
            return render_template(
                'CommentatorTeacher/CommentatorTeacher.html',
                label_text_comment="Комментарий преподавателя:",
                success=success,
                comment_text=comment_text,
                entity_id=entity_id
            )
        except Exception as e:
            id_error = error_id_logger(e)
            return render_template('error/error.html', id_error=id_error)

    @app.route('/base')
    def base():
        try:
            if 'user' not in session:
                return redirect(url_for('login'))
            return render_template('Base/Base.html')
        except Exception as e:
            id_error = error_id_logger(e)
            return render_template('error/error.html', id_error=id_error)
    @app.route('/filesblock')
    def filesblock():
        try:
            if 'user' not in session:
                return redirect(url_for('login'))
            files = {
                'test.txt': {'desc': 'Тестовый файл', 'name': 'test.txt', 'last_modified': '2024-01-01 19:00:00'},
                'example.pdf': {'desc': 'Пример PDF файла', 'name': 'example.pdf', 'last_modified': '2024-01-02 15:30:00'}
            }
            files_dir = 'kurse1'
            project_uploads = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads', files_dir)
            # load saved checkbox states from session (fid or name -> bool)
            checked_map = session.get('checked_files', {})
            file_entries = []
            for fname, fileinfo in files.items():
                abs_path = os.path.join(project_uploads, fname)
                if os.path.isfile(abs_path):
                    # derive a stable fid from the absolute path so it stays consistent across requests
                    fid = hashlib.sha1(os.path.abspath(abs_path).encode('utf-8')).hexdigest()
                    file_map[fid] = os.path.abspath(abs_path)
                    file_entries.append({
                        'name': fileinfo['name'],
                        'desc': fileinfo['desc'],
                        'last_modified': fileinfo['last_modified'],
                        'url': url_for('download_file', fid=fid),
                        'system_path': os.path.abspath(abs_path),
                        'fid': fid,
                        'checked': checked_map.get(fid, False)
                    })
                else:
                    file_entries.append({
                        'name': fileinfo['name'],
                        'desc': fileinfo['desc'],
                        'url': None,
                        'system_path': os.path.abspath(abs_path),
                        'fid': None,
                        'checked': checked_map.get(fileinfo['name'], False)
                    })
            return render_template('BlockFiles/BlockFiles.html', files=file_entries)
        except Exception as e:
            id_error = error_id_logger(e)
            return render_template('error/error.html', id_error=id_error)

    @app.route('/filesblock/toggle', methods=['POST'])
    def toggle_check():
        try:
            # fid identifies the file row (may be None for missing file)
            fid = request.form.get('fid')
            # Checkbox presence: if checked, 'checked' will be in form data
            checked = 'checked' in request.form
            print(f"[toggle_check] fid={fid!r}, checked={checked}")
            # persist state in session so the checkbox stays checked after redirect
            checked_map = session.get('checked_files', {})
            key = fid or request.form.get('fid') or ''
            # use fid when available, otherwise fallback to provided identifier
            if fid:
                checked_map[fid] = checked
            else:
                # try to store by name (if fid is None)
                name_key = request.form.get('fid')
                if name_key:
                    checked_map[name_key] = checked
            session['checked_files'] = checked_map
            session.modified = True
            # For now, simply redirect back to the filesblock view
            return redirect(url_for('filesblock'))
        except Exception as e:
            id_error = error_id_logger(e)
            return render_template('error/error.html', id_error=id_error)

    @app.route('/dashboard')
    def dashboard():
        try:
            if 'user' not in session:
                return redirect(url_for('login'))
            return render_template('./dashboard/dashboard.html', 
                                username=session['user'],
                                lesson_name='Название занятия',
                                lesson_lecturer_name='Имя преподавателя',
                                lesson_time='с 12:00 до 13:30'
                                )
        except Exception as e:
            id_error = error_id_logger(e)
            return render_template('error/error.html', id_error=id_error)

    @app.route('/logout', methods=['GET', 'POST'])
    def logout():
        try:
            if request.method == 'POST':
                session.pop('user', None)
                return redirect(url_for('login'))
            return render_template('logout.html')
        except Exception as e:
            id_error = error_id_logger(e)
            return render_template('error/error.html', id_error=id_error)

    @app.route('/input_file', methods=['GET', 'POST'])
    def input_file():
        try:
            if request.method == 'GET':
                success = f'Пока не отправлено ни одного файла.'
                return render_template('input_file/input.html', status=success)
            else:
                try:
                    files = request.files.getlist('file')
                    upload_folder = 'static/uploads'
                    os.makedirs(upload_folder, exist_ok=True)
                    for file in files:
                        if file.filename == '':
                            return "No selected file", 400
                        file.save(os.path.join(upload_folder, file.filename))
                    success = f'Успешно загружено файлов: {len(files)}'
                except Exception as e:
                    success = f'Ошибка при загрузке файлов: {str(e)}'
                return render_template('input_file/input.html', status=success)
        except Exception as e:
            id_error = error_id_logger(e)
            return render_template('error/error.html', id_error=id_error)
        
    @app.route('/settings', methods=['GET', 'POST'])
    def settings():
        try:
            if 'user' not in session:
                return redirect(url_for('login'))
            if request.method == 'POST':
                # Получаем данные из формы
                theme = request.form.get('theme')
                session['theme'] = theme
                print(theme)
            return render_template('settings/settings.html')
        except Exception as e:
            id_error = error_id_logger(e)
            return render_template('error/error.html', id_error=id_error)

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
        {"name": "Основы программирования", "count": 11, "stat": 0, "count_number_task": 0}
    ]

    default_logo = 'static\\courses\\icons\\logo-4d9aa449.png'

    user_profile = {
        'name':  'Баранова София Алексеевна',
        'avatar_text': 'БС',
        'logo': default_logo,
        # theme: 'dark' or 'light'
        'theme': 'dark'
    }


    @app.route('/courses')
    def courses():
        try:
            return render_template('courses/courses.html', courses=courses_data, user_profile=user_profile)
        except Exception as e:
            id_error = error_id_logger(e)
            return render_template('error/error.html', id_error=id_error)
    @app.route('/ui-ui-a', methods=['GET', 'POST'])
    def ui_ui_a():
        try:
            return render_template('ui-ui-a/ui-ui-a.html')
        except Exception as e:
            id_error = error_id_logger(e)
            return render_template('error/error.html', id_error=id_error)    
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        try:
            error = None
            if request.method == 'POST':
                username = request.form.get('username')
                password = request.form.get('password')
                if username in users and users[username] == password:
                    session['user'] = username
                    return redirect(url_for('dashboard'))
                else:
                    error = 'Неверное имя пользователя или пароль'
            return render_template('login/login.html', error=error)
        except Exception as e:
            id_error = error_id_logger(e)
            return render_template('error/error.html', id_error=id_error)

    @app.route('/download/<fid>')
    def download_file(fid):
        # Serve a file referenced by the in-memory file_map created in /filesblock.
        if 'user' not in session:
            return redirect(url_for('login'))
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
    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def catch_all(path):
        return render_template('error/error.html', id_error=id_error)

if __name__ == '__main__':
    app.run(debug=True, port=5000)