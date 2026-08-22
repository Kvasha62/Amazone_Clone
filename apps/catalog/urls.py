# ────────────────────────────────────────────────────────────
# urls.py — URL-маршруты для API каталога.
#
# ВСЕ МАРШРУТЫ ПОДКЛЮЧАЮТСЯ В config/urls.py:
#   path('api/v1/catalog/', include('apps.catalog.urls'))
#
# ПОЛНЫЙ СПИСОК ЭНДПОИНТОВ:
#   GET    /api/v1/catalog/products/                        — listing
#   POST   /api/v1/catalog/products/create/                 — создать (staff)
#   GET    /api/v1/catalog/products/{uuid или slug}/        — карточка
#   PATCH  /api/v1/catalog/products/{uuid}/update/          — обновить (staff)
#   GET    /api/v1/catalog/categories/                      — дерево категорий
#   GET    /api/v1/catalog/categories/{slug}/               — детали категории
#   GET    /api/v1/catalog/brands/                          — список брендов
#   GET    /api/v1/catalog/brands/{slug}/                   — детали бренда
#
# ПОЧЕМУ APIView, А НЕ ViewSet:
#   У нас не стандартный CRUD. Каждый эндпоинт имеет свою логику:
#   - listing с пагинацией и фильтрами
#   - detail с инкрементом просмотров
#   - create с staff-проверкой
#   ViewSet бы добавил ненужные методы (put, delete).
#
# ЧТО БУДЕТ, ЕСЛИ УДАЛИТЬ ФАЙЛ:
#   Все 8 URL-маршрутов каталога → 404.
# ────────────────────────────────────────────────────────────

# path — функция Django для определения URL-маршрутов.
from django.urls import path

# Импортируем все view-классы из api_views/__init__.py.
# Каждый view уже зарегистрирован через @extend_schema
# для Swagger-документации.
from apps.catalog.api_views import (
    BrandDetailView,
    BrandListView,
    CategoryDetailView,
    CategoryTreeView,
    ProductBySlugsView,
    ProductCreateView,
    ProductDetailView,
    ProductListView,
    ProductUpdateView,
)

# app_name — пространство имён для reverse():
#   reverse('catalog:product-list') → '/api/v1/catalog/products/'
# Без app_name: reverse('product-list') — риск конфликта имён
# с другими приложениями (users:product-list, cart:product-list).
app_name = 'catalog'

# URL-маршруты подключаются в config/urls.py:
#   path('api/v1/catalog/', include('apps.catalog.urls'))
# Таким образом полный URL = 'api/v1/catalog/' + путь из urlpatterns.

urlpatterns = [
    # ----------------------------------------------------------
    # Products
    # ----------------------------------------------------------

    # GET /api/v1/catalog/products/
    # Listing товаров с фильтрацией, поиском, пагинацией.
    # name='product-list' — для reverse() и Swagger.
    path('products/', ProductListView.as_view(), name='product-list'),

    # GET /api/v1/catalog/products/by-slugs/?slugs=slug1,slug2
    # Bulk lookup по slug'ам — для «Недавно просмотренных».
    # ВАЖНО: by-slugs/ ДОЛЖЕН быть ПЕРЕД <str:identifier>/
    # иначе 'by-slugs' будет воспринят как identifier (slug).
    path('products/by-slugs/', ProductBySlugsView.as_view(), name='product-by-slugs'),

    # POST /api/v1/catalog/products/create/
    # Создание нового товара (staff only).
    # ВАЖНО: create/ ДОЛЖЕН быть ПЕРЕД <str:identifier>/
    # иначе 'create' будет воспринят как identifier (slug).
    path('products/create/', ProductCreateView.as_view(), name='product-create'),

    # GET /api/v1/catalog/products/{identifier}/
    # identifier — UUID или slug. str — любой строковый паттерн.
    # ПОЧЕМУ str, А НЕ uuid: нужен поиск и по slug (SEO-URL).
    # Если бы只用 uuid: path('products/<uuid:uuid>/', ...)
    # → /products/iphone-15-pro/ не совпало бы (не UUID).
    path('products/<str:identifier>/', ProductDetailView.as_view(), name='product-detail'),

    # PATCH /api/v1/catalog/products/{uuid}/update/
    # uuid:uuid — Django валидирует что это UUID формат.
    # ПОЧЕМУ ОТДЕЛЬНЫЙ URL ДЛЯ UPDATE:
    #   /products/{uuid}/ — GET (detail)
    #   /products/{uuid}/update/ — PATCH (update)
    #   Разные URL → разные view → чистое разделение ответственности.
    #   Альтернатива: один URL + Router → но у нас APIView, не ViewSet.
    path('products/<uuid:uuid>/update/', ProductUpdateView.as_view(), name='product-update'),

    # ----------------------------------------------------------
    # Categories
    # ----------------------------------------------------------

    # GET /api/v1/catalog/categories/
    # Полное дерево категорий (для навигации).
    path('categories/', CategoryTreeView.as_view(), name='category-tree'),

    # GET /api/v1/catalog/categories/{slug}/
    # slug:slug — Django валидирует формат slug ([a-z0-9-]+).
    path('categories/<slug:slug>/', CategoryDetailView.as_view(), name='category-detail'),

    # ----------------------------------------------------------
    # Brands
    # ----------------------------------------------------------

    # GET /api/v1/catalog/brands/
    # Список всех активных брендов (для фильтров sidebar).
    path('brands/', BrandListView.as_view(), name='brand-list'),

    # GET /api/v1/catalog/brands/{slug}/
    # Детали бренда с количеством товаров.
    path('brands/<slug:slug>/', BrandDetailView.as_view(), name='brand-detail'),
]
