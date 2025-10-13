from flask import Flask, render_template, request, redirect, session, url_for
import os
from flask_socketio import SocketIO

app = Flask(__name__, static_folder='static', template_folder='templates')
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins='*')

# Простые пользователи
users = {
    'admin': 'admin',
    'student': '123' 
}
load_files = ''

@app.route('/')
def index():
    if 'user' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
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

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html', username=session['user'])

@app.route('/logout', methods=['GET', 'POST'])
def logout():
    if request.method == 'POST':
        session.pop('user', None)
        return redirect(url_for('login'))
    return render_template('logout.html')

@app.route('/input_file', methods=['GET', 'POST'])
def input_file():
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
if __name__ == '__main__':
    app.run(debug=True, port=5000)