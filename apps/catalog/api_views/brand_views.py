# ────────────────────────────────────────────────────────────
# Views для брендов (Brand) — API-эндпоинты.
#
# ДВА ЭНДПОИНТА:
#   BrandListView   — GET /api/v1/catalog/brands/          (список)
#   BrandDetailView — GET /api/v1/catalog/brands/{slug}/   (детали)
#
# Оба эндпоинта публичные (AllowAny) — бренды видны без авторизации.
#
# ЧТО БУДЕТ, ЕСЛИ УДАЛИТЬ ФАЙЛ:
#   GET /api/v1/catalog/brands/ → 404 (URL не найдёт view).
# ────────────────────────────────────────────────────────────

# logging — структурированное логирование.
import logging

# AllowAny — доступ без авторизации (публичный каталог).
from rest_framework.permissions import AllowAny

# Response — JSON-ответ DRF.
from rest_framework.response import Response

# APIView — базовый класс DRF для API.
from rest_framework.views import APIView

# Сериализаторы брендов для преобразования ORM → JSON.
from apps.catalog.serializers import BrandListSerializer, BrandDetailSerializer

# CatalogService — бизнес-логика каталога (содержит методы для брендов).
from apps.catalog.services.catalog_service import CatalogService

# drf-spectacular — опциональная зависимость для OpenAPI документации.
# try/except — если не установлена, декораторы-заглушки не ломают проект.
try:
    from drf_spectacular.utils import extend_schema, extend_schema_view
except ImportError:
    # Заглушки: decorate(func) → func (без изменений).
    def extend_schema(**kwargs):
        def decorator(func):
            return func
        return decorator

    def extend_schema_view(**kwargs):
        def decorator(cls):
            return cls
        return decorator

# Логгер с именем модуля.
logger = logging.getLogger(__name__)


# @extend_schema_view — декоратор для документации OpenAPI.
# get=extend_schema(...) — описывает GET-метод для Swagger UI.
@extend_schema_view(
    get=extend_schema(
        summary='Список брендов',
        description='Все активные бренды. Используется для фильтров каталога.',
    ),
)
class BrandListView(APIView):
    """
    GET /api/v1/catalog/brands/

    Все активные бренды. Лёгкий запрос — для фильтров.

    ПОЧЕМУ AllowAny:
        Фильтр брендов в каталоге — публичная функция.
        Незарегистрированный пользователь тоже может фильтровать по бренду.
    """

    # Публичный доступ — без JWT-токена.
    permission_classes = (AllowAny,)

    def get(self, request):
        """
        Возвращает список всех активных брендов.

        ПОТОК ДАННЫХ:
            1. Service: получить QuerySet активных брендов
            2. Serializer: конвертировать в JSON
            3. Response: вернуть клиенту

        ПОЧЕМУ НЕТ ПАГИНАЦИИ:
            Брендов обычно 10-100 — весь список помещается в один ответ.
            Пагинация добавила бы сложность без пользы.
            Если брендов станет >1000 — добавим пагинацию.
        """
        # CatalogService.get_active_brands() —
        # Brand.objects.filter(is_active=True).order_by('name')
        brands = CatalogService.get_active_brands()
        # many=True — сериализируем QuerySet (много объектов).
        serializer = BrandListSerializer(brands, many=True)
        # serializer.data — Python dict/list, Response() → JSON.
        return Response(serializer.data)


@extend_schema_view(
    get=extend_schema(
        summary='Детали бренда',
        description='Полная информация о бренде + количество товаров.',
    ),
)
class BrandDetailView(APIView):
    """
    GET /api/v1/catalog/brands/{slug}/

    Страница бренда с количеством товаров.
    """

    permission_classes = (AllowAny,)

    def get(self, request, slug: str):
        """
        slug — из URL path (Django конвертер <slug:slug>).
        Валидируется на уровне роутинга — только [a-z0-9-]+.
        """
        # Получаем бренд по slug (CatalogService проверяет is_active).
        brand = CatalogService.get_brand_by_slug(slug)

        # ─── Динамическое поле: количество товаров бренда ───
        # products_count — НЕ поле модели Brand, оно вычисляется на лету.
        # Lazy-импорт Product — чтобы не загружать модель при импорте модуля.
        from apps.catalog.models import Product
        # Product.objects.for_brand(brand) — метод QuerySet:
        # .active().filter(brand=brand)
        # .count() — SELECT COUNT(*) — быстрый запрос.
        products_count = Product.objects.for_brand(brand).count()
        # setattr — добавляет атрибут к объекту бренда В ПАМЯТИ.
        # В БД ничего не сохраняется — это только для сериализации.
        # BrandDetailSerializer читает brand.products_count.
        setattr(brand, 'products_count', products_count)

        # Сериализуем бренд с динамическим products_count.
        serializer = BrandDetailSerializer(brand)
        return Response(serializer.data)
