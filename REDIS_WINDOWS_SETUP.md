# 🔴 Налаштування Redis на Windows

## Проблема
Worker потребує запущеного Redis сервера для обробки фонових задач.

## Варіанти запуску Redis на Windows

### Варіант 1: Docker (Рекомендовано) ⭐

Якщо у вас встановлений Docker:

```powershell
# Запустити Redis в Docker
docker run -d -p 6379:6379 --name redis-auramail redis:latest

# Перевірити, що Redis працює
docker ps
```

Або використайте `docker-compose.yml`:
```powershell
docker-compose up -d redis
```

### Варіант 2: WSL (Windows Subsystem for Linux)

Якщо у вас встановлений WSL:

```bash
# У WSL терміналі:
wsl

# Встановити Redis в WSL
sudo apt-get update
sudo apt-get install redis-server

# Запустити Redis
sudo service redis-server start

# Перевірити
redis-cli ping
```

### Варіант 3: Memurai (Нативний Redis для Windows)

1. Завантажити з: https://www.memurai.com/
2. Встановити Memurai
3. Запустити як Windows Service

### Варіант 4: Redis для Windows (неофіційний порт)

1. Завантажити з: https://github.com/tporadowski/redis/releases
2. Розпакувати архів
3. Запустити `redis-server.exe`

## Перевірка підключення

Після запуску Redis, перевірте підключення:

```powershell
python check_redis.py
```

Або вручну:
```powershell
# Якщо redis-cli доступний
redis-cli ping
# Має повернути: PONG
```

## Запуск Worker після запуску Redis

```powershell
python worker.py
```

