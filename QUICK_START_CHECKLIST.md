# ⚡ Швидкий чек-лист для запуску AuraMail

## 🚀 За 5 хвилин

### 1. Налаштування середовища
```bash
# Клонувати репозиторій
git clone <repo-url>
cd auramail

# Створити virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# або
venv\Scripts\activate  # Windows

# Встановити залежності
pip install -r requirements.txt
```

### 2. Конфігурація
```bash
# Створити .env файл
cp .env.example .env

# Відредагувати .env - додати:
# - FLASK_SECRET_KEY (згенерувати: python -c "import secrets; print(secrets.token_hex(32))")
# - GEMINI_API_KEY (з Google AI Studio)
# - BASE_URI=http://localhost:5000 (для dev)
```

### 3. Google OAuth
- [ ] Завантажити `client_secret.json` з Google Cloud Console
- [ ] Розмістити в корені проекту
- [ ] Налаштувати Redirect URI в Google Console: `http://localhost:5000/callback`

### 4. Запуск сервісів
```bash
# Redis (локально або Docker)
redis-server
# або
docker run -d -p 6379:6379 redis

# База даних (SQLite для dev)
python init_database.py
```

### 5. Запуск додатку
```bash
# Термінал 1: Flask сервер
python server.py

# Термінал 2: RQ Worker
rq worker
```

### 6. Перевірка
- [ ] Відкрити http://localhost:5000
- [ ] Натиснути "Авторизуватися"
- [ ] Пройти OAuth flow
- [ ] Перевірити dashboard

---

## 🐳 Docker (альтернатива)

```bash
# Зібрати та запустити
docker compose build
docker compose up -d

# Перевірити логи
docker compose logs -f web
docker compose logs -f worker

# Ініціалізувати базу даних
docker compose exec web python init_database.py
```

---

## ✅ Швидка перевірка

```bash
# Перевірити залежності
pip list | grep -E "Flask|redis|rq|SQLAlchemy"

# Перевірити конфігурацію
python -c "from config import *; print('✅ Config OK')"

# Перевірити базу даних
python -c "from database import db; print('✅ DB OK')"

# Запустити тести
pytest tests/ -v
```

---

## 🆘 Типові проблеми

### Помилка: "No module named 'X'"
```bash
pip install -r requirements.txt
```

### Помилка: "Redis connection failed"
```bash
# Перевірити чи Redis запущений
redis-cli ping
# Має відповісти: PONG
```

### Помилка: "FLASK_SECRET_KEY not set"
```bash
# Додати в .env:
FLASK_SECRET_KEY=<your-secret-key>
```

### Помилка: "client_secret.json not found"
- Завантажити з Google Cloud Console
- Розмістити в корені проекту

---

**Детальний чек-лист:** [docs/DEVELOPMENT_CHECKLIST.md](docs/DEVELOPMENT_CHECKLIST.md)

