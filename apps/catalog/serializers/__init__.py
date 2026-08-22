# ────────────────────────────────────────────────────────────
# serializers/__init__.py — реэкспорт всех сериализаторов каталога.
#
# АРХИТЕКТУРНАЯ РОЛЬ:
#   Вместо того чтобы в views писать:
#     from apps.catalog.serializers.product_serializers import ProductListSerializer
#   можно:
#     from apps.catalog.serializers import ProductListSerializer
#
#   Это фасад (Facade pattern) — скрывает внутреннюю структуру
#   файлов сериализаторов от потребителей.
#
# __all__ — белый список для `from apps.catalog.serializers import *`.
# Без __all__: import * вытащит ВСЕ имена модуля (включая
# импортированные из rest_framework) — засорение пространства имён.
# С __all__: импортируются только перечисленные сериализаторы.
#
# ЧТО БУДЕТ, ЕСЛИ УДАЛИТЬ ФАЙЛ:
#   from apps.catalog.serializers import ProductListSerializer
#   → ImportError (views не найдут сериализаторы).
# ────────────────────────────────────────────────────────────

# Каждый импорт из конкретного файла-модуля.
# Имена модулей во множественном числе (brand_serializers),
# имена классов в единственном (BrandListSerializer).
from apps.catalog.serializers.brand_serializers import BrandListSerializer, BrandDetailSerializer
from apps.catalog.serializers.category_serializers import (
    CategoryTreeSerializer,
    CategoryDetailSerializer,
    BreadcrumbSerializer,
)
from apps.catalog.serializers.product_serializers import (
    ProductListSerializer,
    ProductDetailSerializer,
    CreateProductInputSerializer,
    UpdateProductInputSerializer,
    ProductListQuerySerializer,
)
from apps.catalog.serializers.tag_serializers import TagSerializer

# __all__ — перечислены в алфавитном порядке для удобства поиска.
# При добавлении нового сериализатора — добавить сюда.
__all__ = [
    'BrandDetailSerializer',
    'BrandListSerializer',
    'BreadcrumbSerializer',
    'CategoryDetailSerializer',
    'CategoryTreeSerializer',
    'CreateProductInputSerializer',
    'ProductDetailSerializer',
    'ProductListQuerySerializer',
    'ProductListSerializer',
    'TagSerializer',
    'UpdateProductInputSerializer',
]
