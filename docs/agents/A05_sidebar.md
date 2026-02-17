# A05 Sidebar Spec (Desktop)

## Основание
- `info.md` 5.2: требуются Variant A/B/C для sidebar desktop-страницы курса.
- `info.md` 16.1: работаем в текущем `Flask + Jinja2`, без смены архитектуры и имен путей.
- `info.md` 21.2 / 21.6 / 21.7: текстовые референсы для широкого, спискового и иконографического сайдбара.

## Ownership A05
- Изменены только sidebar-зона в `templates/my_curse/my_curse.html`.
- Изменены только sidebar-селекторы в `static/my_curse/my_curse.css`.
- Main content (`page-content`) структурно не изменялся.

## Primary Recommendation
- **Primary variant: `sidebar-variant-b` (списковая колонка).**
- Причина: лучше балансирует ширину, читаемость и соответствие референсу `Image #5` из раздела 21.6; не перегружает экран как Variant A и не теряет контекст как Variant C.

## Variant Classes
Переключение делается классом на `#appSidebar`:
- `sidebar-variant-a` - широкая колонка с профилем и поиском.
- `sidebar-variant-b` - списковая колонка сущностей курса (**по умолчанию/primary**).
- `sidebar-variant-c` - узкая иконографическая колонка.

Пример:
- `<aside class="app-sidebar sidebar-variant-b" id="appSidebar" ...>`

## Общие блоки (переиспользуются)
- `.sidebar-top`, `.sidebar-title`
- `.course-pill` (`.pill-icon`, `.pill-text`, `.pill-close`)
- `.sidebar-nav` + `.nav-item` (`.nav-icon`, `.nav-text`)

## Спецификация вариантов

### Variant A (`sidebar-variant-a`)
- Ширина ~296px.
- Включены: `.sidebar-profile`, `.sidebar-search`.
- Навигация: иконка + текст.
- `sidebar-entity-list` скрыт.

### Variant B (`sidebar-variant-b`) - primary
- Ширина ~252px.
- Профиль и поиск скрыты.
- Включен `.sidebar-entity-list` (строковый список сущностей с маркерами).
- Локальная навигация курса остаётся ниже списка.

### Variant C (`sidebar-variant-c`)
- Ширина ~88px.
- Показаны только иконки меню (`.nav-text` скрыт).
- Скрыты заголовок, курс-плашка и списковые сущности.
- Используется как компактный режим по мотивам `Image #6` (раздел 21.7).
