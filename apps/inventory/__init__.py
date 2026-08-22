# ==============================================================================
# apps/inventory/__init__.py
# ==============================================================================
# Пустой __init__.py делает директорию «inventory» Python-пакетом.
#
# Почему это нужно:
#   Без __init__.py Python не распознаёт директорию как пакет,
#   и `from apps.inventory.models import Stock` выбросит ImportError.
#
# 📖 https://docs.python.org/3/reference/import.html#regular-packages
#
# ЧТО БУДЕТ, ЕСЛИ УДАЛИТЬ ФАЙЛ:
#   • Python не найдёт пакет apps.inventory → ImportError
#   • INSTALLED_APPS = [..., 'apps.inventory', ...] → AppConfig не загрузится
# ==============================================================================

default_app_config = 'apps.inventory.apps.InventoryConfig'
