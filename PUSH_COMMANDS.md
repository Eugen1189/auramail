# 📤 Команди для публікації коду на GitHub

## Крок 1: Перевірка статусу Git
```bash
git status
```

## Крок 2: Додавання всіх файлів
```bash
git add .
```

## Крок 3: Створення коміту
```bash
git commit -m "feat: Initial commit - AuraMail with 66% test coverage and CI/CD pipeline"
```

## Крок 4: Додавання/оновлення remote репозиторію
```bash
# Якщо remote ще не додано:
git remote add origin https://github.com/Eugen1189/auramail.git

# АБО якщо remote вже існує (оновити URL):
git remote set-url origin https://github.com/Eugen1189/auramail.git

# Перевірити remote:
git remote -v
```

## Крок 5: Встановлення гілки main
```bash
git branch -M main
```

## Крок 6: Push до GitHub
```bash
git push -u origin main
```

---

## 🚀 Альтернатива: Використання готового скрипта

### Windows PowerShell:
```powershell
.\push_to_github.ps1
```

### Windows CMD:
```cmd
push_to_github.bat
```

---

## ⚠️ Якщо потрібна автентифікація

GitHub більше не підтримує паролі. Вам потрібен **Personal Access Token (PAT)**:

1. Створіть токен: https://github.com/settings/tokens
2. Додайте права: `repo` (повний доступ до репозиторіїв)
3. При `git push` використовуйте токен замість пароля:
   - Username: ваш GitHub username
   - Password: ваш Personal Access Token

---

## 🔍 Діагностика проблем

### Перевірити налаштування Git:
```bash
git config --list
```

### Перевірити remote:
```bash
git remote -v
```

### Перевірити гілки:
```bash
git branch
```

### Переглянути останній коміт:
```bash
git log -1
```


