# A12 Status Catalog (Execution + Grades)

Sources used: `info.md` sections `7`, `16.1`, `21`.

## Scope
- Execution statuses: `Не начато`, `В процессе`, `Выполнено`, `Просрочено`.
- Grade statuses: `Не оценено`, `Удовлетворительно`, `Хорошо`, `Отлично`, `Неудовл.`.
- Ownership output: `static/my_curse/statuses.css` + this catalog only.

## CSS Base API
- Base class: `status-chip` (alias: `status-badge`).
- Score bubble inside grade badge: `status-chip__score`.
- Status modifier format: `status-chip--<group>-<slug>`.
- Groups:
  - execution: `exec-*`
  - grading: `grade-*`

## Execution Status Matrix
| Label (RU) | CSS modifier | BG | Text | Border | Contrast (text/bg) |
|---|---|---|---|---|---|
| Не начато | `status-chip--exec-not-started` | `#EEF1F5` | `#344054` | `#D0D5DD` | `9.23:1` |
| В процессе | `status-chip--exec-in-progress` | `#EDEBFF` | `#4A2A96` | `#C6BAFF` | `8.69:1` |
| Выполнено | `status-chip--exec-completed` | `#DCFCE7` | `#166534` | `#86EFAC` | `6.49:1` |
| Просрочено | `status-chip--exec-overdue` | `#FEE2E2` | `#991B1B` | `#FCA5A5` | `6.80:1` |

## Grade Status Matrix
| Label (RU) | CSS modifier | BG | Text | Border | Contrast (text/bg) |
|---|---|---|---|---|---|
| Не оценено | `status-chip--grade-not-graded` | `#EEE8FF` | `#5B32A8` | `#CBB6FF` | `7.14:1` |
| Удовлетворительно | `status-chip--grade-satisfactory` | `#FFF6DB` | `#8A4B00` | `#FFD778` | `6.30:1` |
| Хорошо | `status-chip--grade-good` | `#E3F0FF` | `#004C9A` | `#A6CCFF` | `7.27:1` |
| Отлично | `status-chip--grade-excellent` | `#DFF7E7` | `#0B6A3D` | `#7ED9A9` | `5.92:1` |
| Неудовл. | `status-chip--grade-unsatisfactory` | `#FDE7EC` | `#9C1D3D` | `#F4A3B8` | `6.71:1` |

All text/background pairs are above WCAG AA `4.5:1` for normal text.

## Jinja Mapping Examples
```jinja
{# Execution status -> CSS class #}
{% set exec_class_map = {
  'Не начато': 'status-chip--exec-not-started',
  'В процессе': 'status-chip--exec-in-progress',
  'Выполнено': 'status-chip--exec-completed',
  'Просрочено': 'status-chip--exec-overdue'
} %}

<span class="status-chip {{ exec_class_map.get(task.execution_status, 'status-chip--exec-not-started') }}">
  {{ task.execution_status }}
</span>
```

```jinja
{# Grade status -> CSS class #}
{% set grade_class_map = {
  'Не оценено': 'status-chip--grade-not-graded',
  'Удовлетворительно': 'status-chip--grade-satisfactory',
  'Хорошо': 'status-chip--grade-good',
  'Отлично': 'status-chip--grade-excellent',
  'Неудовл.': 'status-chip--grade-unsatisfactory'
} %}

<span class="status-chip {{ grade_class_map.get(task.grade_status, 'status-chip--grade-not-graded') }}">
  {{ task.grade_status }}
  {% if task.grade_points is not none %}
    <span class="status-chip__score">{{ task.grade_points }}</span>
  {% endif %}
</span>
```

## Notes for Integration
- Reference CSS file: `static/my_curse/statuses.css`.
- Intended use is compatible with Flask + Jinja (`info.md` section `16.1`).
- Visual direction follows section `21` pastel semantics with explicit status contrast safety.
