# ────────────────────────────────────────────────────────────
# Сериализаторы категорий (Category).
#
# ТРИ СЕРИАЛИЗАТОРА:
#   BreadcrumbSerializer — элемент цепочки навигации
#   CategoryTreeSerializer — рекурсивное дерево категорий
#   CategoryDetailSerializer — полная информация о категории
#
# ПОЧЕМУ TreeSerializer ИСПОЛЬЗУЕТ SerializerMethodField:
#   Дерево категорий — рекурсивная структура:
#   {
#     "name": "Электроника",
#     "children": [
#       {"name": "Смартфоны", "children": [...]},
#       {"name": "Ноутбуки", "children": [...]}
#     ]
#   }
#   ModelSerializer не поддерживает рекурсию из коробки.
#   SerializerMethodField позволяет вручную вызвать
#   CategoryTreeSerializer(children) — рекурсивная сериализация.
#
# ЧТО БУДЕТ, ЕСЛИ УДАЛИТЬ ФАЙЛ:
#   GET /api/v1/catalog/categories/ → ImportError (500).
# ────────────────────────────────────────────────────────────

# serializers — базовые классы DRF.
from rest_framework import serializers

# Category — модель с treebeard MP_Node (дерево).
from apps.catalog.models import Category


class BreadcrumbSerializer(serializers.Serializer):
    """
    Элемент цепочки навигации (breadcrumbs).

    ПОЧЕМУ ОТДЕЛЬНЫЙ СЕРИАЛИЗАТОР, А НЕ СЛОВАРЬ:
        Валидация и автодокументация (drf-spectacular).
        Serializer → OpenAPI схема автоматически знает структуру.
        Без: swagger-документация покажет "object" без полей.
    """
    # name — отображаемый текст: «Электроника»
    name = serializers.CharField()
    # slug — для URL: /catalog/elektronika/
    slug = serializers.CharField()
    # url_path — полный путь: /catalog/elektronika/smartfony/
    url_path = serializers.CharField()


class CategoryTreeSerializer(serializers.ModelSerializer):
    """
    Узел дерева категорий.
    Рекурсивная структура — children вложены.

    КАК РАБОТАЕТ РЕКУРСИЯ:
        CategoryTreeSerializer(root_nodes, many=True)
          → get_children() для каждого корня
            → CategoryTreeSerializer(children, many=True)
              → get_children() для каждого ребёнка
                → ... пока children = [] (лист дерева)

    ГЛУБИНА РЕКУРСИИ:
        Категории обычно 3-4 уровня: Корень → Подкатегория → Тип → Подтип.
        На каждом уровне — один SQL-запрос к treebeard.
        4 уровня × N узлов = управляемое количество запросов.
    """

    # SerializerMethodField — поле, значение которого вычисляется
    # в методе get_children(). Без: ModelSerializer не знает
    # как сериализовать children (это не поле модели, а метод treebeard).
    children = serializers.SerializerMethodField()

    class Meta:
        model = Category
        # id — идентификатор узла
        # name — «Электроника»
        # slug — 'elektronika'
        # url_path — '/catalog/elektronika/'
        # depth — глубина в дереве (1=корень, 2=ребёнок, ...)
        # is_active — показывать ли в навигации
        # children — вложенные подкатегории (SerializerMethodField)
        fields = ('id', 'name', 'slug', 'url_path', 'depth', 'is_active', 'children')

    def get_children(self, obj):
        """
        Рекурсивная сериализация детей.

        obj — текущий узел Category (из treebeard MP_Node).

        ПОЧЕМУ ФИЛЬТРАЦИЯ is_active=True:
            Неактивные категории (скрытые, тестовые) не должны
            попадать в навигацию. Без: пользователь увидит
            «Тестовая категория» в меню — нелогично.

        ПОЧЕМУ .exists() + .data, А НЕ ПРЯМО .data:
            Оптимизация: если детей нет — сразу возвращаем []
            без создания сериализатора. На листовых узлах экономим
            ~50% работы сериализатора.
        """
        # get_children() — метод treebeard MP_Node.
        # Возвращает QuerySet непосредственных детей (depth+1).
        # filter(is_active=True) — только активные дети.
        children = obj.get_children().filter(is_active=True)
        # .exists() — SELECT 1 ... LIMIT 1 — быстрый способ
        # проверить есть ли записи, без загрузки данных.
        if not children.exists():
            return []
        # РЕКУРСИЯ: создаём CategoryTreeSerializer для детей.
        # many=True — сериализируем список, а не один объект.
        # .data — триггерит сериализацию (вызовет get_children для каждого).
        return CategoryTreeSerializer(children, many=True).data


class CategoryDetailSerializer(serializers.ModelSerializer):
    """
    Полная информация о категории.

    ПОЧЕМУ НЕ CategoryTreeSerializer:
        CategoryTreeSerializer — для навигации (минимум полей).
        CategoryDetailSerializer — для страницы категории:
        описание, изображение, SEO, breadcrumbs, количество товаров.
    """

    # breadcrumbs — цепочка предков (динамическое поле из view).
    # many=True — список breadcrumb-объектов.
    breadcrumbs = BreadcrumbSerializer(many=True, read_only=True)
    # products_count — количество товаров в категории.
    # Динамическое поле, устанавливается через setattr() в view:
    #   setattr(category, 'products_count', count)
    products_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Category
        # Полный набор полей для страницы категории.
        # full_name_cached — «Электроника > Смартфоны > Apple» (денормализованный)
        # breadcrumbs — цепочка навигации
        # products_count — динамическое поле
        # meta_title/meta_description — SEO
        fields = (
            'id',
            'name',
            'slug',
            'description',
            'image',
            'url_path',
            'full_name_cached',
            'depth',
            'is_active',
            'breadcrumbs',
            'products_count',
            'meta_title',
            'meta_description',
        )
        read_only_fields = fields
