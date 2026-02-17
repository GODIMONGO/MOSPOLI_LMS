# A17 Accessibility & QA Audit

Дата аудита: 2026-02-16

## Scope и критерии
Проверены текущие изменения в `templates/*`, `static/*`, `routes/*`.
Критерии: `info.md` разделы 8, 11, 16.1, 21 + базовые требования WCAG 2.1/2.2 (контраст, фокус, клавиатура, target size, корректная ARIA-семантика).

## Critical

1. Недоступные чекбоксы из-за `display: none` на нативном `input`.
- File refs: `static/my_curse/my_curse_block.css:264`, `templates/my_curse/my_curse.html:89`, `templates/my_curse/components/task_card_expanded.html:17`.
- Риск: чекбоксы выпадают из клавиатурной навигации/assistive tech, состояние нельзя надежно менять с клавиатуры.
- Fix: использовать visually-hidden паттерн вместо `display: none` (например `position:absolute; width:1px; height:1px; clip-path: inset(50%);`), оставить `input` фокусируемым, добавить явные text-label/`aria-label` с контекстом.

2. Фокусируемая «декоративная» кнопка скрыта от AT (`aria-hidden="true"`).
- File refs: `templates/my_curse/my_curse.html:109`, `static/my_curse/my_curse_block.css:187`.
- Риск: лишняя tab-stop без действия; для screen reader элемент скрыт, для клавиатуры фокусируется, что ломает UX и ожидания.
- Fix: заменить на неинтерактивный `span`/`i` (если декор), либо оставить `button` только при наличии действия и доступного имени.

## Major

1. Строки курсов сделаны как `li tabindex="0"` без корректной интерактивной семантики и перехода.
- File refs: `templates/courses/courses.html:57`, `templates/courses/courses.html:144`, `templates/courses/courses.html:147`.
- Риск: клавиатурный пользователь получает «кликабельный» ряд без роли/URL; core-flow `/courses -> /my_curse/<id>` не реализован через строки.
- Fix: сделать `li > a` с `href` на курс (или `button` + явный action), убрать `tabindex` с `li`, оставить фокус на интерактивном элементе.

2. Низкий контраст ссылки «Все разделы» (AA fail).
- File refs: `static/courses/courses.css:131`, `templates/courses/courses.html:32`.
- Проверка: `#6d9dec` на `#ffffff` ≈ `2.73:1`.
- Риск: слабая читаемость для low-vision пользователей.
- Fix: усилить цвет до AA (минимум `4.5:1` для обычного текста; либо гарантировать large-text и `>=3:1`).

3. Удалён видимый focus у поля поиска без полноценной замены.
- File refs: `static/courses/courses.css:84`, `templates/courses/courses.html:15`.
- Риск: клавиатурный фокус на input плохо различим.
- Fix: добавить `.search-input:focus-visible` (ring/outline с достаточным контрастом), не убирать фокус без эквивалентной индикации.

4. Размер интерактивной зоны кнопки раскрытия ниже рекомендаций target size.
- File refs: `static/my_curse/my_curse_block.css:216`.
- Риск: 22x22 px ухудшает доступность на touch/моторных ограничениях.
- Fix: увеличить минимум до `24x24`, практично до `40x40` с внутренним padding.

5. В `task_detail` «файлы ответа» не кликабельны.
- File refs: `templates/my_curse/task_detail.html:52`, `templates/my_curse/task_detail.html:53`.
- Риск: функциональная деградация страницы задания (нет перехода к файлу/скачиванию).
- Fix: отдавать `href` в `task.answer_files` и рендерить `<a>` с понятным именем ссылки.

6. CTA-кнопки на странице задания не привязаны к действиям/маршрутам.
- File refs: `templates/my_curse/task_detail.html:107`, `templates/my_curse/task_detail.html:108`.
- Риск: пользователь видит primary actions, но результат отсутствует.
- Fix: связать с route/form (`POST`/`GET`), либо временно `disabled` + пояснение статуса функциональности.

7. Глобальный перехват `Ctrl+K` может конфликтовать с браузерными и assistive shortcuts.
- File refs: `templates/courses/courses.html:169`, `templates/courses/courses.html:173`.
- Риск: конфликт горячих клавиш и непредсказуемое поведение.
- Fix: ограничить обработку контекстом страницы/фокусом, добавить явную подсказку и fallback, не перехватывать в input/textarea/contenteditable.

## Minor

1. Неконтекстный `aria-label` у кнопок раскрытия.
- File refs: `templates/my_curse/my_curse.html:99`.
- Риск: screen reader не сообщает, какой именно раздел раскрывается.
- Fix: формировать label с названием блока (например, `Развернуть раздел "{{ block_title }}"`).

2. Дублирование озвучивания из-за `alt` на иконках рядом с текстом ссылки.
- File refs: `templates/my_curse/my_curse.html:44`, `templates/my_curse/my_curse.html:48`, `templates/my_curse/my_curse.html:52`, `templates/my_curse/my_curse.html:56`, `templates/my_curse/my_curse.html:60`.
- Риск: лишний шум для screen reader.
- Fix: для декоративных иконок `alt=""` + `aria-hidden="true"`.

3. Плейсхолдер-ссылки `href="#"` в navigation-блоках.
- File refs: `templates/my_curse/my_curse.html:37`, `templates/my_curse/my_curse.html:38`, `templates/my_curse/my_curse.html:39`, `templates/my_curse/my_curse.html:40`, `templates/my_curse/my_curse.html:47`, `templates/my_curse/my_curse.html:51`, `templates/my_curse/my_curse.html:55`, `templates/my_curse/my_curse.html:59`.
- Риск: ложная навигация (фокус есть, перехода нет), ухудшение QA по flow.
- Fix: заменить на реальные URL или `button type="button"` для небраузерных действий.

4. `aria-current` используется как маркер выбора строки, а не текущей страницы/позиции.
- File refs: `templates/courses/courses.html:107`.
- Риск: некорректная семантика для assistive tech.
- Fix: убрать `aria-current`, либо перейти на корректный паттерн (`listbox` + `aria-selected`) при реальной single-select модели.

5. Добавлены компонентные файлы без интеграции в основной шаблон.
- File refs: `templates/my_curse/components/content_card.html:1`, `templates/my_curse/components/module_row.html:1`, `templates/my_curse/components/task_card_expanded.html:1`, `static/my_curse/components.css:1`, `static/my_curse/statuses.css:1`.
- Риск: расхождение между реализованным UI и библиотекой компонентов, рост техдолга.
- Fix: либо подключить/использовать в `templates/my_curse/my_curse.html`, либо явно пометить как staged и покрыть задачей интеграции.

## Краткое резюме
Основные риски сосредоточены в клавиатурной доступности и семантике интерактивных элементов: недоступные чекбоксы, фокусируемые псевдо-контролы и некорректная интерактивность строк курсов. После устранения critical/major блоков (чекбоксы, семантика строк, контраст, фокус, wiring CTA/files) макеты будут существенно ближе к DoD из `info.md` (разделы 8 и 11).

## Touched files
- `docs/agents/A17_accessibility_qa.md`

## Untouched contracts
- `routes/*`: read-only (без изменений кода/контрактов API)
- `templates/*`: read-only (без изменений шаблонов)
- `static/*`: read-only (без изменений стилей/скриптов)
