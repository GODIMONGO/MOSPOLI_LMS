# A10 Expanded Task Card

## Основание
- `info.md` 5.3: нужны состояния карточки `collapsed / expanded / with-comment / with-files`.
- `info.md` 16.1: реализация в текущем стеке `Flask + Jinja2 + static CSS/JS`.
- `info.md` 21.3 и 21.10: референс раскрытой карточки с белыми блоками комментария и файлов на лиловом фоне.

## Ownership A10
- `templates/my_curse/components/task_card_expanded.html`
- `static/my_curse/scripts/script.js`
- `static/my_curse/my_curse_block.css` (только expanded states)

## Что сделал
- Создан компонент `TaskCardExpanded` в `templates/my_curse/components/task_card_expanded.html`.
- Добавлены ARIA-состояния:
  - кнопка toggle: `aria-controls`, `aria-expanded`;
  - контент-панель: `role="region"`, `aria-hidden`, `aria-labelledby`;
  - карточка: `data-state="collapsed|expanded"` для визуального и логического состояния.
- Добавлена структура expanded-карточки:
  - заголовок с иконкой типа и правым чекбоксом;
  - блок `Комментарий педагога`;
  - блок `Файлы для выполнения` со строками файла и правыми чекбоксами;
  - мета-блок `Автор` и `Период`;
  - кнопка сворачивания/разворачивания.
- Обновлен `static/my_curse/scripts/script.js`:
  - единая синхронизация `collapsed` класса, `data-state`, `aria-expanded`, `aria-hidden`, `title`;
  - поддержка поиска панели по `aria-controls`.
- Обновлен `static/my_curse/my_curse_block.css`:
  - состояния скрытия/раскрытия теперь работают и через `data-state`;
  - добавлены стили expanded task card (лиловая карточка, белые внутренние секции, file rows, meta, mobile-подстройка).

## Почему
- Реализация напрямую закрывает требования `5.3` и референс `21.3`: комментарий + список файлов внутри раскрытой карточки.
- `data-state` + ARIA позволяют синхронизировать визуальное и доступное состояние без изменения стека (`16.1`).

## Что отдал следующему агенту
- Компонент готов к include в курсовой странице:
  - файл: `templates/my_curse/components/task_card_expanded.html`
  - ожидаемый контекст: `task` (или `block`) с полями:
    - `id`, `title`, `type`, `icon`, `cross_icon`, `collapsed`, `completed`, `comment`,
    - `files[]` (`name`, `href`, `icon`, `checked`),
    - `meta` (`author`, `period`).
- Поведение toggle уже централизовано в `static/my_curse/scripts/script.js`.
