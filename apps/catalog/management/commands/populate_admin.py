# ────────────────────────────────────────────────────────────────────────
# apps/catalog/management/commands/populate_admin.py
#
# Полное заполнение ВСЕХ разделов админки.
# Создаёт данные для каждой модели во всех 31 таблице.
#
# Использование:
#   python manage.py populate_admin              — заполнить
#   python manage.py populate_admin --clear      — очистить и заполнить
#
# ВАЖНО: Category использует django-treebeard MP_Node,
#        поэтому создаём через add_root() / add_child(),
#        а НЕ через Category.objects.create().
# ────────────────────────────────────────────────────────────────────────

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

User = get_user_model()


class Command(BaseCommand):
    help = 'Полное заполнение ВСЕХ разделов админки.'

    def add_arguments(self, parser):
        parser.add_argument('--clear', action='store_true', help='Удалить все данные перед заполнением.')

    def handle(self, *args, **options):
        if options['clear']:
            self._clear_all()

        self.stdout.write('\n🚀 Заполнение админки...\n')

        # ── Создание данных по порядку зависимостей ──
        users = self._create_users()
        profiles = self._create_profiles(users)
        addresses = self._create_addresses(users)
        categories = self._create_categories()
        brands = self._create_brands()
        tags = self._create_tags()
        attributes, attr_values = self._create_attributes()
        products, variants = self._create_products(categories, brands, tags, attributes, attr_values)
        prices, price_histories = self._create_prices(variants)
        stocks, stock_movements = self._create_stocks(variants)
        carts, cart_items = self._create_carts(users, variants)
        orders, order_items = self._create_orders(users, variants, addresses)
        payments, payment_events = self._create_payments(orders, users)
        campaigns, coupons = self._create_campaigns_and_coupons()
        zones, methods = self._create_shipping()
        shipments = self._create_shipments(orders, methods, users)
        reviews, review_images, helpful_votes = self._create_reviews(users, products)
        wishlists, wishlist_items = self._create_wishlists(users, variants)
        notifications = self._create_notifications(users, orders)
        product_views = self._create_product_views(users, products)

        total = (
            len(users) + len(profiles) + len(addresses) +
            len(categories) + len(brands) + len(tags) +
            len(attributes) + len(attr_values) +
            len(products) + len(variants) +
            len(prices) + len(price_histories) +
            len(stocks) + len(stock_movements) +
            len(carts) + len(cart_items) +
            len(orders) + len(order_items) +
            len(payments) + len(payment_events) +
            len(campaigns) + len(coupons) +
            len(zones) + len(methods) + len(shipments) +
            len(reviews) + len(review_images) + len(helpful_votes) +
            len(wishlists) + len(wishlist_items) +
            len(notifications) + len(product_views)
        )
        self.stdout.write(self.style.SUCCESS(f'\n✅ Готово! Создано {total} записей в 31 таблице.'))

    # ==============================================================
    # Очистка (в порядке зависимостей — сначала зависимые)
    # ==============================================================
    def _clear_all(self):
        self.stdout.write('🗑️  Очистка всех данных...')
        from apps.analytics.models import ProductView
        from apps.notifications.models import Notification
        from apps.reviews.models import ReviewHelpfulVote, ReviewImage, Review
        from apps.wishlist.models import WishlistItem, Wishlist
        from apps.payments.models import PaymentEvent, Payment
        from apps.shipping.models import Shipment
        from apps.orders.models import OrderItem, Order
        from apps.discounts.models import Coupon, Campaign
        from apps.cart.models import CartItem, Cart
        from apps.inventory.models import StockMovement, Stock
        from apps.pricing.models import PriceHistory, Price
        from apps.catalog.models import (
            VariantAttribute, ProductImage, ProductVariant, Product,
            AttributeValue, Attribute, Tag, Brand, Category,
        )
        from apps.users.models import Address, UserProfile
        from apps.shipping.models import ShippingMethod, ShippingZone

        ProductView.objects.all().delete()
        Notification.objects.all().delete()
        ReviewHelpfulVote.objects.all().delete()
        ReviewImage.objects.all().delete()
        Review.objects.all().delete()
        WishlistItem.objects.all().delete()
        Wishlist.objects.all().delete()
        PaymentEvent.objects.all().delete()
        Payment.objects.all().delete()
        Shipment.objects.all().delete()
        OrderItem.objects.all().delete()
        Order.objects.all().delete()
        Coupon.objects.all().delete()
        Campaign.objects.all().delete()
        CartItem.objects.all().delete()
        Cart.objects.all().delete()
        StockMovement.objects.all().delete()
        Stock.objects.all().delete()
        PriceHistory.objects.all().delete()
        Price.objects.all().delete()
        VariantAttribute.objects.all().delete()
        ProductImage.objects.all().delete()
        ProductVariant.objects.all().delete()
        Product.objects.all().delete()
        AttributeValue.objects.all().delete()
        Attribute.objects.all().delete()
        Tag.objects.all().delete()
        Brand.objects.all().delete()
        Category.objects.all().delete()
        Address.objects.all().delete()
        UserProfile.objects.all().delete()
        ShippingMethod.objects.all().delete()
        ShippingZone.objects.all().delete()
        User.objects.all().delete()
        self.stdout.write('  Очищено.\n')

    # ==============================================================
    # Пользователи
    # User: username, email, phone, first_name, last_name,
    #       is_staff, is_superuser, is_active, password
    # ==============================================================
    def _create_users(self):
        self.stdout.write('  👤 Пользователи...')
        data = [
            ('admin@shop.ru', 'admin12345', 'Админ', 'Админов', True, True, '+7-900-000-0001'),
            ('ivan@shop.ru', 'Test12345!', 'Иван', 'Иванов', False, False, '+7-900-111-1111'),
            ('maria@shop.ru', 'Test12345!', 'Мария', 'Петрова', False, False, '+7-900-222-2222'),
            ('alexey@shop.ru', 'Test12345!', 'Алексей', 'Сидоров', False, False, '+7-900-333-3333'),
            ('olga@shop.ru', 'Test12345!', 'Ольга', 'Козлова', False, False, '+7-900-444-4444'),
            ('dmitry@shop.ru', 'Test12345!', 'Дмитрий', 'Новиков', False, False, '+7-900-555-5555'),
            ('anna@shop.ru', 'Test12345!', 'Анна', 'Морозова', False, False, '+7-900-666-6666'),
            ('sergey@shop.ru', 'Test12345!', 'Сергей', 'Волков', False, False, '+7-900-777-7777'),
        ]
        users = []
        for email, pw, fn, ln, is_staff, is_su, phone in data:
            u, _ = User.objects.get_or_create(
                email=email,
                defaults={
                    'username': email.split('@')[0],
                    'first_name': fn,
                    'last_name': ln,
                    'is_staff': is_staff,
                    'is_superuser': is_su,
                    'is_active': True,
                    'phone': phone,
                },
            )
            u.set_password(pw)
            u.save()
            users.append(u)
        return users

    # ==============================================================
    # Профили
    # UserProfile: user, gender, language, timezone,
    #              date_of_birth, email_subscribed, avatar
    # ==============================================================
    def _create_profiles(self, users):
        self.stdout.write('  🪪 Профили...')
        from apps.users.models import UserProfile
        genders = ['M', 'F', 'O', '', 'F', 'M', 'F', 'M']
        langs = ['ru', 'ru', 'en', 'ru', 'ru', 'en', 'ru', 'ru']
        tzones = [
            'Europe/Moscow', 'Europe/Moscow', 'America/New_York',
            'Asia/Yekaterinburg', 'Europe/Berlin', 'Europe/Moscow',
            'Asia/Novosibirsk', 'Europe/Moscow',
        ]
        dob = timezone.now().date() - timedelta(days=365 * 25)
        profiles = []
        for i, u in enumerate(users):
            p, _ = UserProfile.objects.get_or_create(
                user=u,
                defaults={
                    'gender': genders[i % len(genders)],
                    'language': langs[i % len(langs)],
                    'timezone': tzones[i % len(tzones)],
                    'date_of_birth': dob - timedelta(days=365 * (i * 3)),
                    'email_subscribed': i % 2 == 0,
                },
            )
            profiles.append(p)
        return profiles

    # ==============================================================
    # Адреса
    # Address: user, recipient_name, country, region, city,
    #          street, postal_code, notes, is_default
    # ==============================================================
    def _create_addresses(self, users):
        self.stdout.write('  🏠 Адреса...')
        from apps.users.models import Address
        addresses = []
        addr_data = [
            ('Иван Иванов', 'Россия', 'Московская обл.', 'Москва', 'ул. Ленина, д. 10, кв. 5', '101000', 'Код домофона 12К'),
            ('Мария Петрова', 'Россия', '', 'Санкт-Петербург', 'Невский пр-т, д. 28, кв. 15', '190000', ''),
            ('Алексей Сидоров', 'Россия', 'Свердловская обл.', 'Екатеринбург', 'ул. Мира, д. 55', '620000', '3-й подъезд'),
            ('Ольга Козлова', 'Россия', '', 'Новосибирск', 'пр-т Строителей, д. 7', '630000', ''),
            ('Дмитрий Новиков', 'Россия', 'Краснодарский край', 'Краснодар', 'ул. Красная, д. 100', '350000', ''),
            ('Анна Морозова', 'Россия', 'Татарстан', 'Казань', 'ул. Баумана, д. 33, кв. 12', '420000', ''),
            ('Сергей Волков', 'Россия', '', 'Нижний Новгород', 'ул. Большая Покровская, д. 8', '603000', 'Офис 301'),
        ]
        for i, (rn, country, region, city, street, postal, notes) in enumerate(addr_data):
            user = users[(i % (len(users) - 1)) + 1]
            a = Address.objects.create(
                user=user, recipient_name=rn, country=country,
                region=region, city=city, street=street,
                postal_code=postal, notes=notes, is_default=(i == 0),
            )
            addresses.append(a)
        return addresses

    # ==============================================================
    # Категории (django-treebeard MP_Node)
    # Category: name, slug, description, is_active (default=True)
    # ⚠️  НЕЛЬЗЯ Category.objects.create() — только add_root/add_child!
    # ==============================================================
    def _create_categories(self):
        self.stdout.write('  📂 Категории...')
        from apps.catalog.models import Category
        roots = [
            ('Электроника', 'elektronika', 'Электроника и гаджеты'),
            ('Одежда', 'odezhda', 'Одежда и обувь'),
            ('Дом и сад', 'dom-i-sad', 'Товары для дома'),
            ('Спорт', 'sport', 'Спортивные товары'),
        ]
        children_map = {
            'Электроника': ['Смартфоны', 'Ноутбуки', 'Аудио'],
            'Одежда': ['Мужская', 'Женская', 'Детская'],
            'Дом и сад': ['Мебель', 'Инструменты', 'Декор'],
            'Спорт': ['Фитнес', 'Туризм', 'Велоспорт'],
        }
        categories = []
        for name, slug, desc in roots:
            root = Category.add_root(name=name, slug=slug, description=desc)
            categories.append(root)
            for ch_name in children_map.get(name, []):
                ch = root.add_child(
                    name=ch_name,
                    slug=f'{slug}-{ch_name.lower()}',
                    description=f'{ch_name} — {name}',
                )
                categories.append(ch)
                for gc_name in ['Популярное', 'Новинки']:
                    gc = ch.add_child(
                        name=f'{ch_name} — {gc_name}',
                        slug=f'{slug}-{ch_name.lower()}-{gc_name.lower()}',
                        description=f'{gc_name} в {ch_name}',
                    )
                    categories.append(gc)
        return categories

    # ==============================================================
    # Бренды
    # Brand: name, slug, description, is_active
    # (нет поля country_code!)
    # ==============================================================
    def _create_brands(self):
        self.stdout.write('  🏷️  Бренды...')
        from apps.catalog.models import Brand
        brands = []
        brand_data = [
            ('Samsung', 'Бренд Samsung — лидер электроники'),
            ('Apple', 'Бренд Apple — премиум-устройства'),
            ('Xiaomi', 'Бренд Xiaomi — доступные гаджеты'),
            ('Sony', 'Бренд Sony — развлечения и аудио'),
            ('Bosch', 'Бренд Bosch — профессиональный инструмент'),
            ('Nike', 'Бренд Nike — спортивная одежда и обувь'),
            ('IKEA', 'Бренд IKEA — мебель и дом'),
            ('Philips', 'Бренд Philips — здоровье и свет'),
        ]
        for name, desc in brand_data:
            b = Brand.objects.create(
                name=name, slug=name.lower(),
                description=desc, is_active=True,
            )
            brands.append(b)
        return brands

    # ==============================================================
    # Теги
    # Tag: name, slug, is_active
    # ==============================================================
    def _create_tags(self):
        self.stdout.write('  🏷️  Теги...')
        from apps.catalog.models import Tag
        tags = []
        for name in ['Хит', 'Новинка', 'Скидка', 'Премиум', 'Эксклюзив', 'Бестселлер', 'Рекомендуем']:
            tags.append(Tag.objects.create(name=name, slug=name.lower(), is_active=True))
        return tags

    # ==============================================================
    # Атрибуты + значения
    # Attribute: name, slug, description
    #   (нет поля attribute_type!)
    # AttributeValue: attribute, value, color_hex
    #   (нет поля slug!)
    # ==============================================================
    def _create_attributes(self):
        self.stdout.write('  📐 Атрибуты...')
        from apps.catalog.models import Attribute, AttributeValue
        attrs_data = [
            ('Цвет', 'color', 'Цвет товара', ['Чёрный', 'Белый', 'Серый', 'Синий', 'Красный', 'Зелёный']),
            ('Размер', 'size', 'Размер товара', ['S', 'M', 'L', 'XL', 'XXL']),
            ('Объём памяти', 'storage', 'Объём встроенной памяти', ['64 ГБ', '128 ГБ', '256 ГБ', '512 ГБ', '1 ТБ']),
            ('Материал', 'material', 'Материал корпуса', ['Алюминий', 'Пластик', 'Стекло', 'Кожа', 'Ткань']),
            ('Вес', 'weight', 'Вес товара', []),
            ('Диагональ экрана', 'screen', 'Диагональ экрана в дюймах', []),
        ]
        # color_hex для основных цветов
        color_map = {
            'Чёрный': '#000000', 'Белый': '#FFFFFF', 'Серый': '#808080',
            'Синий': '#0000FF', 'Красный': '#FF0000', 'Зелёный': '#008000',
        }
        attributes, attr_values = [], []
        for name, slug, desc, vals in attrs_data:
            a = Attribute.objects.create(name=name, slug=slug, description=desc)
            attributes.append(a)
            for v in vals:
                hex_val = color_map.get(v, '')
                av = AttributeValue.objects.create(
                    attribute=a, value=v, color_hex=hex_val,
                )
                attr_values.append(av)
        return attributes, attr_values

    # ==============================================================
    # Товары + варианты
    # Product: name, slug, description, primary_category (FK),
    #          brand (FK), status, is_featured, rating,
    #          reviews_count, views_count
    #   (нет short_description!)
    #   categories — M2M, tags — M2M
    #
    # ProductVariant: product, sku, barcode, is_active, weight
    #   (нет price, sale_price, attributes-словаря!)
    #
    # ProductImage: product, image, alt, is_main, order
    #   (alt_text → alt, sort_order → order)
    #
    # VariantAttribute: variant, attribute (FK→Attribute),
    #                   value (FK→AttributeValue)
    #   (нет attribute_value — два отдельных FK!)
    # ==============================================================
    def _create_products(self, categories, brands, tags, attributes, attr_values):
        self.stdout.write('  📦 Товары + варианты...')
        from apps.catalog.models import Product, ProductVariant, ProductImage, VariantAttribute

        color_attr = attributes[0]   # Цвет
        storage_attr = attributes[2]  # Объём памяти
        colors = [av for av in attr_values if av.attribute == color_attr]
        storages = [av for av in attr_values if av.attribute == storage_attr]

        products, variants = [], []
        prod_data = [
            ('Samsung Galaxy S24 Ultra', 'samsung-galaxy-s24-ultra', 'Флагманский смартфон Samsung с S Pen и камерой 200 МП.', 149990),
            ('iPhone 15 Pro Max', 'iphone-15-pro-max', 'Топовый iPhone с чипом A17 Pro и титановым корпусом.', 159990),
            ('Xiaomi 14 Pro', 'xiaomi-14-pro', 'Флагман Xiaomi с камерой Leica и Snapdragon 8 Gen 3.', 79990),
            ('MacBook Pro 16"', 'macbook-pro-16', 'Профессиональный ноутбук Apple с M3 Pro.', 249990),
            ('Sony WH-1000XM5', 'sony-wh-1000xm5', 'Беспроводные наушники с лучшим шумоподавлением.', 29990),
            ('Samsung 65" QLED', 'samsung-65-qled', '65-дюймовый QLED-телевизор Samsung.', 89990),
            ('Nike Air Max 90', 'nike-air-max-90', 'Культовые кроссовки Nike с видимой воздушной подушкой.', 12990),
            ('IKEA KALLAX', 'ikea-kallax', 'Система хранения KALLAX — стиль и функциональность.', 9990),
            ('Bosch Professional Drill', 'bosch-professional-drill', 'Профессиональный перфоратор Bosch.', 15990),
            ('Philips Hue Starter Kit', 'philips-hue-starter', 'Набор умного освещения Philips Hue.', 9990),
            ('PlayStation 5', 'playstation-5', 'Игровая консоль нового поколения от Sony.', 49990),
            ('Dyson V15 Detect', 'dyson-v15-detect', 'Беспроводной пылесос с лазерным обнаружением пыли.', 59990),
            ('Kindle Paperwhite', 'kindle-paperwhite', 'Электронная книга Amazon с экраном 6.8".', 14990),
            ('GoPro Hero 12', 'gopro-hero-12', 'Экшн-камера GoPro с 5.3K видео.', 34990),
            ('Canon EOS R6 Mark II', 'canon-eos-r6-ii', 'Полнокадровая беззеркальная камера Canon.', 189990),
        ]
        for i, (name, slug, desc, base_price) in enumerate(prod_data):
            cat = categories[i % len(categories)]
            brand = brands[i % len(brands)]
            p = Product.objects.create(
                name=name, slug=slug, description=desc,
                primary_category=cat, brand=brand,
                status='active', is_featured=(i < 5),
                rating=Decimal('0.00'), reviews_count=0,
                views_count=i * 20 + 10,
            )
            # M2M: categories и tags
            p.categories.add(cat)
            p.tags.set([tags[i % len(tags)], tags[(i + 1) % len(tags)]])
            products.append(p)

            # ── Вариант товара (без price/sale_price — они в Price модели) ──
            color = colors[i % len(colors)]
            storage = storages[i % len(storages)] if storages else None
            v = ProductVariant.objects.create(
                product=p,
                sku=f'{slug.upper()[:8]}-{i + 1:03d}',
                barcode=f'460{p.pk:010d}',
                is_active=True,
                weight=Decimal('0.5'),
            )
            # ── VariantAttribute: variant + attribute (FK) + value (FK) ──
            VariantAttribute.objects.create(variant=v, attribute=color_attr, value=color)
            if storage:
                VariantAttribute.objects.create(variant=v, attribute=storage_attr, value=storage)
            variants.append(v)

            # ── Изображение (ProductImage: alt, order — НЕ alt_text, sort_order!) ──
            # ImageField требует путь относительно MEDIA_ROOT
            ProductImage.objects.create(
                product=p, image=f'products/{slug}.jpg',
                alt=name, is_main=True, order=0,
            )
        return products, variants

    # ==============================================================
    # Цены
    # Price: variant (OneToOne), price, sale_price, currency
    #   (нет effective_price, cost_price!)
    #
    # PriceHistory: variant (FK), old_price, new_price,
    #              old_sale_price, new_sale_price, reason
    #   (FK на variant, НЕ на price! change_reason → reason)
    # ==============================================================
    def _create_prices(self, variants):
        self.stdout.write('  💰 Цены...')
        from apps.pricing.models import Price, PriceHistory
        prices, histories = [], []
        for v in variants:
            # base_price из варианта — достаём из первого OrderItem-подобного значения
            # (вариант не хранит цену, используем вычисленную)
            base = Decimal('9990') + Decimal(str(v.pk * 1000))
            sale = (base * Decimal('0.9')).quantize(Decimal('1')) if v.pk % 3 == 0 else None
            p = Price.objects.create(
                variant=v,
                price=base,
                sale_price=sale,
                currency='RUB',
            )
            prices.append(p)
            histories.append(PriceHistory.objects.create(
                variant=v,
                old_price=base + Decimal('1000'),
                new_price=base,
                old_sale_price=None,
                new_sale_price=sale,
                reason='Начальное ценообразование',
            ))
        return prices, histories

    # ==============================================================
    # Склад
    # Stock: variant (OneToOne), quantity, reserved_quantity,
    #        low_stock_threshold
    #   (reserved → reserved_quantity!)
    #
    # StockMovement: stock (FK), kind (НЕ movement_type!),
    #               delta (НЕ quantity!), quantity_before,
    #               quantity_after, note (НЕ reason!)
    #   (нет поля reference!)
    # ==============================================================
    def _create_stocks(self, variants):
        self.stdout.write('  📦 Склад...')
        from apps.inventory.models import Stock, StockMovement
        stocks, movements = [], []
        for v in variants:
            qty = 50 + hash(v.sku) % 200
            s = Stock.objects.create(
                variant=v,
                quantity=qty,
                reserved_quantity=0,
                low_stock_threshold=5,
            )
            stocks.append(s)
            movements.append(StockMovement.objects.create(
                stock=s,
                kind='in',
                delta=qty,
                quantity_before=0,
                quantity_after=qty,
                note='Начальное поступление',
            ))
        return stocks, movements

    # ==============================================================
    # Корзины
    # Cart: user, session_key_hash, is_active
    # CartItem: cart, variant, quantity
    # ==============================================================
    def _create_carts(self, users, variants):
        self.stdout.write('  🛒 Корзины...')
        from apps.cart.models import Cart, CartItem
        carts, items = [], []
        for u in users[1:4]:
            c, _ = Cart.objects.get_or_create(
                user=u,
                defaults={'session_key_hash': None, 'is_active': True},
            )
            carts.append(c)
            for v in variants[:2]:
                ci, created = CartItem.objects.get_or_create(
                    cart=c, variant=v, defaults={'quantity': 1},
                )
                if created:
                    items.append(ci)
        return carts, items

    # ==============================================================
    # Заказы
    # Order: status, user, recipient_name, country, region,
    #        city, street, postal_code, subtotal, delivery_cost,
    #        discount, total, notes, confirmed_at, delivered_at
    #   (order_number генерируется автоматически в save())
    # OrderItem: order, variant, product_name, sku, unit_price, quantity
    # ==============================================================
    def _create_orders(self, users, variants, addresses):
        self.stdout.write('  📋 Заказы...')
        from apps.orders.models import Order, OrderItem
        now = timezone.now()
        orders, order_items = [], []
        statuses = [
            'pending', 'confirmed', 'processing',
            'shipped', 'delivered', 'cancelled',
            'delivered', 'confirmed',
        ]
        for i, u in enumerate(users[1:]):
            addr = addresses[i % len(addresses)] if addresses else None
            st = statuses[i % len(statuses)]
            v1, v2 = variants[i % len(variants)], variants[(i + 1) % len(variants)]

            # Вычисляем цену из связанной модели Price
            p1 = getattr(v1, 'price', None)
            p2 = getattr(v2, 'price', None)
            price1 = p1.price if p1 else Decimal('10000')
            price2 = p2.price if p2 else Decimal('8000')

            subtotal = price1 * 2 + price2
            delivery = Decimal('290.00')
            o = Order.objects.create(
                status=st,
                user=u,
                recipient_name=addr.recipient_name if addr else u.full_name,
                country=addr.country if addr else 'Россия',
                region=addr.region if addr else '',
                city=addr.city if addr else 'Москва',
                street=addr.street if addr else 'ул. Тестовая, д. 1',
                postal_code=addr.postal_code if addr else '101000',
                subtotal=subtotal,
                delivery_cost=delivery,
                discount=Decimal('0.00'),
                total=subtotal + delivery,
                notes=f'Заказ #{i + 1} от {u.email}',
                confirmed_at=now - timedelta(days=3) if st in ('confirmed', 'processing', 'shipped', 'delivered') else None,
                delivered_at=now - timedelta(days=1) if st == 'delivered' else None,
            )
            orders.append(o)
            order_items.append(OrderItem.objects.create(
                order=o, variant=v1,
                product_name=v1.product.name, sku=v1.sku,
                unit_price=price1, quantity=2,
            ))
            order_items.append(OrderItem.objects.create(
                order=o, variant=v2,
                product_name=v2.product.name, sku=v2.sku,
                unit_price=price2, quantity=1,
            ))
        return orders, order_items

    # ==============================================================
    # Платежи
    # Payment: order, user, status, provider, method (НЕ payment_method!),
    #          amount, external_id
    #   (order_number генерируется автоматически)
    #
    # PaymentEvent: payment, event_type, new_status, payload (НЕ data!)
    # ==============================================================
    def _create_payments(self, orders, users):
        self.stdout.write('  💳 Платежи...')
        from apps.payments.models import Payment, PaymentEvent
        from apps.payments.constants import PAYMENT_STATUS_SUCCEEDED
        payments, events = [], []
        for o in orders:
            p = Payment.objects.create(
                order=o,
                user=o.user,
                amount=o.total,
                status=PAYMENT_STATUS_SUCCEEDED,
                provider='mock',
                method='card',
                external_id=f'mock-{o.order_number}',
            )
            payments.append(p)
            events.append(PaymentEvent.objects.create(
                payment=p,
                event_type='succeeded',
                new_status=PAYMENT_STATUS_SUCCEEDED,
                payload={'message': 'Оплата прошла успешно'},
            ))
        return payments, events

    # ==============================================================
    # Кампании + купоны
    # Campaign: name, description, is_active, started_at, ended_at
    # Coupon: code, discount_type, discount_value, max_discount,
    #         campaign, min_order_amount, max_total_uses,
    #         max_uses_per_user, started_at, ended_at, is_active
    # ==============================================================
    def _create_campaigns_and_coupons(self):
        self.stdout.write('  🎫 Кампании + купоны...')
        from apps.discounts.models import Campaign, Coupon
        now = timezone.now()
        campaigns, coupons = [], []
        for name, sd, ed in [
            ('Чёрная пятница 2026', -30, 30),
            ('Новогодние скидки', -10, 60),
            ('Летняя распродажа', 0, 90),
        ]:
            campaigns.append(Campaign.objects.create(
                name=name, description=f'Кампания «{name}»',
                is_active=True,
                started_at=now + timedelta(days=sd),
                ended_at=now + timedelta(days=ed),
            ))
        coupon_data = [
            ('BF20', 'percent', Decimal('20'), campaigns[0], Decimal('5000')),
            ('BF5000', 'fixed', Decimal('5000'), campaigns[0], None),
            ('NY10', 'percent', Decimal('10'), campaigns[1], Decimal('3000')),
            ('NY3000', 'fixed', Decimal('3000'), campaigns[1], None),
            ('SUMMER15', 'percent', Decimal('15'), campaigns[2], Decimal('4000')),
            ('WELCOME5', 'percent', Decimal('5'), None, Decimal('1000')),
        ]
        for code, dtype, dval, camp, max_d in coupon_data:
            coupons.append(Coupon.objects.create(
                code=code, discount_type=dtype, discount_value=dval,
                max_discount=max_d, campaign=camp,
                min_order_amount=Decimal('1000.00'),
                max_total_uses=1000, max_uses_per_user=3,
                started_at=now - timedelta(days=5),
                ended_at=now + timedelta(days=60),
                is_active=True,
            ))
        return campaigns, coupons

    # ==============================================================
    # Доставка
    # ShippingZone: name, zone_code, regions, is_active
    # ShippingMethod: name, shipping_type, zone, base_price,
    #   price_per_kg, free_shipping_threshold, max_shipping_cost,
    #   estimated_days_min, estimated_days_max, max_weight_kg,
    #   sort_order, is_active, pickup_address
    # ==============================================================
    def _create_shipping(self):
        self.stdout.write('  🚚 Доставка...')
        from apps.shipping.models import ShippingZone, ShippingMethod
        zones, methods = [], []
        for name, code, regions in [
            ('Москва и МО', 'msk', ['Москва', 'Московская область']),
            ('Центральная Россия', 'central', ['Тульская обл.', 'Калужская обл.']),
            ('Северо-Запад', 'northwest', ['Санкт-Петербург', 'Ленинградская область']),
        ]:
            zones.append(ShippingZone.objects.create(
                name=name, zone_code=code, regions=regions, is_active=True,
            ))
        method_data = [
            ('Курьер Москва', 'courier', zones[0], Decimal('290'), Decimal('50'), Decimal('5000'), None, 1, 3, Decimal('30'), 10),
            ('Самовывоз Москва', 'pickup', zones[0], Decimal('0'), Decimal('0'), Decimal('0'), None, 0, 1, Decimal('30'), 20),
            ('Почта Россия', 'post', zones[1], Decimal('350'), Decimal('80'), Decimal('8000'), Decimal('1500'), 3, 14, Decimal('20'), 30),
            ('Курьер СПб', 'courier', zones[2], Decimal('350'), Decimal('60'), Decimal('6000'), None, 1, 4, Decimal('30'), 10),
        ]
        for name, stype, zone, bp, pkg, free, maxc, dmin, dmax, mw, so in method_data:
            methods.append(ShippingMethod.objects.create(
                name=name, shipping_type=stype, zone=zone,
                base_price=bp, price_per_kg=pkg,
                free_shipping_threshold=free,
                max_shipping_cost=maxc,
                estimated_days_min=dmin, estimated_days_max=dmax,
                max_weight_kg=mw, sort_order=so, is_active=True,
                pickup_address='г. Москва, ул. Примерная, д. 1' if stype == 'pickup' else '',
            ))
        return zones, methods

    # ==============================================================
    # Отправления
    # Shipment: order (OneToOne), user, method (НЕ shipping_method!),
    #           status, tracking_number, shipping_cost,
    #           shipped_at, delivered_at
    #   (нет estimated_delivery! есть shipping_cost, user!)
    # ==============================================================
    def _create_shipments(self, orders, methods, users):
        self.stdout.write('  📦 Отправления...')
        from apps.shipping.models import Shipment
        now = timezone.now()
        shipments = []
        for o in orders:
            if o.status in ('shipped', 'delivered'):
                shipments.append(Shipment.objects.create(
                    order=o,
                    user=o.user,
                    method=methods[0],
                    tracking_number=f'RF{o.pk:010d}',
                    status='in_transit' if o.status == 'shipped' else 'delivered',
                    shipping_cost=Decimal('290.00'),
                    shipped_at=now - timedelta(days=2),
                    delivered_at=now - timedelta(days=1) if o.status == 'delivered' else None,
                ))
        return shipments

    # ==============================================================
    # Отзывы + голоса + фото
    # Review: user, product, rating, title, text,
    #         verified_purchase, is_approved, helpful_yes, helpful_no
    # ReviewImage: review, image, alt_text, sort_order
    # ReviewHelpfulVote: user, review, vote
    # ==============================================================
    def _create_reviews(self, users, products):
        self.stdout.write('  ⭐ Отзывы...')
        from apps.reviews.models import Review, ReviewHelpfulVote, ReviewImage
        reviews, review_images, helpful_votes = [], [], []
        review_data = [
            (5, 'Превосходно!', 'Пользуюсь уже полгода — работает без нареканий. Качество сборки на высоте, материалы премиальные. Рекомендую всем!'),
            (4, 'Хороший товар', 'В целом доволен, но есть мелкие недочёты. Например, упаковка могла бы быть лучше. В остальном — отлично.'),
            (3, 'Нормально', 'Средний товар за свои деньги. Ничего особенного, но и плохого мало. Подойдёт для базовых задач.'),
            (2, 'Не очень', 'Не оправдал ожиданий. Дороговато для такого качества. Громоздкий и неудобный в использовании.'),
            (1, 'Ужасно', 'Сломался через неделю после покупки. Очень разочарован, не рекомендую никому. Обращаюсь за возвратом.'),
            (5, 'Лучший выбор', 'Сравнивал с конкурентами — этот выигрывает по всем параметрам. Стоит каждой потраченной копейки!'),
            (4, 'Рекомендую', 'Отличное соотношение цена/качество. Покупкой доволен, доставка быстрая. Буду заказывать ещё.'),
            (3, 'Средненько', 'Работает, но фишки из рекламы не оправдались. За эту цену можно было что-то получше найти.'),
            (5, 'Идеально', 'Превзошёл все ожидания! Удобный, красивый, функциональный. Пять звёзд без колебаний.'),
            (4, 'Твёрдая четвёрка', 'Хороший продукт с парой шероховатостей. Если доработают софт — будет пять звёзд.'),
            (2, 'Разочарован', 'Проблемы с подключением, поддержка не отвечает. Вернул через два дня, слишком много проблем с совместимостью.'),
            (5, 'Супер!', 'Купил жене в подарок — она в восторге! Качество отличное, дизайн современный. Рекомендую как подарок.'),
        ]
        for i, (rating, title, text) in enumerate(review_data):
            u = users[(i % (len(users) - 1)) + 1]
            p = products[i % len(products)]
            if Review.objects.filter(user=u, product=p).exists():
                continue
            r = Review.objects.create(
                user=u, product=p,
                rating=rating, title=title, text=text,
                verified_purchase=(i % 3 == 0),
                is_approved=True,
                helpful_yes=i * 2, helpful_no=i,
            )
            reviews.append(r)
            # ── Голос за полезность ──
            voter = users[(i + 2) % len(users)]
            if voter.pk != u.pk:
                helpful_votes.append(ReviewHelpfulVote.objects.create(
                    user=voter, review=r,
                    vote='yes' if i % 2 == 0 else 'no',
                ))
            # ── Фото к отзыву ──
            if i % 3 == 0:
                review_images.append(ReviewImage.objects.create(
                    review=r,
                    image=f'reviews/review_{r.pk}.jpg',
                    alt_text=f'Фото к отзыву #{r.pk}',
                    sort_order=0,
                ))
        return reviews, review_images, helpful_votes

    # ==============================================================
    # Избранное
    # Wishlist: user, items_count
    # WishlistItem: wishlist, variant, note, sort_order
    # ==============================================================
    def _create_wishlists(self, users, variants):
        self.stdout.write('  ❤️  Избранное...')
        from apps.wishlist.models import Wishlist, WishlistItem
        wishlists, items = [], []
        for u in users[1:5]:
            wl, _ = Wishlist.objects.get_or_create(
                user=u, defaults={'items_count': 0},
            )
            wishlists.append(wl)
            for j, v in enumerate(variants[:3]):
                wi, created = WishlistItem.objects.get_or_create(
                    wishlist=wl, variant=v,
                    defaults={
                        'note': f'Хочу купить {v.product.name}' if j == 0 else '',
                        'sort_order': j,
                    },
                )
                if created:
                    items.append(wi)
            wl.items_count = WishlistItem.objects.filter(wishlist=wl).count()
            wl.save(update_fields=['items_count'])
        return wishlists, items

    # ==============================================================
    # Уведомления
    # Notification: user, notification_type, channel (default='in_app'),
    #               title, body (НЕ message!), status,
    #               related_object_type, related_object_id,
    #               action_url, sent_at, read_at
    # ==============================================================
    def _create_notifications(self, users, orders):
        self.stdout.write('  🔔 Уведомления...')
        from apps.notifications.models import Notification
        now = timezone.now()
        notifications = []
        ntypes = ['order_confirmed', 'order_shipped', 'review_reply', 'promo', 'welcome', 'price_drop']
        titles = ['Заказ подтверждён', 'Заказ отправлен', 'Ответ на отзыв', 'Специальное предложение', 'Добро пожаловать!', 'Снижение цены']
        for i, u in enumerate(users[1:]):
            for j in range(4):
                notifications.append(Notification.objects.create(
                    user=u,
                    notification_type=ntypes[j % len(ntypes)],
                    channel='in_app',
                    title=titles[j % len(titles)],
                    body=f'Уведомление #{j + 1} для {u.email}',
                    status='read' if j < 2 else 'pending',
                    related_object_type='order' if j < 2 else '',
                    related_object_id=orders[i % len(orders)].pk if orders and j < 2 else None,
                    action_url=f'/orders/{orders[i % len(orders)].order_number}' if orders and j < 2 else '',
                    sent_at=now - timedelta(hours=j + 1),
                    read_at=now - timedelta(hours=j) if j < 2 else None,
                ))
        return notifications

    # ==============================================================
    # Просмотры товаров
    # ProductView: product, user, session_key, source,
    #              ip_address, user_agent
    # ==============================================================
    def _create_product_views(self, users, products):
        self.stdout.write('  👁️  Просмотры...')
        from apps.analytics.models import ProductView
        views = []
        sources = ['direct', 'search', 'social', 'referral', 'organic']
        for p in products:
            for i in range(5):
                views.append(ProductView.objects.create(
                    product=p,
                    user=users[(i + 1) % len(users)] if i < len(users) - 1 else None,
                    session_key=f'sess_{p.pk}_{i}' if i >= len(users) - 1 else '',
                    source=sources[i % len(sources)],
                    ip_address=f'192.168.{i}.{p.pk % 256}',
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0',
                ))
        return views
