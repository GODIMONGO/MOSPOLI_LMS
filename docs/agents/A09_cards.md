# A09 Content Card Types

## Scope
- Role: `A09 Content Card Types`.
- Sources used:
  - `info.md` section `5.3` (types/states/elements of course cards).
  - `info.md` section `6` (componentized reusable system).
  - `info.md` section `16.1` (Flask + Jinja constraints, no stack changes).
  - `info.md` section `21` (visual semantics and reference behavior).

## Artifacts
- `templates/my_curse/components/content_card.html`
- `templates/my_curse/components/module_row.html`
- `static/my_curse/components.css`
- `docs/agents/A09_cards.md`

## Unified Jinja Component API

### `module_row(module, module_index=0)`
- Purpose: render one module with nested content cards (`module -> cards`).
- Expected `module` schema:
```json
{
  "id": "module-1",
  "title": "Модуль 1. Основы проектной деятельности",
  "subtitle": "Базовые материалы и задания",
  "period": "01.09.2025 - 30.09.2025",
  "progress": "2/5 выполнено",
  "collapsed": false,
  "cards": []
}
```

### `content_card(card, module_id='module', card_index=0)`
- Purpose: render card types `info/video/task/lab/test` in one markup contract.
- Required behavior coverage from section `5.3`:
  - Types: `Инфо`, `Видео`, `Задание`, `Лабораторная`, `Тест`.
  - States: `collapsed`, `expanded`, `completed`, `with-grade`, `with-comment`, `with-files`.
  - Elements: type icon, right checkbox, expand/collapse arrow, metadata, nested file list.
- Expected `card` schema:
```json
{
  "id": "card-lab-2",
  "type": "lab",
  "title": "Лабораторная работа №2",
  "href": "/my_curse/123/task/lab-2",
  "icon": "my_curse/icons/todo_list.svg",
  "arrow_icon": "my_curse/icons/arrow.svg",
  "collapsed": false,
  "completed": true,
  "grade": "8/10",
  "author": "Преподаватель",
  "date": "27.10.2025",
  "period": "Неделя 2",
  "description": "Краткое описание задания",
  "comment": "Комментарий педагога...",
  "files": [
    {
      "title": "Шаблон отчета.docx",
      "href": "#",
      "icon": "my_curse/icons/info.svg",
      "checked": false
    }
  ]
}
```

## Styling Contract (`static/my_curse/components.css`)
- `content-card--info` -> green semantic surface (`Общая информация`).
- `content-card--video` -> pink semantic surface.
- `content-card--task` / `content-card--lab` -> lilac semantic surface.
- `content-card--test` -> cyan semantic surface.
- Mobile support included:
  - compact spacing/typography under `768px`.
  - checkbox/toggle tap zones are at least `40x40`.

## Partial Template Set
- `content_card.html`: base reusable card component + nested `file_row` macro.
- `module_row.html`: module wrapper that imports and renders `content_card` for each card.

## Integration Notes
- Current ownership intentionally avoids touching `templates/my_curse/my_curse.html` wiring.
- To use components in page template:
  1. import macro: `{% import "my_curse/components/module_row.html" as module_ui %}`
  2. iterate module list: `{{ module_ui.module_row(module, loop.index0) }}`
  3. include CSS: `static/my_curse/components.css` in page `<head>`.
- Works inside Flask + Jinja2 architecture, no JS framework required.

## Impact Statement
- Files touched:
  - `templates/my_curse/components/content_card.html`
  - `templates/my_curse/components/module_row.html`
  - `static/my_curse/components.css`
  - `docs/agents/A09_cards.md`
- Contracts not touched:
  - `routes/*`
  - `main.py`
  - `templates/my_curse/my_curse.html`
  - existing CSS/JS files (`static/my_curse/my_curse.css`, `static/my_curse/my_curse_block.css`, `static/my_curse/scripts/script.js`)
