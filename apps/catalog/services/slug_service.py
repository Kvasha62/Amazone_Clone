# ────────────────────────────────────────────────────────────────────────
# apps/catalog/services/slug_service.py — утилита для генерации уникальных slug.
#
# НАЗНАЧЕНИЕ:
#   Генерирует URL-friendly слаг из произвольной строки с проверкой
#   уникальности. Если слаг занят — добавляет числовой суффикс:
#     'nike' → 'nike' (свободно)
#     'nike' → 'nike-2' (занято)
#     'nike' → 'nike-3' (занято и nike-2)
#
# ИСПОЛЬЗУЕТСЯ В:
#   • Brand.save() — slug из brand.name
#   • Product.save() — slug из product.name
#   • ProductVariant.save() — slug из 'product-name-sku'
#   • Category.save() — slug из category.name
#   • Tag.save() — slug из tag.name
#   • Attribute.save() — slug из attribute.name
#
# АЛГОРИТМ:
#   1. slugify(value) → 'iPhone 15 Pro!' → 'iphone-15-pro'
#   2. Проверяем существует ли объект с таким slug
#   3. Если да → добавляем '-2', '-3', ... пока не найдём свободный
#   4. Возвращаем уникальный slug
#
# 📖 https://docs.djangoproject.com/en/stable/ref/utils/#django.utils.text.slugify
#
# ЧТО БУДЕТ, ЕСЛИ УДАЛИТЬ ФАЙЛ:
#   • Все модели каталога с auto-slug → ImportError при импорте
# ────────────────────────────────────────────────────────────────────────

from django.utils.text import slugify


def generate_unique_slug(instance, field_value: str, slug_field_name: str = 'slug') -> str:
    """
    Генерирует уникальный slug для модели.

    АРГУМЕНТЫ:
      instance — экземпляр модели (нужен для получения класса и PK)
      field_value — строка для генерации slug ('iPhone 15 Pro')
      slug_field_name — имя поля slug в модели (default: 'slug')

    ВОЗВРАЩАЕТ:
      Уникальный slug: 'iphone-15-pro' или 'iphone-15-pro-2'

    АЛГОРИТМ:
      1. slugify(field_value) → 'iPhone 15 Pro!' → 'iphone-15-pro'
      2. QuerySet filter(slug=base_slug).exclude(pk=instance.pk)
         → исключаем текущий объект (при обновлении)
      3. Если slug занят → base_slug + '-2', '-3', ...

    📖 https://docs.djangoproject.com/en/stable/ref/utils/#django.utils.text.slugify
    """
    # slugify — Django-утилита: 'Hello World!' → 'hello-world'
    # Удаляет спецсимволы, приводим к lower case, пробелы → дефисы.
    base_slug = slugify(field_value)

    # Если slugify вернул пустую строку (например, все символы — не-ASCII)
    # → используем fallback 'item'.
    if not base_slug:
        base_slug = 'item'

    model_class = instance.__class__

    # exclude(pk=instance.pk) — при обновлении объекта его собственный
    # slug не должен считаться «занятым».
    # instance.pk может быть None (новый объект) → exclude(None) → safe.
    queryset = model_class._default_manager.all()

    # Если у объекта уже есть PK — исключаем его из проверки.
    if instance.pk:
        queryset = queryset.exclude(pk=instance.pk)

    # Проверяем свободен ли base_slug.
    slug = base_slug
    counter = 2

    while queryset.filter(**{slug_field_name: slug}).exists():
        # slug занят → добавляем числовой суффикс.
        slug = f'{base_slug}-{counter}'
        counter += 1

    return slug
