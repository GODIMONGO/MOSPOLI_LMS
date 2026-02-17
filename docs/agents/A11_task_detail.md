# A11 Task Detail Page

Источник требований: `info.md` разделы `5.4`, `16.1`, `21.5`, `21.8`.
Архитектура: `Flask + Jinja2 + static CSS`, без изменения стека и нейминга.

## 1) Route Contract

- Endpoint: `GET /my_curse/<course_id>/task/<task_id>`
- Файл: `routes/my_curse.py`
- Handler: `task_detail(course_id, task_id)`
- Auth guard: при отсутствии `session['user']` -> redirect на `login`
- Template: `templates/my_curse/task_detail.html`
- Styles: `static/my_curse/task_detail.css`

### Передаваемые в шаблон данные
- `course_id: str`
- `task_id: str`
- `page_title: str`
- `task: dict`
  - `title`
  - `is_compact`
  - `completion_status`
  - `completion_class`
  - `grading_status`
  - `grading_class`
  - `grade_value`
  - `is_graded`
  - `updated_at`
  - `answer_files[]`
  - `has_files`
  - `answer_comment`
  - `has_comment`
  - `assignment_brief`
  - `report_items[]`
  - `materials[]`
- `status_legend[]`

### Управление состояниями через query (для QA/демо)
- `?view=full|compact`
- `?files=none`
- `?comment=none`
- `?grading=none|satisfactory|good|excellent|poor`
- `?grade=<int>`
- `?completion=<text>`

## 2) Template Structure (`templates/my_curse/task_detail.html`)

- `task-topbar`
  - ссылка `Все разделы` -> `/courses`
  - ссылка `Вернуться в курс` -> `/my_curse/<course_id>`
- `status-legend`
  - набор плашек: `Отлично`, `Хорошо`, `Удовлетворительно`, `Неудовл.`, `В процессе`
- `task-card`
  - `task-meta-column` (левый инфо-столбец)
    - статус выполнения
    - состояние оценивания (+ числовой бейдж при наличии)
    - последнее изменение
    - ответ в виде файла (список / empty)
    - комментарий к ответу (текст / empty)
  - `task-main-column` (основной контент)
    - заголовок задания
    - серый блок `Текст задания`
    - `Содержание отчета` (для full-варианта, Image #4)
    - `Прикрепленные материалы` (для full-варианта)
    - CTA: `Редактировать ответ`, `Удалить ответ`

## 3) State Matrix

| Измерение | Состояния | Реализация |
|---|---|---|
| Выполнение | `Не начато`, `В процессе`, `Выполнено`, `Просрочено` | CSS-классы `status-pill--not-started/in-progress/done/overdue` |
| Оценивание | `Не оценено`, `Удовлетворительно`, `Хорошо`, `Отлично`, `Неудовл.` | CSS-классы `status-pill--not-graded/satisfactory/good/excellent/poor`, optional `grade-badge` |
| Файлы | `с файлом`, `без файла` | `has_files` + условный рендер списка/empty |
| Комментарий | `с комментарием`, `без комментария` | `has_comment` + условный рендер `comment-box`/empty |
| Плотность экрана | `full` (Image #4), `compact` (Image #7) | `task.is_compact` + блоки `report_items/materials` |

## 4) Визуальные и адаптивные правила

- Левый информационный столбец и правый контент повторяют композицию `Image #4/#7`.
- Легенда статусов вынесена в верхнюю часть страницы.
- Mobile/tablet: одна колонка, без горизонтального скролла, кнопки с высотой не ниже `40px`.

## 5) Touched Files

- `routes/my_curse.py`
- `templates/my_curse/task_detail.html`
- `static/my_curse/task_detail.css`
- `docs/agents/A11_task_detail.md`

## 6) Untouched Contracts

- Стек не менялся: `Flask + Jinja2 + static CSS/JS`.
- Существующие blueprint-границы `my_curse`, `gantt`, `input_file` не изменены.
- Нейминг домена `my_curse` сохранен.
- Контракты файлов `courses/*`, `gantt/*`, `input_file/*` не затронуты.
