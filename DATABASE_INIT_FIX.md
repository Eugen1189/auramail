# 🔧 Виправлення помилки "no such table: action_logs"

## Проблема

```
sqlite3.OperationalError: no such table: action_logs
```

База даних (`auramail.db`) існує, але таблиці не створені.

## Виправлення

### Автоматичне створення таблиць

Додано автоматичне створення таблиць при старті додатка в `app_factory.py`:

```python
# Ensure database tables exist (create if they don't)
# This is safe - db.create_all() only creates missing tables
with app.app_context():
    db.create_all()
```

### Альтернативний метод (якщо автоматичне створення не спрацювало)

Запустіть скрипт ініціалізації бази даних:

```powershell
python init_database.py
```

Або використайте Alembic міграції:

```powershell
alembic upgrade head
```

## Перевірка

Після перезапуску сервера таблиці мають створитися автоматично. Перевірте:

1. Перезапустіть сервер:
   ```powershell
   python server.py
   ```

2. Перевірте, що dashboard завантажується без помилок

3. Перевірте базу даних (опціонально):
   ```powershell
   python
   ```
   ```python
   from app_factory import create_app
   from database import db, ActionLog, Progress, Report
   
   app = create_app()
   with app.app_context():
       print(f"ActionLog table exists: {db.engine.dialect.has_table(db.engine.connect(), 'action_logs')}")
       print(f"Progress table exists: {db.engine.dialect.has_table(db.engine.connect(), 'progress')}")
       print(f"Report table exists: {db.engine.dialect.has_table(db.engine.connect(), 'reports')}")
   ```

## Структура таблиць

Додаток використовує три таблиці:

1. **action_logs** - Журнал обробки листів
2. **progress** - Поточний прогрес обробки
3. **reports** - Звіти про сортування

Всі таблиці створюються автоматично при старті додатка.

