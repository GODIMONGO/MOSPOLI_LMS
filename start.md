# MOSPOLI_LMS: запуск без Docker (Windows)

## 1. Базовый запуск проекта (пошагово)

1. Открой PowerShell и перейди в проект:

```powershell
cd D:\REALPROJECTS\MOSPOLI_LMS
```

2. Проверь Python:

```powershell
python --version
```

Нужен Python 3.10+ (рекомендуется 3.13).

3. Создай и активируй виртуальное окружение:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Если PowerShell блокирует активацию:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

4. Установи зависимости:

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

5. Подними Redis (обязателен для текущего `main.py`).

6. Задай переменные окружения:

```powershell
$env:REDIS_URL="redis://127.0.0.1:6379/0"
$env:SECRET_KEY="dev-secret"
```

7. Запусти приложение:

```powershell
python main.py
```

8. Открой:

`http://127.0.0.1:5000/login`

9. Тестовые логины:

- `admin / admin`
- `student / 123`

10. Опционально запусти Dramatiq worker во втором окне:

```powershell
cd D:\REALPROJECTS\MOSPOLI_LMS
.\.venv\Scripts\Activate.ps1
$env:REDIS_URL="redis://127.0.0.1:6379/0"
dramatiq tasks routes.input_file --processes 2 --threads 4
```

---

## 2. Что значит «Установи и запусти Redis (вариант A: Memurai)»

Это запуск Redis-совместимого сервиса как обычной службы Windows (без Docker).

Почему нужно:

- При старте `main.py` вызывается задача через Dramatiq.
- Dramatiq использует Redis как брокер.
- Если Redis недоступен, приложение не стартует.

### Вариант A (Windows Service через Memurai)

1. Скачай и установи **Memurai Developer Edition** с официального сайта Memurai.
2. Во время установки оставь запуск как Windows Service.
3. Проверь службу:

```powershell
Get-Service *Memurai*
```

4. Если служба не запущена:

```powershell
Start-Service Memurai
```

5. Проверь порт:

```powershell
Test-NetConnection 127.0.0.1 -Port 6379
```

6. Проверь ответ Redis-протокола:

```powershell
redis-cli -h 127.0.0.1 -p 6379 ping
```

Если `redis-cli` нет, используй `memurai-cli ping`.

Ожидаемый ответ: `PONG`.

---

## 3. Альтернативы Memurai

### Вариант B: Redis через WSL (без Docker)

```powershell
wsl
sudo apt update
sudo apt install redis-server -y
sudo service redis-server start
redis-cli ping
exit
```

После этого в Windows:

```powershell
$env:REDIS_URL="redis://127.0.0.1:6379/0"
python main.py
```

### Вариант C: другой Redis-совместимый сервер

Можно использовать KeyDB/Valkey и т.п., главное:

- сервер доступен на `127.0.0.1:6379`
- переменная:

```powershell
$env:REDIS_URL="redis://127.0.0.1:6379/0"
```

### Вариант D: временно без Redis (только для локальной верстки/демо)

Требуется dev-патч в `main.py`:

- обернуть `broker_init_check.send()` в `try/except` или флаг окружения
- тогда UI поднимется без Redis
- но фоновые задачи Dramatiq работать не будут

---

## 4. Быстрая диагностика

1. Ошибка `ModuleNotFoundError` (например `dramatiq`):

- не установлены зависимости или не активирована `.venv`
- решение: активировать окружение и выполнить `pip install -r requirements.txt`

2. Ошибка подключения к Redis:

- Redis не запущен / слушает другой порт
- проверить `Test-NetConnection 127.0.0.1 -Port 6379`
- проверить `redis-cli ping`

3. Сайт стартует, но задачи не обрабатываются:

- не запущен worker Dramatiq
- запустить команду из шага 10
