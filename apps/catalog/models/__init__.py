# ==============================================================================
# apps/catalog/models/__init__.py — Центральный импорт моделей каталога
# ==============================================================================
# Все модели каталога импортируются через этот файл:
#   from apps.catalog.models import Product, Brand, Category
#
# Зачем отдельный __init__.py:
#   1. DRY — не нужно помнить путь к каждому файлу.
#   2. Разрешение циклических импортов — модели ссылаются друг на друга
#      через строки ('catalog.Product'), а импорты централизованы.
#   3. ProductStatus импортируется сюда из constants —
#      чтобы внешний код писал:
#        from apps.catalog.models import ProductStatus
#      вместо:
#        from apps.catalog.constants import ProductStatus
#
# __all__ — явно перечисляет публичные имена. Полезно для:
#   from apps.catalog.models import *
# ==============================================================================

from apps.catalog.constants import ProductStatus
from apps.catalog.models.attribute import Attribute
from apps.catalog.models.attribute_value import AttributeValue
from apps.catalog.models.brand import Brand
from apps.catalog.models.category import Category
from apps.catalog.models.product import Product
from apps.catalog.models.product_image import ProductImage
from apps.catalog.models.product_variant import ProductVariant
from apps.catalog.models.tag import Tag
from apps.catalog.models.variant_attribute import VariantAttribute

__all__ = [
    'Attribute',
    'AttributeValue',
    'Brand',
    'Category',
    'Product',
    'ProductImage',
    'ProductStatus',
    'ProductVariant',
    'Tag',
    'VariantAttribute',
]
