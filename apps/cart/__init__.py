# ────────────────────────────────────────────────────────────────────────
# apps/cart/__init__.py — точка входа Python-пакета «корзина».
#
# Этот файл превращает директорию apps/cart/ в импортируемый Python-пакет.
# Без него: import apps.cart → ModuleNotFoundError.
#
# Единственная строка — указание Django конфигурационного класса приложения.
# Django при загрузке INSTALLED_APPS ищет default_app_config
# чтобы узнать какой AppConfig использовать.
#
# 📖 https://docs.djangoproject.com/en/stable/ref/applications/#configuring-applications
#
# ЧТО БУДЕТ, ЕСЛИ УДАЛИТЬ ФАЙЛ:
#   • Django не обнаружит apps.cart в INSTALLED_APPS → таблицы не создадутся
#   • import apps.cart.models → ModuleNotFoundError
#   • Все URL корзины (/api/v1/cart/) → 404
# ────────────────────────────────────────────────────────────────────────

# default_app_config — путь к классу AppConfig.
# Django загружает CartConfig при старте (python manage.py runserver).
# CartConfig определяет: name, verbose_name, default_auto_field, ready().
# 📖 https://docs.djangoproject.com/en/stable/ref/applications/#django.apps.AppConfig
#
# Почему указываем 'apps.cart.apps.CartConfig', а не просто 'apps.cart':
#   - Явное указание класса → Django вызывает CartConfig.ready()
#   - ready() подключает сигналы (merge_guest_cart_on_login)
#   - Без ready(): гостевые корзины не сливаются при логине
default_app_config = 'apps.cart.apps.CartConfig'
