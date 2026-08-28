# ==============================================================================
# apps/catalog/management/commands/populate_catalog.py
# Заполнение каталога тестовыми данными для демонстрации фронтенда.
#
# Создает:
#   1. Категории (treebeard MP_Node — add_root/add_child)
#   2. Бренды
#   3. Теги
#   4. EAV атрибуты (Attribute + AttributeValue)
#   5. Товары (Product) с статусом ACTIVE
#   6. Варианты товаров (ProductVariant) + EAV (VariantAttribute)
#   7. Цены (Price) — базовая + sale_price
#   8. Остатки (Stock) — quantity + reserved
#   9. Тестовый суперпользователь + JWT-ready
#
# Использование:
#   python manage.py populate_catalog
#   python manage.py populate_catalog --clear  (удалить все созданные данные)
#
# ВАЖНО: категории создаются через treebeard API (add_root/add_child),
#   а НЕ Category.objects.create() — иначе depth=NULL IntegrityError.
# ==============================================================================

from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.catalog.models import (
    Category, Brand, Product, ProductVariant, Tag,
    Attribute, AttributeValue, VariantAttribute,
)
from apps.catalog.constants import ProductStatus
from apps.pricing.models import Price
from apps.pricing.services.pricing_service import PricingService
from apps.inventory.models import Stock
from apps.users.models import User


class Command(BaseCommand):
    help = 'Заполнить каталог тестовыми данными (категории, бренды, товары, варианты, цены, остатки, EAV)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Удалить все тестовые данные перед заполнением',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self._clear_data()

        self._create_superuser()
        categories = self._create_categories()
        brands = self._create_brands()
        tags = self._create_tags()
        eav_attrs = self._create_eav_attributes()
        self._create_products(categories, brands, tags, eav_attrs)

        self.stdout.write(self.style.SUCCESS('\n✅ Каталог заполнен тестовыми данными!'))
        self.stdout.write('\n📋 СУПЕРПОЛЬЗОВАТЕЛЬ:')
        self.stdout.write('   Email:    admin@test.com')
        self.stdout.write('   Password: admin12345')
        self.stdout.write('\n📋 API LOGIN:')
        self.stdout.write('   POST /api/v1/auth/token/')
        self.stdout.write('   {"email": "admin@test.com", "password": "admin12345"}')
        self.stdout.write('\n📋 FRONTEND: http://localhost:5173')

    # ── Очистка ──────────────────────────────────────────────────

    def _clear_data(self):
        """Удалить все тестовые данные."""
        with transaction.atomic():
            VariantAttribute.objects.all().delete()
            AttributeValue.objects.all().delete()
            Attribute.objects.all().delete()
            Stock.objects.all().delete()
            Price.objects.all().delete()
            ProductVariant.objects.all().delete()
            Product.objects.all().delete()
            Tag.objects.all().delete()
            Brand.objects.all().delete()
            Category.objects.all().delete()
        self.stdout.write(self.style.WARNING('🗑️ Все данные удалены.'))

    # ── Суперпользователь ──────────────────────────────────────────

    def _create_superuser(self):
        """Создать суперпользователя для admin и JWT-логина."""
        if User.objects.filter(email='admin@test.com').exists():
            self.stdout.write('  👤 Суперпользователь уже существует, пропускаем.')
            return

        user = User.objects.create_superuser(
            email='admin@test.com',
            username='admin',
            password='admin12345',
        )
        self.stdout.write(f'  👤 Суперпользователь создан: {user.email}')

    # ── Категории (treebeard!) ────────────────────────────────────

    def _create_categories(self):
        """Создать дерево категорий через treebeard API."""
        # ВАЖНО: add_root() / add_child() — НЕ Category.objects.create()

        cats_data = {
            'Электроника': ['Телефоны', 'Ноутбуки', 'Аксессуары'],
            'Одежда': ['Мужская', 'Женская', 'Детская'],
            'Дом и сад': ['Инструменты', 'Мебель', 'Освещение'],
            'Спорт': ['Фитнес', 'Бег', 'Плавание'],
        }

        created = []
        for root_name, children in cats_data.items():
            root = Category.add_root(name=root_name)
            created.append(root)
            for child_name in children:
                child = root.add_child(name=child_name)
                created.append(child)

        self.stdout.write(f'  📂 Категории: {len(created)} создано')
        return created

    # ── Бренды ────────────────────────────────────────────────────

    def _create_brands(self):
        """Создать бренды."""
        brands_data = [
            ('Samsung', 'Мировой лидер электроники'),
            ('Apple', 'Инновационные устройства'),
            ('Nike', 'Спортивная одежда и обувь'),
            ('Adidas', 'Спортивные товары'),
            ('Bosch', 'Инструменты и техника для дома'),
            ('IKEA', 'Мебель и товары для дома'),
        ]

        created = []
        for name, desc in brands_data:
            brand = Brand.objects.create(name=name, description=desc)
            created.append(brand)

        self.stdout.write(f'  🏷️ Бренды: {len(created)} создано')
        return created

    # ── Теги ──────────────────────────────────────────────────────

    def _create_tags(self):
        """Создать теги."""
        tags_data = ['Новинка', 'Хит продаж', 'Скидка', 'Эксклюзив', 'Премиум']

        created = []
        for name in tags_data:
            tag = Tag.objects.create(name=name)
            created.append(tag)

        self.stdout.write(f'  🔖 Теги: {len(created)} создано')
        return created

    # ── EAV атрибуты ──────────────────────────────────────────────

    def _create_eav_attributes(self):
        """Создать EAV атрибуты с допустимыми значениями."""
        attrs_data = {
            'Цвет': ['Чёрный', 'Белый', 'Титановый', 'Серый'],
            'Память': ['128GB', '256GB', '512GB'],
            'Размер': ['42', '43', '44', '45'],
            'Материал': ['Алюминий', 'Пластик', 'Ткань'],
        }

        result = {}  # {attr_name: {value_name: AttributeValue obj}}

        for attr_name, values in attrs_data.items():
            attr = Attribute.objects.create(name=attr_name)
            value_objs = {}
            for val in values:
                av = AttributeValue.objects.create(
                    attribute=attr,
                    value=val,
                    color_hex='#000000' if attr_name == 'Цвет' else '',
                )
                value_objs[val] = av
            result[attr_name] = {'attr': attr, 'values': value_objs}

        self.stdout.write(f'  🔧 EAV атрибуты: {len(result)} создано')
        return result

    # ── Товары + варианты + цены + остатки ────────────────────────

    def _create_products(self, categories, brands, tags, eav_attrs):
        """Создать товары с вариантами, ценами, остатками и EAV."""
        # Leaf-узлы для primary_category (treebeard: is_leaf())
        leaf_cats = [c for c in categories if c.is_leaf()]

        if not leaf_cats or not brands:
            self.stdout.write(self.style.ERROR('  Нет категорий/брендов — пропускаем товары.'))
            return

        products_data = [
            # (name, brand_idx, leaf_cat_idx, description, is_featured, variants)
            # variants: [(sku, base_price, sale_price_or_None, {attr: value})]
            (
                'Galaxy S24 Ultra',
                0,  # Samsung
                0,  # Телефоны (first leaf)
                'Флагманский смартфон с AI-камерой и S Pen.',
                True,
                [
                    ('GS24-256-B', Decimal('89990'), None, {'Цвет': 'Чёрный', 'Память': '256GB'}),
                    ('GS24-512-B', Decimal('109990'), Decimal('94990'), {'Цвет': 'Чёрный', 'Память': '512GB'}),
                    ('GS24-256-W', Decimal('89990'), None, {'Цвет': 'Белый', 'Память': '256GB'}),
                ],
            ),
            (
                'iPhone 16 Pro',
                1,  # Apple
                0,
                'Новейший iPhone с чипом A18 Pro и камерой 48MP.',
                True,
                [
                    ('IP16-128-N', Decimal('99990'), None, {'Цвет': 'Титановый', 'Память': '128GB'}),
                    ('IP16-256-N', Decimal('119990'), Decimal('104990'), {'Цвет': 'Титановый', 'Память': '256GB'}),
                ],
            ),
            (
                'MacBook Air M3',
                1,  # Apple
                1,  # Ноутбуки
                'Лёгкий и мощный ноутбук с чипом Apple M3.',
                True,
                [
                    ('MBA-M3-8-256', Decimal('129990'), Decimal('114990'), {'Память': '128GB'}),
                    ('MBA-M3-16-512', Decimal('159990'), None, {'Память': '256GB'}),
                ],
            ),
            (
                'Nike Air Max 270',
                2,  # Nike
                7,  # Бег (leaf index 7)
                'Кроссовки с Air-подошвой для комфорта каждый день.',
                False,
                [
                    ('NK-AM270-42', Decimal('12990'), Decimal('9990'), {'Размер': '42', 'Цвет': 'Чёрный'}),
                    ('NK-AM270-44', Decimal('12990'), None, {'Размер': '44', 'Цвет': 'Белый'}),
                ],
            ),
            (
                'Adidas Ultraboost',
                3,  # Adidas
                7,
                'Беговые кроссовки с технологией Boost.',
                False,
                [
                    ('AD-UB-42', Decimal('14990'), Decimal('11990'), {'Размер': '42', 'Цвет': 'Серый'}),
                    ('AD-UB-43', Decimal('14990'), None, {'Размер': '43', 'Цвет': 'Чёрный'}),
                ],
            ),
            (
                'Bosch дрель GSR 180',
                4,  # Bosch
                6,  # Инструменты
                'Ударная дрель для профессионального ремонта.',
                False,
                [
                    ('BOSCH-GSR180', Decimal('5990'), None, {}),
                ],
            ),
            (
                'Samsung Galaxy Buds FE',
                0,  # Samsung
                2,  # Аксессуары
                'Беспроводные наушники с активным шумоподавлением.',
                False,
                [
                    ('SG-BUDS-FE-B', Decimal('4990'), Decimal('3990'), {'Цвет': 'Чёрный'}),
                    ('SG-BUDS-FE-W', Decimal('4990'), None, {'Цвет': 'Белый'}),
                ],
            ),
            (
                'IKEA Книжный шкаф Kallax',
                5,  # IKEA
                9,  # Мебель
                'Модульный шкаф для хранения книг и вещей.',
                False,
                [
                    ('IKEA-KALLAX-2X2', Decimal('3990'), None, {}),
                    ('IKEA-KALLAX-4X4', Decimal('7990'), Decimal('6490'), {}),
                ],
            ),
        ]

        created_products = 0
        created_variants = 0

        for name, brand_idx, cat_idx, desc, featured, variants_data in products_data:
            brand = brands[brand_idx] if brand_idx < len(brands) else brands[0]
            primary_cat = leaf_cats[cat_idx] if cat_idx < len(leaf_cats) else leaf_cats[0]

            product = Product.objects.create(
                name=name,
                brand=brand,
                primary_category=primary_cat,
                description=desc,
                status=ProductStatus.ACTIVE,
                is_featured=featured,
            )

            # M2M: категории (основная + все предки)
            parent_cats = list(primary_cat.get_ancestors()) + [primary_cat]
            product.categories.set(parent_cats)

            # M2M: теги (2 тега)
            product.tags.set(tags[:2])

            # Создаем варианты
            for sku, base_price, sale_price, attr_values in variants_data:
                variant = ProductVariant.objects.create(
                    product=product,
                    sku=sku,
                    is_active=True,
                    weight=Decimal('0.50'),
                )

                # Price (OneToOne)
                Price.objects.create(
                    variant=variant,
                    price=base_price,
                    sale_price=sale_price,
                )

                # Stock (OneToOne)
                Stock.objects.create(
                    variant=variant,
                    quantity=50,
                    reserved_quantity=0,
                )

                # EAV: VariantAttribute связи
                for attr_name, val_name in attr_values.items():
                    if attr_name in eav_attrs and val_name in eav_attrs[attr_name]['values']:
                        VariantAttribute.objects.create(
                            variant=variant,
                            attribute=eav_attrs[attr_name]['attr'],
                            value=eav_attrs[attr_name]['values'][val_name],
                        )

                created_variants += 1

            # ARCH-001 Stage 2: Product.recalculate_prices() удалён — он
            # читал pricing.Price из каталога. Пересчёт через контракт
            # pricing → CatalogService.set_product_prices.
            PricingService.recalculate_product_bounds(product)
            created_products += 1

        self.stdout.write(
            f'  📦 Товары: {created_products} создано'
            f' ({created_variants} вариантов)'
        )
