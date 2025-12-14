# 🔧 Виправлення "Working outside of application context" в ThreadPoolExecutor

## Проблема

Worker обгортає `background_sort_task` з Flask app context, але всередині задачі використовується `ThreadPoolExecutor`, який створює нові потоки. Ці потоки не успадковують Flask app context від основного потоку, тому `db.session` не працює.

**Помилка:**
```
RuntimeError: Working outside of application context.
```

## Виправлення

### 1. Створення app context всередині кожного потоку

Оновлено `process_single_email_task` для створення Flask app context всередині потоку:

```python
def process_single_email_task(msg, credentials_json, gemini_client, label_cache, flask_app=None):
    # ThreadPoolExecutor creates new threads without Flask app context
    # We need to create app context inside each thread
    if flask_app is None:
        from app_factory import create_app
        flask_app = create_app()
    
    # Create app context for this thread
    with flask_app.app_context():
        return _process_single_email_task_impl(msg, credentials_json, gemini_client, label_cache)
```

### 2. Передача Flask app в ThreadPoolExecutor

Оновлено `_background_sort_task_impl` для передачі Flask app instance в потоки:

```python
# Create Flask app instance to pass to threads
# Each thread needs its own app context
from app_factory import create_app
thread_app = create_app()

with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
    future_to_msg = {
        executor.submit(
            process_single_email_task, 
            msg, 
            credentials_json,
            gemini_client, 
            label_cache,
            thread_app  # Pass Flask app so thread can create context
        ): msg for msg in unique_messages
    }
```

## Як це працює

1. **Worker wrapper** створює Flask app context для `background_sort_task`
2. **background_sort_task** створює Flask app instance для передачі в потоки
3. **ThreadPoolExecutor** запускає `process_single_email_task` в окремих потоках
4. **process_single_email_task** створює новий Flask app context для кожного потоку
5. **Кожен потік** має власний Flask app context з доступом до `db.session`

## Перевірка

Після виправлення помилка `Working outside of application context` має зникнути, і worker має правильно обробляти листи з логуванням в базу даних.

## Важливо

- Кожен потік має власний Flask app context (thread-safe)
- Flask app створюється через `create_app()` для правильної конфігурації
- `db.session` тепер доступний в кожному потоці

