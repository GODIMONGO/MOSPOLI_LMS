# MOSPOLI_LMS

## Запуск проекта через `venv`

### 1. Создать виртуальное окружение

```powershell
py -m venv .venv
```

### 2. Активировать окружение

Windows (PowerShell):

```powershell
.\.venv\Scripts\Activate.ps1
```

Windows (cmd):

```cmd
.\.venv\Scripts\activate.bat
```

macOS / Linux:

```bash
source .venv/bin/activate
```

### 3. Установить зависимости

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 4. Запустить сервер

```powershell
python main.py
```

После запуска приложение будет доступно по адресу:

`http://127.0.0.1:5000`

### 5. Остановить сервер и выйти из `venv`

Остановка сервера: `Ctrl + C`

Деактивация окружения:

```powershell
deactivate
```

## Быстрый запуск (PowerShell)

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python main.py
```
