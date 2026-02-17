# A02 Scope Matrix (MoSCoW)

Источник: `info.md` разделы `3`, `10`, `12`, `16.1`, `21`.
Контекст архитектуры: `Flask + Jinja2 + static CSS/JS`, без смены стека; ключевые зоны `courses`, `my_curse`, `gantt`, `input_file`.

## Must
| ID | Scope | Привязка к файлам проекта | Обоснование (разделы) |
|---|---|---|---|
| M1 | Карточки задач/контента в курсе + раскрытие/сворачивание | `routes/my_curse.py`, `templates/my_curse/my_curse.html`, `static/my_curse/my_curse_block.css`, `static/my_curse/scripts/script.js` | `3` (в scope обязательно), `10` (приоритет 1-2), `21.2/21.3/21.8/21.9` |
| M2 | Система статусов выполнения и оценивания (единая для курса и детали задачи) | `static/my_curse/statuses.css` (новый), `templates/my_curse/my_curse.html`, `templates/my_curse/task_detail.html` (новый), `static/my_curse/task_detail.css` (новый) | `3` (обязательно), `10` (приоритет 3), `12` (риск по единому источнику правды), `21.5/21.7` |
| M3 | Детальная страница задания | `routes/my_curse.py` (route contract), `templates/my_curse/task_detail.html` (новый), `static/my_curse/task_detail.css` (новый) | `3` (обязательно), `10` (приоритет 4), `21.5/21.7` |
| M4 | Экран "Мои курсы" (`/courses`) | `templates/courses/courses.html`, `static/courses/courses.css`, `main.py` (только совместимость контракта `courses_data`) | `3` (обязательно), `21.4/21.12` |
| M5 | Экран курса (`/my_curse/<id>`) с левой навигацией и модульной иерархией | `routes/my_curse.py`, `templates/my_curse/my_curse.html`, `static/my_curse/my_curse.css`, `static/my_curse/my_curse_block.css` | `3` (обязательно), `10` (приоритет 5-6), `21.2/21.6/21.7/21.9` |
| M6 | Мобильная адаптация core-сценариев (`/courses`, `/my_curse/<id>`, task detail) | `static/courses/mobile.css` (новый), `static/my_curse/mobile.css` (новый), `static/my_curse/task_detail.css` (responsive), `templates/courses/courses.html`, `templates/my_curse/my_curse.html`, `templates/my_curse/task_detail.html` | `3` (обязательно), `21.10/21.12` |

## Критерии приемки для Must
### M1
1. В `course_data.blocks[*].items[*]` поддержаны типы: `info`, `video`, `task`, `lab`, `test` с единым контрактом данных.
2. Для карточек и модулей работают состояния `collapsed/expanded` с корректными `aria-expanded` и `aria-hidden`.
3. Раскрытая карточка корректно отображает длинный комментарий и список файлов без поломки верстки на desktop и tablet.

### M2
1. Покрыты состояния выполнения: `Не начато`, `В процессе`, `Выполнено`, `Просрочено`.
2. Покрыты состояния оценивания: `Не оценено`, `Удовлетворительно`, `Хорошо`, `Отлично`, `Неудовл.`.
3. Один и тот же набор CSS-классов/токенов статусов используется в `my_curse` и `task_detail` без дублирования смыслов.

### M3
1. Есть рабочий маршрут детали задания в `routes/my_curse.py` с рендером `templates/my_curse/task_detail.html`.
2. На странице присутствуют: левый инфо-столбец (статусы, дата/время, файл, комментарий), правый контент (заголовок, текст задания, CTA `Редактировать`, `Удалить`).
3. Отрисованы состояния: `с файлом/без`, `с комментарием/без`, `оценено/не оценено`, `выполнено/не выполнено`.

### M4
1. `/courses` показывает строку поиска и список курсов с правым индикатором прогресса/метрики.
2. В `static/courses/courses.css` заданы состояния строки `default/hover/active`.
3. Длинные названия курсов не перекрывают счетчики/индикаторы и остаются читаемыми.

### M5
1. `/my_curse/<id>` сохраняет shell-структуру `app-shell/app-sidebar/page-content` и отображает левую навигацию.
2. Иерархия `модуль -> карточки` рендерится из данных `routes/my_curse.py` через Jinja-циклы.
3. Взаимодействие с чекбоксами/стрелками раскрытия сохраняет доступность с клавиатуры.

### M6
1. На mobile (узкие экраны) ключевые экраны не требуют горизонтального скролла в основном контенте.
2. Интерактивные зоны чекбоксов/стрелок соответствуют минимальному размеру `40x40`.
3. Иерархия `модуль -> карточка -> раскрытие` остается читаемой и управляемой в одной колонке.

## Should
| ID | Scope | Привязка к файлам проекта | Обоснование (разделы) |
|---|---|---|---|
| S1 | Варианты sidebar B/C как альтернативы базовому варианту | `templates/my_curse/my_curse.html`, `static/my_curse/my_curse.css` | `10` (приоритет 5), `12` (риск: обязательны ли все 3), `21.6/21.7` |
| S2 | Формализация сортировки и группировки модулей/тем | `routes/my_curse.py`, `templates/my_curse/my_curse.html` | `10` (приоритет 6), `12` (риск по правилам группировки), `21.9` |
| S3 | Единый API для контентных блоков на базе текущих шаблонов | `templates/Base/Base.html`, `templates/BlockFiles/BlockFiles.html`, `templates/BlockVideo/BlockVideo.html`, `templates/my_curse/my_curse.html` | `16.1` (использовать существующие базовые блоки), `21` (повторяемые паттерны карточек) |

## Could
| ID | Scope | Привязка к файлам проекта | Обоснование (разделы) |
|---|---|---|---|
| C1 | Календарный блок на странице курса | `templates/my_curse/my_curse.html`, `templates/my_curse/components/calendar_block.html` (новый), `static/my_curse/calendar.css` (новый), `routes/my_curse.py` | `3` (дополнительно после core), `10` (приоритет 7), `12` (уточнить интерактивность) |
| C2 | Встраивание/полировка блока Ганта | `routes/gantt.py`, `templates/gantt/gantt_dhtmlx.html`, `static/gantt/dhtmlxgantt.css` | `3` (дополнительно), `10` (приоритет 8), `16.1` (не менять стек/библиотеку), `21.9` |
| C3 | Полировка темы (вариативность оформления, включая dark/light при подтверждении) | `static/courses/courses.css`, `static/my_curse/my_curse.css`, `static/my_curse/my_curse_block.css`, `templates/settings/settings.html` | `3` (дополнительно), `12` (риск: нужна ли dark theme), `21.1` |

## Won't (текущий релиз)
| ID | Out-of-scope | Привязка к файлам проекта | Обоснование (разделы) |
|---|---|---|---|
| W1 | Смена технологического стека (React/Vue/SPA-миграция) | `main.py`, `templates/**`, `static/**` (read-only в этой части) | `16.1` (фиксированный стек Flask+Jinja2) |
| W2 | Переименование доменных путей/нейминга (`my_curse`, `courses`, `gantt`, `input_file`) | `routes/my_curse.py`, `routes/gantt.py`, `routes/input_file.py`, пути `templates/*`, `static/*` | `16.1` (нейминг и пути не ломать) |
| W3 | Замена библиотеки DHTMLX и правки vendor-ядра Ганта | `static/gantt/scripts/dhtmlxgantt.js` | `16.1` + ограничения архитектуры |
| W4 | Обязательная реализация всех трех sidebar-вариантов до решения по риску | `templates/my_curse/my_curse.html`, `static/my_curse/my_curse.css` | `12` (нужно продуктовое решение), `10` (не выше core-задач) |
