# A08 Module & Theme Structure (resume pass)

## Inputs and Constraints
- `info.md` section `5.3`: карточки контента и их состояния.
- `info.md` section `16.1`: стек `Flask + Jinja2 + static CSS/JS`, без смены архитектуры.
- `info.md` section `21` (`Image #8/#9`): иерархия `модуль -> тема -> карточки`.
- Ownership (`info.md` `19/20`): только `routes/my_curse.py` (data schema), `templates/my_curse/my_curse.html` (Jinja loops), `docs/agents/A08_module_theme.md`.

## Implemented Backend Schema (`routes/my_curse.py`)
`course_data` переведен на целевую структуру:

```json
{
  "id": "<course_id>",
  "schema_version": "2.1",
  "name": "Основы проектирования БД",
  "pill": {
    "icon": "my_curse/icons/curse-icon.svg",
    "text": "Осн.БД 25",
    "close_icon": "my_curse/icons/cross.svg"
  },
  "modules": [
    {
      "id": "module-1",
      "title": "Модуль 1. ...",
      "collapsed": false,
      "cross_icon": "my_curse/icons/arrow.svg",
      "themes": [
        {
          "id": "module-1-theme-1",
          "title": "Тема 1. ...",
          "tone": "info|task|video|test",
          "collapsed": false,
          "cross_icon": "my_curse/icons/arrow.svg",
          "cards": [
            {
              "id": "card-1",
              "type": "info|video|assignment|lab|test",
              "title": "...",
              "icon": "my_curse/icons/*.svg",
              "href": "...",
              "collapsed": true,
              "completed": false,
              "with_grade": false,
              "with_comment": false,
              "with_files": false,
              "meta": {
                "author": "...",
                "date": "DD.MM.YYYY",
                "period": "..."
              }
            }
          ]
        }
      ]
    }
  ],
  "blocks": "legacy projection from modules/themes"
}
```

Дополнительно:
- добавлен helper `_project_modules_to_legacy_blocks(modules)` для обратной совместимости со старым контрактом `blocks/items`;
- `blocks` формируется из `modules` на сервере, а не хранится отдельным источником правды.

## Implemented Jinja Loops (`templates/my_curse/my_curse.html`)
Страница курса теперь рендерит целевую иерархию:
1. `for module in modules`
2. `for theme in module['themes']`
3. `for card in theme['cards']`

Для совместимости со скриптом раскрытия сохранен DOM-контракт:
- контейнер: `.curse-block`;
- кнопка: `.cross` + `aria-controls` / `aria-expanded`;
- раскрываемая часть: `.block-items` + `aria-hidden`;
- состояние: класс `.collapsed`.

Если `modules` пустой, остается fallback на legacy `blocks`.

## A10/A11 Safety
- `task_detail` endpoint и вся статусная логика в `routes/my_curse.py` сохранены:
  - `STATUS_LEGEND`
  - `COMPLETION_CLASS_MAP`
  - `GRADING_CLASS_MAP`
  - `_build_task_detail_data`
  - `_apply_task_state_overrides`
  - `_prepare_task_view_model`
- `static/my_curse/scripts/script.js` не изменялся; селекторы и поведение collapse остались совместимыми.

## Touched Files
- `routes/my_curse.py`
- `templates/my_curse/my_curse.html`
- `docs/agents/A08_module_theme.md`

## Untouched Contracts
- `routes/my_curse.py` task-detail contract A11 (`/my_curse/<course_id>/task/<task_id>`) и status matrix.
- `templates/my_curse/task_detail.html`, `static/my_curse/task_detail.css` (A11).
- `templates/my_curse/components/task_card_expanded.html`, `static/my_curse/scripts/script.js`, `static/my_curse/my_curse_block.css` expanded logic (A10).
- `main.py`, `routes/gantt.py`, `routes/input_file.py`.
