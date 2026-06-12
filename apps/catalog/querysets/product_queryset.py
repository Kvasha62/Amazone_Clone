# ────────────────────────────────────────────────────────────
# QuerySet товара — набор методов для построения оптимальных
# SQL-запросов к таблице catalog_product.
#
# АРХИТЕКТУРНЫЙ ПРИНЦИП:
#   Каждый метод возвращает НОВЫЙ QuerySet (не выполняет запрос),
#   что позволяет цепочить вызовы:
#       Product.objects.visible().with_related().order_by('-rating')
#
#   Это называется «composability» (компонуемость):
#   каждый метод добавляет свой фильтр / prefetch, не дублируя другие.
#   Без этого паттерна пришлось бы писать огромные методы
#   с десятками параметров-флагов (if with_images: qs = ...).
#
# ПОЧЕМУ ОТДЕЛЬНЫЙ ФАЙЛ, А НЕ ВНУТРИ MANAGER:
#   Django разделяет QuerySet (методы, возвращающие qs)
#   и Manager (точка входа .objects).
#   ProductManager комбинирует QuerySet через
#   ProductManager.from_queryset(ProductQuerySet),
#   чтобы методы qs стали доступны через Product.objects.active().
#
# ЧТО БУДЕТ, ЕСЛИ УДАЛИТЬ ФАЙЛ:
#   Product.objects.active()  → AttributeError
#   Product.objects.catalog() → AttributeError
#   Все API-эндпоинты каталога перестанут работать.
# ────────────────────────────────────────────────────────────

# models.QuerySet — базовый класс Django для построения SQL-запросов.
# Даёт filter(), exclude(), annotate(), select_related() и т.д.
# Без этого импорта не от чего наследовать наш кастомный QuerySet.
from django.db import models

# Prefetch — инструмент для кастомного prefetch_related.
# Позволяет подсунуть свой QuerySet вместо стандартного,
# чтобы prefetch делал только нужные записи с нужными полями.
# Q — объект для построения сложных OR/AND условий в filter().
# Без Prefetch variants подтягивались бы ВСЕ (включая is_active=False).
# Без Q нельзя выразить «published_at IS NULL OR published_at <= now()».
from django.db.models import Prefetch, Q

# Импортируем Enum-статусы товара из констант модуля.
# Используем класс, а не строку 'active', чтобы:
#   1) IDE подсказывала значения (автодополнение)
#   2) Опечатка в статусе → ошибка на старте, а не в проде
#   3) Единое место изменения (DRY) — если статус переименуется
# Без: filter(status='active') — хардкод строки, риск опечатки.
from apps.catalog.constants import ProductStatus


class ProductQuerySet(models.QuerySet):
    """
    QuerySet товара. Оптимизирует выборку для каталога и API.

    Методы строятся по принципу composability:
        Product.objects.visible().with_related().order_by('-rating')
    Каждый метод добавляет свой фильтр / prefetch, не дублируя другие.
    """

    # ----------------------------------------------------------
    # Фильтрация по статусу
    # ----------------------------------------------------------

    def active(self):
        """
        Только активные товары (status='active').
        Это PRIMARY фильтр для всего каталога.

        ПОЧЕМУ НЕ ПРОСТО filter(status='active') В КАЖДОМ МЕТОДЕ:
            DRY — если статус 'active' изменится на 'published',
            меняем только ProductStatus.ACTIVE. Без этого — ищи
            по всему проекту.

        ЧТО БУДЕТ БЕЗ ЭТОГО МЕТОДА:
            Каждый потребитель писал бы .filter(status=ProductStatus.ACTIVE)
            самостоятельно, дублируя логику.
        """
        # filter() возвращает новый QuerySet (не выполняет SQL!).
        # SQL будет выполнен только при итерации / list() / len().
        # ProductStatus.ACTIVE = 'active' — из констант.
        return self.filter(status=ProductStatus.ACTIVE)

    def visible(self):
        """
        Товары, видимые в каталоге:
          - status = ACTIVE
          - primary_category активна
          - published_at в прошлом или NULL

        ПОЧЕМУ ТРИ УСЛОВИЯ, А НЕ ОДНО:
            Достаточно только active() — но товар может быть active
            при неактивной категории (админ деактивировал категорию).
            published_at позволяет запланировать публикацию товара
            на будущую дату (отложенная публикация).

        ЧТО БУДЕТ БЕЗ is_active=True НА КАТЕГОРИИ:
            Товары из деактивированных категорий появятся в каталоге.
            Пользователь перейдёт → категория «Электроника» отключена,
            но товары из неё показываются — нелогично.

        ЧТО БУДЕТ БЕЗ published_at ПРОВЕРКИ:
            Запланированные товары (published_at = завтра) появятся
            раньше времени — утечка информации о новинках.
        """
        # Lazy-импорт timezone — чтобы избежать циклического импорта
        # и не загружать модуль timezone при импорте queryset.
        # timezone.now() возвращает datetime с учётом USE_TZ=True из settings.
        from django.utils import timezone

        # .active() — вызываем наш же метод (composability!)
        # .filter(primary_category__is_active=True) — JOIN к catalog_category,
        # проверяем что главная категория товара активна.
        # __ (двойное подчёркивание) — синтаксис Django для навигации по связям.
        return self.active().filter(
            primary_category__is_active=True,
        # Второй .filter() — отдельный AND-фильтр.
        # Не объединяем в один .filter() потому что Q с OR
        # логически отдельное условие — читаемость лучше.
        ).filter(
            # Q() — объект для OR-условий.
            # published_at__isnull=True → ещё не опубликован (NULL = нет даты)
            # published_at__lte=timezone.now() → дата публикации в прошлом
            # Знак | (pipe) = OR в Django Q-объектах.
            # Без Q пришлось бы писать raw SQL или два отдельных запроса.
            Q(published_at__isnull=True)
            | Q(published_at__lte=timezone.now()),
        )

    def featured(self):
        """
        Рекомендуемые товары (is_featured=True).

        ПОЧЕМУ .active(), А НЕ НАПРЯМУЮ filter(is_featured=True):
            Рекомендуемым может быть и DRAFT-товар — мы этого не хотим.
            Поэтому сначала фильтруем по active, потом по featured.

        ЧТО БУДЕТ БЕЗ ЭТОГО МЕТОДА:
            Придётся везде писать:
            Product.objects.filter(status='active', is_featured=True)
        """
        # .active() — гарантируем что товар опубликован,
        # .filter(is_featured=True) — только рекомендуемые.
        return self.active().filter(is_featured=True)

    # ----------------------------------------------------------
    # Фильтрация по связям
    # ----------------------------------------------------------

    def for_category(self, category):
        """
        Товары в категории. Ищет по M2M categories,
        чтобы учесть все привязки товара.

        ПОЧЕМУ M2M (categories), А НЕ FK (primary_category):
            Товар может быть в нескольких категориях:
            «iPhone» → «Смартфоны» + «Электроника» + «Apple».
            primary_category — только для сортировки/отображения,
            а M2M categories — для фильтрации.

        АРГУМЕНТ category — ЭТО ОБЪЕКТ Category, НЕ id.
            Передаём объект, не pk — Django сам извлечёт pk
            и подставит в SQL: WHERE catalog_product_categories.category_id = X.

        ЧТО БУДЕТ БЕЗ ЭТОГО МЕТОДА:
            Нельзя фильтровать товары по категории из QuerySet API.
        """
        # categories — M2M-поле, Django создаст промежуточную таблицу
        # catalog_product_categories и сделает JOIN к ней.
        return self.active().filter(categories=category)

    def for_brand(self, brand):
        """
        Товары бренда.

        ПОЧЕМУ НЕ for_brand_id(brand_id):
            Удобнее передавать объект: Brand.objects.get(slug='nike')
            Django автоматически извлечёт pk. Но можно и по id:
            .filter(brand_id=brand_id) — без JOIN, быстрее.
            Мы передаём объект для единообразия с for_category().

        ЧТО БУДЕТ БЕЗ: duplicate filter(brand=X) по всему проекту.
        """
        # brand — FK-поле, Django сделает простой WHERE brand_id = X
        # (без JOIN, только фильтр по id).
        return self.active().filter(brand=brand)

    # ----------------------------------------------------------
    # Фильтрация по цене
    # ----------------------------------------------------------

    def price_range(self, min_price=None, max_price=None):
        """
        Фильтрация по денормализованной цене.
        Работает с min_price/max_price на Product — без JOIN к вариантам.

        ПОЧЕМУ ДЕНОРМАЛИЗАЦИЯ, А НЕ JOIN К ВАРИАНТАМ:
            У товара может быть 10+ вариантов с ценами.
            JOIN + MIN/MAX на лету = тяжёлый запрос при 100К товаров.
            Денормализованные min_price/max_price на Product позволяют
            фильтровать без JOIN — индекс по min_price работает мгновенно.

        ЧТО БУДЕТ БЕЗ: 3+ JOIN для фильтрации по цене = медленно.

        ПОЧЕМУ min_price=None ПО УМОЛЧАНИЮ:
            Если None — условие не применяется (показать все).
            Это позволяет вызывать price_range(min_price=100),
            price_range(max_price=5000), или price_range(100, 5000).
        """
        # Начинаем с self — немодифицированного QuerySet.
        # Если оба параметра None — вернётся self без изменений.
        qs = self
        # min_price__gte — «greater than or equal» (>=).
        # __gte — Django lookup, транслируется в SQL: WHERE min_price >= X.
        # gte, а не gt (>): если товар стоит ровно 100₽,
        # при min_price=100 он должен показываться.
        if min_price is not None:
            qs = qs.filter(min_price__gte=min_price)
        # max_price__lte — «less than or equal» (<=).
        # lte, а не lt (<): если max_price=5000 и товар стоит 5000₽ —
        # он должен показываться (включительно).
        if max_price is not None:
            qs = qs.filter(max_price__lte=max_price)
        # Возвращаем модифицированный QuerySet (SQL ещё не выполнен!).
        return qs

    # ----------------------------------------------------------
    # Полнотекстовый поиск
    # ----------------------------------------------------------

    def search(self, query: str):
        """
        Полнотекстовый поиск через SearchVectorField + GIN-индекс.
        Мгновенный на миллионах записей (в отличие от __icontains).

        ПОЧЕМУ НЕ __icontains:
            icontains = ILIKE '%query%' — полное сканирование таблицы.
            На 1М записей — 2-5 секунд.
            SearchVector + GIN-индекс = 5-20мс на тех же данных.

        СОВМЕСТИМОСТЬ С SQLITE:
            SearchVector работает ТОЛЬКО с PostgreSQL.
            При использовании SQLite — fallback на __icontains
            (медленнее, но работает для локальной разработки и тестов).
        """
        # Пустой запрос → не применяем фильтр → возвращаем всё.
        if not query:
            return self

        from django.db import connection

        if connection.vendor == 'postgresql':
            # PostgreSQL: используем GIN-индекс через SearchVectorField.
            # filter(search_vector=query) — PostgreSQL приводит строку к tsquery.
            return self.filter(search_vector=query)
        else:
            # SQLite / другие БД: fallback на icontains.
            # Ищем по name и description — медленнее, но совместимо.
            from django.db.models import Q
            return self.filter(
                Q(name__icontains=query) | Q(description__icontains=query)
            )

    # ----------------------------------------------------------
    # Оптимизация запросов (prefetch / select_related)
    # ----------------------------------------------------------

    def with_related(self):
        """
        Подтягивает основные связи для listing / карточки.
        Один-два запроса вместо N+1.

        select_related — JOIN в том же запросе (FK / OneToOne).
        Без этого: каждый доступ к product.brand — отдельный SQL.
        Для 50 товаров на странице = 50+1 = 51 запрос вместо 1.

        ПОЧЕМУ ИМЕННО ЭТИ СВЯЗИ:
            brand — нужен для бренда в карточке/листинге.
            primary_category — категория товара.
            main_image — главное изображение (OneToOne-подобие через FK).
            Это минимальный набор для отображения товара.
        """
        # select_related — JOIN (один SQL-запрос).
        # 'brand' — FK к catalog_brand.
        # 'primary_category' — FK к catalog_category.
        # 'main_image' — FK к catalog_productimage (nullable, может быть NULL).
        return self.select_related(
            'brand',
            'primary_category',
            'main_image',
        )

    def with_images(self):
        """
        Prefetch всех изображений товара.

        ПОЧЕМУ prefetch_related, А НЕ select_related:
            images — reverse FK (у одного товара много изображений).
            select_related не работает с reverse FK (OneToMany).
            prefetch_related — отдельный SELECT WHERE product_id IN (...).

        ЧТО БУДЕТ БЕЗ:
            product.images.all() → отдельный SQL на КАЖДЫЙ товар.
            50 товаров = 50 дополнительных запросов (проблема N+1).
        """
        # prefetch_related('images') — один дополнительный запрос:
        # SELECT * FROM catalog_productimage WHERE product_id IN (1,2,3...)
        return self.prefetch_related('images')

    def with_variants(self):
        """
        Prefetch активных вариантов с ценой и стоком.
        Lazy-импорт — избегаем циклов на старте Django.

        ПОЧЕМУ КАСОМНЫЙ Prefetch, А НЕ prefetch_related('variants'):
            Нам нужны ТОЛЬКО is_active=True варианты, и сразу
            с подтянутыми price и stock. Без кастомного QuerySet
            подтянулись бы ВСЕ варианты (включая неактивные)
            и без price/stock — ещё 2 запроса на каждый вариант.

        ПОЧЕМУ LAZY-ИМПОРТ:
            ProductVariant импортирует Product (FK).
            Product импортирует ProductQuerySet (этот файл).
            Без lazy: Product → ProductQuerySet → ProductVariant → Product → ♻️ цикл!
            Lazy-импорт разрывает цикл: импорт происходит при ВЫЗОВЕ,
            когда все модели уже загружены.

        ЧТО БУДЕТ БЕЗ select_related('price', 'stock'):
            Каждый variant.price — отдельный SQL-запрос.
            10 вариантов × 50 товаров = 500 запросов.
        """
        # Lazy-импорт модели — разрываем циклическую зависимость.
        # Если сделать from ... import ProductVariant наверху файла —
        # Django упадёт при старте с ImportError.
        from apps.catalog.models.product_variant import ProductVariant

        # Строим QuerySet для вариантов: только активные,
        # с подтянутыми price (FK к pricing).
        # stock будет добавлен когда inventory app будет создан.
        variants_qs = (
            ProductVariant.objects
            # Только is_active=True — неактивные варианты не нужны в каталоге.
            .filter(is_active=True)
            # select_related для price — JOIN в том же запросе.
            # price — FK к pricing.PriceVariant (pricing app).
            # stock — будет добавлен после создания inventory app:
            #   .select_related('price', 'stock')
            .select_related('price', 'stock')
        )

        # Prefetch с кастомным QuerySet — Django выполнит:
        # SELECT * FROM catalog_productvariant
        #   WHERE product_id IN (...) AND is_active = True
        # и подставит результаты в product.variants.all().
        return self.prefetch_related(
            Prefetch('variants', queryset=variants_qs),
        )

    def with_categories(self):
        """
        Prefetch M2M категорий товара.

        ПОЧЕМУ НУЖЕН ОТДЕЛЬНЫЙ МЕТОД:
            Категории нужны только на карточке товара (detail),
            но не в listing-списке. Разделяем для оптимизации:
            listing не тянет категории (экономим 1 запрос).

        ЧТО БУДЕТ БЕЗ:
            product.categories.all() → отдельный SQL с JOIN
            к промежуточной таблице на каждый товар.
        """
        # prefetch_related для M2M: Django выполнит
        # SELECT catalog_category.* FROM catalog_category
        #   INNER JOIN catalog_product_categories ON ...
        #   WHERE catalog_product_categories.product_id IN (...)
        return self.prefetch_related(
            'categories',
        )

    # ----------------------------------------------------------
    # Композитные методы
    # ----------------------------------------------------------

    def catalog(self):
        """
        Полный набор для listing-страниц каталога:
        видимые + связи + изображения + варианты.

        ПОЧЕМУ КОМПОЗИТНЫЙ МЕТОД:
            Listing-страница (список товаров) всегда нуждается
            в одних и тех же данных: visible-фильтр + все prefetch.
            Вместо того чтобы в каждой view писать 4 метода,
            делаем один композитный .catalog().

        ПОЧЕМУ visible(), А НЕ active():
            На listing-странице показываем только реально видимые
            товары (проверка категории + даты публикации).
            Если используем active() — появятся черновики из
            неактивных категорий.

        ПОЧЕМУ НЕ for_card():
            for_card() не фильтрует по visible (может понадобиться
            DRAFT-товар для staff). catalog() — публичный доступ.

        ЧТО БУДЕТ БЕЗ ЭТОГО МЕТОДА:
            В каждой view: Product.objects.visible().with_related()... — дублирование.
        """
        return (
            self.visible()        # Только видимые в каталоге
            .with_related()       # brand + primary_category + main_image (JOIN)
            .with_images()        # Все изображения (prefetch)
            .with_variants()      # Активные варианты с ценами (prefetch)
        )

    def for_card(self):
        """
        Минимальный набор для карточки товара:
        связи + изображения + варианты + категории.

        ОТЛИЧИЕ ОТ catalog():
            Нет visible() — карточка может быть показана для DRAFT
            (staff-доступ). И есть with_categories() — для хлебных крошек.

        ПОЧЕМУ НЕ ТЯНЕМ СПИСОК ТЕГОВ:
            Теги подтягиваются отдельно — они нужны не всегда.
            Если понадобятся — добавим with_tags().

        ЧТО БУДЕТ БЕЗ:
            N+1 запросы при открытии карточки товара.
        """
        return (
            self.with_related()    # brand + primary_category + main_image (JOIN)
            .with_images()         # Все изображения (prefetch)
            .with_variants()       # Активные варианты с ценами (prefetch)
            .with_categories()     # M2M категории для breadcrumbs
        )
