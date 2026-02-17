# A01 Orchestrator: Sprint Plan and Dependencies

## 1) Sprint Plan (Wave-based)

### Sprint goal
Собрать согласованный UI-поток LMS (`/courses -> /my_curse/<id> -> task detail`) в архитектуре `Flask + Jinja + static`, без смены стека и без нарушения file-ownership.

### Priority baseline (from section 21.11)
1. Доработка блоков задач в курсе.
2. Оценки и статусы.
3. Страница задачи.
4. Боковая плашка.
5. Календарь.
6. Диаграмма Ганта.
7. Блоки/карточки контента.
8. Темы/модули.

### Wave 1: Base and frame
Agents: `A02, A03, A04, A05, A06` (coordination by `A01`).

Deliverables:
- Scope matrix (`A02`).
- IA/flow (`A03`).
- Design tokens and migration plan (`A04`).
- Sidebar variants (`A05`).
- Courses list states (`A06`).

Gate G1 to open Wave 2:
- Зафиксированы foundations (`A04`) и выбранная sidebar/layout-стратегия (`A05`) без конфликтов с `/courses` (`A06`).

### Wave 2: Course content and states
Agents: `A07, A08, A09, A10, A11, A12, A13`.

Deliverables:
- Course overview frame (`A07`).
- Module/theme schema and Jinja loops (`A08`).
- Unified content cards (`A09`).
- Expanded task card (`A10`).
- Task detail page contract+template (`A11`).
- Status/grade catalog (`A12`).
- Mobile adaptation (`A13`).

Gate G2 to open Wave 3:
- Закрыты state-matrix по заданиям/оценкам (`A12`, `A11`) и mobile baseline (`A13`).

### Wave 3: Quality, calendar/gantt, release handoff
Agents: `A14, A15, A16, A17, A18`.

Deliverables:
- Calendar block (`A14`).
- Gantt improvements on existing DHTMLX stack (`A15`).
- Empty/error/loading catalog (`A16`).
- Accessibility and QA report (`A17`).
- Final integration and dev handoff (`A18`).

Release gate:
- `A18` starts final package only after `A17` report is complete.

## 2) Dependency Map A02-A18

## 2.1 Upstream dependencies by agent
- `A02`: no upstream; feeds `A01`, `A18`.
- `A03`: no upstream; feeds `A07`, `A11`, `A18`.
- `A04`: no upstream; feeds `A07`, `A09`, `A14`, `A15`, `A18`.
- `A05`: no upstream; feeds `A07`, `A18`.
- `A06`: no upstream; feeds `A13`, `A16`, `A18`.
- `A07`: needs `A04`, `A05`; feeds `A08`, `A14`, `A15`, `A13`, `A16`, `A18`.
- `A08`: needs `A07`; feeds `A10`, `A13`, `A16`, `A18`.
- `A09`: needs `A04`; feeds `A10`, `A12`, `A13`, `A16`, `A18`.
- `A10`: needs `A09` (+ structure from `A08`); feeds `A11`, `A13`, `A16`, `A18`.
- `A11`: needs `A12` (+ flow from `A03`); feeds `A13`, `A16`, `A18`.
- `A12`: no strict upstream; feeds `A11`, `A16`, `A17`, `A18`.
- `A13`: needs `A06`, `A07`, `A08`, `A09`, `A10`, `A11`; feeds `A17`, `A18`.
- `A14`: needs `A04`, `A07`; feeds `A16`, `A17`, `A18`.
- `A15`: needs `A04`, `A07`; feeds `A16`, `A17`, `A18`.
- `A16`: needs outputs `A06-A15`; feeds `A17`, `A18`.
- `A17`: needs all final screens/components (`A06-A16`); feeds `A18`.
- `A18`: needs consolidated outputs `A01-A17`; final integrator and merge-owner.

## 2.2 Conflict-prone merge points (owner-gated)
- `templates/my_curse/my_curse.html`: contributors `A05/A07/A08/A10/A14`, merge-owner `A18`.
- `routes/my_curse.py`: contributors `A08/A11/A14`, merge-owner `A18`.
- `static/my_curse/my_curse_block.css`: contributors `A07/A10`, merge-owner `A18`.
- `static/my_curse/scripts/script.js`: contributor `A10`, merge-owner `A18`.
- `templates/courses/courses.html` + `static/courses/courses.css`: contributor `A06`, mobile-pass `A13`, merge-owner `A18`.

## 2.3 Execution fact snapshot (completed)
- `A07`: DONE, artifact exists, run `019c687f-2e7c-7ac0-ba36-444eb3969112`.
- `A08`: DONE, resume complete, run `019c687f-355f-7442-ac8a-79532bfe370a`.
- `A09`: DONE, run `019c687f-3d51-7ae3-b6c5-c5a1c55763bf`.
- `A10`: DONE, artifact exists, run `019c687f-4316-7643-bce2-a680497da23d`.
- `A11`: DONE, artifact exists, run `019c687f-48b4-7183-b492-b6c5d326de55`.
- `A12`: DONE, run `019c687f-4e4e-7a31-90cc-aabd590556b0`.
- Downstream chain `A13 -> A14 -> A15 -> A16 -> A17 -> A18`: DONE.

## 3) Handoff Rules

### 3.1 Mandatory output format for every agent
Каждый агент завершает отчет блоками:
- `Что сделал`.
- `Почему`.
- `Что отдал следующему агенту`.
- `Touched files`.
- `Untouched contracts`.

### 3.2 Ownership and write policy
- Один файл = один Primary owner на запись.
- Остальные агенты не пишут напрямую в чужой файл; только proposal diff через owner.
- Любое пересечение по файлу: handoff от owner + подтверждение `A01`.
- Read-only зоны из section 19.2 не изменяются.

### 3.3 Integration sequence and acceptance
1. Агент сдает артефакт в свой `docs/agents/Axx_*.md` и/или allowed files.
2. `A01` проверяет соответствие scope, architecture и ownership.
3. Если файл конфликтный, `A18` выполняет merge как owner.
4. После Wave 2 запускается quality pass (`A16`, затем `A17`).
5. `A18` выпускает final handoff только после закрытия критичных замечаний `A17`.

### 3.4 Non-negotiable architecture constraints
- Только `Flask + Jinja2 + static CSS/JS`.
- Без React/Vue и без переименования существующих route/file contracts (`my_curse`, `courses`, `gantt`, `input_file`).
- Визуальные решения опираются только на текст section 21.

## 4) Final Status by Waves

## 4.1 Wave status snapshot
| Wave | Scope | Status | Gate |
|---|---|---|---|
| Wave 1 | A02-A06 | DONE | G1 closed |
| Wave 2 | A07-A13 | DONE | G2 closed |
| Wave 3 | A14-A18 | DONE | release gate passed |

## 4.2 Agent final status
| Agent | Status | Note |
|---|---|---|
| A01 | DONE | orchestration finalized |
| A02 | DONE | scope matrix delivered |
| A03 | DONE | IA/flow delivered |
| A04 | DONE | foundations delivered |
| A05 | DONE | sidebar variants delivered |
| A06 | DONE | courses screen delivered |
| A07 | DONE | artifact exists, run `019c687f-2e7c-7ac0-ba36-444eb3969112` |
| A08 | DONE | resume complete, run `019c687f-355f-7442-ac8a-79532bfe370a` |
| A09 | DONE | run `019c687f-3d51-7ae3-b6c5-c5a1c55763bf` |
| A10 | DONE | artifact exists, run `019c687f-4316-7643-bce2-a680497da23d` |
| A11 | DONE | artifact exists, run `019c687f-48b4-7183-b492-b6c5d326de55` |
| A12 | DONE | run `019c687f-4e4e-7a31-90cc-aabd590556b0` |
| A13 | DONE | mobile adaptation delivered |
| A14 | DONE | calendar block delivered |
| A15 | DONE | gantt block delivered |
| A16 | DONE | state catalog delivered |
| A17 | DONE | accessibility/QA delivered |
| A18 | DONE | final handoff and integration completed |

## 5) Final Conflict Summary
- `templates/my_curse/my_curse.html`: resolved by `A18` merge-owner; conflicts between `A05/A07/A08/A10/A14` normalized by zone-based merge.
- `routes/my_curse.py`: resolved by `A18` merge-owner; `course_data` structure and task-detail contract aligned.
- `static/my_curse/my_curse_block.css`: resolved by `A18`; overview and expanded-task selectors consolidated.
- `static/my_curse/scripts/script.js`: resolved by `A18`; expanded-card behavior synchronized with final DOM contracts.
- `A11`/`A12` status semantics: resolved; status mapping treated as single source-of-truth in final templates/styles.
- Open blocking conflicts: none.

## 6) Final Merge Order (applied)
1. Baseline sync: `A02`, `A03`, `A04`, `A05`, `A06`.
2. Course frame and data model: `A07` -> `A08` -> `A09`.
3. Task experience: `A10` -> `A12` -> `A11`.
4. Mobile and feature blocks: `A13` -> `A14` -> `A15`.
5. System hardening: `A16` -> `A17`.
6. Final integration and release handoff: `A18` (merge-owner on conflict files).
