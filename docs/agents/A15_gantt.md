# A15 Gantt Block

Sources used: `info.md` sections `6`, `9` (stage 6), `16.1`, `21`.

## Scope
- Agent: `A15`.
- Ownership respected:
  - `routes/gantt.py`
  - `templates/gantt/gantt_dhtmlx.html`
  - `static/gantt/dhtmlxgantt.css`
  - `docs/agents/A15_gantt.md`
- No changes to DHTMLX library JavaScript (`static/gantt/scripts/dhtmlxgantt.js`).
- Styling policy: UX polish only, mobile behavior included.

## What was implemented
1. Route-level UI contract (`routes/gantt.py`)
- Added `mobile_timeline_first` query flag (default `true`) for mobile-first timeline behavior.
- Added `legend` payload for semantic color chips in template header.
- Aligned task color palette with project pastel system from section `21`.
- Kept all data APIs (`/api/gantt_tasks*`) and CRUD flow intact.

2. Gantt page UX shell (`templates/gantt/gantt_dhtmlx.html`)
- Rebuilt page wrapper around DHTMLX canvas: header, status badge, mode label, legend, and tool buttons.
- Added `Сегодня` action and mobile-only `Показать/Скрыть список` action.
- Preserved editable/read-only modes and server sync behavior.
- Read-only flow: task click opens modal with formatted task metadata.
- Added responsive viewport config:
  - desktop: grid + timeline,
  - mobile: timeline-first (optional), larger tap targets, compact scales/columns.
- Kept DHTMLX internals untouched; only configuration/templates were adjusted.

3. CSS UX polish + mobile behavior (`static/gantt/dhtmlxgantt.css`)
- Appended a dedicated override block `/* LMS Gantt UX Overrides (A15) */` at file end.
- Introduced `lms-gantt-*` namespace for page shell and modal.
- Added non-destructive visual overrides for Gantt container (radius, colors, typography, row polish).
- Added mobile breakpoints (`920px`, `600px`) with timeline-first support and touch-friendly controls.
- Added grid resizer visuals without changing core DHTMLX logic.

## Compatibility and contracts
- Flask + Jinja + static CSS/JS architecture preserved (`16.1`).
- Existing endpoints and payload shape preserved:
  - `GET /gantt/<id>`
  - `GET /api/gantt_tasks` and `GET /api/gantt_tasks/<id>`
  - `POST/PUT/DELETE /api/gantt_tasks/<id>`
- No rename of existing blueprint/routes.

## Touched files
- `routes/gantt.py`
- `templates/gantt/gantt_dhtmlx.html`
- `static/gantt/dhtmlxgantt.css`
- `docs/agents/A15_gantt.md`

## Untouched contracts
- `static/gantt/scripts/dhtmlxgantt.js` (library file not modified).
- Blueprints/routes outside `gantt` were not changed.
- Shared course/task templates and CSS outside Gantt ownership were not changed by A15.
