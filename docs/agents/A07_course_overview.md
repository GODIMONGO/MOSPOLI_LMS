# A07 Course Overview Screen

## Scope
- Agent: `A07`.
- Ownership respected:
  - `templates/my_curse/my_curse.html` (только main content frame).
  - `static/my_curse/my_curse_block.css` (каркас контента).
  - `docs/agents/A07_course_overview.md`.
- Не изменялись sidebar-селекторы A05 и `routes/my_curse.py`.

## Inputs Used
- `info.md` `5.2`: desktop course page, основной контент с шапкой курса и блоками.
- `info.md` `16.1`: Flask + Jinja + static CSS/JS, текущие пути/нейминг без изменений.
- `info.md` `21`: визуальные референсы (#1/#5/#6/#8), pastel-card композиция, чекбоксы справа, стрелка раскрытия.

## Layout Spec (Main Content Frame)
1. `page-content` -> `course-overview-frame`
- Светлый фон-контейнер для рабочей зоны.
- Внутренний центрирующий контейнер `content-inner`.

2. Header row (`overview-header`)
- Слева CTA `Все разделы` (ссылка на `/courses` через `url_for('courses')`).
- В центре название курса `h1.name_of_curse`.
- Справа счетчик разделов `overview-counter` = `blocks|length`.
- Для длинных заголовков применены:
  - clamp до 2 строк,
  - `ellipsis`,
  - `title` для tooltip-подсказки.

3. Content surface (`overview-surface`)
- Общий card-контейнер для потока блоков.
- Внутри `curse-content` с вертикальным стеком `curse-block`.

4. Block card (`curse-block`)
- Сохраняет совместимость с текущим JS:
  - `.curse-block`,
  - `.cross`,
  - `.block-items`,
  - состояние `.collapsed`.
- Структура карточки:
  - `block-header`:
    - `h2.h2-block` (длинные заголовки: clamp + tooltip),
    - `block-controls` (`items-count` + checkbox).
  - `button.cross` для expand/collapse (aria + icon mask).
  - `block-items` список `list-item` с `item-icon` и `item-link`.

5. Empty state
- Если `blocks` пустой: показывается `empty-state` (не ломает маршрут и шаблон).

## Backend Contract (Compatible with `routes/my_curse.py`)
Используется текущий контракт без обязательных изменений в роуте:

- `name: str`
- `blocks: list[block]`

`block`:
- `id: str`
- `title: str`
- `collapsed: bool`
- `cross_icon: str` (path в `static`)
- `items: list[item]`
- optional: `tone: info|task|video|test` (если не передан -> `info`)

`item`:
- `text: str`
- `href: str`
- `icon: str` (path в `static`)

В шаблоне добавлены безопасные fallback-значения через `dict.get(...)`, поэтому текущий `course_data` из `routes/my_curse.py` рендерится без правок backend.

## Visual Rules Implemented
- Мягкий светлый surface + rounded cards (section 21.1).
- Цветовые тона карточек поддержаны через классы:
  - `tone-info`, `tone-task`, `tone-video`, `tone-test`.
- Правый чекбокс и нижняя стрелка раскрытия сохранены как в refs (#1/#5/#6/#8).

## Touched Files
- `templates/my_curse/my_curse.html`
- `static/my_curse/my_curse_block.css`
- `docs/agents/A07_course_overview.md`

## Untouched Contracts
- `routes/my_curse.py` (без изменений контракта роута).
- `static/my_curse/my_curse.css` (sidebar A05 не менялся).
- `static/my_curse/scripts/script.js` (используется существующее поведение collapse/expand).
