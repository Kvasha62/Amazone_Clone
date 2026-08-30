# ==============================================================================
# apps/catalog/models/product.py — Товар
# ==============================================================================
# Главная сущность каталога. Содержит:
#   - Публичный UUID (для API, PK наружу не светим)
#   - SEO-slug (генерируется один раз, не меняется при переименовании)
#   - Статус (DRAFT → ACTIVE → OUT_OF_STOCK → ARCHIVED)
#   - Денормализованные min_price / max_price из вариантов
#   - Денормализованные rating / reviews_count / views_count
#   - Полнотекстовый поиск (PostgreSQL SearchVectorField + GIN-индекс)
#   - Связи: Brand, Category (M2M), Tags (M2M), ProductImage, ProductVariant
#
# Почему uuid + slug, а не PK:
#   PK (id=1,2,3...) раскрывает:
#     - Количество товаров в базе (id=5000 → ~5000 товаров)
#     - Позволяет перебор /scraping: /api/products/1/ ... /api/products/5000/
#   UUID решает обе проблемы: непредсказуем и неинформативен.
#   Slug решает SEO: /products/iphone-15-pro/ лучше чем /products/uuid/.
# ==============================================================================

import uuid
from decimal import Decimal

from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.db.models import F
from django.utils import timezone

from apps.catalog.constants import ProductStatus
from apps.catalog.managers.product_manager import ProductManager
from apps.catalog.services.slug_service import generate_unique_slug
from apps.core.models import BaseModel

# ── PostgreSQL-specific imports — conditional ──
# SearchVectorField и GinIndex поддерживаются ТОЛЬКО PostgreSQL.
# На SQLite эти поля/индексы недоступны — Django создаст обычный TextField
# и пропустит GinIndex при makemigrations.
# Конструкция try/except позволяет модели загружаться на любой БД.
# 🔴 Django 6.1: проверяем не только импорт, но и наличие в INSTALLED_APPS,
# иначе системная проверка (postgres.E005) падает на SQLite.
try:
    from django.contrib.postgres.indexes import GinIndex
    from django.contrib.postgres.search import SearchVectorField
    from django.conf import settings
    _HAS_POSTGRES = 'django.contrib.postgres' in settings.INSTALLED_APPS
except (ImportError, RuntimeError):
    _HAS_POSTGRES = False

if not _HAS_POSTGRES:
    # Fallback: SearchVectorField → TextField (SQLite не поддерживает tsvector)
    SearchVectorField = models.TextField
    GinIndex = None


class Product(BaseModel):
    """
    Товар каталога.

    Архитектурные решения:
    ─────────────────────
    uuid            Публичный идентификатор для API. PK наружу не светим.
    slug            Генерируется ОДИН раз при создании. При переименовании
                    не меняется — SEO-ссылки не ломаются.
    status          TextChoices вместо is_active BooleanField. Четыре статуса:
                    draft → active → out_of_stock → archived.
    min_price/      Денормализованные цены из вариантов. Без них listing
    max_price       «сортировка по цене» требует JOIN через variant → price.
    main_image      Прямой FK на главное изображение. Без него listing
                    делает N+1 к ProductImage на каждый товар.
    search_vector   PostgreSQL full-text search с GIN-индексом.
                    __icontains = sequential scan на 100K+ товаров.
                    SearchVectorField + GinIndex = миллисекунды.
    categories      M2M — товар лежит в нескольких категориях одновременно
                    (Amazon: iPhone ∈ Смартфоны ∩ Электроника ∩ Apple).
    """

    # ------------------------------------------------------------------
    # ProductManager — кастомный менеджер с QuerySet-методами
    # ------------------------------------------------------------------
    # Подключает ProductQuerySet.active(), .visible(), .catalog() и др.
    # Вызов: Product.objects.active().with_related().order_by('-rating')
    # Без менеджера пришлось бы писать Product.objects.filter(status='active')
    # в каждом месте — DRY.
    # ------------------------------------------------------------------
    objects = ProductManager()

    # ==================================================================
    # Публичный идентификатор
    # ==================================================================

    uuid = models.UUIDField(
        # default=uuid.uuid4 — генерирует случайный UUID v4 при создании.
        # Каждый вызов uuid4() возвращает новое значение —
        # поэтому default=uuid.uuid4 (без скобок!) — передаём функцию,
        # а не результат. Django вызовет её при создании объекта.
        default=uuid.uuid4,
        # editable=False — не показывается в Django admin формах
        editable=False,
        # unique=True — индекс для быстрого поиска по UUID.
        # API: GET /api/v1/catalog/products/<uuid>/
        unique=True,
        verbose_name='Public UUID',
    )

    # ==================================================================
    # Основная информация
    # ==================================================================

    name = models.CharField(
        verbose_name='Название',
        max_length=255,
        # db_index=True — товары часто ищутся по name.
        # Хотя основной поиск идёт через SearchVectorField,
        # точный поиск по имени (__exact, __startswith) нужен в admin.
        db_index=True,
    )

    slug = models.SlugField(
        verbose_name='SEO slug',
        max_length=255,
        unique=True,
        blank=True,  # заполняется автоматически в save()
    )

    description = models.TextField(
        verbose_name='Описание',
        blank=True,
    )

    # ==================================================================
    # Полнотекстовый поиск (PostgreSQL)
    # ==================================================================
    # SearchVectorField хранит предобработанный tsvector:
    #   'iphone' → 'iphon':1A (стемминг + позиция + вес)
    #
    # GinIndex над этим полем делает поиск мгновенным:
    #   WHERE search_vector @@ to_tsquery('iphone')
    #   → Index Scan вместо Sequential Scan.
    #
    # Почему не __icontains:
    #   __icontains на 100K товаров → 100K строк читаются с диска.
    #   GIN-индекс → читаются только совпадающие строки.
    #
    # null=True — у новых товаров search_vector может быть NULL,
    #   обновляется через сигнал post_save.
    # ==================================================================

    # SearchVectorField — PostgreSQL full-text search (tsvector).
    # GIN-индекс делает поиск мгновенным:
    #   WHERE search_vector @@ to_tsquery('iphone') → Index Scan.
    search_vector = SearchVectorField(
        verbose_name='Поисковый вектор',
        null=True,
        blank=True,
        editable=False,
        help_text=(
            'Автоматически обновляется через trigger / celery. '
            'Не редактировать вручную.'
        ),
    )

    # ==================================================================
    # SEO-поля
    # ==================================================================
    # meta_title и meta_description — для <meta> тегов в HTML.
    # Если пустые — фронтенд подставляет name / description товара.
    # ==================================================================

    meta_title = models.CharField(
        verbose_name='SEO title',
        max_length=255,
        blank=True,
    )

    meta_description = models.TextField(
        verbose_name='SEO description',
        blank=True,
    )

    # ==================================================================
    # Бизнес-идентификаторы
    # ==================================================================

    manufacturer_code = models.CharField(
        verbose_name='Артикул производителя',
        max_length=100,
        blank=True,
        db_index=True,  # поиск по артикулу в admin
    )

    # ==================================================================
    # Статус
    # ==================================================================

    status = models.CharField(
        verbose_name='Статус',
        max_length=20,
        choices=ProductStatus.choices,
        default=ProductStatus.DRAFT,  # Новые товары — черновики
        db_index=True,                # Фильтр по статусу — в каждом запросе
    )

    is_featured = models.BooleanField(
        verbose_name='Рекомендуемый',
        default=False,
        db_index=True,  # Частый фильтр: «показать рекомендуемые»
        help_text='Показывать в блоке «Рекомендуем» на главной.',
    )

    published_at = models.DateTimeField(
        verbose_name='Дата публикации',
        null=True,
        blank=True,
        db_index=True,  # Фильтр «опубликовано до NOW()»
        help_text=(
            'Запланированная дата публикации. '
            'null = не опубликован. Заполняется при переходе в ACTIVE.'
        ),
    )

    # ==================================================================
    # Связи
    # ==================================================================

    # ------------------------------------------------------------------
    # brand — производитель товара
    # ------------------------------------------------------------------
    # on_delete=PROTECT — нельзя удалить бренд, у которого есть товары.
    #   Сначала нужно перенести товары на другой бренд (или архивировать).
    #   Это предотвращает случайное удаление «Samsung» и потерю 1000 товаров.
    #
    # related_name='products' — обращение: brand.products.all()
    # ------------------------------------------------------------------
    brand = models.ForeignKey(
        'catalog.Brand',
        on_delete=models.PROTECT,
        related_name='products',
        verbose_name='Бренд',
    )

    # ------------------------------------------------------------------
    # categories — M2M, товар может лежать в нескольких категориях
    # ------------------------------------------------------------------
    # Amazon-подход: iPhone ∈ «Смартфоны» ∩ «Электроника» ∩ «Apple».
    # blank=True — товар может быть без категории (черновик).
    # ------------------------------------------------------------------
    categories = models.ManyToManyField(
        'catalog.Category',
        related_name='products',
        verbose_name='Категории',
        blank=True,
    )

    # ------------------------------------------------------------------
    # primary_category — ОСНОВНАЯ категория (одна)
    # ------------------------------------------------------------------
    # Зачем, если есть M2M categories:
    #   1. Breadcrumbs — «Главная → Электроника → Смартфоны → iPhone»
    #      нужен ОДИН путь, а не все M2M.
    #   2. Canonical URL — SEO требует одну каноническую категорию.
    #   3. Фильтр по умолчанию в listing-е.
    #
    # on_delete=PROTECT — нельзя удалить категорию с товарами.
    # ------------------------------------------------------------------
    primary_category = models.ForeignKey(
        'catalog.Category',
        on_delete=models.PROTECT,
        related_name='primary_products',
        verbose_name='Основная категория',
        help_text='Используется для breadcrumbs и canonical URL.',
    )

    # ------------------------------------------------------------------
    # main_image — главное изображение товара
    # ------------------------------------------------------------------
    # Денормализация: без этого поля listing-страница делает
    #   N+1 запросов — для каждого товара ищет главное изображение.
    # С этим полем — один SELECT + один JOIN (или prefetch).
    #
    # on_delete=SET_NULL — при удалении изображения
    #   main_image становится NULL (товар остаётся).
    # ------------------------------------------------------------------
    main_image = models.ForeignKey(
        'catalog.ProductImage',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='featured_in_products',
        verbose_name='Главное изображение',
        help_text='Отображается в listing-е и карточке товара.',
    )

    # ------------------------------------------------------------------
    # tags — M2M теги
    # ------------------------------------------------------------------
    tags = models.ManyToManyField(
        'catalog.Tag',
        related_name='products',
        verbose_name='Теги',
        blank=True,
    )

    # ==================================================================
    # Денормализованные цены (из вариантов)
    # ==================================================================
    # min_price / max_price пересчитываются автоматически:
    #   - при изменении цены варианта (pricing-сигнал)
    #   - при деактивации варианта (catalog-сигнал)
    #
    # Зачем денормализация:
    #   Без неё «сортировка по цене» требует:
    #     SELECT p.* FROM products p
    #     JOIN variants v ON v.product_id = p.id
    #     JOIN prices pr ON pr.variant_id = v.id
    #     ORDER BY pr.price
    #   Это тройной JOIN — медленно на миллионах.
    #
    #   С денормализацией:
    #     SELECT * FROM products ORDER BY min_price
    #   Индексный скан — мгновенно.
    # ==================================================================

    min_price = models.DecimalField(
        verbose_name='Минимальная цена',
        max_digits=12,
        decimal_places=2,
        null=True,     # Нет вариантов с ценой → NULL
        blank=True,
        db_index=True,  # ORDER BY min_price, WHERE min_price >= X
        help_text=(
            'Автоматически пересчитывается при изменении цен вариантов. '
            'null = у товара нет вариантов с ценой.'
        ),
    )

    max_price = models.DecimalField(
        verbose_name='Максимальная цена',
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=(
            'Автоматически пересчитывается при изменении цен вариантов. '
            'null = у товара нет вариантов с ценой.'
        ),
    )

    # ==================================================================
    # Денормализованные счётчики
    # ==================================================================
    # Эти поля обновляются ТОЛЬКО через авторитетные пути:
    #   • rating / reviews_count — CatalogService.set_review_stats()
    #     (ARCH-001 C1: вызывается из ReviewService; прямой мутации нет);
    #   • views_count — атомарный increment_views() или celery-задачи.
    #
    # Почему денормализация:
    #   AVG(rating) FROM reviews WHERE product=X — GROUP BY на миллионах.
    #   Хранение на товаре — O(1) при чтении, обновление — редко.
    # ==================================================================

    rating = models.DecimalField(
        verbose_name='Рейтинг',
        max_digits=3,       # 0.00 .. 5.00
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[
            MinValueValidator(Decimal('0.00')),
            MaxValueValidator(Decimal('5.00')),
        ],
        db_index=True,  # ORDER BY -rating (топ товаров)
    )

    reviews_count = models.PositiveIntegerField(
        verbose_name='Количество отзывов',
        default=0,
    )

    views_count = models.PositiveBigIntegerField(
        # PositiveBigIntegerField (64-bit) — просмотры могут быть > 2 млрд
        verbose_name='Просмотры',
        default=0,
    )

    # ==================================================================
    # Удобные свойства (computed, не хранятся в БД)
    # ==================================================================

    @property
    def is_active(self) -> bool:
        """Обратная совместимость: is_active = status == ACTIVE."""
        return self.status == ProductStatus.ACTIVE

    @property
    def is_visible(self) -> bool:
        """
        Видимость в каталоге: активен и дата публикации прошла.
        """
        return (
            self.status == ProductStatus.ACTIVE
            and (self.published_at is None or self.published_at <= timezone.now())
        )

    @property
    def display_rating(self) -> str:
        """Рейтинг для UI: '4.50' вместо Decimal('4.50')."""
        return f'{self.rating:.2f}'

    @property
    def price_range(self) -> str:
        """Строка для UI: '1299.00 — 3499.00' или '1299.00' или 'Цена не указана'."""
        if self.min_price is None:
            return 'Цена не указана'
        if self.min_price == self.max_price:
            return f'{self.min_price:.2f}'
        return f'{self.min_price:.2f} — {self.max_price:.2f}'

    class Meta:
        verbose_name = 'Товар'
        verbose_name_plural = 'Товары'
        ordering = ('-created_at',)

        indexes = [
            # ── Regular indexes (work on ALL databases) ──
            models.Index(
                fields=['status', 'primary_category'],
                name='product_status_category_idx',
            ),
            models.Index(
                fields=['status', 'brand'],
                name='product_status_brand_idx',
            ),
            models.Index(
                fields=['-rating'],
                name='product_rating_idx',
            ),
            models.Index(
                fields=['min_price'],
                name='product_min_price_idx',
            ),
            models.Index(
                fields=['-max_price'],
                name='product_max_price_idx',
            ),
            models.Index(
                fields=['-created_at'],
                name='product_created_at_idx',
            ),
            models.Index(
                fields=['-created_at', 'is_featured'],
                name='product_featured_idx',
            ),
        ]

        # ── PostgreSQL partial indexes + GIN ──
        # Partial indexes (condition=...) оптимизируют частые фильтры:
        # только активные товары (status='active').
        # GinIndex — мгновенный полнотекстовый поиск.
        indexes.extend([
                # Partial: «активные товары в категории X»
                models.Index(
                    fields=['status', 'primary_category'],
                    condition=models.Q(status=ProductStatus.ACTIVE),
                    name='product_active_category_idx',
                ),
                # Partial: «активные товары бренда X»
                models.Index(
                    fields=['status', 'brand'],
                    condition=models.Q(status=ProductStatus.ACTIVE),
                    name='product_active_brand_idx',
                ),
                # Partial: «топ по рейтингу»
                models.Index(
                    fields=['-rating'],
                    condition=models.Q(status=ProductStatus.ACTIVE),
                    name='product_top_rating_idx',
                ),
                # Partial: «по цене (дешевле)»
                models.Index(
                    fields=['min_price'],
                    condition=models.Q(status=ProductStatus.ACTIVE),
                    name='product_price_asc_idx',
                ),
                # Partial: «по цене (дороже)»
                models.Index(
                    fields=['-max_price'],
                    condition=models.Q(status=ProductStatus.ACTIVE),
                    name='product_price_desc_idx',
                ),
                # Partial: «новинки»
                models.Index(
                    fields=['-created_at'],
                    condition=models.Q(status=ProductStatus.ACTIVE),
                    name='product_newest_idx',
                ),
                # Partial: «рекомендуемые»
                models.Index(
                    fields=['-created_at'],
                    condition=models.Q(
                        status=ProductStatus.ACTIVE,
                        is_featured=True,
                    ),
                    name='product_featured_partial_idx',
                ),
                # GIN-индекс для полнотекстового поиска
                GinIndex(
                    fields=['search_vector'],
                    name='product_search_gin',
                ),
            ])

        constraints = [
            # Рейтинг от 0 до 5 — защита от ошибок в коде
            models.CheckConstraint(
        condition=(
                    models.Q(rating__gte=0)
                    & models.Q(rating__lte=5)
                ),
                name='product_rating_range',
            ),
            # Счётчики ≥ 0 — защита от F()-декремента ниже нуля
            models.CheckConstraint(
        condition=models.Q(reviews_count__gte=0),
                name='product_reviews_count_gte_0',
            ),
            models.CheckConstraint(
        condition=models.Q(views_count__gte=0),
                name='product_views_count_gte_0',
            ),
            # min_price ≥ 0 или NULL
            models.CheckConstraint(
        condition=models.Q(min_price__isnull=True) | models.Q(min_price__gte=0),
                name='product_min_price_gte_0',
            ),
            # max_price ≥ min_price (если оба не NULL)
            models.CheckConstraint(
        condition=(
                    models.Q(min_price__isnull=True)
                    | models.Q(max_price__isnull=True)
                    | models.Q(max_price__gte=models.F('min_price'))
                ),
                name='product_max_price_gte_min',
            ),
        ]

    # ----------------------------------------------------------
    # Представление
    # ----------------------------------------------------------

    def __str__(self) -> str:
        return self.name

    def get_absolute_url(self) -> str:
        """URL товара во фронтенде."""
        return f'/products/{self.slug}/'

    # ----------------------------------------------------------
    # Сохранение
    # ----------------------------------------------------------

    def save(self, *args, **kwargs):
        # Slug — генерируется один раз при создании.
        # При переименовании slug НЕ меняется — стабильность SEO-URL.
        if not self.slug:
            self.slug = generate_unique_slug(
                instance=self,
                field_value=self.name,
            )
        # published_at — проставляется автоматически при первом
        # переходе в ACTIVE (для scheduled publishing).
        if self.status == ProductStatus.ACTIVE and not self.published_at:
            self.published_at = timezone.now()
        super().save(*args, **kwargs)

    # ----------------------------------------------------------
    # Атомарные операции над счётчиками
    # ----------------------------------------------------------
    # F() — database-level арифметика. Без F():
    #   product.views_count += 1  →  SELECT views_count; Python += 1; UPDATE
    #   При параллельных запросах — race condition (lost update).
    #
    # С F():
    #   UPDATE products SET views_count = views_count + 1 WHERE id=X
    #   Атомарно на уровне PostgreSQL — нет race condition.
    # ----------------------------------------------------------

    def increment_views(self) -> None:
        """Атомарно +1 к просмотрам через F()."""
        # F('views_count') + 1 — выражение, выполнится в БД
        self.views_count = F('views_count') + 1
        # update_fields — оптимизация: обновляем только 2 поля,
        # а не все 20+ полей товара
        self.save(update_fields=['views_count', 'updated_at'])
        # refresh_from_db — после F() значение в Python — строка
        # 'F(views_count) + 1', а не число. Перечитываем из БД
        # чтобы следующий код видел актуальное значение.
        self.refresh_from_db(fields=['views_count'])

    # ARCH-001 Stage C1: Product.update_rating() удалён — это был
    # cross-context mutation path: reviews вызывал метод catalog-модели
    # и сам решал, когда мутировать агрегаты каталога.
    #
    # Авторитетный путь записи теперь один:
    #   ReviewService.recalculate_product_rating()
    #     → расчёт AVG/COUNT из данных reviews
    #     → CatalogService.set_review_stats(product, rating, reviews_count)
    #     → catalog.Product
    #
    # `reviews` владеет знанием о расчёте агрегатов отзывов,
    # `catalog` — записью собственных полей (ownership boundary).
    #
    # ARCH-001 Stage 2: Product.recalculate_prices() удалён — он читал
    # цены pricing через ORM-lookup по вариантам (JOIN на таблицу цен
    # pricing — запрещённая обратная зависимость catalog → pricing).
    #
    # Пересчёт min_price/max_price теперь выполняется ТОЛЬКО явными
    # service-вызовами (ARCHITECTURE.md → Cross-Domain Coordination):
    #   1) рассчитывает pricing — PricingService.recalculate_product_bounds()
    #      (из СВОИХ данных Price, только активные варианты);
    #   2) записывает catalog — CatalogService.set_product_prices().
    # Смена is_active / удаление варианта — через
    # PricingService.set_variant_active / delete_variant
    # (автоматической реакции на ORM-события нет).
