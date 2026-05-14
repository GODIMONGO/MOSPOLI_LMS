# Быстрый запуск MOSPOLI LMS в Google Colab

Этот сценарий не требует Docker, QEMU, VPN, Cloudflare или localtunnel. Сначала запускается быстрый mock-режим AI-навигации, чтобы проверить, что сайт и API вообще работают в Colab. Реальная GGUF-модель запускается отдельно после этого.

## 1. Открой notebook

Открой файл:

```text
deploy/colab/MOSPOLI_LMS_Colab.ipynb
```

Если открываешь через GitHub, ссылка должна вести на актуальный репозиторий/ветку после push изменений.

## 2. Выполни ячейки сверху вниз

В notebook есть готовые ячейки:

```text
1. Clone or update the project
2. Install Node.js 22 and build tools
3. Fast reliable start: frontend + API with mock embeddings
4. Local checks inside Colab
5. Open the site through Colab's built-in authenticated proxy
```

После ячейки 3 должны быть строки:

```text
Services are running.
ai-navigation-service: http://127.0.0.1:3001
frontend:              http://127.0.0.1:5173
```

## 3. Открой сайт

Запусти ячейку 5. Она использует встроенный прокси Colab:

```text
google.colab.kernel.proxyPort(5173)
```

Это не внешний tunnel. VPN обычно не мешает этому способу.

## 4. Если порт 5173 не поднялся

Запусти диагностическую ячейку 7 в notebook. Важны три вывода:

```text
ss -ltnp
.colab/logs/frontend.log
.colab/logs/ai-navigation-service.log
```

Если `frontend.log` пустой или там ошибка `Cannot find module`, значит ячейка установки зависимостей не прошла или была прервана.

Если в выводе нет `node deploy/colab/serve-frontend.mjs`, frontend-сервер не запущен.

Если `node --version` ниже `v20.19.0`, значит Node.js не обновился. Перезапусти ячейку установки Node.js.

## 5. Реальная модель Qwen/llama.cpp

Только после того как mock-режим открыл сайт, можно запускать ячейку 6:

```text
Optional: real embeddings with Qwen GGUF + llama.cpp CUDA
```

Перед этим в Colab включи GPU:

```text
Runtime -> Change runtime type -> T4 GPU
```

Реальный режим скачивает большую GGUF-модель и собирает `llama.cpp`, поэтому он может занимать много времени. Для проверки интерфейса он не нужен.

## 6. Что именно запускается

В mock-режиме:

```text
browser
  -> Colab proxy
  -> frontend static/proxy server :5173
  -> /api proxy
  -> ai-navigation-service :3001
  -> mock embeddings
```

В real-режиме:

```text
browser
  -> Colab proxy
  -> frontend static/proxy server :5173
  -> /api proxy
  -> ai-navigation-service :3001
  -> llama.cpp :8080
  -> Qwen3 GGUF
```
