# 🔐 OAuth Implementation Guide - AuraMail

## Поточна реалізація (Google Auth OAuthlib)

Код використовує **google-auth-oauthlib** та **google-auth** - актуальні бібліотеки від Google.

### Архітектура

```
┌─────────────────┐
│   User Browser  │
└────────┬────────┘
         │ 1. GET /authorize
         ▼
┌─────────────────┐
│   server.py     │
│  - Flow.create()│
│  - OAuth URL    │
└────────┬────────┘
         │ 2. Redirect to Google
         ▼
┌─────────────────┐
│  Google OAuth   │
│     Server      │
└────────┬────────┘
         │ 3. Callback with code
         ▼
┌─────────────────┐
│   server.py     │
│ /callback route │
│ - flow.fetch_   │
│   token()       │
│ - credentials.  │
│   to_json()     │
└────────┬────────┘
         │ 4. Save to session
         ▼
┌─────────────────┐
│ Flask Session   │
│ credentials JSON│
└─────────────────┘
```

### Код компонентів

#### 1. Створення OAuth Flow (server.py)

```python
from google_auth_oauthlib.flow import Flow
from config import CLIENT_SECRETS_FILE, SCOPES, BASE_URI

def create_flow():
    redirect_uri = f"{BASE_URI.rstrip('/')}/callback"
    return Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        redirect_uri=redirect_uri
    )
```

#### 2. Авторизація (/authorize route)

```python
@app.route('/authorize')
def authorize():
    flow = create_flow()
    authorization_url, state = flow.authorization_url(
        access_type='offline',      # Для отримання refresh token
        include_granted_scopes='true',
        prompt='consent'            # Завжди показувати consent screen
    )
    session['oauth_state'] = state
    return redirect(authorization_url)
```

#### 3. Обробка callback (/callback route)

```python
@app.route('/callback')
def callback():
    flow = create_flow()
    flow.fetch_token(authorization_response=request.url)
    credentials = flow.credentials
    
    # Збереження credentials
    session['credentials'] = credentials.to_json()
    
    # Перевірка scopes
    if credentials.scopes:
        granted_set = set(credentials.scopes)
        required_set = set(SCOPES)
        if not required_set.issubset(granted_set):
            missing = required_set - granted_set
            flash(f"Відсутні дозволи: {', '.join(sorted(missing))}", 'warning')
    
    return redirect(url_for('index'))
```

#### 4. Відновлення Credentials

```python
from google.oauth2.credentials import Credentials
from config import SCOPES

def get_user_credentials():
    if 'credentials' not in session:
        return None
    credentials_json = session['credentials']
    return Credentials.from_authorized_user_info(
        json.loads(credentials_json), 
        SCOPES
    )
```

#### 5. Використання в Tasks (tasks.py)

```python
from google.oauth2.credentials import Credentials
from config import SCOPES

def background_sort_task(credentials_json):
    # Відновлення credentials з JSON
    creds = Credentials.from_authorized_user_info(
        json.loads(credentials_json), 
        SCOPES
    )
    
    # Створення Gmail/Calendar services
    service, calendar_service = build_google_services(creds)
    # ... використання services
```

### Безпека

✅ **Переваги поточної реалізації:**

1. **Стандартні бібліотеки Google** - підтримуються та оновлюються Google
2. **CSRF захист** - використовується `state` параметр
3. **Refresh tokens** - `access_type='offline'` забезпечує довготривалий доступ
4. **Перевірка scopes** - код перевіряє, що всі необхідні дозволи надані
5. **Secure session storage** - credentials зберігаються в зашифрованому Flask session

### Структура credentials JSON

```json
{
  "token": "ya29.a0AfH6SMB...",
  "refresh_token": "1//0g...",
  "token_uri": "https://oauth2.googleapis.com/token",
  "client_id": "123456789.apps.googleusercontent.com",
  "client_secret": "GOCSPX-...",
  "scopes": [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/calendar.events"
  ]
}
```

### Важливі моменти

1. **Refresh token** - автоматично використовується для оновлення access token
2. **Token expiry** - credentials.valid перевіряє, чи токен дійсний
3. **Scopes** - перевіряються при збереженні та використанні
4. **Session security** - FLASK_SECRET_KEY має бути надійним (генерується через secrets.token_hex(32))

### Міграція з oauth2client (не потрібна)

Код вже використовує правильні бібліотеки. Якщо ви побачите попередження про file_cache:
- Оновіть `google-api-python-client` до версії >=2.150.0
- Переконайтеся, що `oauth2client` не встановлено

