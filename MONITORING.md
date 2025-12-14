# 📊 Моніторинг та Логування AuraMail

## 🔍 Prometheus Metrics

AuraMail експортує метрики Prometheus для моніторингу продуктивності та здоров'я додатку.

### Endpoint

Метрики доступні за адресою:
```
http://localhost:5000/metrics
```

### Доступні метрики

#### Counters (лічильники)

- **`auramail_emails_processed_total`** - Загальна кількість оброблених листів
  - Labels: `category`, `action`
  
- **`auramail_classification_errors_total`** - Кількість помилок класифікації AI
  - Labels: `error_type`
  
- **`auramail_api_requests_total`** - Загальна кількість API запитів
  - Labels: `endpoint`, `method`, `status`

#### Histograms (гістограми тривалості)

- **`auramail_email_processing_duration_seconds`** - Час обробки одного листа
  - Buckets: 0.1s, 0.5s, 1s, 2s, 5s, 10s, 30s, 60s
  
- **`auramail_sort_job_duration_seconds`** - Час обробки повного завдання сортування
  - Buckets: 10s, 30s, 60s, 120s, 300s, 600s, 1800s, 3600s
  
- **`auramail_api_request_duration_seconds`** - Час обробки API запиту
  - Labels: `endpoint`
  - Buckets: 0.01s, 0.05s, 0.1s, 0.5s, 1s, 2s, 5s

#### Gauges (поточні значення)

- **`auramail_emails_in_queue`** - Поточна кількість листів у черзі обробки
- **`auramail_active_workers`** - Кількість активних RQ workers
- **`auramail_redis_connection_status`** - Статус з'єднання з Redis (1=підключено, 0=відключено)
- **`auramail_database_pool_size`** - Розмір пулу з'єднань з БД

### Налаштування Prometheus

Додайте до `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'auramail'
    static_configs:
      - targets: ['localhost:5000']
    metrics_path: '/metrics'
```

### Grafana Dashboards

Використовуйте метрики для створення дашбордів у Grafana:

1. **Email Processing Rate** - `rate(auramail_emails_processed_total[5m])`
2. **Error Rate** - `rate(auramail_classification_errors_total[5m])`
3. **API Request Duration** - `histogram_quantile(0.95, auramail_api_request_duration_seconds_bucket)`
4. **Active Workers** - `auramail_active_workers`

---

## 📝 Structured Logging

AuraMail використовує **structlog** для структурованого логування в форматі JSON, що дозволяє легко інтегруватися з ELK Stack.

### Формат логів

Логи виводяться у форматі JSON:

```json
{
  "event": "email_processed",
  "msg_id": "19b08f49db31ff52",
  "category": "IMPORTANT",
  "action": "MOVE",
  "timestamp": "2025-12-12T10:30:00Z",
  "level": "info"
}
```

### Використання в коді

```python
from utils.logging_config import get_logger

logger = get_logger(__name__)

# Info log
logger.info(
    "email_processed",
    msg_id="19b08f49db31ff52",
    category="IMPORTANT",
    action="MOVE"
)

# Error log
logger.error(
    "classification_failed",
    msg_id="19b0e66fcd74631e",
    error="429 RESOURCE_EXHAUSTED",
    error_type="rate_limit"
)
```

### Інтеграція з ELK Stack

#### Запуск ELK Stack

```bash
docker-compose -f docker-compose.elk.yml up -d
```

#### Налаштування Logstash

Логи надсилаються на Logstash через TCP (порт 5000) або UDP.

Конфігурація Logstash знаходиться в `deployment/logstash/pipeline/logstash.conf`.

#### Доступ до Kibana

Відкрийте http://localhost:5601 для перегляду логів у Kibana.

### Перехід з print на structured logging

Старий код:
```python
print(f"✅ Email {msg_id} processed: {category}")
```

Новий код:
```python
logger.info("email_processed", msg_id=msg_id, category=category)
```

---

## 🔧 Health Checks

### Prometheus Health Check

```bash
curl http://localhost:5000/metrics
```

### Application Health Check

```bash
curl http://localhost:5000/
```

### Redis Health Check

```python
from redis import Redis
r = Redis.from_url('redis://localhost:6379/0')
r.ping()  # Should return True
```

---

## 📊 Приклад Grafana Dashboard

Створіть dashboard з наступними панелями:

1. **Emails Processed per Minute**
   ```
   rate(auramail_emails_processed_total[1m])
   ```

2. **Classification Error Rate**
   ```
   rate(auramail_classification_errors_total[5m])
   ```

3. **API Request Duration (95th percentile)**
   ```
   histogram_quantile(0.95, auramail_api_request_duration_seconds_bucket{endpoint="/api/progress"})
   ```

4. **Active Workers**
   ```
   auramail_active_workers
   ```

5. **Redis Connection Status**
   ```
   auramail_redis_connection_status
   ```

---

## 🚀 Production Deployment

### Prometheus + Grafana

Використовуйте Docker Compose для розгортання:

```yaml
# docker-compose.monitoring.yml
version: '3.8'
services:
  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    ports:
      - "9090:9090"
  
  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
```

### ELK Stack

Використовуйте `docker-compose.elk.yml` для розгортання ELK Stack.

---

## 📚 Корисні посилання

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Dashboards](https://grafana.com/grafana/dashboards/)
- [ELK Stack Documentation](https://www.elastic.co/guide/index.html)
- [Structlog Documentation](https://www.structlog.org/)


