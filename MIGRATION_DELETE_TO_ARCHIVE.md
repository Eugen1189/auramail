# 🔄 Міграція: DELETE → ARCHIVE

## Зміни в базі даних

Модель `Report` оновлена: поле `deleted` замінено на `archived`.

### Створення міграції Alembic

```bash
alembic revision --autogenerate -m "Change deleted to archived in Report model"
```

### Вручну виконати SQL (якщо потрібно)

```sql
-- SQLite
ALTER TABLE reports RENAME COLUMN deleted TO archived;

-- PostgreSQL
ALTER TABLE reports RENAME COLUMN deleted TO archived;
```

### Перевірка

Після міграції перевірте:
- `Report.archived` існує
- Старі дані з `deleted` перенесені (якщо були)
- Всі залежності оновлені

## Зміни в коді

✅ `database.py` - модель Report оновлена  
✅ `utils/db_logger.py` - save_report використовує archived  
✅ `tasks.py` - статистика використовує archived  
✅ `server.py` - calculate_stats використовує archived  
✅ `templates/` - UI оновлено для archived  

## Backward Compatibility

Код автоматично перетворює старі `DELETE` дії на `ARCHIVE` в `utils/gmail_api.py`:
- `process_message_action` - конвертує DELETE → ARCHIVE
- `rollback_action` - конвертує DELETE → ARCHIVE для відкату

