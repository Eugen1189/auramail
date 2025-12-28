# ⚡ Швидке вирішення: Створення таблиць без Flask-Migrate

## Проблема

Flask-Migrate не встановлений в Docker контейнері, тому команда `flask db init` не працює.

## ✅ Швидке рішення (без міграцій)

### Варіант 1: Через Python команду (найшвидше)

```bash
docker compose exec web python -c "
from server import app
from database import db
from database import ActionLog, Progress, Report

with app.app_context():
    db.create_all()
    print('✅ Tables created successfully!')
    
    # Перевірити таблиці
    from sqlalchemy import inspect
    inspector = inspect(db.engine)
    tables = inspector.get_table_names()
    print(f'✅ Found {len(tables)} tables:')
    for table in tables:
        print(f'   - {table}')
"
```

### Варіант 2: Через Python інтерактивну консоль

```bash
# Зайти в Python
docker compose exec web python

# Виконати команди:
from server import app
from database import db
from database import ActionLog, Progress, Report

with app.app_context():
    db.create_all()
    print("✅ Tables created!")

exit()
```

### Варіант 3: Використати init_database.py

```bash
docker compose exec web python init_database.py
```

---

## 🔧 Повне рішення (з Flask-Migrate)

Якщо хочете використовувати міграції:

### 1. Перебудувати Docker image

```bash
# Зупинити контейнери
docker compose down

# Перебудувати з новими залежностями
docker compose build

# Запустити знову
docker compose up -d
```

### 2. Перевірити встановлення

```bash
docker compose exec web pip list | grep Flask-Migrate
```

### 3. Ініціалізувати міграції

```bash
# Ініціалізувати (перший раз)
docker compose exec web flask db init

# Створити міграцію
docker compose exec web flask db migrate -m "Initial migration"

# Застосувати міграції
docker compose exec web flask db upgrade
```

---

## 📋 Перевірка таблиць

### Через PostgreSQL:

```bash
docker compose exec db psql -U auramail -d auramail -c "\dt"
```

### Через Python:

```bash
docker compose exec web python -c "
from server import app
from database import db
from sqlalchemy import inspect

with app.app_context():
    inspector = inspect(db.engine)
    tables = inspector.get_table_names()
    print(f'✅ Found {len(tables)} tables:')
    for table in tables:
        print(f'   - {table}')
"
```

---

## 🎯 Рекомендація

**Для швидкого старту:** Використайте Варіант 1 (Python команда)  
**Для production:** Перебудуйте Docker image та використайте Flask-Migrate

---

**Статус:** ✅ Готово до використання

