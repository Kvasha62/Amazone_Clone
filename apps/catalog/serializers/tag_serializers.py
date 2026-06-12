# ────────────────────────────────────────────────────────────
# Сериализатор тегов (Tag).
#
# ОДИН СЕРИАЛИЗАТОР:
#   Теги — простая сущность: id, name, slug.
#   Нет отдельного detail/list — теги не имеют вложенных данных.
#
# ПОЧЕМУ ТОЛЬКО ЧТЕНИЕ:
#   Теги создаются/управляются через Django Admin.
#   API-пользователь не может создавать теги —
#   это задача контент-менеджера.
#   Без read_only_fields: любой POST с {"name": "spam"}
#   создал бы тег — Security risk.
#
# ЧТО БУДЕТ, ЕСЛИ УДАЛИТЬ ФАЙЛ:
#   GET /api/v1/catalog/tags/ → ImportError (если есть такой endpoint).
#   Вложенные теги в ProductDetailSerializer перестанут сериализоваться.
# ────────────────────────────────────────────────────────────

# serializers — базовые классы DRF.
from rest_framework import serializers

# Tag — модель тега: name, slug, is_active.
from apps.catalog.models import Tag


class TagSerializer(serializers.ModelSerializer):
    """
    Тег — только чтение (создание через admin).

    ПОЛЯ:
        id — идентификатор тега
        name — «Новинка», «Распродажа»
        slug — 'new', 'sale' (для URL-фильтров)
    """

    class Meta:
        model = Tag
        # Минимальный набор полей для отображения тега.
        # is_active не включён — frontend не видит deactivated теги
        # (они отфильтрованы в сервисе get_active_tags()).
        fields = ('id', 'name', 'slug')
        # read_only_fields = fields — все 3 поля только для чтения.
        # Это запрещает POST/PUT/PATCH на уровне сериализатора.
        # Даже если view не проверяет — сериализатор отклонит запись.
        read_only_fields = fields
