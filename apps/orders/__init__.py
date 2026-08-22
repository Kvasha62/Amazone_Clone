# ==============================================================================
# apps/orders/__init__.py
# ==============================================================================
# Пустой __init__.py делает директорию «orders» Python-пакетом.
#
# Почему это нужно:
#   Без __init__.py Python не распознаёт директорию как пакет,
#   и `from apps.orders.models import Order` выбросит ImportError.
#   Это стандартный механизм Python-пакетов (regular package).
#
# 📖 https://docs.python.org/3/reference/import.html#regular-packages
#
# ЧТО БУДЕТ, ЕСЛИ УДАЛИТЬ ФАЙЛ:
#   • Python не найдёт пакет apps.orders → ImportError
#   • INSTALLED_APPS = [..., 'apps.orders', ...] → AppConfig не загрузится
#   • Все миграции, модели, views → недоступны
# ==============================================================================

# default_app_config — указывает Django какой AppConfig использовать.
# В Django 3.2+ автоматически находится по имени приложения,
# но оставляем для совместимости с INSTALLED_APPS без суффикса.
default_app_config = 'apps.orders.apps.OrdersConfig'
