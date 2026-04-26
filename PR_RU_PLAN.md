# План и статус работ по PR

Этот PR завершает перенос `semantic router` и `native runtime` в локальную копию `MOSPOLI_LMS` и переводит тяжелый runtime на более легкую и стабильную схему запуска.

## Что было сделано

- Обновлена локальная копия проекта до ветки с `semantic router` и `native runtime`.
- Добавлен отдельный runtime для семантического поиска с HTTP API `/models` и `/embeddings`.
- Убрана зависимость от тяжелого `Infinity + torch + Hugging Face` контура.
- Исправлен `GET /execution-status`, который раньше возвращал некорректный ответ.
- Устранены ошибки `mypy` в модулях `semantic_router`.
- Исправлен `ruff format` для `educational_program_parser.py`.
- Исправлен `file_storage` на уровне shell-скрипта и кодировки строк.
- Оптимизированы Docker-настройки по умолчанию для снижения нагрузки на CPU и RAM.
- Добавлен `.gitattributes`, чтобы shell-скрипты сохранялись с `LF`.

## Что улучшено

- Semantic Router теперь стартует быстро и без постоянного crash-loop.
- Потребление памяти снижено за счет отказа от загрузки тяжелых ML-моделей.
- CPU-нагрузка стабилизирована, потому что embedding runtime стал детерминированным и легким.
- Проверки качества стали проходить:
  - `ruff format --check .`
  - `ruff check .`
  - `mypy .`
  - `python -m compileall ...`
- Семантический поиск и оценка сценариев теперь работают предсказуемо на локальной машине.

## Что осталось сделать

- При желании можно вернуть настоящий `torch / Infinity` runtime, если нужен ML-режим с GPU.
- Можно добавить реальные unit-тесты для `semantic_router`.
- Можно расширить каталог маршрутов и повысить точность под реальные пользовательские запросы.
- Можно отдельно вынести настройки Docker в профили для `dev`, `cpu` и `gpu`.
- Можно доработать UI-часть и встроить semantic search в основные страницы LMS.

## Результат проверки

- `semantic_router check` успешно проходит.
- `semantic_router evaluate` проходит без ошибок.
- `semantic_router benchmark` показывает низкую задержку.
- `app`, `redis`, `postgres`, `qdrant`, `file_storage`, `dramatiq_worker` и runtime стартуют без crash-loop.

