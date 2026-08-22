"""
Django settings for config project.
"""

import os
import sys
from datetime import timedelta
from pathlib import Path

# ────────────────────────────────────────────────────────────────────────
# .env — переменные окружения (django-cors-headers, python-dotenv)
#
# ЧТО БУДЕТ, ЕСЛИ НЕТ .env:
#   os.getenv() вернёт значение по умолчанию (второй аргумент).
#   Проект работает «из коробки» с дефолтами.
# ────────────────────────────────────────────────────────────────────────

from dotenv import load_dotenv

# Загружаем .env если файл существует (silent=True — нет ошибки если нет)
load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=False)

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/6.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used for production secret!
SECRET_KEY = os.getenv(
    "DJANGO_SECRET_KEY",
    "django-insecure-0o6-#o=vdk-tmhlq9^m=-ygr4y9lcscmft!fs(+#eno+&i-(n=",
)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv("DJANGO_DEBUG", "True").lower() in ("true", "1", "yes")

ALLOWED_HOSTS = os.getenv("DJANGO_ALLOWED_HOSTS", "*").split(",")

# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Third-party
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",  # 🔴 JWT blacklist — ROTATE_REFRESH_TOKENS + BLACKLIST_AFTER_ROTATION
    "django_filters",
    "treebeard",
    "drf_spectacular",
    "corsheaders",  # 🔴 CORS — React frontend support

    # Local apps
    "apps.core.apps.CoreConfig",
    "apps.users",
    "apps.catalog",
    "apps.inventory",
    "apps.pricing",
    "apps.cart",
    "apps.orders",
    "apps.payments",
    "apps.reviews",
    "apps.discounts",
    "apps.shipping",
    "apps.wishlist",
    "apps.notifications",
    "apps.analytics",
]

# ── PostgreSQL-specific ──
# django.contrib.postgres нужен для SearchVectorField, GinIndex и т.д.
# На SQLite он не нужен и вызывает проблемы с миграциями.
# DB_ENGINE читается из .env (загружен выше через load_dotenv).
DB_ENGINE = os.getenv("DB_ENGINE", "django.db.backends.sqlite3")
if DB_ENGINE == "django.db.backends.postgresql":
    INSTALLED_APPS.insert(6, "django.contrib.postgres")

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",   # 🔴 CORS — ДО CommonMiddleware
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(BASE_DIR, "templates")],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# Database
# https://docs.djangoproject.com/en/6.0/ref/settings/#databases

# ── DATABASES — читаем из .env, fallback на SQLite ──
# DB_ENGINE уже определён выше (в INSTALLED_APPS-блоке).
# Для PostgreSQL — полный набор (FOR UPDATE, GinIndex, SearchVectorField).
# Для SQLite — ограниченный (нет row-locking, нет full-text search).
#
# PostgreSQL adapter (psycopg3 vs psycopg2):
#   Django 4.2+ автоматически определяет адаптер:
#     если установлен psycopg (v3) → использует его
#     иначе если установлен psycopg2 → использует его
#   ENGINE остаётся "django.db.backends.postgresql" в обоих случаях!
#
# psycopg3 преимущества:
#   • Активная разработка (psycopg2 — только багфиксы)
#   • Встроенный пул соединений (Django 5.1+ OPTIONS.pool)
#   • Поддержка PostgreSQL 18
#   • Быстрее: бинарный протокол, 2x throughput

if DB_ENGINE == "django.db.backends.postgresql":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("DB_NAME", "amazone_clone"),
            "USER": os.getenv("DB_USER", "postgres"),
            "PASSWORD": os.getenv("DB_PASSWORD", ""),
            "HOST": os.getenv("DB_HOST", "localhost"),
            "PORT": os.getenv("DB_PORT", "5432"),
            # ── psycopg3: пул соединений (Django 5.1+) ──
            # Раскомментируйте для продакшена:
            # "OPTIONS": {
            #     "pool": {
            #         "min_size": 4,
            #         "max_size": 16,
            #         "timeout": 10,
            #     },
            # },
            # ── Важно при pool: CONN_MAX_AGE = 0 ──
            # Пул сам управляет жизненным циклом соединений.
            # "CONN_MAX_AGE": 0,
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": os.path.join(BASE_DIR, "db.sqlite3"),
        }
    }

# Password validation
# https://docs.djangoproject.com/en/6.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Internationalization
# https://docs.djangoproject.com/en/6.0/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/6.0/howto/static-files/

STATIC_URL = "static/"
MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "media")

# ==========================================================
# 🔴 CORS — React Frontend Support
# ==========================================================
# django-cors-headers позволяет React (localhost:3000)
# делать запросы к Django (localhost:8000).
# Без CORS браузер заблокирует все XHR-запросы.
#
# 📖 https://github.com/adamchainz/django-cors-headers

# CORS_ALLOW_ALL_ORIGINS — для dev (True).
# В production — обязательно False + CORS_ALLOWED_ORIGINS!
CORS_ALLOW_ALL_ORIGINS = os.getenv(
    "CORS_ALLOW_ALL_ORIGINS", "True" if DEBUG else "False",
).lower() in ("true", "1", "yes")

CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ALLOWED_ORIGINS",
        "http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173",
    ).split(",")
    if origin.strip()
]

# Разрешаем React отправлять JWT в заголовке Authorization
CORS_ALLOW_HEADERS = [
    "accept",
    "accept-encoding",
    "authorization",
    "content-type",
    "dnt",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
]

# Разрешаем куки (если понадобятся)
CORS_ALLOW_CREDENTIALS = True

# ==========================================================
# Django REST Framework
# ==========================================================

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    # 🟡 DEFAULT_RENDERER_CLASSES — только JSON (React не поймёт HTML)
    "DEFAULT_RENDERER_CLASSES": (
        "rest_framework.renderers.JSONRenderer",
    ),
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.OrderingFilter",
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    # 🟡 DEFAULT_THROTTLE_CLASSES — защита от спама
    # В TESTING режиме throttle отключается (THROTTLE_RATES = None)
    "DEFAULT_THROTTLE_CLASSES": (
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {
        "anon": os.getenv("THROTTLE_ANON", "60/min"),
        "user": os.getenv("THROTTLE_USER", "120/min"),
    },
}

# ==========================================================
# SimpleJWT
# ==========================================================

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    # 🔴 JWT login по EMAIL (не username)
    # SimpleJWT по умолчанию использует USERNAME_FIELD = "username".
    # Наш User использует email как USERNAME_FIELD —
    # но TokenObtainPairView проверяет authenticate(username=..., password=...).
    # Нужно указать, что поле для входа — email.
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}

# ==========================================================
# drf-spectacular (API documentation)
# ==========================================================

SPECTACULAR_SETTINGS = {
    "TITLE": "Amazone Clone API",
    "DESCRIPTION": "Marketplace API",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

# ==========================================================
# Test Runner
# ==========================================================
# Кастомный runner решает проблему с Python 3.14,
# где unittest discover() некорректно импортирует
# вложенные пакеты tests/ внутри apps/*.
TEST_RUNNER = "config.test_runner.AppDiscoverRunner"

# ==========================================================
# Default primary key field type
# ==========================================================
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ==========================================================
# Custom User model
# ==========================================================
AUTH_USER_MODEL = "users.User"

# ==========================================================
# 🔴 Authentication Backends — login by email
# ==========================================================
# По умолчанию Django ищет по username.
# EmailOrUsernameModelBackend позволяет логин по email.
# ModelBackend — fallback для Django Admin (username).
# 📖 https://docs.djangoproject.com/en/stable/topics/auth/customizing/#writing-an-authentication-backend
AUTHENTICATION_BACKENDS = [
    "apps.users.backends.EmailOrUsernameModelBackend",
    "django.contrib.auth.backends.ModelBackend",
]

# ==========================================================
# TESTING — отключаем throttle
# ==========================================================
# В тестах throttle мешает (слишком много запросов за секунду).
# 📖 https://www.django-rest-framework.org/api-guide/testing/#setting-throttling-policy
# Определяем, запущены ли тесты.
# Способ 1: env var DJANGO_TESTING (устанавливается test_runner.py)
# Способ 2: sys.argv содержит 'test' (manage.py test)
# Оба способа нужны потому что settings.py загружается ДО test_runner.py,
# поэтому DJANGO_TESTING может быть ещё не установлен.
_is_testing = (
    os.getenv("DJANGO_TESTING", "False").lower() in ("true", "1", "yes")
    or "test" in sys.argv
)

if _is_testing:
    REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"] = {
        "anon": None,
        "user": None,
    }
