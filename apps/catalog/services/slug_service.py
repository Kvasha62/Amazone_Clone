from slugify import slugify

# 🔧 Функция генерации уникального slug
def generate_unique_slug(instance, field_value, slug_field_name="slug", max_length=220):
    # Преобразуем строку в slug (например "iPhone 13" → "iphone-13")
    # и обрезаем до максимальной длины
    # base_slug = slugify(field_value or "")[:max_length]
    base_slug = slugify(field_value or "item", lowercase=True)[:max_length]

    # Начальный slug (без суффиксов)
    slug = base_slug

    # Счетчик для добавления "-1", "-2" и т.д. при совпадениях
    counter = 1

    # Получаем модель текущего объекта (например Product, Category)
    model = instance.__class__

    # Проверяем, существует ли уже такой slug в базе
    # exclude(pk=instance.pk) — исключаем текущий объект (важно при обновлении)
    while model.objects.filter(**{slug_field_name: slug}).exclude(pk=instance.pk).exists():
        # Если slug занят — добавляем суффикс
        slug = f"{base_slug}-{counter}"
        counter += 1  # увеличиваем счетчик

    # Возвращаем уникальный slug
    return slug