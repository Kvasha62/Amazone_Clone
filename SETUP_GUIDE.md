# 🚀 SETUP: PostgreSQL + Миграции — пошаговая инструкция

## ❗ ПРОБЛЕМА: вы всё ещё на SQLite!

Ошибка `sqlite3/base.py` означает что `.env` файл НЕ был создан
на вашем компьютере. Settings по умолчанию использует SQLite,
но проект требует PostgreSQL (SearchVectorField, GinIndex, FOR UPDATE).

---

## Шаг 1: Установите psycopg2-binary

```powershell
pip install psycopg2-binary
```

---

## Шаг 2: Создайте файл `.env`

Создайте файл `I:\NewPythonProjects\Amazone_Clone\.env` (рядом с manage.py):

```env
# Database: PostgreSQL
DB_ENGINE=django.db.backends.postgresql
DB_NAME=amazone_clone
DB_USER=postgres
DB_PASSWORD=Postgres123!
DB_HOST=localhost
DB_PORT=5432

# Django
DJANGO_SECRET_KEY=django-insecure-0o6-#o=vdk-tmhlq9^m=-ygr4y9lcscmft!fs(+#eno+&i-(n=
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=*
CORS_ALLOW_ALL_ORIGINS=True
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173
```

**⚠️ ЗАМЕНИТЕ DB_PASSWORD на ваш реальный пароль PostgreSQL!**

---

## Шаг 3: Создайте базу данных в PostgreSQL

В pgAdmin или в терминале PostgreSQL:

```sql
CREATE DATABASE amazone_clone;
```

Или через PowerShell:
```powershell
psql -U postgres -c "CREATE DATABASE amazone_clone;"
```

---

## Шаг 4: Удалите старые миграции + db.sqlite3

```powershell
# Удалите SQLite базу (если существует)
del db.sqlite3

# Удалите ВСЕ старые файлы миграций (НЕ __init__.py!)
# Для каждого app:
foreach ($app in analytics,cart,catalog,discounts,inventory,notifications,orders,payments,reviews,shipping,wishlist,users) {
    Remove-Item "apps\$app\migrations\*.py" -Exclude "__init__.py"
}
```

---

## Шаг 5: Создайте новые миграции

```powershell
python manage.py makemigrations
```

Это создаст один `0001_initial.py` для каждого app (без дубликатов!).

---

## Шаг 6: Примените миграции

```powershell
python manage.py migrate
```

---

## Шаг 7: Заполните тестовыми данными

```powershell
python manage.py populate_catalog
```

---

## Шаг 8: Проверьте Swagger

Откройте: http://localhost:8000/api/v1/docs/

---

## Шаг 9: Запустите frontend

```powershell
cd frontend
npm install
npm run dev
```

Откройте: http://localhost:5173

---

## Если PostgreSQL недоступен (fallback на SQLite)

Если PostgreSQL не установлен или не запущен, проект может работать
на SQLite, но с ограничениями:

1. НЕ создавайте `.env` или НЕ задайте DB_ENGINE
2. Удалите `db.sqlite3` и старые миграции
3. `python manage.py makemigrations` — модели автоматически
   используют TextField вместо SearchVectorField на SQLite
4. `python manage.py migrate` — SkipIf в тестах пропускает PostgreSQL-only тесты

Ограничения SQLite:
- Нет FOR UPDATE (select_for_update → no-op, возможны race conditions)
- Нет full-text search (fallback на __icontains)
- Нет partial indexes (condition=... не поддерживается)
- Нет GinIndex
