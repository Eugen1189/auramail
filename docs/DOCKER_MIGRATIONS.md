# 🐳 Docker Migrations Guide

## Проблема: Flask-Migrate не встановлений

**Симптоми:**
```
Error: No such command 'db'
```

## ✅ Рішення

### Крок 1: Перебудувати Docker image

Flask-Migrate додано до `requirements.txt`, але потрібно перебудувати image:

```bash
# Зупинити контейнери
docker compose down

# Перебудувати з новими залежностями
docker compose build

# Запустити знову
docker compose up -d
```

### Крок 2: Перевірити встановлення

```bash
# Перевірити чи Flask-Migrate встановлений
docker compose exec web pip list | grep Flask-Migrate
```

Має показати:
```
Flask-Migrate         4.0.x
```

### Крок 3: Ініціалізувати міграції

```bash
# Ініціалізувати міграції (перший раз)
docker compose exec web flask db init

# Створити міграцію
docker compose exec web flask db migrate -m "Initial migration"

# Застосувати міграції
docker compose exec web flask db upgrade
```

---

## 🔄 Альтернатива: Створити таблиці без міграцій

Якщо не хочете використовувати міграції, можна створити таблиці напряму:

```bash
# Зайти в Python консоль
docker compose exec web python
```

Потім в Python:
```python
from server import app
from database import db, ActionLog, Progress, Report

with app.app_context():
    db.create_all()
    print("✅ Tables created!")
    
    # Перевірити таблиці
    from sqlalchemy import inspect
    inspector = inspect(db.engine)
    tables = inspector.get_table_names()
    print(f"✅ Created {len(tables)} tables:")
    for table in tables:
        print(f"   - {table}")
```

---

## 📋 Перевірка

### Перевірити чи таблиці створені:

```bash
# Зайти в PostgreSQL
docker compose exec db psql -U auramail -d auramail

# Перелічити таблиці
\dt

# Вийти
\q
```

Або через Python:
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

## 🚨 Troubleshooting

### Помилка: "No such command 'db'"

**Причина:** Flask-Migrate не встановлений

**Рішення:**
1. Перевірити `requirements.txt` - має бути `Flask-Migrate>=4.0.0`
2. Перебудувати Docker image: `docker compose build`
3. Перезапустити контейнери: `docker compose up -d`

### Помилка: "Could not locate a Flask application"

**Причина:** FLASK_APP не налаштований

**Рішення:**
Перевірити `docker-compose.yml` - має бути:
```yaml
environment:
  - FLASK_APP=server:app
```

### Помилка: "ModuleNotFoundError: No module named 'flask_migrate'"

**Причина:** Flask-Migrate не встановлений в контейнері

**Рішення:**
1. Перебудувати Docker image
2. Або встановити вручну: `docker compose exec web pip install Flask-Migrate`

---

## ✅ Швидке рішення

**Найпростіше - створити таблиці без міграцій:**

```bash
docker compose exec web python -c "
from server import app
from database import db

with app.app_context():
    db.create_all()
    print('✅ Tables created successfully!')
"
```

---

**Статус:** ✅ Готово до використання
