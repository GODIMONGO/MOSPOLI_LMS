# A18 Final Handoff & Dev Specs

Дата среза: 2026-02-16  
Источник правил: `info.md` разделы `17`, `18`, `19`, `20`, `21` + ownership-матрица.

## 1) Scope A18
- Primary output: `docs/agents/A18_handoff.md`.
- Допустимые интеграционные файлы A18:  
  `templates/my_curse/my_curse.html`, `templates/courses/courses.html`, `main.py`, `routes/__init__.py`.
- В текущем срезе дополнительные правки в `main.py` и `routes/__init__.py` **не требуются**.

## 2) Фактический статус дерева (dirty-tree)

### 2.1 Modified (tracked)
- `routes/gantt.py`
- `routes/my_curse.py`
- `static/courses/courses.css`
- `static/my_curse/my_curse.css`
- `static/my_curse/my_curse_block.css`
- `static/my_curse/scripts/script.js`
- `templates/courses/courses.html`
- `templates/my_curse/my_curse.html`

### 2.2 Added (untracked)
- Docs:  
  `docs/agents/A01_orchestrator.md`  
  `docs/agents/A02_scope_matrix.md`  
  `docs/agents/A03_ia_userflow.md`  
  `docs/agents/A04_foundations.md`  
  `docs/agents/A05_sidebar.md`  
  `docs/agents/A06_courses.md`  
  `docs/agents/A07_course_overview.md`  
  `docs/agents/A08_module_theme.md`  
  `docs/agents/A09_cards.md`  
  `docs/agents/A10_expanded_task.md`  
  `docs/agents/A11_task_detail.md`  
  `docs/agents/A12_status_catalog.md`  
  `docs/agents/A13_mobile.md`  
  `docs/agents/A14_calendar.md`  
  `docs/agents/A16_states.md`  
  `docs/agents/A17_accessibility_qa.md`
- Design system:  
  `static/design/tokens.css`  
  `static/design/typography.css`
- Course/mobile:  
  `static/courses/mobile.css`
- My course additions:  
  `static/my_curse/mobile.css`  
  `static/my_curse/calendar.css`  
  `static/my_curse/components.css`  
  `static/my_curse/statuses.css`  
  `static/my_curse/task_detail.css`  
  `templates/my_curse/components/calendar_block.html`  
  `templates/my_curse/components/content_card.html`  
  `templates/my_curse/components/module_row.html`  
  `templates/my_curse/components/task_card_expanded.html`  
  `templates/my_curse/task_detail.html`
- Input-file/mobile:  
  `static/input_file/mobile.css`
- UI states:  
  `templates/components/ui_states.html`  
  `static/components/ui_states.css`

## 3) Готовность артефактов по разделу 18

1. `Roadmap + dependency map` (A01): **готово** (`docs/agents/A01_orchestrator.md`).
2. `Priority matrix` (A02): **готово** (`docs/agents/A02_scope_matrix.md`).
3. `IA + user flow` (A03): **готово** (`docs/agents/A03_ia_userflow.md`).
4. `Foundations` (A04): **готово** (`docs/agents/A04_foundations.md`, `static/design/*`).
5. `Desktop screens` (A05-A11): **готово по артефактам**, интеграция частично staged.
6. `Mobile screens` (A13): **готово по CSS-артефактам**, wiring в шаблонах частично отсутствует.
7. `Calendar/Gantt` (A14-A15):  
   - Calendar A14: **готово (staged)**, без финального встраивания в `my_curse` шаблон.  
   - Gantt A15: **частично** (есть изменение `routes/gantt.py`, но отсутствует `docs/agents/A15_gantt.md` в срезе).
8. `State catalog` (A12, A16): **готово** (`static/my_curse/statuses.css`, `templates/components/ui_states.html`, `static/components/ui_states.css`).
9. `QA report` (A17): **готово** (`docs/agents/A17_accessibility_qa.md`).
10. `Final handoff spec` (A18): **готово этим документом**.

## 4) Backend contracts (фактические)

### 4.1 `/courses` -> `templates/courses/courses.html`
Контракт данных (из `main.py`) используется без смены API:
- `course.name` (обязательное отображение),
- `course.count_number_task` (метрика тем),
- `course.stat` (процент/индикатор),
- `course.id` (опционально; fallback на `loop.index`).

### 4.2 `/my_curse/<id>` -> `templates/my_curse/my_curse.html`
Контракт `routes/my_curse.py`:
- `id`, `schema_version`, `name`, `pill`, `modules`, `blocks`.
- Целевая структура: `modules -> themes -> cards`.
- Backward compatibility: `blocks` генерируется как legacy-проекция.

### 4.3 `/my_curse/<course_id>/task/<task_id>` -> `templates/my_curse/task_detail.html`
Контракт task detail:
- `task` c полями статусов/оценивания/файлов/комментария/контента.
- `status_legend`.
- QA/query overrides:
  `view`, `files`, `comment`, `grading`, `grade`, `completion`.

### 4.4 `/gantt/<id>` (фактическое изменение)
В `routes/gantt.py` добавлены:
- `mobile_timeline_first` query-flag,
- updated color map,
- `legend` payload в шаблон.

## 5) Ownership и merge-owner точки

Критические файлы пересечения (из `19.4`) и фактический статус:
1. `templates/my_curse/my_curse.html`  
   Contributors: A05/A07/A08/A10/A14, merge-owner: **A18**.  
   Статус: файл уже содержит смешанный результат (sidebar + overview + module/theme loops).
2. `routes/my_curse.py`  
   Contributors: A08/A11/A14, merge-owner: **A18**.  
   Статус: объединены module-schema + task-detail endpoint.
3. `static/my_curse/my_curse_block.css`  
   Contributors: A07/A10, merge-owner: **A18**.  
   Статус: объединены overview + expanded card rules.
4. `static/my_curse/scripts/script.js`  
   Contributor: A10, merge-owner: **A18**.  
   Статус: присутствует unified state sync (class + aria + dataset).
5. `templates/courses/courses.html` + `static/courses/courses.css`  
   Contributor: A06 (+ mobile-pass A13), merge-owner: **A18**.  
   Статус: новый layout и client search присутствуют; mobile CSS вынесен отдельным файлом.

## 6) Интеграционные правки A18 в разрешенных файлах

На момент этого handoff:
- Дополнительные правки в `main.py` и `routes/__init__.py` не обязательны.
- Дополнительные правки в `templates/my_curse/my_curse.html` и `templates/courses/courses.html` в рамках этого шага **не выполнялись** (берется фактический уже измененный срез).

Причина:
- Маршруты зарегистрированы (`main.py`: `app.register_blueprint(my_curse_bp)` уже есть).
- Основные цепочки UI уже собраны в текущих изменениях дерева.

## 7) Порядок мержа (рекомендуемый)

1. Зафиксировать foundations и базовые стили:
   - `static/design/*`, `static/courses/courses.css`, `static/my_curse/my_curse.css`.
2. Слить core flow:
   - `templates/courses/courses.html`,
   - `routes/my_curse.py`,
   - `templates/my_curse/my_curse.html`,
   - `static/my_curse/my_curse_block.css`,
   - `static/my_curse/scripts/script.js`.
3. Слить task detail:
   - `templates/my_curse/task_detail.html`,
   - `static/my_curse/task_detail.css`.
4. Слить staged components/mobile/states:
   - `templates/my_curse/components/*`,
   - `static/my_curse/components.css`,
   - `static/my_curse/statuses.css`,
   - `templates/components/ui_states.html`,
   - `static/components/ui_states.css`,
   - `static/*/mobile.css`.
5. Слить gantt-изменения:
   - `routes/gantt.py` (и синхронизацию с шаблоном/стилями при наличии A15-пакета).
6. Финальный QA-pass по A17 и только затем release merge.

## 8) Риски мержа (актуальные)

### High
1. Конфликтные зоны в `templates/my_curse/my_curse.html` и `routes/my_curse.py` при параллельных правках.
2. Неполный пакет A15 (нет `docs/agents/A15_gantt.md` в текущем срезе).
3. A17 critical замечания (доступность checkbox/focus semantics) могут блокировать приемку.

### Medium
1. Staged-компоненты (`A09/A14/A16`) частично не подключены в production templates.
2. Mobile CSS (`A13`) существует отдельными файлами, но не везде подтверждено подключение.
3. Разночтения статусов между `statuses.css` (A12) и конкретными классами task-detail при дальнейших правках.

### Low
1. Разные визуальные контракты в legacy `blocks` и новой `modules` структуре.
2. CRLF/LF предупреждения при merge.

## 9) Release gate перед финальным merge
- Закрыть critical/major из `docs/agents/A17_accessibility_qa.md`.
- Подтвердить финальный wiring staged-компонентов (или явно отложить их в backlog).
- Дособрать/подтвердить A15-пакет (doc + template/css sync для gantt, если входит в релиз).

## 10) Touched files
- `docs/agents/A18_handoff.md`

## 11) Untouched contracts
- `main.py` (без новых изменений в этом шаге A18)
- `routes/__init__.py` (без новых изменений в этом шаге A18)
