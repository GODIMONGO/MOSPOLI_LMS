from flask import Blueprint, render_template, request, redirect, url_for, jsonify, session, send_from_directory, abort, current_app
from loguru import logger
from uuid import uuid4

my_curse_bp = Blueprint('my_curse', __name__)

def _error_id_logger(error):
    id_error = str(uuid4())
    logger.error(f"ID: {id_error} Ошибка: {error}")
    return id_error

@my_curse_bp.route('/my_curse/<path:id>')
def my_curse(id):
    try:
        current_app.logger.info(f"Открыт мой курс id={id}")
        if 'user' not in session:
            return redirect(url_for('login'))
        
        return render_template(
            'my_curse/my_curse.html',
            name='Основы проектирования БД',
        )
    
    except Exception as e:
        id_error = _error_id_logger(e)
        return render_template('error/error.html', id_error=id_error)
