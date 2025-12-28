# 🔧 Flask-Migrate Fix для Docker

**Дата:** 2025-12-26  
**Статус:** ✅ Виправлено

## Проблема

Flask-Migrate не був встановлений та не був налаштований в `app_factory.py`, що призводило до помилок при запуску міграцій в Docker.

## Рішення

### 1. Додано Flask-Migrate до requirements.txt

```txt
Flask-Migrate>=4.0.0
```

### 2. Створено app_factory.py з Flask-Migrate

```python
from flask_migrate import Migrate
from database import db

# Initialize Flask-Migrate
migrate = Migrate()

def create_app():
    app = Flask(__name__)
    
    # Configure database
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialize database
    db.init_app(app)
    
    # Initialize Flask-Migrate
    migrate.init_app(app, db)
    
    return app
```

## Використання

### В Docker контейнері:

```bash
# Ініціалізувати міграції (перший раз)
docker compose exec web flask db init

# Створити міграцію
docker compose exec web flask db migrate -m "Initial migration"

# Застосувати міграції
docker compose exec web flask db upgrade
```

### Альтернатива (створення таблиць без міграцій):

```bash
# Зайти в Python консоль
docker compose exec web python

# Створити таблиці
from server import app
from database import db

with app.app_context():
    db.create_all()
    print("✅ Tables created!")
```

## Перевірка

```bash
# Перевірити чи Flask-Migrate встановлений
docker compose exec web pip list | grep Flask-Migrate

# Перевірити чи app_factory працює
docker compose exec web python -c "from app_factory import create_app; app = create_app(); print('✅ OK')"
```

---

**Статус:** ✅ Виправлено та готово до використання

