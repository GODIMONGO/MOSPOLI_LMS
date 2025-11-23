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

        # Подготавливаем структуру данных курса (иконки и текст приходят с бэка)
        course_data = {
            'name': 'Основы проектирования БД',
            'pill': {
                'icon': 'my_curse/icons/curse-icon.svg',
                'text': 'Осн.БД 25',
                'close_icon': 'my_curse/icons/cross.svg'
            },
            'blocks': [
                {
                    'id': 'block-items-1',
                    'title': 'Общая информация',
                    'collapsed': True,
                    'cross_icon': 'my_curse/icons/arrow.svg',
                    'items': [
                        {
                            'id': 'item-1',
                            'icon': 'my_curse/icons/todo_list.svg',
                            'text': 'Теоретический материал',
                            'href': '#'
                        },
                        {
                            'id': 'item-2',
                            'icon': 'my_curse/icons/info.svg',
                            'text': 'Информация',
                            'href': '#'
                        },
                    ]
                },
                # можно добавлять другие блоки тут
            ],
        }

        return render_template(
            'my_curse/my_curse.html',
            name=course_data['name'],
            course_pill=course_data['pill'],
            blocks=course_data['blocks'],
        )

    except Exception as e:
        id_error = _error_id_logger(e)
        return render_template('error/error.html', id_error=id_error)
