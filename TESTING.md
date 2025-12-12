# Testing Guide for AuraMail

## Overview

AuraMail використовує pytest для тестування. Тести поділені на:
- **Unit тести**: Тестують окремі функції та компоненти
- **Integration тести**: Тестують взаємодію між компонентами (Flask, RQ, БД)

## Встановлення

```bash
pip install -r requirements.txt
```

## Запуск тестів

### Всі тести:
```bash
pytest
```

### З покриттям коду:
```bash
pytest --cov=. --cov-report=html
```
Відкрийте `htmlcov/index.html` в браузері для перегляду звіту.

### Конкретний тестовий файл:
```bash
pytest tests/test_rate_limiter.py -v
```

### Тільки unit тести:
```bash
pytest -m unit
```

### Тільки integration тести:
```bash
pytest -m integration
```

## Структура тестів

```
tests/
├── __init__.py
├── conftest.py              # Pytest fixtures та конфігурація
├── test_rate_limiter.py     # Unit тести для rate limiter
├── test_retry_mechanism.py  # Unit тести для retry (tenacity)
├── test_api_endpoints.py    # Integration тести для Flask API
└── test_database.py         # Integration тести для БД операцій
```

## Тестові фікстури

Фікстури в `conftest.py`:
- `app`: Flask додаток для тестування
- `client`: Flask test client
- `mock_redis`: Mock Redis клієнт
- `mock_gemini_client`: Mock Gemini API клієнт

## Приклади використання

### Тест з мокованим Redis:
```python
@patch('utils.gemini_processor.redis_client')
def test_rate_limit(mock_redis):
    mock_redis.zcard.return_value = 0
    result = check_gemini_rate_limit()
    assert result is True
```

### Тест з Flask app контекстом:
```python
def test_log_action(app):
    with app.app_context():
        log_action('msg-123', {...}, 'MOVE', 'Subject')
        entry = ActionLog.query.filter_by(msg_id='msg-123').first()
        assert entry is not None
```

## CI/CD Integration

Тести автоматично запускаються через GitHub Actions при:
- Push в `main` або `develop`
- Pull Request в `main` або `develop`

Див. `.github/workflows/ci.yml` для деталей.

## Написання нових тестів

1. Створіть файл `tests/test_*.py`
2. Імпортуйте потрібні фікстури з `conftest.py`
3. Використовуйте `@pytest.mark.unit` або `@pytest.mark.integration`
4. Назви функцій: `test_*`

Приклад:
```python
import pytest
from unittest.mock import patch

@pytest.mark.unit
def test_my_function(mock_redis):
    # Your test code
    pass
```

