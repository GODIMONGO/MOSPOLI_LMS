# План архитектуры Semantic Router для MOSPOLI_LMS

Документ описывает переносимую архитектуру Semantic Router внутри текущего Flask LMS. Цель: добавить поиск нужного маршрута LMS по естественному запросу студента, не ломая существующие страницы, blueprints и файловые сценарии. Runtime должен подниматься локально на Windows через `uv` и `.venv`, а внешние сервисы должны быть заменяемыми и настраиваемыми через конфиг.

## 1. Цель

Semantic Router принимает текстовый запрос из интерфейса LMS, например `Как мне заселиться?`, ищет наиболее подходящий маршрут в базе маршрутов, возвращает путь для redirect или список уточняющих вариантов.

Основные сценарии:

- студент вводит вопрос в интерфейсе LMS;
- backend строит embedding запроса через локальный Infinity API;
- Qdrant возвращает top-N кандидатов по векторам;
- reranker уточняет порядок кандидатов;
- LMS либо выполняет redirect на лучший route path, либо показывает кнопки уточнения;
- администратор или разработчик может переиндексировать базу маршрутов отдельной командой.

## 2. Архитектурный принцип

Semantic Router добавляется как отдельный домен:

```text
routes/semantic_router.py       # Flask API и UI-интеграция
semantic_router/
  __init__.py
  config.py                     # настройки router/infinity/qdrant
  models.py                     # RouteRecord, SearchResult
  catalog.py                    # загрузка маршрутов из JSON/YAML/Python
  http.py                       # общий JSON HTTP-клиент на stdlib
  embeddings.py                 # REST-клиент Infinity embeddings API
  vector_store.py               # REST-клиент Qdrant
  reranker.py                   # REST rerank через Infinity или fallback
  service.py                    # orchestration: embed -> qdrant -> rerank -> decision
  indexer.py                    # индексация route catalog
  cli.py                        # команды индексации и smoke-check
data/
  semantic_routes.json          # переносимая база маршрутов
```

`main.py` должен только зарегистрировать blueprint:

```python
from routes.semantic_router import semantic_router_bp

app.register_blueprint(semantic_router_bp)
```

Доменная логика не размещается в `main.py`, чтобы сохранить текущий стиль проекта: новые зоны ответственности выносятся в `routes/*` и отдельные пакеты.

## 3. Runtime через uv и venv

Базовый переносимый запуск на Windows:

```powershell
uv venv .venv --python 3.10
.\.venv\Scripts\Activate.ps1
uv pip install -r requirements.txt
```

Текущая реализация Semantic Router не требует дополнительных Python-зависимостей: клиенты Infinity и Qdrant работают через стандартный HTTP-клиент Python. Внешними обязательными компонентами остаются только сами сервисы Infinity и Qdrant. Если позже понадобится официальный SDK, можно добавить `qdrant-client` и заменить REST-адаптер `semantic_router/vector_store.py`.

Рекомендуемые локальные переменные окружения:

```powershell
$env:SEMANTIC_ROUTER_ENABLED="1"
$env:SEMANTIC_ROUTER_ROUTES_FILE="data/semantic_routes.json"
$env:SEMANTIC_ROUTER_SCORE_THRESHOLD="0.60"
$env:INFINITY_BASE_URL="http://localhost:7997"
$env:INFINITY_EMBEDDING_MODEL="jina-embeddings-v5-text-small"
$env:INFINITY_RERANKER_MODEL="jina-reranker-v3"
$env:QDRANT_URL="http://localhost:6333"
$env:QDRANT_COLLECTION="routes"
```

Команды разработки:

```powershell
.\scripts\start_native.ps1
uv run python -m semantic_router.cli check
uv run python -m semantic_router.cli index
.\scripts\stop_native.ps1
```

Docker-вариант:

```bash
docker compose up --build
```

## 4. Внешние сервисы

Минимальный локальный стек:

```text
Windows 10 Native
Python 3.10+
uv
.venv
Qdrant localhost:6333
Infinity localhost:7997
```

Qdrant и Infinity считаются внешними портативными сервисами. LMS не должна хранить их клиентов в глобальном изменяемом состоянии без конфигурации. Все URL, имена моделей, collection name, threshold и top-K задаются через config/env.

## 5. Индексация маршрутов

Индексация выполняется один раз при создании или обновлении базы маршрутов.

Поток из схемы `Этап A: Индексация`:

```text
semantic_routes.json
  -> Python indexer
  -> Infinity /embeddings
  -> jina-embeddings-v5-text-small
  -> dense vectors
  -> Qdrant upsert
  -> collection routes
```

Формат записи маршрута:

```json
{
  "id": "settlement_info",
  "path": "/my_curse/settlement",
  "title": "Заселение",
  "example_queries": [
    "Как мне заселиться?",
    "Где посмотреть информацию о заселении?",
    "Что нужно для общежития?"
  ],
  "metadata": {
    "section": "student_life",
    "role": "student"
  }
}
```

Текст для embedding строится детерминированно:

```text
title: Заселение
path: /my_curse/settlement
examples:
- Как мне заселиться?
- Где посмотреть информацию о заселении?
- Что нужно для общежития?
section: student_life
role: student
```

В Qdrant сохраняются:

- `id`;
- dense vector;
- `path`;
- `title`;
- `example_text`;
- `metadata`;
- `updated_at`;
- `content_hash`.

`content_hash` нужен, чтобы индексатор мог пропускать неизмененные маршруты.

## 6. Обработка запроса

Поток из схемы `Этап B: Обработка запроса`:

```text
Интерфейс LMS
  -> POST /api/semantic-router/search
  -> SemanticRouterService
  -> Infinity embedding
  -> Qdrant top-20
  -> reranker
  -> decision by max relevance_score
  -> JSON success или JSON clarify
```

API endpoint:

```http
POST /api/semantic-router/search
Content-Type: application/json

{
  "query": "Как мне заселиться?"
}
```

Ответ при уверенном совпадении:

```json
{
  "status": "success",
  "path": "/my_curse/settlement",
  "title": "Заселение",
  "score": 0.82
}
```

Ответ при недостаточной уверенности:

```json
{
  "status": "clarify",
  "message": "Уточните, какой раздел нужен",
  "options": [
    {
      "path": "/my_curse/settlement",
      "title": "Заселение",
      "score": 0.58
    }
  ]
}
```

Базовое правило решения:

```text
if best_score >= SEMANTIC_ROUTER_SCORE_THRESHOLD:
    return success
else:
    return clarify with top guesses
```

Начальный threshold для Qdrant-only режима: `0.60`. Для реального `jina-reranker-v3` score-scale ниже, поэтому в текущем portable-контуре используется `0.30`. Порог нужно подбирать на реальных запросах студентов.

## 7. Интеграция в LMS UI

Минимальная интеграция:

- добавить search-box или command input в dashboard/header;
- JS вызывает `POST /api/semantic-router/search`;
- при `success` выполняется `window.location.href = path`;
- при `clarify` показываются кнопки вариантов;
- все API-роуты требуют `session["user"]`, как остальные UI-сценарии LMS.

Отдельный blueprint:

```text
routes/semantic_router.py

GET  /semantic-router              # dev/debug страница, только для авторизованных
POST /api/semantic-router/search   # основной endpoint
POST /api/semantic-router/reindex  # опционально, admin-only
```

Для первого этапа `reindex` лучше оставить только CLI-командой, а не публичным HTTP endpoint.

## 8. Конфигурация

Нужно поддержать два источника:

- env vars для переносимого запуска через `uv`;
- `config.json` для совместимости с текущим стилем проекта.

Пример расширения `config.json`:

```json
{
  "semantic_router": {
    "enabled": true,
    "routes_file": "data/semantic_routes.json",
    "score_threshold": 0.6,
    "top_k": 20,
    "qdrant_url": "http://localhost:6333",
    "qdrant_collection": "routes",
    "infinity_base_url": "http://localhost:7997",
    "embedding_model": "jina-embeddings-v5-text-small",
    "reranker_model": "jina-reranker-v3"
  }
}
```

Env vars имеют приоритет над `config.json`.

## 9. Отказоустойчивость

Если Infinity или Qdrant недоступны:

- API возвращает `503` с коротким JSON-сообщением;
- ошибка логируется через `loguru` с UUID, как в существующих роутерах;
- UI показывает нейтральное сообщение и не ломает текущую навигацию.

Если reranker недоступен:

- можно временно использовать score из Qdrant;
- в ответ добавляется диагностическое поле только в dev/debug режиме.

Если индекс пустой:

- endpoint возвращает `clarify` без redirect;
- CLI `check` должен явно сообщать, что collection пустая.

## 10. Безопасность

Обязательные ограничения:

- принимать только JSON-запросы с полем `query`;
- ограничить длину запроса, например до `512` символов;
- не выполнять redirect на внешние URL;
- разрешать только относительные `path`, начинающиеся с `/`;
- фильтровать результаты по роли пользователя, если в metadata есть `role`;
- не отдавать внутренние ошибки клиенту.

## 11. Этапы реализации

### Этап 1. Каркас и переносимый запуск

- добавить зависимости для Qdrant/HTTP/config/CLI;
- создать пакет `semantic_router`;
- создать `data/semantic_routes.json` с первыми маршрутами LMS;
- добавить `uv`-команды в README или отдельный раздел документации;
- реализовать `semantic_router.config`.

### Этап 2. Индексация

- реализовать `catalog.py`;
- реализовать `embeddings.py`;
- реализовать `vector_store.py`;
- реализовать `indexer.py`;
- добавить CLI:
  - `uv run python -m semantic_router.cli check`;
  - `uv run python -m semantic_router.cli index`.

### Этап 3. Поиск

- реализовать `service.py`;
- реализовать Qdrant top-K поиск;
- добавить reranker;
- добавить threshold decision;
- покрыть unit-тестами decision logic без внешних сервисов.

### Этап 4. Flask API

- добавить `routes/semantic_router.py`;
- зарегистрировать blueprint в `main.py`;
- endpoint `POST /api/semantic-router/search`;
- авторизация через `session["user"]`;
- единый формат ошибок.

### Этап 5. LMS UI

- добавить компактный интерфейс запроса в dashboard/header;
- обработать `success` redirect;
- обработать `clarify` через список кнопок;
- не блокировать обычную навигацию при ошибке сервиса.

### Этап 6. Проверка качества

- smoke-test CLI;
- smoke-test Flask endpoint;
- `ruff format --check .`;
- `ruff check .`;
- `mypy .`;
- `python -m compileall -q main.py config.py app_state.py broker.py tasks.py routes libs semantic_router`.

## 12. Definition of Done

Функция считается готовой, когда:

- проект поднимается через `uv venv .venv --python 3.10`;
- `uv run python -m semantic_router.cli check` видит Infinity и Qdrant;
- `uv run python -m semantic_router.cli index` создает или обновляет collection `routes`;
- `POST /api/semantic-router/search` возвращает `success` для известных запросов;
- слабые запросы возвращают `clarify`, а не случайный redirect;
- path из результата всегда внутренний и безопасный;
- текущие страницы LMS продолжают работать.

## 13. Минимальная первая версия route catalog

Для MVP достаточно проиндексировать существующие страницы:

```text
/dashboard
/courses
/settings
/filesblock
/input_file/test
/gantt
/admin
/admin/course-builder
/admin/grades
```

Для каждого маршрута нужно вручную добавить `title`, `path`, `example_queries` и `metadata.role`. После MVP каталог можно генерировать полуавтоматически из Flask route map, но ручное описание лучше для семантического качества.
