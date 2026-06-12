# ────────────────────────────────────────────────────────────
# api_views/__init__.py — реэкспорт всех view-классов каталога.
#
# АРХИТЕКТУРНАЯ РОЛЬ:
#   Центральная точка импорта для urls.py:
#     from apps.catalog.api_views import ProductListView, ...
#   Без __init__.py: пришлось бы импортировать из каждого файла отдельно.
#
# __all__ — белый список для import *.
# Перечислены в алфавитном порядке для поддерживаемости.
#
# ЧТО БУДЕТ, ЕСЛИ УДАЛИТЬ ФАЙЛ:
#   urls.py: from apps.catalog.api_views import ... → ImportError.
#   Все URL-маршруты каталога перестанут работать.
# ────────────────────────────────────────────────────────────

# Каждый view-класс импортируется из своего файла.
# Файлы разделены по сущности: product, brand, category.
# Это предотвращает создание одного гигантского views.py
# на 1000+ строк (anti-pattern «God Module»).
from apps.catalog.api_views.brand_views import BrandListView, BrandDetailView
from apps.catalog.api_views.category_views import CategoryTreeView, CategoryDetailView
from apps.catalog.api_views.product_views import (
    ProductListView,
    ProductDetailView,
    ProductCreateView,
    ProductUpdateView,
)

# __all__ — при `from apps.catalog.api_views import *` экспортируются
# только эти 8 классов. Без __all__: утекут внутренние импорты
# (Response, status, logging и т.д.) — засорение namespace.
__all__ = [
    'BrandDetailView',
    'BrandListView',
    'CategoryDetailView',
    'CategoryTreeView',
    'ProductCreateView',
    'ProductDetailView',
    'ProductListView',
    'ProductUpdateView',
]
