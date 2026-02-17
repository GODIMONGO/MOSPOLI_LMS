# A03 UX Flow & IA: Dashboard -> Courses -> My Course -> Task Detail

## Scope and sources
- Agent: `A03 UX Flow & IA Designer`.
- Ownership respected: edits only in `docs/agents/A03_ia_userflow.md`.
- Source constraints used:
  - `info.md` section `4` (target IA levels and entities).
  - `info.md` section `16.1` (Flask + Jinja2 architecture and existing file map).
  - `info.md` section `21` (text references for `/courses`, `/my_curse/<id>`, task detail states from Image `#4/#7`).

## 1) IA tree (target, aligned to current architecture)
- `L0: /dashboard`
  - Purpose: entry hub after auth.
  - Template: `templates/dashboard/dashboard.html`.
  - Primary CTA in flow: `Курс` -> `/courses`.
- `L1: /courses` (`Все разделы -> Мои курсы` context)
  - Purpose: list of user courses, search, progress indicators.
  - Template: `templates/courses/courses.html`.
  - Data source: `courses_data` from `main.py`.
  - Child entities:
    - `Course row` (name, count, progress ring).
    - `Search state` (empty/result).
  - Outgoing path in target flow:
    - course row click -> `/my_curse/<course_id>`.
- `L2: /my_curse/<id>` (course overview)
  - Purpose: inside-course navigation + blocks/modules/cards.
  - Blueprint: `my_curse` (`routes/my_curse.py`).
  - Template: `templates/my_curse/my_curse.html`.
  - Content entities (from section 4 + section 21.8):
    - `Course shell` (sidebar variants A/B/C from references #1/#5/#6).
    - `Blocks/modules`.
    - `Task/lab cards` collapsed/expanded.
    - Embedded integrations (same IA level, separate blueprints):
      - `Gantt`: `/gantt/<id>` (`routes/gantt.py`, `templates/gantt/gantt_dhtmlx.html`).
      - `Input files`: `/input_file/<uuid_for_upload>` (`routes/input_file.py`, `templates/input_file/input.html`).
  - Outgoing path in target flow:
    - task card click -> `/my_curse/<id>/task/<task_id>` (task detail endpoint in `my_curse` blueprint).
- `L3: /my_curse/<id>/task/<task_id>` (task detail page, target IA node)
  - Purpose: full task context, status, grading, files, comment, actions.
  - Visual model: section `21`, Image `#4/#7`.
  - Main zones:
    - Left info column: execution status, grade status/value, last update, files, comment.
    - Main column: title, assignment brief/content, attachments, CTA (`Редактировать`, `Удалить`).
  - Required state branches:
    - `default`: has files + has grade.
    - `no-files`: file panel is empty-state (no uploaded answer files).
    - `no-grade`: grading panel shows `Не оценено` state.
    - Combined branch: `no-files + no-grade`.

## 2) Route map (as-is vs target)

### 2.1 As-is routes in repository
- `/dashboard` -> `templates/dashboard/dashboard.html` (defined in `main.py`).
- `/courses` -> `templates/courses/courses.html` (defined in `main.py`).
- `/my_curse/<id>` -> `templates/my_curse/my_curse.html` (defined in `routes/my_curse.py`, blueprint `my_curse`).
- Related side routes (same product area):
  - `/gantt/<id>` -> `templates/gantt/gantt_dhtmlx.html` (blueprint `gantt`).
  - `/input_file/<ID_fields>` -> `templates/input_file/input.html` (blueprint `input_file`).

### 2.2 Target route chain for requested user flow
1. `/dashboard`
2. `/courses`
3. `/my_curse/<course_id>`
4. `/my_curse/<course_id>/task/<task_id>`

Notes:
- Step 4 is the missing link in current codebase and should stay under `my_curse` blueprint boundary (per section `16.1` and prompt A03).
- Naming should preserve existing domain term `my_curse` (no renaming).

## 3) User-flow transitions by screen

### 3.1 `/dashboard` -> `/courses`
- Trigger: user clicks tile `Курс`.
- Current implementation: anchor in `templates/dashboard/dashboard.html` uses `url_for('courses')`.
- Exit conditions:
  - Auth valid -> move forward.
  - Auth invalid -> redirect to `/login` (already in backend guards).

### 3.2 `/courses` -> `/my_curse/<course_id>`
- Trigger: user selects a course row in list.
- IA contract for row:
  - `course_id` must be stable routing key.
  - row remains selectable from default/hover/active states.
- Transition result:
  - open course overview with blocks/modules/cards.

### 3.3 `/my_curse/<course_id>` -> `/my_curse/<course_id>/task/<task_id>`
- Trigger options:
  - click task/lab title in collapsed card.
  - click `Подробнее` action from expanded card.
- Data handoff from course page to detail:
  - `course_id`
  - `task_id`
  - optional context: `module_id`, `from=course`.

### 3.4 Task detail internal branches (required)
- Branch A: `default (files + grade)`
  - Left column shows grade badge + uploaded file list.
- Branch B: `no-files`
  - Left column file section becomes empty-state.
  - Primary next action: `Редактировать ответ` (upload/attach path).
- Branch C: `no-grade`
  - Grade section fixed to `Не оценено` without numeric badge.
  - File/comment blocks still available.
- Branch D: `no-files + no-grade`
  - Both empty grading and empty files visible simultaneously.
  - Keep CTA set unchanged for consistent behavior.

## 4) URL-template mapping for handoff
- `/dashboard` -> `templates/dashboard/dashboard.html` (`main.py`).
- `/courses` -> `templates/courses/courses.html` (`main.py`).
- `/my_curse/<id>` -> `templates/my_curse/my_curse.html` (`routes/my_curse.py`).
- `/my_curse/<id>/task/<task_id>` -> target template for task detail inside `templates/my_curse/*` under `my_curse` blueprint.
- Supporting blueprints in same flow perimeter:
  - `/gantt/<id>` -> `templates/gantt/gantt_dhtmlx.html`.
  - `/input_file/<uuid_for_upload>` -> `templates/input_file/input.html`.

## 5) UX rules that keep IA coherent
- Keep one primary linear path: dashboard -> courses -> course -> task detail.
- Keep task detail as a dedicated page (not modal) to match Image `#4/#7` density.
- Keep state model explicit at detail level: `completion`, `grading`, `files`, `comment`.
- Keep back-navigation deterministic:
  - from detail -> course (`/my_curse/<course_id>`),
  - from course -> courses (`/courses`),
  - from courses -> dashboard (`/dashboard`).

## 6) Minimal contract for task detail state (for downstream agents)
- Required route params:
  - `course_id: string`
  - `task_id: string`
- Required task state fields:
  - `completion_status`
  - `grading_status`
  - `grade_value` (nullable)
  - `updated_at`
  - `answer_files[]` (can be empty)
  - `answer_comment` (nullable/empty)
- Branch logic:
  - `no-files` when `len(answer_files) == 0`
  - `no-grade` when `grade_value is null` or `grading_status == 'Не оценено'`

---
Result: IA and routing scheme are built for `/dashboard -> /courses -> /my_curse/<id> -> task detail` with explicit `no-files`/`no-grade` branches, fully aligned to sections `4`, `16.1`, `21` and current Flask blueprint boundaries.
