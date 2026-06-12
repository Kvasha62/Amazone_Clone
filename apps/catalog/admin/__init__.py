# ────────────────────────────────────────────────────────────
# admin/__init__.py — реэкспорт всех admin-классов каталога.
#
# АРХИТЕКТУРНАЯ РОЛЬ:
#   Django admin автоматически обнаруживает модули admin.py
#   в каждом приложении. Но мы разделили админку на несколько
#   файлов (по сущности), поэтому __init__.py нужен для:
#   1) Импорта всех admin-классов (регистрирование @admin.register)
#   2) Единой точки входа для Django при загрузке admin
#
# Без __init__.py: Django найдёт пустой пакет admin/
# и НЕ загрузит ни один admin-класс → в /admin/ будет пусто.
# ────────────────────────────────────────────────────────────

# Каждый admin-класс импортируется из своего файла.
# Импорт РЕГИСТРИРУЕТ класс через @admin.register(Model):
#   @admin.register(Brand) → django.admin.sites.register(Brand, BrandAdmin)
# Поэтому достаточно просто импортировать — регистрация происходит
# как побочный эффект импорта (side effect).
from apps.catalog.admin.attribute_admin import AttributeAdmin, AttributeValueAdmin
from apps.catalog.admin.brand_admin import BrandAdmin
from apps.catalog.admin.category_admin import CategoryAdmin
from apps.catalog.admin.product_admin import ProductAdmin
from apps.catalog.admin.product_variant_admin import ProductVariantAdmin
from apps.catalog.admin.tag_admin import TagAdmin

# __all__ — белый список для `from apps.catalog.admin import *`.
# Перечислены в алфавитном порядке для поддерживаемости.
__all__ = [
    'AttributeAdmin',
    'AttributeValueAdmin',
    'BrandAdmin',
    'CategoryAdmin',
    'ProductAdmin',
    'ProductVariantAdmin',
    'TagAdmin',
]
