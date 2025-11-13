from flask import Flask, render_template, request, redirect, session, url_for, jsonify
import os
from flask_socketio import SocketIO
from loguru import logger
from uuid import uuid4
import json

with open("config.json", "r") as file:
    config_data = json.load(file)
app = Flask(__name__, static_folder='static', template_folder='templates')
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins='*')

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

    @app.route('/')
    def index():
        try:
            if 'user' in session:
                return redirect(url_for('dashboard'))
            return redirect(url_for('login'))
        except Exception as e:
            id_error = error_id_logger(e)
            return render_template('error/error.html', id_error=id_error)

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        try:
            error = None
            if request.method == 'POST':
                username = request.form['username']
                password = request.form['password']
                two_fa = request.form['2fa']
                if username in users and users[username] == password:
                    session['user'] = username
                    return redirect(url_for('dashboard'))
                else:
                    error = 'Неверный логин или пароль. Пожалуйста, попробуйте снова.'
            
            return render_template('login/login.html', error=error)
        except Exception as e:
            id_error = error_id_logger(e)
            return render_template('error/error.html', id_error=id_error)
    @app.route('/comments')
    def comments():
        try:
            if 'user' not in session:
                return redirect(url_for('login'))
            return render_template('CommentatorTeacher/CommentatorTeacher.html')
        except Exception as e:
            id_error = error_id_logger(e)
            return render_template('error/error.html', id_error=id_error)
    @app.route('/filesblock')
    def filesblock():
        try:
            if 'user' not in session:
                return redirect(url_for('login'))
            return render_template('BlockFiles/BlockFiles.html')
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
except Exception as e:
    id_error = error_id_logger(e)
    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def catch_all(path):
        return render_template('error/error.html', id_error=id_error)

if __name__ == '__main__':
    app.run(debug=True, port=5000)