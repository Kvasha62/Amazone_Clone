# ────────────────────────────────────────────────────────────
# Views для категорий (Category) — API-эндпоинты.
#
# ДВА ЭНДПОИНТА:
#   CategoryTreeView   — GET /api/v1/catalog/categories/          (дерево)
#   CategoryDetailView — GET /api/v1/catalog/categories/{slug}/   (детали)
#
# Категории используют treebeard MP_Node — дерево Materialized Path.
# CategoryTreeView отдаёт ВСЁ дерево одним запросом (для навигации).
# CategoryDetailView — данные конкретной категории (для страницы).
#
# ЧТО БУДЕТ, ЕСЛИ УДАЛИТЬ ФАЙЛ:
#   GET /api/v1/catalog/categories/ → 404 (URL не найдёт view).
# ────────────────────────────────────────────────────────────

# logging — структурированное логирование.
import logging

# status — HTTP-статус коды DRF.
from rest_framework import status

# AllowAny — публичный доступ (каталог без авторизации).
from rest_framework.permissions import AllowAny

# Response — JSON-ответ DRF.
from rest_framework.response import Response

# APIView — базовый класс DRF для API-эндпоинтов.
from rest_framework.views import APIView

# Сериализаторы категорий для преобразования ORM → JSON.
from apps.catalog.serializers import (
    CategoryDetailSerializer,   # Полная информация о категории
    CategoryTreeSerializer,     # Рекурсивное дерево
    BreadcrumbSerializer,       # Цепочка навигации
)

# CatalogService — бизнес-логика (методы get_category_tree, get_category_by_slug, etc.)
from apps.catalog.services.catalog_service import CatalogService

# drf-spectacular — опциональная зависимость для OpenAPI документации.
# try/except: если не установлена — декораторы-заглушки (no-op).
try:
    from drf_spectacular.utils import extend_schema, extend_schema_view
except ImportError:
    def extend_schema(**kwargs):
        def decorator(func):
            return func
        return decorator

    def extend_schema_view(**kwargs):
        def decorator(cls):
            return cls
        return decorator

# Логгер модуля.
logger = logging.getLogger(__name__)


@extend_schema_view(
    get=extend_schema(
        summary='Дерево категорий',
        description='Возвращает полное дерево категорий каталога.',
    ),
)
class CategoryTreeView(APIView):
    """
    GET /api/v1/catalog/categories/

    Полное дерево категорий. Один запрос — вся иерархия.
    Используется в навигации, меню, breadcrumbs.

    ПОЧЕМУ AllowAny:
        Навигация по каталогу — публичная функция.
        Меню категорий видно даже незарегистрированным.

    ПОЧЕМУ НЕТ ПАГИНАЦИИ:
        Дерево категорий — иерархическая структура.
        Пагинация разрушит иерархию (покажет только часть дерева).
        Категорий обычно 50-200 — влезает в один ответ.
    """

    permission_classes = (AllowAny,)

    def get(self, request):
        """
        Возвращает рекурсивное дерево категорий.

        ПОТОК ДАННЫХ:
            1. Service: Category.get_root_nodes() — корневые категории
            2. Serializer: рекурсивная сериализация с children
            3. Response: JSON-дерево

        CategoryTreeSerializer рекурсивно обходит всех детей:
            root → get_children() → serializer(children) → ...
        """
        # get_category_tree() → Category.get_root_nodes()
        # Возвращает QuerySet корневых категорий (depth=1).
        tree_data = CatalogService.get_category_tree()
        # many=True — сериализируем QuerySet (все корни).
        # CategoryTreeSerializer сам вызовет get_children() для каждого корня
        # и рекурсивно сериализирует поддеревья.
        serializer = CategoryTreeSerializer(tree_data, many=True)
        return Response(serializer.data)


@extend_schema_view(
    get=extend_schema(
        summary='Детали категории',
        description='Возвращает информацию о категории + breadcrumbs + кол-во товаров.',
    ),
)
class CategoryDetailView(APIView):
    """
    GET /api/v1/catalog/categories/{slug}/

    Информация о категории с breadcrumbs и количеством товаров.
    """

    permission_classes = (AllowAny,)

    def get(self, request, slug: str):
        """
        slug — из URL path (<slug:slug> в urls.py).
        Валидируется Django: только [a-z0-9-]+.
        """
        # Получаем категорию по slug (сервис проверяет is_active=True).
        category = CatalogService.get_category_by_slug(slug)

        # ─── Добавляем breadcrumbs ───
        # get_category_breadcrumbs() возвращает список словарей:
        # [{'name': 'Электроника', 'slug': 'elektronika', 'url_path': '/catalog/elektronika/'}, ...]
        breadcrumbs = CatalogService.get_category_breadcrumbs(category)
        # setattr — добавляет динамический атрибут для сериализатора.
        # В БД не пишется — только в памяти объекта.
        setattr(category, 'breadcrumbs', breadcrumbs)

        # ─── Количество товаров в категории ───
        # Lazy-импорт — чтобы не загружать модель при импорте модуля.
        from apps.catalog.models import Product
        # for_category(category) — .active().filter(categories=category)
        # .count() — SELECT COUNT(*) — быстрая агрегация.
        products_count = Product.objects.for_category(category).count()
        setattr(category, 'products_count', products_count)

        # CategoryDetailSerializer сериализует:
        # - поля модели (name, slug, description, image, ...)
        # - динамические атрибуты (breadcrumbs, products_count)
        serializer = CategoryDetailSerializer(category)
        return Response(serializer.data)
