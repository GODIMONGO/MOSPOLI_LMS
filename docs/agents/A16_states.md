# A16 Empty/Error/Loading States

Sources used: `info.md` sections `7`, `16.1`, `21`.

## Scope
- Reusable system states for current LMS screens.
- Minimum DoD states (from `info.md` A16): `empty`, `loading`, `error`, `no-results`, `no-files`.
- Stack preserved: `Flask + Jinja2 + static CSS/JS` (`16.1`).

## Ownership A16
- `templates/components/ui_states.html`
- `static/components/ui_states.css`
- `docs/agents/A16_states.md`

## Delivered Component Contract

### 1) Template API (`templates/components/ui_states.html`)
- Import:
```jinja
{% import "components/ui_states.html" as ui_states %}
```
- Base macro:
```jinja
{{ ui_states.render_ui_state(
    state='empty',
    title=None,
    description=None,
    action_label=None,
    action_href=None,
    action_id=None,
    action_class='',
    action_name=None,
    action_value=None,
    size='default',
    extra_class=''
) }}
```
- Shortcut macros:
  - `ui_states.empty(...)`
  - `ui_states.loading(...)`
  - `ui_states.error(...)`
  - `ui_states.no_results(...)`
  - `ui_states.no_files(...)`

### 2) CSS Contract (`static/components/ui_states.css`)
- Root block: `.ui-state`
- State modifiers:
  - `.ui-state--empty`
  - `.ui-state--loading`
  - `.ui-state--error`
  - `.ui-state--no-results`
  - `.ui-state--no-files`
- Size modifiers:
  - `.ui-state--compact`
  - `.ui-state--page`

## State Matrix
| State | Typical usage | Accessibility |
|---|---|---|
| `empty` | empty section/list in course page | `role="status"`, `aria-live="polite"` |
| `loading` | async load in list/file/gantt blocks | `aria-busy="true"`, spinner + skeleton |
| `error` | request/load/save failure | `role="alert"`, `aria-live="assertive"` |
| `no-results` | search/filter returned 0 matches | `role="status"`, optional reset action |
| `no-files` | files list is empty | `role="status"`, optional upload action |

## Visual Decisions (from section 21)
- Light pastel surfaces + rounded cards (`12-20px` radius).
- Montserrat-based typography.
- Semantic tinting by state:
  - neutral (`empty`),
  - soft violet (`loading`),
  - soft red (`error`),
  - soft blue (`no-results`),
  - soft green (`no-files`).
- 8px spacing rhythm preserved.

## Integration Examples for Current Screens

### `/courses` (`templates/courses/courses.html`)
- Replace local "Ничего не найдено" block with:
```jinja
{{ ui_states.no_results(
    title='Ничего не найдено',
    description='Попробуйте изменить формулировку или очистить поиск.',
    action_label='Сбросить поиск',
    action_id='courses-reset',
    size='compact'
) }}
```

### `/my_curse/<id>` (`templates/my_curse/my_curse.html`)
- For empty course blocks:
```jinja
{{ ui_states.empty(
    title='В этом курсе пока нет разделов',
    description='Материалы появятся после публикации преподавателем.',
    size='page'
) }}
```
- For empty files inside expanded cards:
```jinja
{{ ui_states.no_files(size='compact') }}
```

### Task detail (`templates/my_curse/task_detail.html`)
- For missing answer files:
```jinja
{{ ui_states.no_files(
    title='Файл ответа не прикреплен',
    description='Добавьте файл, чтобы отправить решение.',
    size='compact'
) }}
```

### Gantt (`templates/gantt/gantt_dhtmlx.html`)
- During fetch:
```jinja
{{ ui_states.loading(
    title='Загружаем диаграмму Ганта',
    description='Синхронизируем задачи и связи...',
    size='page'
) }}
```
- On API failure:
```jinja
{{ ui_states.error(
    title='Ошибка загрузки диаграммы',
    description='Не удалось получить данные задач.',
    action_label='Повторить',
    action_id='gantt-retry'
) }}
```

### Input file (`templates/input_file/input.html`)
- For empty file list:
```jinja
{{ ui_states.no_files(
    title='Пока файлов нет',
    description='Добавьте файлы кнопкой выше или перетащите их в область загрузки.',
    action_label='Добавить файлы',
    action_id='browse-btn'
) }}
```

## Wiring Notes
- Add stylesheet where states are used:
```jinja
<link rel="stylesheet" href="{{ url_for('static', filename='components/ui_states.css') }}">
```
- Import macros per-template:
```jinja
{% import "components/ui_states.html" as ui_states %}
```

## Touched Files
- `templates/components/ui_states.html`
- `static/components/ui_states.css`
- `docs/agents/A16_states.md`

## Untouched Contracts
- Existing routes/blueprints (`routes/*`) unchanged.
- Existing screen templates/styles unchanged outside A16 ownership.
- Current naming and structure from `16.1` preserved.
