# ────────────────────────────────────────────────────────────
# Сериализаторы товаров (Product).
#
# ТРИ ТИПА СЕРИАЛИЗАТОРОВ:
#   1. OUTPUT (ModelSerializer) — для ответов API:
#      ProductListSerializer, ProductDetailSerializer
#   2. INPUT (Serializer) — для валидации входящих данных:
#      CreateProductInputSerializer, UpdateProductInputSerializer
#   3. QUERY (Serializer) — для валидации query-параметров:
#      ProductListQuerySerializer
#
# ПОЧЕМУ ОТДЕЛЬНЫЕ СЕРИАЛИЗАТОРЫ ДЛЯ LIST И DETAIL:
#   List — 50 товаров на странице → минимум полей → быстрый JSON.
#   Detail — 1 товар → все поля, варианты, изображения → полный ответ.
#   Без разделения: listing вернёт description (5KB текст) × 50 = 250KB мусора.
#
# ЧТО БУДЕТ, ЕСЛИ УДАЛИТЬ ФАЙЛ:
#   Все product-related API endpoints перестанут работать.
# ────────────────────────────────────────────────────────────

# Decimal — для валидации денежных значений в query-параметрах.
# Почему не float: см. services/catalog_service.py — та же причина.
from decimal import Decimal

# serializers — модуль DRF с базовыми классами полей.
# ModelSerializer — автоматический сериализатор по модели (Meta.model).
# Serializer — ручной сериализатор (поля указаны явно).
from rest_framework import serializers

# ProductStatus — Enum-статусы для ChoiceField в input-сериализаторах.
from apps.catalog.constants import ProductStatus

# Модели для output-сериализаторов.
# ProductImage и ProductVariant — для вложенных сериализаторов.
from apps.catalog.models import Product, ProductImage, ProductVariant


# ==========================================================
# Вложенные сериализаторы (для использования внутри Product)
# ==========================================================

class ProductImageSerializer(serializers.ModelSerializer):
    """
    Изображение товара — только чтение.

    ПОЧЕМУ ТОЛЬКО ЧТЕНИЕ:
        Загрузка изображений — отдельный процесс (multipart form,
        S3 upload, etc). Этот сериализатор только для отображения.
        Без read_only_fields: API позволил бы менять is_main через JSON.
    """

    class Meta:
        # ProductImage — модель для автоматической генерации полей.
        model = ProductImage
        # fields — строгий белый список полей.
        # image — URL файла (Django автоматически конвертирует
        # ImageField в URL при сериализации).
        # alt — alt-текст для <img alt="..."> (SEO + accessibility).
        # is_main — флаг главного изображения.
        # order — порядок сортировки (1, 2, 3...).
        fields = ('id', 'image', 'alt', 'is_main', 'order')
        # read_only_fields = fields — ВСЕ поля только для чтения.
        # Это удобнее чем перечислять каждое поле дважды:
        # fields = (...) и read_only_fields = (...)
        read_only_fields = fields


class ProductVariantListSerializer(serializers.ModelSerializer):
    """
    Вариант товара для listing внутри Product.
    Минимальный набор для карточки.

    ПОЧЕМУ НЕ ВСЕ ПОЛЯ VARIANT:
        Внутри ProductDetailSerializer варианты — вложенный список.
        Если у товара 10 вариантов по 20 полей — JSON будет огромным.
        Минимальный набор: sku, slug, цена, сток, активность.
    """

    # Цена берётся из связанной модели pricing (Other app).
    # source='price.price' — навигация по связям:
    #   variant.price (FK к pricing) → price_obj.price (DecimalField).
    # Двойной .price: первый — related_name, второй — поле модели.
    # allow_null=True — вариант может не иметь цены (новый, без прайса).
    # read_only=True — цена не меняется через этот сериализатор.
    price = serializers.DecimalField(
        max_digits=12,         # До 999 999 999 999.99 ₽ — хватит для всего
        decimal_places=2,      # Копейки (2 знака после точки)
        source='price.price',  # Навигация: variant.price.price
        allow_null=True,       # Вариант без цены → null в JSON
        read_only=True,        # Только для чтения (не PUT/POST)
    )

    # Сток — аналогично цене, через related_name 'stock'.
    stock_quantity = serializers.IntegerField(
        source='stock.quantity',  # variant.stock.quantity
        allow_null=True,          # Нет складской записи → null
        read_only=True,
    )

    class Meta:
        model = ProductVariant
        # Минимальный набор для карточки товара:
        # id — идентификатор варианта
        # sku — артикул для поиска
        # slug — для URL варианта (если нужна отдельная страница)
        # price — цена (из pricing, через source)
        # stock_quantity — остаток (из inventory, через source)
        # is_active — показывает доступность варианта
        fields = (
            'id',
            'sku',
            'slug',
            'price',
            'stock_quantity',
            'is_active',
        )
        read_only_fields = fields


# ==========================================================
# LISTING (список товаров)
# ==========================================================

class ProductListSerializer(serializers.ModelSerializer):
    """
    Товар для listing-страниц каталога.
    Минимальный набор — без variants, без description.

    ПОЧЕМУ НЕ ProductDetailSerializer ДЛЯ ВСЕГО:
        Listing = 50 товаров на странице.
        Detail-сериализатор тянет variants + images + tags × 50 =
        огромный JSON, медленная сериализация.
        List-сериализатор = только базовые поля + brand + category + 1 картинка.

    ПОЧЕМУ DENORMALIZED ПОЛЯ (brand_name, category_name):
        Чтобы frontend не делал дополнительных запросов за именами.
        Альтернатива: frontend получает brand_id и сам запрашивает /brands/.
        Но это +1 API-вызов — медленнее.
    """

    # source='brand.name' — навигация через FK:
    # product.brand (FK к Brand) → brand_obj.name (CharField).
    # read_only=True — не меняется через listing API.
    brand_name = serializers.CharField(source='brand.name', read_only=True)
    brand_slug = serializers.CharField(source='brand.slug', read_only=True)
    category_name = serializers.CharField(
        source='primary_category.name', read_only=True,
    )
    category_slug = serializers.CharField(
        source='primary_category.slug', read_only=True,
    )
    # ImageField — автоматически возвращает URL изображения.
    # source='main_image.image' → product.main_image.image (ImageField).
    # allow_null=True — у товара может не быть главного изображения.
    # default=None — если main_image = None → null в JSON (не ошибка).
    main_image_url = serializers.ImageField(
        source='main_image.image',
        read_only=True,
        allow_null=True,
        default=None,
    )
    # price_range — property на модели Product:
    # «1 000 – 5 000 ₽» (строка, уже отформатированная).
    # read_only без source — берёт из product.price_range (property).
    price_range = serializers.CharField(read_only=True)

    class Meta:
        model = Product
        # Поля для listing-карточки товара:
        # uuid — публичный идентификатор для URL
        # name — название товара
        # slug — SEO-friendly URL
        # brand_name/slug — бренд
        # category_name/slug — категория
        # main_image_url — главное изображение
        # min_price/max_price — денормализованные цены
        # price_range — отформатированная строка цен
        # rating — средний рейтинг (float)
        # reviews_count — количество отзывов
        # is_featured — флаг «рекомендуемый»
        # published_at — дата публикации
        # created_at — дата создания (для сортировки)
        fields = (
            'uuid',
            'name',
            'slug',
            'brand_name',
            'brand_slug',
            'category_name',
            'category_slug',
            'main_image_url',
            'min_price',
            'max_price',
            'price_range',
            'rating',
            'reviews_count',
            'is_featured',
            'published_at',
            'created_at',
        )
        read_only_fields = fields


# ==========================================================
# DETAIL (карточка товара)
# ==========================================================

class ProductDetailSerializer(serializers.ModelSerializer):
    """
    Полная карточка товара.

    ОТЛИЧИЕ ОТ ProductListSerializer:
        + description — полный текст описания
        + images — все изображения (вложенный список)
        + variants — все варианты с ценами
        + tags — теги товара
        + SEO-поля (meta_title, meta_description)
        + views_count, display_rating
        + updated_at
    """

    brand_name = serializers.CharField(source='brand.name', read_only=True)
    brand_slug = serializers.CharField(source='brand.slug', read_only=True)
    # brand_logo — ImageField возвращает URL файла логотипа.
    brand_logo = serializers.ImageField(
        source='brand.logo', read_only=True, allow_null=True,
    )
    category_name = serializers.CharField(
        source='primary_category.name', read_only=True,
    )
    category_slug = serializers.CharField(
        source='primary_category.slug', read_only=True,
    )
    # many=True — у товара много изображений.
    # Serializer вложен — images = [{id:1, ...}, {id:2, ...}].
    images = ProductImageSerializer(many=True, read_only=True)
    # many=True — у товара много вариантов.
    variants = ProductVariantListSerializer(many=True, read_only=True)
    # SlugRelatedField — вместо id тега отдаёт его slug.
    # slug_field='slug' — поле для отображения.
    # many=True — M2M, много тегов.
    # Результат: tags: ["new", "sale", "popular"]
    # (вместо tags: [1, 5, 12] — непонятно для frontend).
    tags = serializers.SlugRelatedField(
        slug_field='slug',
        many=True,
        read_only=True,
    )
    price_range = serializers.CharField(read_only=True)
    # display_rating — property на модели: «4.5 / 5.0 ★»
    display_rating = serializers.CharField(read_only=True)
    # get_status_display — Django-метод для_choices полей:
    # status='active' → 'Активный' (из ProductStatus.choices).
    # source='get_status_display' — вызов метода модели.
    status = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Product
        # Полный набор полей для карточки товара.
        # Включает SEO-поля для meta-тегов страницы.
        fields = (
            'uuid',
            'name',
            'slug',
            'description',
            'status',
            'brand_name',
            'brand_slug',
            'brand_logo',
            'category_name',
            'category_slug',
            'images',
            'variants',
            'tags',
            'min_price',
            'max_price',
            'price_range',
            'rating',
            'display_rating',
            'reviews_count',
            'views_count',
            'is_featured',
            'published_at',
            'meta_title',
            'meta_description',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields


# ==========================================================
# INPUT (валидация запросов)
# ==========================================================

class ProductListQuerySerializer(serializers.Serializer):
    """
    Валидация query-параметров listing'а:
        GET /api/v1/catalog/products/?category=phones&brand=nike&min_price=100

    ПОЧЕМУ НЕ ModelSerializer:
        Query-параметры — не модель. Это фильтры, а не поля товара.
        Serializer даёт полный контроль над валидацией.

    ПОЧЕМУ ВАЛИДАЦИЯ ВОБЩЕ НУЖНА:
        Без неё: ?min_price=abc → SQL-ошибка → 500.
        С ней: ?min_price=abc → «Введите число.» → 400.
    """

    # SlugField — валидирует формат slug (буквы, цифры, дефисы).
    # required=False — параметр необязателен (показать все).
    category = serializers.SlugField(required=False)
    brand = serializers.SlugField(required=False)
    tag = serializers.SlugField(required=False)
    # min_value=Decimal('0') — цена не может быть отрицательной.
    # max_digits=12 — до 999 999 999 999.99.
    min_price = serializers.DecimalField(
        max_digits=12, decimal_places=2,
        required=False, min_value=Decimal('0'),
    )
    max_price = serializers.DecimalField(
        max_digits=12, decimal_places=2,
        required=False, min_value=Decimal('0'),
    )
    # max_length=200 — защита от гигантских поисковых запросов.
    # Без: ?search=<1MB текст> → нагрузка на PostgreSQL.
    search = serializers.CharField(required=False, max_length=200)
    # ordering — строка сортировки. Валидируется в сервисе (whitelist).
    # default='-created_at' — если не передан → по умолчанию новые первыми.
    ordering = serializers.CharField(
        required=False,
        default='-created_at',
    )


class CreateProductInputSerializer(serializers.Serializer):
    """
    Валидация тела POST /api/v1/catalog/products/.

    ПОЧЕМУ НЕ ModelSerializer:
        Input API отличается от модели:
        - category_ids вместо categories (M2M через id)
        - brand_id вместо brand (FK через id)
        - Нет slug (генерируется автоматически)
        - Нет UUID (генерируется автоматически)
    """

    # max_length=255 — соответствует модели Product.name.
    name = serializers.CharField(max_length=255)
    # min_value=1 — id начинается с 1, нет смысла передавать 0 или отрицательное.
    brand_id = serializers.IntegerField(min_value=1)
    primary_category_id = serializers.IntegerField(min_value=1)
    # required=False, default='' — описание не обязательно.
    description = serializers.CharField(required=False, default='')
    manufacturer_code = serializers.CharField(
        required=False, max_length=100, default='',
    )
    # ChoiceField — валидирует что статус из ProductStatus.choices.
    # default=DRAFT — новый товар черновик по умолчанию (без модерации).
    status = serializers.ChoiceField(
        choices=ProductStatus.choices,
        default=ProductStatus.DRAFT,
    )
    is_featured = serializers.BooleanField(required=False, default=False)
    # ListField — массив целых чисел [1, 2, 3].
    # child=serializers.IntegerField(min_value=1) — каждый элемент >= 1.
    # default=[] — если не передан → пустой список (нет категорий).
    category_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        required=False,
        default=[],
    )
    tag_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        required=False,
        default=[],
    )


class UpdateProductInputSerializer(serializers.Serializer):
    """
    Валидация тела PATCH /api/v1/catalog/products/{uuid}/.

    ОТЛИЧИЕ ОТ CreateProductInputSerializer:
        - Все поля required=False (PATCH = частичное обновление).
        - Нет default (None = не менять).
        - category_ids/tag_ids тоже optional (None = не менять, [] = очистить).
    """

    name = serializers.CharField(max_length=255, required=False)
    brand_id = serializers.IntegerField(min_value=1, required=False)
    primary_category_id = serializers.IntegerField(min_value=1, required=False)
    # Без max_length — позволяет очистить описание пустой строкой.
    description = serializers.CharField(required=False)
    manufacturer_code = serializers.CharField(max_length=100, required=False)
    status = serializers.ChoiceField(
        choices=ProductStatus.choices, required=False,
    )
    is_featured = serializers.BooleanField(required=False)
    # Без default — если не передан → key отсутствует в validated_data
    # → сервис не трогает categories/tags.
    category_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        required=False,
    )
    tag_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        required=False,
    )
