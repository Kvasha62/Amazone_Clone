# ────────────────────────────────────────────────────────────
# Сериализаторы брендов (Brand).
#
# ДВА СЕРИАЛИЗАТОРА:
#   BrandListSerializer — краткий (для listing / фильтров sidebar)
#   BrandDetailSerializer — полный (для страницы бренда)
#
# ПОЧЕМУ ДВА, А НЕ ОДИН:
#   Listing-страница показывает 50+ брендов в sidebar фильтра.
#   Тянуть description и logo для каждого — лишний трафик.
#   Detail-страница бренда — полный контент.
#
# ЧТО БУДЕТ, ЕСЛИ УДАЛИТЬ ФАЙЛ:
#   GET /api/v1/catalog/brands/ → ImportError (500).
# ────────────────────────────────────────────────────────────

# serializers — базовые классы DRF для сериализации.
from rest_framework import serializers

# Brand — модель бренда с полями: name, slug, description, logo, is_active.
from apps.catalog.models import Brand


class BrandListSerializer(serializers.ModelSerializer):
    """
    Бренд для listing-страниц / фильтров.

    ПОЧЕМУ НЕ ВСЕ ПОЛЯ:
        В sidebar фильтра каталога нужно только:
        id (для чекбокса), name (для подписи), slug (для URL),
        logo (для иконки). Описание не нужно — экономим трафик.
    """

    class Meta:
        model = Brand
        # id — для идентификации на frontend
        # name — «Apple», «Samsung»
        # slug — для URL фильтра: ?brand=apple
        # logo — URL логотипа (ImageField → URL автоматически)
        fields = ('id', 'name', 'slug', 'logo')
        # Все поля read-only — бренды создаются/редактируются через admin.
        # API не позволяет создавать бренды через POST.
        read_only_fields = fields


class BrandDetailSerializer(serializers.ModelSerializer):
    """
    Полная информация о бренде.

    ОТЛИЧИЕ ОТ BrandListSerializer:
        + description — текст о бренде
        + products_count — сколько товаров этого бренда
        (products_count — динамическое поле, не из модели)
    """

    # products_count — НЕ поле модели Brand.
    # Это динамическое значение, вычисляемое в view через:
    #   setattr(brand, 'products_count', count)
    # read_only=True — не ожидается в запросе, только в ответе.
    # IntegerField без source — берётся из obj.products_count.
    products_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Brand
        # Полный набор полей для страницы бренда.
        # description — HTML/текст описания бренда.
        # products_count — добавлен динамически (через setattr в view).
        fields = (
            'id',
            'name',
            'slug',
            'description',
            'logo',
            'products_count',
        )
        read_only_fields = fields
