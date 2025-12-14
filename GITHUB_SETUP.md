# 📤 Інструкція по публікації коду на GitHub

## Крок 1: Ініціалізація Git (якщо ще не зроблено)

```bash
git init
```

## Крок 2: Додавання всіх файлів

```bash
git add .
```

## Крок 3: Створення першого коміту

```bash
git commit -m "feat: Initial commit - AuraMail with 66% test coverage and CI/CD pipeline"
```

## Крок 4: Додавання remote репозиторію

```bash
git remote add origin https://github.com/Eugen1189/auramail.git
```

Якщо remote вже існує, оновіть його:
```bash
git remote set-url origin https://github.com/Eugen1189/auramail.git
```

## Крок 5: Встановлення гілки main

```bash
git branch -M main
```

## Крок 6: Push до GitHub

```bash
git push -u origin main
```

## Альтернатива: Використання готових скриптів

### Windows PowerShell:
```powershell
.\push_to_github.ps1
```

### Windows CMD:
```cmd
push_to_github.bat
```

## Важливі файли, які НЕ потраплять у репозиторій (через .gitignore):

✅ **Безпека:**
- `.env` - конфіденційні дані
- `client_secret.json` - OAuth credentials
- `*.db` - локальні бази даних
- `*.log` - логи

✅ **Temporary файли:**
- `__pycache__/` - кеш Python
- `.pytest_cache/` - кеш тестів
- `htmlcov/` - coverage звіти
- `instance/` - локальні дані Flask

## Після публікації:

1. Перевірте репозиторій: https://github.com/Eugen1189/auramail
2. Налаштуйте GitHub Secrets для CI/CD:
   - `PROD_HOST`
   - `PROD_USERNAME`
   - `PROD_SSH_KEY`
   - та інші (див. DEPLOYMENT.md)
3. GitHub Actions автоматично запуститься після push


