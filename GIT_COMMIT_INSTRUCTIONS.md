# 📝 Інструкції для збереження змін у Git

## Варіант 1: Використайте .bat скрипт (Windows)

Просто запустіть:
```powershell
.\commit_changes.bat
```

## Варіант 2: Виконайте команди вручну

Відкрийте PowerShell або Command Prompt і виконайте:

```powershell
# Перевірка статусу
git status

# Додавання всіх змін
git add -A

# Створення commit
git commit -m "Fix: Session management, database initialization, worker context, and Gmail label colors

- Fixed Flask session configuration for OAuth callback
- Added automatic database table creation in app_factory.py
- Fixed Flask app context for ThreadPoolExecutor threads in tasks.py
- Updated Gmail label colors to use color names instead of HEX codes
- Added fallback logic for label color creation
- Updated init_database.py to use app_factory.create_app()
- Fixed worker.py to properly wrap tasks with Flask app context
- Updated LABEL_COLOR_MAP to use Gmail API color names
- Removed FLASK_SECRET_KEY default value for security
- Added session.permanent = True in before_request middleware"

# Перевірка фінального статусу
git status
```

## Варіант 3: Використайте Python скрипт

```powershell
python commit_changes.py
```

## Після commit

Якщо потрібно відправити зміни на remote репозиторій:

```powershell
git push
```

Або якщо це перший push:

```powershell
git push -u origin main
```

## Змінені файли

Основні зміни в цих файлах:
- `app_factory.py` - конфігурація сесій та автоматичне створення таблиць
- `server.py` - session.permanent в before_request
- `tasks.py` - Flask app context для ThreadPoolExecutor
- `worker.py` - обгортка задач з Flask app context
- `utils/gmail_api.py` - кольори міток (назви замість HEX)
- `config.py` - LABEL_COLOR_MAP оновлено, FLASK_SECRET_KEY без default
- `init_database.py` - використовує app_factory.create_app()
- `tests/` - оновлені тести (видалено run_task_in_context)

