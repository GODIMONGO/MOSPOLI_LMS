# A06 Courses List Screen

## Основание
- Раздел `5.1`: экран списка курсов с крупным поиском, строками и правыми индикаторами.
- Раздел `16.1`: стек `Flask + Jinja2 + static CSS/JS`, без смены архитектуры и без правок роута `/courses`.
- Раздел `21` (референс `21.4 Image #3`): фиолетовая верхняя зона, центральный поиск, список курсов в card-контейнере.

## Что изменено
1. Пересобрана структура `templates/courses/courses.html` под паттерн `Image #3`:
- фиолетовый hero-блок;
- центрированный поиск с иконкой и `CTRL K`;
- card-контейнер `Все разделы / Мои курсы`;
- список строк курсов с правой метрикой (`тем`) и индикатором прогресса.

2. Реализовано поведение поиска без изменений backend:
- фильтрация строк в браузере по вводу;
- чтение параметра `?search=...` при загрузке;
- пустое состояние для запроса без совпадений + кнопка сброса;
- горячая клавиша `Ctrl+K` (или `Cmd+K` на macOS) для фокуса в поле.

3. Реализованы состояния строк:
- `default`;
- `hover`;
- `focus-visible` для клавиатуры;
- `active` (клик/Enter/Space) с акцентом.

4. Добавлена поддержка длинных названий:
- перенос и ограничение до 2 строк (`line-clamp`);
- мягкое усечение;
- полный текст в `title`.

## CSS state-map
- `.course-row` -> default.
- `.course-row:hover` -> hover.
- `.course-row:focus-visible` -> keyboard focus.
- `.course-row.is-active` -> active.
- `.courses-empty[hidden=false]` -> пустой поиск.

## Совместимость с текущим `/courses` в `main.py`
- Контракт данных сохранен: используются поля `course.name`, `course.count_number_task`, `course.stat`.
- Роуты/blueprints/endpoint names не менялись.
- Внешние шаблоны и другие экраны (`my_curse`, `gantt`, `input_file`) не затронуты.

## Затронутые файлы
- `templates/courses/courses.html`
- `static/courses/courses.css`
- `docs/agents/A06_courses.md`

## Контракты, которые не тронуты
- `main.py` (`/courses` route)
- `routes/*`
- `templates/my_curse/*`
- `templates/input_file/*`
- `templates/gantt/*`
- `static/my_curse/*`, `static/input_file/*`, `static/gantt/*`
