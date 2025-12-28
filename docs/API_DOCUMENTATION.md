# AuraMail API Documentation

## Swagger/OpenAPI Documentation

AuraMail надає повну API документацію через Swagger UI, доступну за адресою:

**`/api-docs`** - Swagger UI інтерфейс для інтерактивного тестування API

**`/apispec.json`** - OpenAPI специфікація в JSON форматі

## Доступ до документації

1. Запустіть сервер:
   ```bash
   python server.py
   ```

2. Відкрийте браузер і перейдіть на:
   ```
   https://127.0.0.1:5000/api-docs
   ```

3. У Swagger UI ви зможете:
   - Переглянути всі доступні endpoints
   - Побачити параметри запитів та відповідей
   - Протестувати API напряму з браузера
   - Переглянути схеми даних

## Групи Endpoints

### Health
- `GET /health` - Перевірка стану сервісу

### Authentication
- `GET /authorize` - Початок OAuth авторизації
- `GET /callback` - OAuth callback обробка
- `GET /logout` - Вихід з системи
- `GET /clear-credentials` - Очищення credentials

### Dashboard
- `GET /` - Головна сторінка дашборду

### Email Sorting
- `GET /sort` - Запуск сортування листів
- `GET /api/progress` - Прогрес обробки
- `POST /rollback/<msg_id>` - Відкат дії для листа

### Export
- `GET /export/csv` - Експорт у CSV
- `GET /export/pdf` - Експорт у PDF

### Analytics
- `GET /api/analytics/roi` - ROI аналітика
- `GET /api/analytics/time-savings` - Аналітика економії часу
- `GET /api/analytics/chart-data` - Дані для графіків

### Reports
- `GET /report` - Сторінка детального звіту

### Voice Search
- `POST /voice/search` - Голосовий пошук листів

### Follow-up
- `POST /save-followup-credentials` - Збереження credentials для follow-up
- `POST /api/sent_hook` - Hook для відправлених листів
- `POST /api/log_sent_email` - Логування відправленого листа

### Monitoring
- `GET /metrics` - Prometheus метрики

## Авторизація

Більшість endpoints вимагають авторизації через OAuth 2.0. 

Для тестування в Swagger UI:
1. Спочатку авторизуйтеся через `/authorize`
2. Після успішної авторизації, сесія буде збережена
3. Swagger UI автоматично використовуватиме cookies для авторизованих запитів

## Приклади використання

### Запуск сортування листів
```bash
curl -X GET "https://127.0.0.1:5000/sort" \
  -H "Cookie: session=<your-session-cookie>"
```

### Отримання ROI аналітики
```bash
curl -X GET "https://127.0.0.1:5000/api/analytics/roi?days=30" \
  -H "Cookie: session=<your-session-cookie>"
```

### Експорт у CSV
```bash
curl -X GET "https://127.0.0.1:5000/export/csv" \
  -H "Cookie: session=<your-session-cookie>" \
  --output report.csv
```

## Технічні деталі

- **OpenAPI версія**: 2.0
- **Формат документації**: YAML (в docstrings)
- **Бібліотека**: flasgger
- **Автоматична генерація**: Так, з docstrings функцій

## Оновлення документації

Документація автоматично генерується з docstrings у `server.py`. 
Для додавання нового endpoint:

1. Додайте функцію з декоратором `@app.route()`
2. Додайте docstring з YAML форматом Swagger:
   ```python
   """
   Опис endpoint.
   ---
   tags:
     - Tag Name
   parameters:
     - name: param
       in: query
       type: string
   responses:
     200:
       description: Success
   """
   ```

3. Swagger UI автоматично оновиться після перезапуску сервера


