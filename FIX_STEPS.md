# 🔧 Покрокова інструкція виправлення

## Що сталося?

Помилка `ValueError: Invalid attribute name: run_task_in_context` означає, що в Redis черзі залишилися старі задачі з посиланням на видалену функцію.

## ✅ Виправлення (3 кроки)

### 1️⃣ Зупиніть Worker
У терміналі з worker натисніть `Ctrl+C`

### 2️⃣ Очистіть чергу Redis

**Найпростіший спосіб - скопіюйте ці команди в Python:**

Відкрийте PowerShell і введіть:
```powershell
python
```

Потім скопіюйте і вставте весь цей блок:
```python
import redis
from rq import Queue
from rq.registry import FailedJobRegistry, StartedJobRegistry

conn = redis.from_url('redis://localhost:6379/0')
q = Queue('default', connection=conn)
print(f"Jobs in queue: {len(q)}")
q.empty()
print("✅ Queue cleared!")

failed = FailedJobRegistry('default', connection=conn)
for job_id in failed.get_job_ids():
    failed.remove(job_id)
print("✅ Failed jobs cleared!")

started = StartedJobRegistry('default', connection=conn)
for job_id in started.get_job_ids():
    started.remove(job_id)
print("✅ Started jobs cleared!")
print("Done! Type exit() and press Enter")
```

Потім введіть `exit()` і натисніть Enter.

### 3️⃣ Перезапустіть Worker
```powershell
python worker.py
```

Готово! Тепер спробуйте запустити нову задачу через веб-інтерфейс.

