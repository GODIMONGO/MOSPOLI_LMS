# A14 Calendar Block

## Scope
- Роль: `A14 Calendar Block`.
- Источники требований:
  - `info.md` раздел `6`: компонент должен быть reusable.
  - `info.md` раздел `14`: формат передачи и координация волны 3.
  - `info.md` раздел `16.1`: текущий стек `Flask + Jinja2 + static`, без смены архитектуры.
  - `info.md` раздел `21`: визуальный стиль пастельных блоков и контент страницы курса.
- Ownership соблюден:
  - `templates/my_curse/components/calendar_block.html`
  - `static/my_curse/calendar.css`
  - `docs/agents/A14_calendar.md`

## Что сделал
- Создан standalone Jinja macro-компонент: `calendar_block(calendar=None, block_id='course-calendar')`.
- Добавлены два состояния блока:
  - `overview` (обзор месяца + ближайшие события).
  - `entry` (фокус на выбранной дате + ее события).
- Добавлен отдельный CSS-контракт для desktop/mobile:
  - grid-календарь на 7 колонок,
  - правая колонка событий,
  - перестройка в одну колонку на узких экранах.

## Почему
- `info.md` `6`: календарь вынесен в отдельный компонент для повторного использования.
- `info.md` `16.1`: реализация только в `templates/*` и `static/*`, без JS-фреймворков и без изменения путей.
- `info.md` `21.1` и `21.9`: соблюдены светлый контейнер, rounded-формы, пастельные статусы и mobile-поведение.

## Template Slot (для merge-owner интеграции)
- Целевой экран: `templates/my_curse/my_curse.html`.
- Рекомендуемый slot: внутри `overview-surface`, перед списком `blocks`.
- Подключение (пример):
```jinja2
{% import "my_curse/components/calendar_block.html" as calendar_ui %}
{{ calendar_ui.calendar_block(calendar_data, block_id='course-calendar') }}
```
- Этот запуск A14 намеренно **не** вносит wiring в основной шаблон.

## Data Contract для `routes/my_curse.py`

Минимально достаточно передать в шаблон переменную `calendar_data` (или `calendar`) вместе с текущим `course_data`.

```json
{
  "state": "overview",
  "title": "Календарь курса",
  "month_label": "Октябрь 2025",
  "timezone": "UTC+03:00",
  "week_days": ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"],
  "selected_date_iso": "2025-10-27",
  "selected_date_label": "27 октября 2025",
  "summary": {
    "total": 8,
    "done": 3,
    "overdue": 1
  },
  "weeks": [
    {
      "days": [
        {
          "day": 29,
          "date_iso": "2025-09-29",
          "outside_month": true,
          "is_today": false,
          "is_active": false,
          "items_count": 0,
          "label": "29 сентября",
          "href": "#"
        }
      ]
    }
  ],
  "entries": [
    {
      "time": "10:00",
      "title": "Лабораторная работа №2",
      "meta": "Дедлайн сегодня",
      "status": "overdue",
      "href": "/my_curse/123/task/lab-2-report"
    }
  ]
}
```

### Поля и поведение
- `state`: `overview | entry` (невалидное значение -> fallback в `overview`).
- `weeks[].days[]`:
  - `day: int`
  - `date_iso: str`
  - `outside_month: bool`
  - `is_today: bool`
  - `is_active: bool`
  - `items_count: int`
  - `label: str` (title/tooltip)
  - `href: str` (optional)
- `entries[].status`: `planned | in-progress | done | overdue` (для цветовой индикации).

## State Description
- `overview`:
  - акцент на месячную сетку;
  - в правой колонке список ближайших событий.
- `entry`:
  - визуальный акцент на выбранный день в сетке;
  - правый блок интерпретируется как события выбранной даты.

## Что отдал следующему агенту
- Готовый компонент:
  - `templates/my_curse/components/calendar_block.html`
  - `static/my_curse/calendar.css`
- Контракт данных для backend wiring в `routes/my_curse.py` (без правок роута в этом запуске).
- Интеграцию в `templates/my_curse/my_curse.html` должен выполнить merge-owner (`A18`).

## Touched Files
- `templates/my_curse/components/calendar_block.html`
- `static/my_curse/calendar.css`
- `docs/agents/A14_calendar.md`

## Untouched Contracts
- `routes/my_curse.py` (не изменялся, только описан контракт данных).
- `templates/my_curse/my_curse.html` (интеграция не выполнялась).
- `main.py`, `routes/gantt.py`, `routes/input_file.py`.
