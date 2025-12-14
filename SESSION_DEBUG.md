# 🔍 Діагностика проблеми з сесіями

## Проблема

Після OAuth авторизації користувача повертає на стартову сторінку для повторної авторизації. Це означає, що сесія не зберігається між запитами.

## Виправлення

### 1. Вимкнено SESSION_COOKIE_SECURE в development

Для development з self-signed сертифікатом браузери відхиляють cookies з `Secure=True`, навіть на HTTPS.

**Зміна:**
```python
if DEBUG:
    app.config['SESSION_COOKIE_SECURE'] = False  # ВИМКНЕНО в development
```

### 2. Додано логування для діагностики

Додано логування в `/callback` маршрут для відстеження збереження сесії.

## Діагностика

### Крок 1: Перевірте логи сервера

Після авторизації перевірте логи - має з'явитися:
```
{"event": "session_saved", "has_credentials": true, "session_permanent": true}
```

### Крок 2: Перевірте cookies в браузері

1. Відкрийте Developer Tools (F12)
2. Перейдіть на Application → Cookies → `https://127.0.0.1:5000`
3. Після `/callback` має з'явитися cookie `session`

**Очікувані значення в development:**
- Name: `session`
- Domain: `127.0.0.1` або порожнє
- Secure: ❌ **False** (це правильно для development!)
- SameSite: `Lax`
- HttpOnly: ✅ True

### Крок 3: Очистіть всі cookies

Якщо старі cookies конфліктують:

1. F12 → Application → Cookies
2. Клікніть правою кнопкою на `https://127.0.0.1:5000`
3. Видаліть всі cookies
4. Спробуйте авторизуватися знову

### Крок 4: Перевірте FLASK_SECRET_KEY

Переконайтеся, що ключ встановлений і однаковий при кожному запуску:

```python
from config import FLASK_SECRET_KEY
print(f"Secret key length: {len(FLASK_SECRET_KEY) if FLASK_SECRET_KEY else 'NOT SET'}")
```

## Якщо проблема залишається

### Варіант 1: Використайте HTTP замість HTTPS для тестування

Тимчасово змініть в `.env`:
```env
FORCE_HTTPS=False
```

І запустіть server без SSL:
```python
app.run(host='127.0.0.1', port=5000, debug=True)  # Без ssl_context
```

⚠️ **Увага:** OAuth не працюватиме без HTTPS! Це тільки для тестування cookies.

### Варіант 2: Перевірте браузер

Деякі браузери блокувати cookies з self-signed cert. Спробуйте:
- Chrome: Перейдіть на `chrome://flags/#allow-insecure-localhost` і увімкніть
- Firefox: Може потребувати додаткових налаштувань
- Edge: Спробуйте додати exception для `127.0.0.1`

### Варіант 3: Додайте явне збереження сесії

Можна додати middleware для явного збереження сесії:

```python
@app.before_request
def make_session_permanent():
    session.permanent = True
```

## Перевірка конфігурації

Запустіть для перевірки:
```python
from app_factory import create_app
app = create_app()
print("DEBUG:", app.config['DEBUG'])
print("SESSION_COOKIE_SECURE:", app.config['SESSION_COOKIE_SECURE'])
print("SESSION_COOKIE_SAMESITE:", app.config['SESSION_COOKIE_SAMESITE'])
print("SESSION_PERMANENT:", app.config['SESSION_PERMANENT'])
```

**Очікуваний вивід в development:**
```
DEBUG: True
SESSION_COOKIE_SECURE: False
SESSION_COOKIE_SAMESITE: Lax
SESSION_PERMANENT: True
```

## Важливо

- `SESSION_COOKIE_SECURE=False` в development - це **правильно** для self-signed cert
- В production має бути `SESSION_COOKIE_SECURE=True`
- Cookies з `Secure=True` на self-signed cert будуть відхилені браузером

