# ==============================================================================
# apps/catalog/management/commands/populate_full.py
#
# ПОЛНОЕ заполнение ВСЕХ моделей проекта тестовыми данными.
# Каждая позиция в админке будет заполнена.
#
# Создаёт:
#   1. Пользователи (5 шт.: admin + 4 обычных)
#   2. UserProfile (автосоздаётся через signal, обновляем)
#   3. Address (по 2-3 адреса на пользователя)
#   4. Category — дерево категорий (4 корня × 3 ребёнка × 2 внука = 28)
#   5. Brand (8 брендов)
#   6. Tag (7 тегов)
#   7. Attribute + AttributeValue (6 атрибутов со значениями)
#   8. Product (15 товаров) + ProductImage + ProductVariant + VariantAttribute
#   9. Price + PriceHistory
#  10. Stock + StockMovement
#  11. ShippingZone + ShippingMethod
#  12. Campaign + Coupon
#  13. Cart + CartItem
#  14. Order + OrderItem
#  15. Payment + PaymentEvent
#  16. Shipment
#  17. Review + ReviewImage
#  18. Wishlist + WishlistItem
#  19. Notification
#  20. ProductView (analytics)
#
# Использование:
#   python manage.py populate_full
#   python manage.py populate_full --clear
# ==============================================================================

import random
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.catalog.models import (
    Attribute, AttributeValue, Brand, Category, Product,
    ProductImage, ProductVariant, Tag, VariantAttribute,
)
from apps.catalog.constants import ProductStatus
from apps.cart.models import Cart, CartItem
from apps.discounts.models import Campaign, Coupon
from apps.inventory.models import Stock, StockMovement
from apps.notifications.models import Notification
from apps.orders.models import Order, OrderItem
from apps.payments.models import Payment, PaymentEvent
from apps.pricing.models import Price, PriceHistory
from apps.reviews.models import Review, ReviewHelpfulVote, ReviewImage
from apps.shipping.models import Shipment, ShippingMethod, ShippingZone
from apps.users.models import Address, User, UserProfile
from apps.wishlist.models import Wishlist, WishlistItem
from apps.analytics.models import ProductView


class Command(BaseCommand):
    help = 'ПОЛНОЕ заполнение ВСЕХ моделей тестовыми данными'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear', action='store_true',
            help='Удалить все данные перед заполнением',
        )

    def handle(self, *args, **options):
        self.stdout.write('\n🚀 ПОЛНОЕ заполнение базы тестовыми данными\n')
        self.stdout.write('=' * 60)

        if options['clear']:
            self._clear_all()

        # ── Порядок важен: FK зависимости ──
        users = self._create_users()
        self._update_profiles(users)
        addresses = self._create_addresses(users)
        categories = self._create_categories()
        brands = self._create_brands()
        tags = self._create_tags()
        eav = self._create_eav()
        products, variants = self._create_products(categories, brands, tags, eav)
        self._create_prices_and_history(variants)
        self._create_stocks_and_movements(variants, users)
        zones, methods = self._create_shipping()
        campaigns, coupons = self._create_discounts()
        carts = self._create_carts(users, variants)
        orders = self._create_orders(users, variants, addresses, coupons)
        self._create_payments(orders, users)
        self._create_shipments(orders, users, methods, zones)
        self._create_reviews(users, products)
        self._create_wishlists(users, variants)
        self._create_notifications(users, orders)
        self._create_analytics(users, products)

        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS('✅ БАЗА ПОЛНОСТЬЮ ЗАПОЛНЕНА!\n'))
        self.stdout.write('\n📋 Вход в админку:  http://localhost:8000/admin/')
        self.stdout.write('📋 Admin:           admin@test.com / admin12345')
        self.stdout.write('📋 Пользователи:    ivan/maria/alex/elena @test.com / Test12345!')
        self.stdout.write('📋 Фронтенд:        http://localhost:5173\n')

    # ================================================================
    # ОЧИСТКА
    # ================================================================

    def _clear_all(self):
        """Удалить ВСЕ данные из всех таблиц."""
        self.stdout.write('🗑️  Удаление всех данных...')
        with transaction.atomic():
            # Порядок обратный зависимостям
            ProductView.objects.all().delete()
            Notification.objects.all().delete()
            WishlistItem.objects.all().delete()
            Wishlist.objects.all().delete()
            ReviewHelpfulVote.objects.all().delete()
            ReviewImage.objects.all().delete()
            Review.objects.all().delete()
            Shipment.objects.all().delete()
            PaymentEvent.objects.all().delete()
            Payment.objects.all().delete()
            OrderItem.objects.all().delete()
            Order.objects.all().delete()
            CartItem.objects.all().delete()
            Cart.objects.all().delete()
            Coupon.objects.all().delete()
            Campaign.objects.all().delete()
            StockMovement.objects.all().delete()
            Stock.objects.all().delete()
            PriceHistory.objects.all().delete()
            Price.objects.all().delete()
            VariantAttribute.objects.all().delete()
            ProductVariant.objects.all().delete()
            ProductImage.objects.all().delete()
            Product.objects.all().delete()
            AttributeValue.objects.all().delete()
            Attribute.objects.all().delete()
            Tag.objects.all().delete()
            Brand.objects.all().delete()
            Category.objects.all().delete()
            ShippingMethod.objects.all().delete()
            ShippingZone.objects.all().delete()
            Address.objects.all().delete()
            UserProfile.objects.all().delete()
            User.objects.all().delete()
        self.stdout.write(self.style.WARNING('   Все данные удалены.\n'))

    # ================================================================
    # 1. ПОЛЬЗОВАТЕЛИ
    # ================================================================

    def _create_users(self):
        """Создать 5 пользователей: 1 admin + 4 обычных."""
        users_data = [
            ('admin@test.com', 'admin', 'Admin', 'Adminov', True, True),
            ('ivan@test.com', 'ivan_petrov', 'Иван', 'Петров', False, False),
            ('maria@test.com', 'maria_sidorova', 'Мария', 'Сидорова', False, False),
            ('alex@test.com', 'alex_kozlov', 'Алексей', 'Козлов', False, False),
            ('elena@test.com', 'elena_novikova', 'Елена', 'Новикова', False, False),
        ]

        users = []
        for email, username, first, last, is_su, is_staff in users_data:
            # 🔴 Admin-пароль: admin12345 (для совместимости с populate_catalog)
            #    Обычные пользователи: Test12345!
            pwd = 'admin12345' if is_su else 'Test12345!'
            if User.objects.filter(email=email).exists():
                user = User.objects.get(email=email)
                self.stdout.write(f'   👤 {email} — уже существует')
            else:
                user = User.objects.create_user(
                    email=email, username=username,
                    password=pwd,
                    first_name=first, last_name=last,
                    is_superuser=is_su, is_staff=is_su or is_staff,
                )
                self.stdout.write(f'   👤 {email} — создан (пароль: {pwd})')
            users.append(user)
        return users

    # ================================================================
    # 2. ПРОФИЛИ
    # ================================================================

    def _update_profiles(self, users):
        """Обновить UserProfile (создаётся сигналом)."""
        profile_data = [
            # (gender, timezone, language, email_subscribed, date_of_birth)
            ('M', 'Europe/Moscow', 'ru', True, '1990-05-15'),
            ('M', 'Europe/Moscow', 'ru', True, '1985-11-22'),
            ('F', 'Europe/Moscow', 'ru', True, '1992-03-08'),
            ('M', 'UTC', 'en', False, '1988-07-01'),
            ('F', 'Europe/Moscow', 'ru', True, '1995-12-30'),
        ]

        for user, (gender, tz, lang, sub, dob) in zip(users, profile_data):
            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.gender = gender
            profile.timezone = tz
            profile.language = lang
            profile.email_subscribed = sub
            profile.date_of_birth = dob
            profile.save()

        self.stdout.write(f'   📋 Профили: {len(users)} обновлено')

    # ================================================================
    # 3. АДРЕСА
    # ================================================================

    def _create_addresses(self, users):
        """Создать 2-3 адреса на каждого пользователя."""
        addr_data = [
            # (recipient, country, region, city, street, postal, is_default)
            ('Иван Петров', 'RU', 'Московская обл.', 'Москва', 'ул. Ленина, д. 10, кв. 5', '101000', True),
            ('Иван Петров', 'RU', 'Ленинградская обл.', 'Санкт-Петербург', 'Невский пр., д. 25', '190000', False),
            ('Мария Сидорова', 'RU', 'Московская обл.', 'Москва', 'ул. Тверская, д. 15', '125009', True),
            ('Мария Сидорова', 'RU', 'Краснодарский край', 'Краснодар', 'ул. Красная, д. 50', '350000', False),
            ('Мария Сидорова', 'RU', 'Республика Татарстан', 'Казань', 'ул. Баумана, д. 30', '420000', False),
            ('Алексей Козлов', 'RU', 'Новосибирская обл.', 'Новосибирск', 'Красный пр., д. 40', '630000', True),
            ('Алексей Козлов', 'RU', 'Свердловская обл.', 'Екатеринбург', 'ул. Ленина, д. 55', '620000', False),
            ('Елена Новикова', 'RU', 'Московская обл.', 'Москва', 'Кутузовский пр., д. 20', '121165', True),
            ('Елена Новикова', 'RU', 'Самарская обл.', 'Самара', 'ул. Фрунзе, д. 8', '443000', False),
        ]

        addresses = []
        idx = 0
        for user in users[1:]:  # skip admin
            count = 2 if idx < 6 else 3
            for i in range(count):
                if idx >= len(addr_data):
                    break
                d = addr_data[idx]
                addr = Address.objects.create(
                    user=user, recipient_name=d[0], country=d[1],
                    region=d[2], city=d[3], street=d[4],
                    postal_code=d[5], is_default=d[6],
                )
                addresses.append(addr)
                idx += 1

        self.stdout.write(f'   🏠 Адреса: {len(addresses)} создано')
        return addresses

    # ================================================================
    # 4. КАТЕГОРИИ (treebeard)
    # ================================================================

    def _create_categories(self):
        """4 корня × 3 ребёнка × 2 внука = 28 категорий."""
        tree = {
            'Электроника': {
                'Телефоны': ['Смартфоны', 'Кнопочные'],
                'Ноутбуки': ['Ультрабуки', 'Игровые'],
                'Аксессуары': ['Наушники', 'Чехлы'],
            },
            'Одежда': {
                'Мужская': ['Рубашки', 'Джинсы'],
                'Женская': ['Платья', 'Блузы'],
                'Обувь': ['Кроссовки', 'Ботинки'],
            },
            'Дом и сад': {
                'Инструменты': ['Электроинструменты', 'Ручные'],
                'Мебель': ['Гостиная', 'Спальня'],
                'Освещение': ['Люстры', 'Торшеры'],
            },
            'Спорт': {
                'Фитнес': ['Гантели', 'Коврики'],
                'Бег': ['Кроссовки', 'Спортивные часы'],
                'Плавание': ['Купальники', 'Очки'],
            },
        }

        categories = []
        for root_name, children in tree.items():
            root = Category.add_root(name=root_name)
            categories.append(root)
            for child_name, grandchildren in children.items():
                child = root.add_child(name=child_name)
                categories.append(child)
                for gc_name in grandchildren:
                    gc = child.add_child(name=gc_name)
                    categories.append(gc)

        self.stdout.write(f'   📂 Категории: {len(categories)} создано')
        return categories

    # ================================================================
    # 5. БРЕНДЫ
    # ================================================================

    def _create_brands(self):
        brands_data = [
            ('Samsung', 'Южнокорейская электроника'),
            ('Apple', 'Американские инновации'),
            ('Nike', 'Спортивная экипировка'),
            ('Adidas', 'Немецкие спортивные товары'),
            ('Bosch', 'Немецкие инструменты'),
            ('IKEA', 'Шведская мебель'),
            ('Sony', 'Японская электроника'),
            ('Xiaomi', 'Китайские гаджеты'),
        ]
        brands = []
        for name, desc in brands_data:
            b, _ = Brand.objects.get_or_create(
                name=name, defaults={'description': desc, 'is_active': True},
            )
            brands.append(b)
        self.stdout.write(f'   🏷️  Бренды: {len(brands)}')
        return brands

    # ================================================================
    # 6. ТЕГИ
    # ================================================================

    def _create_tags(self):
        tags_names = ['Новинка', 'Хит продаж', 'Скидка', 'Эксклюзив', 'Премиум', 'Бестселлер', 'Лидер рейтинга']
        tags = []
        for name in tags_names:
            t, _ = Tag.objects.get_or_create(name=name, defaults={'is_active': True})
            tags.append(t)
        self.stdout.write(f'   🔖 Теги: {len(tags)}')
        return tags

    # ================================================================
    # 7. EAV АТРИБУТЫ
    # ================================================================

    def _create_eav(self):
        attrs_data = {
            'Цвет': [('Чёрный', '#000000'), ('Белый', '#FFFFFF'), ('Титановый', '#8A8D8F'), ('Серый', '#808080'), ('Синий', '#0000FF'), ('Красный', '#FF0000')],
            'Память': [('128GB', ''), ('256GB', ''), ('512GB', ''), ('1TB', '')],
            'Размер': [('42', ''), ('43', ''), ('44', ''), ('45', ''), ('S', ''), ('M', ''), ('L', ''), ('XL', '')],
            'Материал': [('Алюминий', ''), ('Пластик', ''), ('Ткань', ''), ('Кожа', '')],
            'Диагональ': [('13"', ''), ('15"', ''), ('17"', '')],
            'Процессор': [('M3', ''), ('M3 Pro', ''), ('Intel i7', ''), ('AMD Ryzen 7', '')],
        }

        result = {}
        for attr_name, values in attrs_data.items():
            attr, _ = Attribute.objects.get_or_create(name=attr_name, defaults={'description': f'Атрибут: {attr_name}'})
            value_objs = {}
            for val_name, hex_color in values:
                av, _ = AttributeValue.objects.get_or_create(
                    attribute=attr, value=val_name,
                    defaults={'color_hex': hex_color},
                )
                value_objs[val_name] = av
            result[attr_name] = {'attr': attr, 'values': value_objs}

        self.stdout.write(f'   🔧 EAV: {len(result)} атрибутов')
        return result

    # ================================================================
    # 8. ТОВАРЫ + ВАРИАНТЫ
    # ================================================================

    def _create_products(self, categories, brands, tags, eav):
        """15 товаров с 2-4 вариантами каждый."""
        leaf_cats = [c for c in Category.objects.all() if c.is_leaf()]

        products_data = [
            # (name, brand_idx, cat_idx, desc, featured, status, variants)
            ('Galaxy S24 Ultra', 0, 0, 'Флагманский смартфон Samsung с AI-камерой 200MP и S Pen.', True, ProductStatus.ACTIVE, [
                ('GS24-256-B', Decimal('89990'), None, {'Цвет': 'Чёрный', 'Память': '256GB'}),
                ('GS24-512-B', Decimal('109990'), Decimal('94990'), {'Цвет': 'Чёрный', 'Память': '512GB'}),
                ('GS24-256-W', Decimal('89990'), None, {'Цвет': 'Белый', 'Память': '256GB'}),
                ('GS24-1TB-T', Decimal('129990'), Decimal('114990'), {'Цвет': 'Титановый', 'Память': '1TB'}),
            ]),
            ('iPhone 16 Pro', 1, 0, 'Новейший iPhone с чипом A18 Pro, камерой 48MP и Dynamic Island.', True, ProductStatus.ACTIVE, [
                ('IP16-128-N', Decimal('99990'), None, {'Цвет': 'Титановый', 'Память': '128GB'}),
                ('IP16-256-N', Decimal('119990'), Decimal('104990'), {'Цвет': 'Титановый', 'Память': '256GB'}),
                ('IP16-512-B', Decimal('139990'), None, {'Цвет': 'Чёрный', 'Память': '512GB'}),
            ]),
            ('MacBook Air M3', 1, 2, 'Ультратонкий ноутбук с чипом Apple M3, 15 часов батареи.', True, ProductStatus.ACTIVE, [
                ('MBA-M3-8-256', Decimal('129990'), Decimal('114990'), {'Диагональ': '13"', 'Память': '256GB', 'Процессор': 'M3'}),
                ('MBA-M3-16-512', Decimal('159990'), None, {'Диагональ': '15"', 'Память': '512GB', 'Процессор': 'M3 Pro'}),
            ]),
            ('Nike Air Max 270', 2, 8, 'Кроссовки с Air-подошвой для ежедневного комфорта.', False, ProductStatus.ACTIVE, [
                ('NK-AM270-42-B', Decimal('12990'), Decimal('9990'), {'Размер': '42', 'Цвет': 'Чёрный'}),
                ('NK-AM270-44-W', Decimal('12990'), None, {'Размер': '44', 'Цвет': 'Белый'}),
                ('NK-AM270-43-G', Decimal('12990'), None, {'Размер': '43', 'Цвет': 'Серый'}),
            ]),
            ('Adidas Ultraboost', 3, 8, 'Беговые кроссовки с технологией Boost и Primeknit.', False, ProductStatus.ACTIVE, [
                ('AD-UB-42-G', Decimal('14990'), Decimal('11990'), {'Размер': '42', 'Цвет': 'Серый'}),
                ('AD-UB-43-B', Decimal('14990'), None, {'Размер': '43', 'Цвет': 'Чёрный'}),
            ]),
            ('Bosch дрель GSR 180', 4, 6, 'Профессиональная ударная дрель 1800Вт.', False, ProductStatus.ACTIVE, [
                ('BOSCH-GSR180', Decimal('5990'), None, {}),
            ]),
            ('IKEA Kallax 2x2', 5, 10, 'Модульный стеллаж для книг и декора.', False, ProductStatus.ACTIVE, [
                ('IKEA-K2X2-W', Decimal('3990'), None, {'Цвет': 'Белый'}),
                ('IKEA-K2X2-B', Decimal('3990'), Decimal('3490'), {'Цвет': 'Чёрный'}),
            ]),
            ('Sony WH-1000XM5', 6, 4, 'Беспроводные наушники с лучшим шумоподавлением.', True, ProductStatus.ACTIVE, [
                ('SONY-XM5-B', Decimal('29990'), Decimal('24990'), {'Цвет': 'Чёрный'}),
                ('SONY-XM5-S', Decimal('29990'), None, {'Цвет': 'Серый'}),
            ]),
            ('Xiaomi Redmi Note 13', 7, 0, 'Бюджетный смартфон с AMOLED-экраном и камерой 108MP.', False, ProductStatus.ACTIVE, [
                ('XI-RN13-128-B', Decimal('16990'), Decimal('13990'), {'Цвет': 'Чёрный', 'Память': '128GB'}),
                ('XI-RN13-256-B', Decimal('19990'), None, {'Цвет': 'Чёрный', 'Память': '256GB'}),
            ]),
            ('Samsung Galaxy Buds FE', 0, 5, 'TWS-наушники с ANC и 30ч автономности.', False, ProductStatus.ACTIVE, [
                ('SG-BUDS-B', Decimal('4990'), Decimal('3990'), {'Цвет': 'Чёрный'}),
                ('SG-BUDS-W', Decimal('4990'), None, {'Цвет': 'Белый'}),
            ]),
            ('Nike Dri-FIT Футболка', 2, 5, 'Спортивная футболка с влагоотведением.', False, ProductStatus.ACTIVE, [
                ('NK-DF-M-B', Decimal('2990'), None, {'Размер': 'M', 'Цвет': 'Чёрный'}),
                ('NK-DF-L-W', Decimal('2990'), Decimal('2490'), {'Размер': 'L', 'Цвет': 'Белый'}),
                ('NK-DF-XL-R', Decimal('2990'), None, {'Размер': 'XL', 'Цвет': 'Красный'}),
            ]),
            ('IKEA MALM Кровать', 5, 11, 'Кровать с подъёмным механизмом и ящиками.', False, ProductStatus.ACTIVE, [
                ('IKEA-MALM-160', Decimal('19990'), Decimal('16990'), {'Размер': 'L', 'Цвет': 'Белый'}),
                ('IKEA-MALM-180', Decimal('24990'), None, {'Размер': 'XL', 'Цвет': 'Чёрный'}),
            ]),
            ('Bosch Перфоратор GBH 2-28', 4, 7, 'Мощный перфоратор SDS-plus для профи.', False, ProductStatus.ACTIVE, [
                ('BOSCH-GBH228', Decimal('12990'), Decimal('10990'), {}),
            ]),
            ('Sony PlayStation 5', 6, 0, 'Игровая консоль нового поколения с SSD.', True, ProductStatus.ACTIVE, [
                ('PS5-DISC', Decimal('49990'), None, {}),
                ('PS5-DIGITAL', Decimal('39990'), Decimal('34990'), {}),
            ]),
            ('Adidas Terrex Free Hiker', 3, 8, 'Трекинговые ботинки с Gore-Tex.', False, ProductStatus.ACTIVE, [
                ('AD-TFH-42', Decimal('18990'), Decimal('15990'), {'Размер': '42', 'Цвет': 'Серый'}),
                ('AD-TFH-44', Decimal('18990'), None, {'Размер': '44', 'Цвет': 'Чёрный'}),
            ]),
        ]

        products = []
        all_variants = []

        for name, brand_idx, cat_idx, desc, featured, status, variants_data in products_data:
            brand = brands[brand_idx % len(brands)]
            cat = leaf_cats[cat_idx % len(leaf_cats)] if leaf_cats else None

            product = Product.objects.create(
                name=name, brand=brand, primary_category=cat,
                description=desc, status=status, is_featured=featured,
            )

            # M2M: категории
            if cat:
                parent_cats = list(cat.get_ancestors()) + [cat]
                product.categories.set(parent_cats)
            # M2M: теги (2-3 случайных)
            product.tags.set(random.sample(tags, min(3, len(tags))))

            for sku, base_price, sale_price, attr_values in variants_data:
                variant = ProductVariant.objects.create(
                    product=product, sku=sku, is_active=True,
                    weight=Decimal('0.50'),
                    length=Decimal('10'), width=Decimal('5'), height=Decimal('2'),
                )

                # EAV
                for attr_name, val_name in attr_values.items():
                    if attr_name in eav and val_name in eav[attr_name]['values']:
                        VariantAttribute.objects.create(
                            variant=variant,
                            attribute=eav[attr_name]['attr'],
                            value=eav[attr_name]['values'][val_name],
                        )

                all_variants.append((variant, base_price, sale_price))

            product.recalculate_prices()
            products.append(product)

        self.stdout.write(f'   📦 Товары: {len(products)}, варианты: {len(all_variants)}')
        return products, all_variants

    # ================================================================
    # 9. ЦЕНЫ + ИСТОРИЯ ЦЕН
    # ================================================================

    def _create_prices_and_history(self, variants):
        """Создать Price (OneToOne) + PriceHistory для каждого варианта."""
        now = timezone.now()
        count_p = 0
        count_h = 0

        for variant, base_price, sale_price in variants:
            _, created = Price.objects.get_or_create(
                variant=variant,
                defaults={'price': base_price, 'sale_price': sale_price, 'currency': 'RUB'},
            )
            if created:
                count_p += 1

            # PriceHistory: 1-2 записи
            PriceHistory.objects.create(
                variant=variant,
                old_price=base_price + Decimal('5000'),
                new_price=base_price,
                old_sale_price=sale_price,
                new_sale_price=sale_price,
                changed_by=None,
                reason='Начальное ценообразование',
            )
            count_h += 1

        self.stdout.write(f'   💰 Цены: {count_p}, история: {count_h}')

    # ================================================================
    # 10. СТОК + ДВИЖЕНИЯ
    # ================================================================

    def _create_stocks_and_movements(self, variants, users):
        """Создать Stock + StockMovement для каждого варианта."""
        count_s = 0
        count_m = 0

        for variant, _, _ in variants:
            qty = random.randint(20, 200)
            reserved = random.randint(0, min(10, qty))
            _, created = Stock.objects.get_or_create(
                variant=variant,
                defaults={'quantity': qty, 'reserved_quantity': reserved, 'low_stock_threshold': 5},
            )
            if created:
                count_s += 1

            stock = variant.stock
            # Движения: поступление + резерв
            StockMovement.objects.create(
                stock=stock, kind='in', delta=qty,
                quantity_before=0, quantity_after=qty,
                performed_by=None, note='Начальное поступление',
            )
            count_m += 1

            if reserved > 0:
                StockMovement.objects.create(
                    stock=stock, kind='reserve', delta=reserved,
                    quantity_before=qty, quantity_after=qty,
                    performed_by=None, note='Резерв для заказа',
                )
                count_m += 1

        self.stdout.write(f'   📦 Сток: {count_s}, движения: {count_m}')

    # ================================================================
    # 11. ДОСТАВКА: ЗОНЫ + МЕТОДЫ
    # ================================================================

    def _create_shipping(self):
        zones_data = [
            ('Москва и МО', 'MSK', ['Москва', 'Московская область']),
            ('Санкт-Петербург и ЛО', 'SPB', ['Санкт-Петербург', 'Ленинградская область']),
            ('Центральная Россия', 'CEN', ['Владимирская обл.', 'Тверская обл.', 'Ярославская обл.']),
            ('Урал', 'URAL', ['Свердловская обл.', 'Челябинская обл.']),
            ('Сибирь', 'SIB', ['Новосибирская обл.', 'Красноярский край']),
            ('Юг', 'SOUTH', ['Краснодарский край', 'Ростовская обл.']),
        ]

        zones = []
        for name, code, regions in zones_data:
            z, _ = ShippingZone.objects.get_or_create(
                zone_code=code,
                defaults={'name': name, 'regions': regions, 'is_active': True},
            )
            zones.append(z)

        methods_data = [
            # (name, type, zone_idx, base, per_kg, free_above, est_min, est_max)
            ('Курьер Standard', 'courier', 0, Decimal('290'), Decimal('30'), Decimal('5000'), 1, 2),
            ('Курьер Express', 'express', 0, Decimal('590'), Decimal('50'), Decimal('10000'), 0, 1),
            ('ПВЗ СДЭК', 'pickup', 0, Decimal('190'), Decimal('0'), Decimal('3000'), 2, 4),
            ('Курьер Standard', 'courier', 1, Decimal('290'), Decimal('30'), Decimal('5000'), 1, 3),
            ('ПВЗ СДЭК', 'pickup', 1, Decimal('190'), Decimal('0'), Decimal('3000'), 2, 5),
            ('Почта России', 'post', 2, Decimal('350'), Decimal('50'), Decimal('0'), 5, 14),
            ('Курьер Standard', 'courier', 3, Decimal('390'), Decimal('40'), Decimal('7000'), 3, 5),
            ('Курьер Standard', 'courier', 4, Decimal('490'), Decimal('50'), Decimal('8000'), 5, 10),
            ('ПВЗ СДЭК', 'pickup', 4, Decimal('290'), Decimal('0'), Decimal('5000'), 4, 8),
            ('Курьер Standard', 'courier', 5, Decimal('350'), Decimal('35'), Decimal('6000'), 2, 5),
        ]

        methods = []
        for i, (name, stype, z_idx, base, per_kg, free_above, est_min, est_max) in enumerate(methods_data):
            m, _ = ShippingMethod.objects.get_or_create(
                name=f'{name} ({zones[z_idx].name})',
                defaults={
                    'shipping_type': stype,
                    'zone': zones[z_idx],
                    'base_price': base,
                    'price_per_kg': per_kg,
                    'free_shipping_threshold': free_above,
                    'estimated_days_min': est_min,
                    'estimated_days_max': est_max,
                    'max_weight_kg': Decimal('30'),
                    'is_active': True,
                    'sort_order': i,
                },
            )
            methods.append(m)

        self.stdout.write(f'   🚚 Зоны: {len(zones)}, методы: {len(methods)}')
        return zones, methods

    # ================================================================
    # 12. СКИДКИ: КАМПАНИИ + КУПОНЫ
    # ================================================================

    def _create_discounts(self):
        now = timezone.now()

        campaigns_data = [
            ('Летняя распродажа', 'Скидки на электронику и одежду', now - timedelta(days=30), now + timedelta(days=30)),
            ('Чёрная пятница', 'Мега-распродажа года', now - timedelta(days=5), now + timedelta(days=2)),
            ('Новогодняя акция', 'Подарки к Новому году', now + timedelta(days=30), now + timedelta(days=60)),
        ]

        campaigns = []
        for name, desc, start, end in campaigns_data:
            c, _ = Campaign.objects.get_or_create(
                name=name,
                defaults={'description': desc, 'is_active': True, 'started_at': start, 'ended_at': end},
            )
            campaigns.append(c)

        coupons_data = [
            # (code, desc, type, value, max_disc, min_order, campaign_idx)
            ('SUMMER20', 'Скидка 20% на всё', 'percent', Decimal('20'), Decimal('10000'), Decimal('3000'), 0),
            ('SUMMER10', 'Скидка 10% на всё', 'percent', Decimal('10'), None, Decimal('1000'), 0),
            ('BF500', 'Скидка 500₽', 'fixed', Decimal('500'), None, Decimal('2000'), 1),
            ('BF1000', 'Скидка 1000₽ при заказе от 5000₽', 'fixed', Decimal('1000'), None, Decimal('5000'), 1),
            ('NEWYEAR15', 'Скидка 15% к Новому году', 'percent', Decimal('15'), Decimal('8000'), Decimal('2000'), 2),
            ('WELCOME500', 'Приветственный бонус 500₽', 'fixed', Decimal('500'), None, Decimal('1000'), 0),
        ]

        coupons = []
        for code, desc, dtype, value, max_disc, min_order, camp_idx in coupons_data:
            camp = campaigns[camp_idx % len(campaigns)]
            c, _ = Coupon.objects.get_or_create(
                code=code,
                defaults={
                    'description': desc, 'discount_type': dtype,
                    'discount_value': value, 'max_discount': max_disc,
                    'min_order_amount': min_order,
                    'max_total_uses': 1000, 'max_uses_per_user': 3,
                    'started_at': camp.started_at, 'ended_at': camp.ended_at,
                    'campaign': camp, 'is_active': True,
                },
            )
            coupons.append(c)

        self.stdout.write(f'   🎫 Кампании: {len(campaigns)}, купоны: {len(coupons)}')
        return campaigns, coupons

    # ================================================================
    # 13. КОРЗИНЫ
    # ================================================================

    def _create_carts(self, users, variants):
        """Создать корзины с товарами для 3 пользователей."""
        cart_users = users[1:4]  # ivan, maria, alex
        count = 0

        for user in cart_users:
            cart, _ = Cart.objects.get_or_create(
                user=user, is_active=True,
                defaults={'session_key_hash': None},
            )
            # 2-3 товара в корзине
            chosen = random.sample(variants, min(3, len(variants)))
            for variant, base_price, sale_price in chosen:
                eff = sale_price if sale_price else base_price
                CartItem.objects.get_or_create(
                    cart=cart, variant=variant,
                    defaults={'quantity': random.randint(1, 3)},
                )
                count += 1

        self.stdout.write(f'   🛒 Корзины: {len(cart_users)}, позиции: {count}')

    # ================================================================
    # 14. ЗАКАЗЫ
    # ================================================================

    def _create_orders(self, users, variants, addresses, coupons):
        """Создать заказы разных статусов для 3 пользователей."""
        now = timezone.now()
        orders = []

        order_configs = [
            # (user_idx, status, items_count, notes)
            (1, 'pending', 2, 'Позвонить перед доставкой'),
            (1, 'confirmed', 1, ''),
            (2, 'delivered', 3, ''),
            (2, 'shipped', 2, 'Доставка до двери'),
            (3, 'processing', 2, ''),
            (3, 'cancelled', 1, 'Передумал'),
            (1, 'delivered', 1, ''),
            (4, 'pending', 2, ''),
        ]

        for user_idx, status, items_count, notes in order_configs:
            if user_idx >= len(users):
                continue
            user = users[user_idx]

            # Адрес
            addr = Address.objects.filter(user=user).first()
            if not addr:
                addr = Address.objects.create(
                    user=user, recipient_name=user.get_full_name() or user.username,
                    country='RU', region='Московская обл.', city='Москва',
                    street='ул. Тестовая, д. 1', postal_code='101000', is_default=True,
                )

            # Создаём заказ
            order = Order.objects.create(
                user=user, status=status,
                recipient_name=addr.recipient_name,
                country=addr.country, region=addr.region,
                city=addr.city, street=addr.street,
                postal_code=addr.postal_code,
                notes=notes,
                subtotal=Decimal('0'), total=Decimal('0'),
            )

            # Товары
            chosen = random.sample(variants, min(items_count, len(variants)))
            subtotal = Decimal('0')
            for variant, base_price, sale_price in chosen:
                eff = sale_price if sale_price else base_price
                qty = random.randint(1, 2)
                OrderItem.objects.create(
                    order=order, variant=variant,
                    product_name=variant.product.name,
                    sku=variant.sku,
                    unit_price=eff, quantity=qty,
                )
                subtotal += eff * qty

            order.subtotal = subtotal
            order.delivery_cost = Decimal('290') if subtotal < Decimal('5000') else Decimal('0')
            order.total = order.subtotal + order.delivery_cost
            if status == 'cancelled':
                order.cancellation_reason = 'changed_mind'
                order.cancelled_at = now
            if status == 'delivered':
                order.delivered_at = now - timedelta(days=random.randint(1, 10))
            if status == 'confirmed':
                order.confirmed_at = now - timedelta(hours=2)
            order.save()

            orders.append(order)

        self.stdout.write(f'   📋 Заказы: {len(orders)}')
        return orders

    # ================================================================
    # 15. ПЛАТЕЖИ
    # ================================================================

    def _create_payments(self, orders, users):
        """Создать платежи для заказов (кроме cancelled)."""
        count = 0
        now = timezone.now()

        for order in orders:
            if order.status == 'cancelled':
                continue

            # Определяем статус платежа по статусу заказа
            if order.status in ('delivered', 'shipped', 'confirmed', 'processing'):
                p_status = 'succeeded'
                p_method = random.choice(['card', 'sbp', 'sberpay'])
            elif order.status == 'pending':
                p_status = 'pending'
                p_method = 'card'
            else:
                p_status = 'pending'
                p_method = 'card'

            payment = Payment.objects.create(
                order=order, user=order.user,
                status=p_status, method=p_method,
                provider='mock',
                amount=order.total,
            )

            # PaymentEvent: created
            PaymentEvent.objects.create(
                payment=payment, event_type='created',
                old_status='', new_status='pending',
            )

            if p_status == 'succeeded':
                payment.paid_at = now - timedelta(hours=random.randint(1, 48))
                payment.save()
                PaymentEvent.objects.create(
                    payment=payment, event_type='status_changed',
                    old_status='pending', new_status='succeeded',
                )

            count += 1

        self.stdout.write(f'   💳 Платежи: {count}')

    # ================================================================
    # 16. ОТПРАВЛЕНИЯ
    # ================================================================

    def _create_shipments(self, orders, users, methods, zones):
        """Создать отправления для отправленных/доставленных заказов."""
        count = 0
        now = timezone.now()

        for order in orders:
            if order.status not in ('shipped', 'delivered', 'processing'):
                continue

            method = methods[0] if methods else None
            if not method:
                continue

            s_status = 'in_transit' if order.status == 'shipped' else 'delivered'

            shipment = Shipment.objects.create(
                order=order, user=order.user, method=method,
                status=s_status,
                shipping_cost=order.delivery_cost,
                weight_kg=Decimal('1.5'),
            )

            if s_status == 'delivered':
                shipment.delivered_at = now - timedelta(days=random.randint(1, 5))
                shipment.shipped_at = now - timedelta(days=random.randint(6, 10))
                shipment.save()

            count += 1

        self.stdout.write(f'   📦 Отправления: {count}')

    # ================================================================
    # 17. ОТЗЫВЫ
    # ================================================================

    def _create_reviews(self, users, products):
        """Создать отзывы на товары."""
        review_texts = [
            ('Отличный товар!', 'Пользуюсь уже месяц — очень доволен. Качество на высоте, рекомендую.'),
            ('Хорошо, но...', 'В целом неплохо, но есть мелкие недочёты. За свои деньги — ок.'),
            ('Превзошёл ожидания', 'Не ожидал такого качества за эту цену. Буду заказывать ещё.'),
            ('Средненько', 'Обычный товар, ничего особенного. Соответствует описанию.'),
            ('Не рекомендую', 'Сломался через неделю. Очень разочарован.'),
        ]

        count = 0
        regular_users = users[1:]  # skip admin

        for product in products[:10]:  # отзывы на первые 10 товаров
            # 1-3 отзыва на товар
            n_reviews = random.randint(1, 3)
            for i in range(n_reviews):
                user = regular_users[i % len(regular_users)]
                rating = random.randint(2, 5)
                title, text = review_texts[random.randint(0, len(review_texts) - 1)]

                _, created = Review.objects.get_or_create(
                    user=user, product=product,
                    defaults={
                        'rating': rating, 'title': title, 'text': text,
                        'verified_purchase': random.choice([True, False]),
                        'is_approved': True,
                        'helpful_yes': random.randint(0, 20),
                        'helpful_no': random.randint(0, 5),
                    },
                )
                if created:
                    count += 1

        self.stdout.write(f'   ⭐ Отзывы: {count}')

    # ================================================================
    # 18. ИЗБРАННОЕ
    # ================================================================

    def _create_wishlists(self, users, variants):
        """Создать списки избранного для пользователей."""
        count = 0

        for user in users[1:]:
            wishlist, _ = Wishlist.objects.get_or_create(user=user)
            # 2-5 товаров в избранном
            chosen = random.sample(variants, min(random.randint(2, 5), len(variants)))
            for variant, _, _ in chosen:
                _, created = WishlistItem.objects.get_or_create(
                    wishlist=wishlist, variant=variant,
                    defaults={'note': '', 'sort_order': count},
                )
                if created:
                    count += 1

        self.stdout.write(f'   ♡  Избранное: {count} позиций')

    # ================================================================
    # 19. УВЕДОМЛЕНИЯ
    # ================================================================

    def _create_notifications(self, users, orders):
        """Создать уведомления для пользователей."""
        count = 0
        now = timezone.now()

        notif_configs = [
            ('order_created', 'Заказ оформлен', 'Ваш заказ успешно создан и ожидает оплаты.'),
            ('order_confirmed', 'Заказ подтверждён', 'Ваш заказ подтверждён и передан в обработку.'),
            ('order_shipped', 'Заказ отправлен', 'Ваш заказ передан в службу доставки.'),
            ('order_delivered', 'Заказ доставлен', 'Ваш заказ успешно доставлен. Спасибо!'),
            ('payment_success', 'Оплата прошла', 'Оплата по вашему заказу успешно проведена.'),
            ('promo', 'Скидка 20%!', 'Используйте промокод SUMMER20 для скидки 20%.'),
            ('system', 'Обновление системы', 'Мы обновили каталог — появились новые товары!'),
            ('review_reply', 'Ответ на отзыв', 'Администратор ответил на ваш отзыв.'),
        ]

        for user in users[1:]:
            # 3-5 уведомлений на пользователя
            n = random.randint(3, 5)
            chosen = random.sample(notif_configs, min(n, len(notif_configs)))
            for ntype, title, body in chosen:
                status = random.choice(['sent', 'read', 'pending'])
                notification = Notification.objects.create(
                    user=user, notification_type=ntype,
                    channel=random.choice(['in_app', 'email', 'push']),
                    title=title, body=body, status=status,
                )
                if status == 'read':
                    notification.read_at = now - timedelta(hours=random.randint(1, 72))
                    notification.save()
                elif status == 'sent':
                    notification.sent_at = now - timedelta(hours=random.randint(1, 48))
                    notification.save()
                count += 1

        self.stdout.write(f'   🔔 Уведомления: {count}')

    # ================================================================
    # 20. АНАЛИТИКА: ПРОСМОТРЫ ТОВАРОВ
    # ================================================================

    def _create_analytics(self, users, products):
        """Создать записи просмотров товаров."""
        count = 0

        for product in products:
            # 5-30 просмотров на товар
            n = random.randint(5, 30)
            for i in range(n):
                user = random.choice(users[1:]) if random.random() > 0.3 else None
                ProductView.objects.create(
                    product=product,
                    user=user,
                    session_key=f'sess_{random.randint(1000, 9999)}' if not user else '',
                    source=random.choice(['catalog', 'search', 'direct', 'recommendation']),
                    ip_address=f'192.168.1.{random.randint(1, 254)}',
                    user_agent='Mozilla/5.0 Test Browser',
                )
                count += 1

        self.stdout.write(f'   📊 Просмотры: {count}')
