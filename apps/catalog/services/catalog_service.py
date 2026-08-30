# ────────────────────────────────────────────────────────────
# CatalogService — бизнес-логика каталога.
#
# АРХИТЕКТУРНЫЙ ПРИНЦИП «Service Layer»:
#   Views вызывают сервис → сервис работает с ORM → ORM делает SQL.
#   Views НЕ знают про транзакции, select_for_update, сложные JOIN.
#
#   ЗАЧЕМ:
#     1) Переиспользование: CatalogService.create_product() можно
#        вызвать из view, из management-команды, из Celery-задачи.
#     2) Тестируемость: сервис можно мокировать в тестах views.
#     3) Один источник истины: логика создания товара в одном месте.
#
# ВСЕ МЕТОДЫ — @staticmethod:
#   Сервис не хранит состояние (stateless). Каждый метод принимает
#   всё что нужно через параметры и возвращает результат.
#   Нет self → нет проблем с сериализацией / мокированием.
#
# ЧТО БУДЕТ, ЕСЛИ УДАЛИТЬ ФАЙЛ:
#   Все API views каталога перестанут работать (ImportError).
# ────────────────────────────────────────────────────────────

# from __future__ — включает PEP 604 синтаксис типов (str | None)
# для совместимости с Python < 3.10.
# В Python 3.10+ можно писать str | None нативно.
# Без: TypeError на Python 3.9 при парсинге аннотаций.
from __future__ import annotations

# logging — стандартная библиотека Python для логирования.
# getLogger(__name__) — создаёт логгер с именем модуля:
# 'apps.catalog.services.catalog_service'.
# Это позволяет в settings.py настроить уровень логирования
# конкретно для этого модуля:
#   LOGGING = {'loggers': {'apps.catalog.services': {'level': 'DEBUG'}}}
import logging

# Decimal — точный тип для денежных значений.
# ПОЧЕМУ НЕ float:
#   float(0.1) + float(0.2) = 0.30000000000000004 (ошибка!)
#   Decimal('0.1') + Decimal('0.2') = Decimal('0.3') (точно).
#   Для цен точность критична — 0.01₽ ошибки накопятся в миллионы.
from decimal import Decimal

# transaction.atomic — декоратор / контекстный менеджер для
# оборачивания кода в SQL-транзакцию:
#   BEGIN; ... код ...; COMMIT;  (или ROLLBACK при исключении).
# Без: при ошибке в середине create_product() часть данных
# сохранится, часть нет — база в неконсистентном состоянии.
from django.db import transaction

# get_object_or_404 — хелпер Django: делает get() и если не найдено,
# выбрасывает Http404 (не DoesNotExist). Удобно для API:
# клиент получит 404, а не 500 (серверная ошибка).
from django.shortcuts import get_object_or_404

# DRF-исключения — транслируются в HTTP-ответы с правильными кодами:
#   NotFound → 404, ValidationError → 400.
# Без: Django DoesNotExist → 500 Internal Server Error.
from rest_framework.exceptions import NotFound, ValidationError

# Статусы товара — Enum из констант. Используем вместо хардкода строк.
from apps.catalog.constants import ProductStatus

# Импортируем все модели, с которыми работает сервис.
# Импортируем конкретные классы (не import *), чтобы:
#   1) IDE знала типы (автодополнение, рефакторинг)
#   2) Явно видно, какие модели используются
from apps.catalog.models import (
    Brand,
    Category,
    Product,
    ProductImage,
    ProductVariant,
    Tag,
)

# Создаём логгер с именем модуля для структурированного логирования.
# __name__ = 'apps.catalog.services.catalog_service'
# Без: print() в проде никто не увидит (нет уровня/формата).
logger = logging.getLogger(__name__)


# ────────────────────────────────────────────────────────────
# ARCH-001 Stage 2: обновление Product.min_price/max_price.
#
# ПРОБЛЕМА:
#   Product.min_price/max_price зависят и от состояния вариантов
#   каталога (is_active, удаление варианта), и от цен pricing.
#   Раньше каталог сам пересчитывал границы, читая цены pricing
#   через ORM-lookup `variant.price` (JOIN на таблицу цен pricing) —
#   это запрещённая обратная зависимость catalog → pricing.
#
# РЕШЕНИЕ (ARCHITECTURE.md → «Cross-Domain Coordination»):
#   Единственный легитимный механизм cross-domain координации —
#   ЯВНЫЕ service-вызовы с видимой точкой в коде и явной транзакцией:
#
#     PricingService.recalculate_product_bounds(product)
#       → расчёт min/max из СВОИХ данных pricing
#       → CatalogService.set_product_prices(product, min_price, max_price)
#       → catalog.Product
#
#   АВТОМАТИЧЕСКОЙ реакции каталога на изменение is_active/удаление
#   варианта НЕТ и быть не может без нарушения архитектуры: любая
#   механика авто-реакции — это либо reverse dependency
#   (catalog → pricing), либо cross-context Django signal, либо
#   глобальный registry/event bus — все три формы запрещены
#   (ARCHITECTURE.md: «explicit service calls» — primary mechanism;
#   сигналы — только same-domain). Поэтому изменение price-relevant
#   состояния варианта выполняется ТОЛЬКО через явные сервисные
#   методы (см. PricingService.set_variant_active / delete_variant).
#   Каталог предоставляет catalog-owned мутации (ниже), pricing —
#   оркестрацию и расчёт. Никаких реестров, локаторов и событий.
# ────────────────────────────────────────────────────────────


class CatalogService:
    """
    Бизнес-логика каталога.

    Views вызывают сервис, сервис работает с ORM.
    Views не знают про транзакции, select_for_update и т.д.
    """

    # ----------------------------------------------------------
    # Товары
    # ----------------------------------------------------------

    @staticmethod
    def get_product_by_uuid(uuid: str) -> Product:
        """
        Возвращает товар по public UUID для API.
        Использует for_card() — полный набор prefetch.

        ПОЧЕМУ UUID, А НЕ PK (id):
            PK — внутренний идентификатор, последовательный (1,2,3...).
            Зная PK можно enumerate все товары — утечка бизнес-инфы.
            UUID — непредсказуемый, безопасный для публичного API.

        ПОЧЕМУ for_card():
            Карточка товара всегда нужна с full prefetch
            (варианты, изображения, теги). Без for_card():
            product.brand → 1 SQL, product.images.all() → 1 SQL и т.д.

        ЧТО БУДЕТ БЕЗ status=ProductStatus.ACTIVE:
            Вернётся DRAFT/ARCHIVED товар — утечка неопубликованного.
        """
        try:
            return (
                Product.objects
                # for_card() — композитный метод QuerySet:
                # select_related(brand, category, main_image)
                # + prefetch_related(images, variants, categories)
                .for_card()
                # .get() — выполняет SQL немедленно (не lazy!).
                # Если найдётся >1 записи — MultipleObjectsReturned.
                # uuid=uuid — фильтр по UUID (уникальный, indexed).
                .get(uuid=uuid, status=ProductStatus.ACTIVE)
            )
        # Product.DoesNotExist — стандартное исключение Django
        # когда .get() ничего не нашёл.
        except Product.DoesNotExist:
            # NotFound — DRF-исключение → HTTP 404.
            # Без: DoesNotExist просочится наверх → 500 (server error).
            raise NotFound('Товар не найден.')

    @staticmethod
    def get_product_by_slug(slug: str) -> Product:
        """
        Возвращает товар по slug (SEO-friendly URL).

        ПОЧЕМУ НУЖЕН ОТДЕЛЬНЫЙ МЕТОД (не только по UUID):
            URL вида /products/iphone-15-pro/ — SEO-оптимизация.
            Поисковики индексируют slug-URL лучше, чем UUID.
            UUID используется для API, slug — для публичных страниц.

        ЧТО БУДЕТ БЕЗ:
            Придётся всегда искать по UUID → не SEO-friendly.
        """
        try:
            return (
                Product.objects
                .for_card()  # Полный prefetch
                .get(slug=slug, status=ProductStatus.ACTIVE)
            )
        except Product.DoesNotExist:
            raise NotFound('Товар не найден.')

    @staticmethod
    def get_product_listing(
        *,
        # *, — заставляет передавать ВСЕ аргументы по имени.
        # Это предотвращает ошибки вида:
        #   get_product_listing('phones')  — что это? category? brand?
        # С *: get_product_listing(category_slug='phones') — явно.
        category_slug: str | None = None,
        brand_slug: str | None = None,
        tag_slug: str | None = None,
        min_price: Decimal | None = None,
        max_price: Decimal | None = None,
        search_query: str | None = None,
        # По умолчанию — новые товары первыми.
        ordering: str = '-created_at',
    # Возвращаем tuple[QuerySet, dict] — кортеж для распаковки:
    #   qs, filters = CatalogService.get_product_listing(...)
    ) -> tuple:
        """
        Возвращает QuerySet для listing-страницы + применённые фильтры.

        Возвращает (queryset, applied_filters) — чтобы API
        мог вернуть фильтры в ответе для UI.

        ПОЧЕМУ ВОЗВРАЩАЕМ applied_filters:
            Frontend показывает пользователю «Фильтры: Nike, 1000-5000₽».
            Если не возвращать — frontend не знает, что реально применено
            (например, slug бренда может быть 'nike', а имя — 'Nike').

        Args:
            category_slug:  slug категории для фильтрации
            brand_slug:     slug бренда
            tag_slug:       slug тега
            min_price:      минимальная цена (денорм.)
            max_price:      максимальная цена (денорм.)
            search_query:   поисковый запрос (SearchVector)
            ordering:       сортировка (проверена против whitelist)
        """
        # .catalog() — композитный метод QuerySet:
        # visible() + with_related() + with_images() + with_variants()
        # Один вызов — все нужные prefetch для listing.
        qs = Product.objects.catalog()

        # applied_filters — словарь для возврата frontend-у.
        # Пустой если фильтров нет → frontend показывает «Все товары».
        applied_filters = {}

        # ─── Фильтр по категории ───
        if category_slug:
            # get_object_or_404 — ищет Category с данным slug.
            # is_active=True — не ищем в деактивированных категориях.
            # Если не найдено → Http404 (не 500).
            category = get_object_or_404(Category, slug=category_slug, is_active=True)
            # for_category(category) — метод QuerySet:
            # .active().filter(categories=category)
            qs = qs.for_category(category)
            # Сохраняем имя категории (не slug!) для UI.
            # Frontend покажет «Электроника», а не «elektronika».
            applied_filters['category'] = category.name

        # ─── Фильтр по бренду ───
        if brand_slug:
            # Аналогично категории — ищем активный бренд по slug.
            brand = get_object_or_404(Brand, slug=brand_slug, is_active=True)
            qs = qs.for_brand(brand)
            applied_filters['brand'] = brand.name

        # ─── Фильтр по тегу ───
        if tag_slug:
            # Теги — M2M-связь. Фильтруем через .filter(tags=tag).
            tag = get_object_or_404(Tag, slug=tag_slug, is_active=True)
            # Не используем отдельный метод for_tag() —
            # теги фильтруются редко, не стоит загрязнять QuerySet.
            qs = qs.filter(tags=tag)
            applied_filters['tag'] = tag.name

        # ─── Фильтр по цене ───
        if min_price is not None or max_price is not None:
            # price_range() — метод QuerySet, работает с денормализованными
            # min_price/max_price на Product (без JOIN к вариантам).
            qs = qs.price_range(min_price=min_price, max_price=max_price)
            # Сохраняем обе границы, даже если указана одна.
            # Frontend покажет «от 1000₽» или «до 5000₽» или «1000-5000₽».
            if min_price is not None:
                # str() — JSON-сериализация. Decimal не сериализуется напрямую.
                applied_filters['min_price'] = str(min_price)
            if max_price is not None:
                applied_filters['max_price'] = str(max_price)

        # ─── Поиск ───
        if search_query:
            # .search() — метод QuerySet, использует GIN-индекс.
            qs = qs.search(search_query)
            applied_filters['search'] = search_query

        # ─── Сортировка (whitelist!) ───
        # ПОЧЕМУ WHITELIST, А НЕ ПРОСТО order_by(ordering):
        #   ordering приходит от пользователя (query-параметр).
        #   Без whitelist: ?ordering=;DROP TABLE products; — SQL-инъекция!
        #   (Django ORM параметризует запросы, но order_by()
        #   принимает строки как имена столбцов — риск остаётся.)
        allowed_orderings = {
            '-created_at', 'created_at',      # По дате (новые/старые)
            '-min_price', 'min_price',         # По цене (дороже/дешевле)
            '-rating', 'rating',               # По рейтингу
            '-views_count', 'views_count',     # По просмотрам
            'name', '-name',                   # По названию (А-Я / Я-А)
        }
        # Если ordering не в whitelist — используем дефолт.
        # Это защита: любой неизвестный параметр → -created_at.
        if ordering not in allowed_orderings:
            ordering = '-created_at'

        # Применяем сортировку.
        # order_by() с '-' prefix = DESC, без = ASC.
        qs = qs.order_by(ordering)

        # Возвращаем кортеж: (QuerySet, dict).
        # QuerySet ещё НЕ выполнен (lazy!) — выполнится при пагинации.
        return qs, applied_filters

    @staticmethod
    # @transaction.atomic — обёрнет метод в SQL-транзакцию.
    # Если внутри упадёт исключение — все изменения откатятся (ROLLBACK).
    # Без: товар создался, а categories/tags не привязались → битые данные.
    @transaction.atomic
    def create_product(
        *,
        name: str,
        brand_id: int,
        primary_category_id: int,
        description: str = '',
        manufacturer_code: str = '',
        status: str = ProductStatus.DRAFT,
        is_featured: bool = False,
        category_ids: list[int] | None = None,
        tag_ids: list[int] | None = None,
    ) -> Product:
        """
        Создаёт товар с категориями и тегами.
        Slug генерируется автоматически в save().

        ПОЧЕМУ НЕ ЧЕРЕЗ SERIALIZER.save():
            Serializer.save() вызывает Model.save() напрямую.
            Но нам нужно: валидация бренда/категории + M2M + логирование.
            Сервис инкапсулирует ВСЮ логику создания.

        ПОЧЕМУ brand_id, А НЕ brand:
            API принимает id (целое число), не объект.
            Преобразование id → объект внутри сервиса — инкапсуляция.
        """
        # Если None — пустой список. Без: category_ids.append() → TypeError.
        if category_ids is None:
            category_ids = []

        if tag_ids is None:
            tag_ids = []

        # ─── Валидация существования бренда ───
        # .exists() — SELECT 1 WHERE ... LIMIT 1 — быстрый запрос.
        # Не используем get() — нам не нужен объект бренда,
        # только факт существования.
        if not Brand.objects.filter(pk=brand_id, is_active=True).exists():
            # ValidationError → DRF вернёт HTTP 400 с деталями.
            # {'brand': ...} — привязка ошибки к полю формы.
            raise ValidationError({'brand': 'Бренд не найден или неактивен.'})

        # ─── Валидация существования главной категории ───
        if not Category.objects.filter(pk=primary_category_id, is_active=True).exists():
            raise ValidationError({'primary_category': 'Категория не найдена или неактивна.'})

        # Создаём объект товара (в памяти, SQL ещё нет!).
        # brand_id=brand_id — прямая установка FK через _id,
        # без SELECT к brand (мы уже проверили существование выше).
        # status=status — по умолчанию DRAFT (неактивен до модерации).
        product = Product(
            name=name,
            brand_id=brand_id,
            primary_category_id=primary_category_id,
            description=description,
            manufacturer_code=manufacturer_code,
            status=status,
            is_featured=is_featured,
        )
        # .save() — INSERT INTO catalog_product (...) VALUES (...)
        # Срабатывает сигнал post_save → обновляется search_vector.
        # Slug генерируется внутри save() через slug_service.
        product.save()

        # M2M: product.categories.set([1,2,3])
        # Без проверки if — set([]) удалит все привязки!
        # .set() заменяет весь список (не добавляет!).
        if category_ids:
            product.categories.set(category_ids)

        if tag_ids:
            product.tags.set(tag_ids)

        # Логируем создание — для мониторинга и отладки.
        # extra — структурированные данные для logstash/datadog.
        # product.pk — внутренний id, str(product.uuid) — публичный.
        logger.info(
            'product_created',
            extra={'product_id': product.pk, 'uuid': str(product.uuid)},
        )

        return product

    @staticmethod
    # @transaction.atomic — если обновление поля упадёт,
    # товар останется в предыдущем состоянии (ROLLBACK).
    @transaction.atomic
    def update_product(
        product: Product,
        *,
        # Все параметры Optional (None) — PATCH, а не PUT.
        # None = «не менять это поле».
        name: str | None = None,
        description: str | None = None,
        brand_id: int | None = None,
        primary_category_id: int | None = None,
        manufacturer_code: str | None = None,
        status: str | None = None,
        is_featured: bool | None = None,
        category_ids: list[int] | None = None,
        tag_ids: list[int] | None = None,
    ) -> Product:
        """
        Обновляет поля товара. None = не менять.

        ПОЧЕМУ НЕ product.save() НАПРЯМУЮ:
            Нужна валидация brand_id/category_id + логирование.
            Без сервиса: кто угодно может передать неактивный brand_id.

        ПОЧЕМУ ПРОВЕРЯЕМ is not None, А НЕ if value:
            Пустая строка '' или 0 — допустимые значения!
            if description: → '' считается False → поле не обновится.
            if description is not None: → '' обновит поле (очистит).
        """

        if name is not None:
            product.name = name

        if description is not None:
            product.description = description

        # ─── Обновление бренда с валидацией ───
        if brand_id is not None:
            # Проверяем что новый бренд существует и активен.
            if not Brand.objects.filter(pk=brand_id, is_active=True).exists():
                raise ValidationError({'brand': 'Бренд не найден или неактивен.'})
            # brand_id=brand_id — прямой FK, без загрузки объекта Brand.
            product.brand_id = brand_id

        # ─── Обновление главной категории с валидацией ───
        if primary_category_id is not None:
            if not Category.objects.filter(pk=primary_category_id, is_active=True).exists():
                raise ValidationError({'primary_category': 'Категория не найдена или неактивна.'})
            product.primary_category_id = primary_category_id

        if manufacturer_code is not None:
            product.manufacturer_code = manufacturer_code

        if status is not None:
            product.status = status

        if is_featured is not None:
            product.is_featured = is_featured

        # .save() — UPDATE catalog_product SET ... WHERE id = ...
        # Сработает сигнал post_save → search_vector обновится
        # если изменилось name или description.
        product.save()

        # M2M: если передали category_ids — заменяем полностью.
        # .set([1,2]) → удалит старые привязки, добавит новые.
        # Если передали [] — отвяжет все категории.
        if category_ids is not None:
            product.categories.set(category_ids)

        if tag_ids is not None:
            product.tags.set(tag_ids)

        logger.info(
            'product_updated',
            extra={'product_id': product.pk},
        )

        return product

    @staticmethod
    def increment_product_views(product: Product) -> None:
        """
        Атомарно +1 просмотр.

        ПОЧЕМУ НЕ product.views_count += 1; product.save():
            Два параллельных запроса прочитают views_count=10,
            оба запишут 11 → потерян 1 просмотр!
            product.increment_views() использует F('views_count') + 1 —
            атомарная операция на уровне SQL:
            UPDATE ... SET views_count = views_count + 1
        """
        # Делегируем модели — инкапсуляция бизнес-правила.
        product.increment_views()

    @staticmethod
    def set_product_prices(
        product: Product,
        *,
        min_price: Decimal | None,
        max_price: Decimal | None,
    ) -> Product:
        """
        Обновляет денормализованные min_price / max_price на Product.

        Это ЕДИНСТВЕННАЯ точка mutation цен товара в bounded context
        `catalog`. Она принимает УЖЕ РАССЧИТАННЫЕ значения и только
        записывает их в catalog.Product.

        ARCH-001 (Pricing → Catalog ownership):
          • Расчёт min_price/max_price — ответственность `pricing`
            (PricingService собирает цены активных вариантов и передаёт
            результат сюда).
          • `catalog` НЕ читает и НЕ ищет цены из `pricing` — никакой
            обратной зависимости catalog → pricing нет.
          • `pricing` не имеет права мутировать `catalog.Product`
            напрямую, поэтому вызывает этот публичный контракт.

        АЛГОРИТМ:
          1. product.min_price = переданное значение (None = цен нет).
          2. product.max_price = переданное значение.
          3. Сохранить ТОЛЬКО эти поля (не трогаем name/rating/...).
        """
        product.min_price = min_price
        product.max_price = max_price
        product.save(update_fields=['min_price', 'max_price', 'updated_at'])

        logger.debug(
            'product_prices_updated',
            extra={
                'product_id': product.pk,
                'min_price': str(product.min_price),
                'max_price': str(product.max_price),
            },
        )
        return product

    @staticmethod
    def set_review_stats(
        product: Product,
        *,
        rating: Decimal | int | str,
        reviews_count: int,
    ) -> Product:
        """
        Обновляет денормализованные rating / reviews_count на Product.

        Это авторитетный service-level путь записи review-агрегатов
        товара в bounded context `catalog` (ARCH-001 Stage C1). Он
        принимает УЖЕ РАССЧИТАННЫЕ значения и только записывает их в
        catalog.Product.

        ARCH-001 (Reviews → Catalog ownership):
          • Расчёт агрегатов AVG(rating)/COUNT по одобренным отзывам —
            domain knowledge `reviews`
            (ReviewService.recalculate_product_rating собирает значения
            из СВОИХ данных Review и передаёт результат сюда).
          • `catalog` владеет записью собственных полей: на сервисном
            уровне Product.rating / Product.reviews_count мутируются
            ТОЛЬКО здесь.
          • `catalog` НЕ читает и НЕ ищет отзывы `reviews` — никакой
            обратной зависимости catalog → reviews нет.
          • `reviews` не имеет права мутировать `catalog.Product`
            напрямую, поэтому вызывает этот публичный контракт.

        ARCH-001 H2 дополняет service-level ownership защитой Admin-
        поверхности: ProductAdmin показывает эти поля как read-only и
        отклоняет forced save, а ReviewAdmin направляет aggregate-
        affecting изменения Review через ReviewService. Это не является
        database-level enforcement и не меняет контракт этого метода.

        ГРАНИЦЫ ЗНАЧЕНИЙ — зеркалят валидаторы полей catalog.Product
        (rating: Decimal(3,2), 0.00..5.00; reviews_count: >= 0):
        знание о допустимых значениях ПОЛЕЙ каталога принадлежит
        каталогу, а не вызывающему контексту.

        АЛГОРИТМ:
          1. Провалидировать rating (0.00..5.00) и reviews_count (>= 0).
          2. product.rating / product.reviews_count = переданные значения.
          3. Сохранить ТОЛЬКО эти поля (не трогаем name/min_price/...).

        Внешнюю транзакцию owns вызывающий код (review-сервис); метод
        сознательно не открывает свою (никаких вложенных независимых
        транзакций) и сам строк не блокирует. ARCH-001 H1: конкурентная
        защита обеспечивается вызывающим review-слоем —
        ReviewService.recalculate_product_rating() захватывает
        SELECT ... FOR UPDATE на authoritative Product ДО расчёта
        агрегатов и держит лок до COMMIT общей транзакции; запись
        здесь выполняется уже под этим локом, поэтому конкурентные
        пересчёты одного товара сериализованы (lost update невозможен).
        """
        if not isinstance(rating, Decimal):
            try:
                rating = Decimal(str(rating))
            except ArithmeticError:
                raise ValidationError(
                    {'rating': 'Рейтинг должен быть числом.'},
                )

        # Специальные значения Decimal (NaN, ±Infinity и т.п.)
        # отклоняются предусмотренным ValidationError: публичный
        # сервисный контракт не должен «протекать»
        # decimal.InvalidOperation (сравнение с NaN / quantize
        # бесконечности падают на уровне decimal).
        if not rating.is_finite():
            raise ValidationError(
                {'rating': 'Рейтинг должен быть конечным числом.'},
            )

        # Поле rating — numeric(3,2): приводим к 2 знакам до записи.
        # Значения с непредставимым порядком величины (напр. 1E+30)
        # не влезают в numeric(3,2) — тоже предусмотренная ошибка,
        # а не InvalidOperation наружу.
        try:
            rating = rating.quantize(Decimal('0.01'))
        except ArithmeticError:
            raise ValidationError(
                {'rating': 'Рейтинг должен быть от 0.00 до 5.00.'},
            )

        # 0.00..5.00 — границы валидаторов поля catalog.Product.rating.
        if rating < Decimal('0.00') or rating > Decimal('5.00'):
            raise ValidationError(
                {'rating': 'Рейтинг должен быть от 0.00 до 5.00.'},
            )

        try:
            reviews_count = int(reviews_count)
        except (TypeError, ValueError):
            raise ValidationError(
                {'reviews_count': 'Количество отзывов должно быть целым числом.'},
            )

        if reviews_count < 0:
            raise ValidationError(
                {'reviews_count': 'Количество отзывов не может быть отрицательным.'},
            )

        product.rating = rating
        product.reviews_count = reviews_count
        product.save(update_fields=['rating', 'reviews_count', 'updated_at'])

        logger.debug(
            'product_review_stats_updated',
            extra={
                'product_id': product.pk,
                'rating': str(product.rating),
                'reviews_count': product.reviews_count,
            },
        )
        return product

    # ----------------------------------------------------------
    # Варианты: catalog-owned мутации price-relevant состояния
    # ----------------------------------------------------------

    @staticmethod
    def set_variant_active(variant: ProductVariant, *, is_active: bool) -> ProductVariant:
        """
        Меняет is_active варианта. ТОЛЬКО мутация каталога.

        ARCH-001 Stage 2: цены здесь НЕ пересчитываются — каталог не
        умеет считать price bounds (не читает pricing). Оркестрацию
        «мутация + пересчёт» выполняет владелец цен:
        PricingService.set_variant_active() (явный service-вызов,
        ARCHITECTURE.md → Cross-Domain Coordination).

        ИЗМЕНЕНИЕ ЭТОГО МЕТОДА В ОБХОД СЕРВИСА PRICING (admin, raw ORM)
        ОСТАВЛЯЕТ min_price/max_price ТОВАРА УСТАРЕВШИМИ ДО СЛЕДУЮЩЕЙ
        ОПЕРАЦИИ С ЦЕНАМИ — так задумано (осознанный trade-off
        однонаправленной архитектуры, см. ARCHITECTURE.md).
        """
        variant.is_active = is_active
        variant.save(update_fields=['is_active', 'updated_at'])

        logger.debug(
            'variant_activity_updated',
            extra={'variant_id': variant.pk, 'is_active': is_active},
        )
        return variant

    @staticmethod
    def delete_variant(variant: ProductVariant) -> None:
        """
        Удаляет вариант. ТОЛЬКО мутация каталога (аналогично
        set_variant_active: пересчёт цен — обязанность PricingService,
        см. PricingService.delete_variant()).
        """
        variant_id = variant.pk
        variant.delete()

        logger.debug(
            'variant_deleted',
            extra={'variant_id': variant_id},
        )

    # ----------------------------------------------------------
    # Категории
    # ----------------------------------------------------------

    @staticmethod
    def get_category_tree():
        """
        Возвращает корневые категории с детьми.
        treebeard MP_Node: get_root_nodes() + recursive children.

        ПОЧЕМУ get_root_nodes():
            treebeard Materialized Path — у каждого узла есть путь (path).
            Корневые = path глубины 1 (depth=1).
            get_root_nodes() — SELECT * WHERE depth=1 — один запрос.

        ЧТО БУДЕТ БЕЗ:
            Category.objects.all() — все категории плоским списком,
            без иерархии. Frontend не построит дерево навигации.
        """
        # MP_Node.get_root_nodes() — метод treebeard.
        # Возвращает QuerySet корневых узлов (depth=1).
        return Category.get_root_nodes()

    @staticmethod
    def get_category_by_slug(slug: str) -> Category:
        """
        Возвращает категорию по slug.

        ПОЧЕМУ НЕ get_object_or_404:
            Мы хотим NotFound (DRF) вместо Http404 (Django).
            DRF NotFound → JSON {"detail": "..."} (API-friendly).
            Http404 → HTML-страница 404 (не подходит для API).
        """
        try:
            return Category.objects.get(slug=slug, is_active=True)
        except Category.DoesNotExist:
            raise NotFound('Категория не найдена.')

    @staticmethod
    def get_category_breadcrumbs(category: Category) -> list[dict]:
        """
        Возвращает цепочку предков для breadcrumbs.
        Использует get_ancestors() от treebeard — один запрос.

        ПОЧЕМУ get_ancestors, А НЕ РЕКУРСИЯ ВВЕРХ ПО parent:
            Materialized Path хранит полный путь в поле path.
            get_ancestors() — один SQL-запрос:
            SELECT * WHERE path IN ('0001', '00010001', '000100010001')
            Без: N запросов (по одному на каждого предка).

        ПОЧЕМУ + [category] В КОНЦЕ:
            get_ancestors() НЕ включает саму категорию, только предков.
            Но breadcrumb: «Главная > Электроника > Смартфоны» —
            последняя ссылка = текущая категория.
        """
        # Список предков + сама категория = полная цепочка.
        # list() — выполнить SQL сейчас (не lazy).
        ancestors = list(category.get_ancestors()) + [category]
        # Возвращаем list[dict] — список словарей с данными для UI.
        # Каждый элемент = шаг в навигации.
        return [
            {
                # name — отображаемое имя: «Электроника»
                'name': a.name,
                # slug — для генерации URL: /catalog/elektronika/
                'slug': a.slug,
                # url_path — полный путь: /catalog/elektronika/smartfony/
                # Используется для <a href="{{ url_path }}">
                'url_path': a.url_path,
            }
            for a in ancestors
        ]

    # ----------------------------------------------------------
    # Бренды
    # ----------------------------------------------------------

    @staticmethod
    def get_active_brands():
        """
        Все активные бренды.

        ПОЧЕМУ НЕ getAll:
            show_inactive_brands в настройках → нет.
            Бренды фильтруются по is_active=True — неактивные
            (заброшенные, тестовые) не утекут в API.

        ПОЧЕМУ order_by('name'):
            Алфавитный порядок — удобно для фильтра в sidebar:
            «Acer, Apple, Asus, Bose, Canon...»
        """
        return Brand.objects.filter(is_active=True).order_by('name')

    @staticmethod
    def get_brand_by_slug(slug: str) -> Brand:
        """
        Возвращает бренд по slug.

        ПОЧЕМУ НЕ get_object_or_404:
            DRF NotFound для API-консистентности.
        """
        try:
            return Brand.objects.get(slug=slug, is_active=True)
        except Brand.DoesNotExist:
            raise NotFound('Бренд не найден.')

    # ----------------------------------------------------------
    # Теги
    # ----------------------------------------------------------

    @staticmethod
    def get_active_tags():
        """
        Все активные теги.

        ПОЧЕМУ ТАКОЙ КОРОТКИЙ МЕТОД:
            Может показаться избыточным — одна строка.
            Но: через месяц добавится кэширование / фильтрация
            по количеству товаров / etc. Метод уже есть —
            просто добавляем логику. Без метода — правим все views.
        """
        return Tag.objects.filter(is_active=True).order_by('name')
