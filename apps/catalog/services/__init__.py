# ────────────────────────────────────────────────────────────
# services/__init__.py — точка сборки сервисного слоя каталога.
#
# ПОЧЕМУ ПУСТОЙ:
#   Все сервисы сейчас в catalog_service.py (CatalogService).
#   Когда сервисов станет несколько (BrandService, CategoryService),
#   сюда добавятся импорты и __all__ для удобства.
#
#   В Django пустой __init__.py превращает директорию в Python-пакет,
#   что позволяет делать: from apps.catalog.services.catalog_service import ...
#
# ЧТО БУДЕТ, ЕСЛИ УДАЛИТЬ ФАЙЛ:
#   from apps.catalog.services.catalog_service import CatalogService
#   → ModuleNotFoundError: No module named 'apps.catalog.services'
#   Python не найдёт каталог services как пакет.
# ────────────────────────────────────────────────────────────
