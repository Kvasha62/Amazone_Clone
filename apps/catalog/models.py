# catalog/models.py

# Импорт базового класса моделей Django (основа всех моделей)
from django.db import models

# Импорт функции для преобразования строки в URL-safe формат (slug)
# from django.utils.text import slugify
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


# 🏷 Модель категорий
class Category(models.Model):
    # Название категории (например "Electronics")
    name = models.CharField('Название', max_length=200)

    # Slug для URL (уникальный, но может быть пустым — мы генерируем его сами)
    slug = models.SlugField('Слаг', unique=True, blank=True, null=True, db_index=True)

    # Родительская категория (для иерархии)
    parent = models.ForeignKey(
        'self',  # ссылка на саму модель (рекурсивная связь)
        on_delete=models.CASCADE,  # удаляется вместе с родителем
        blank=True,  # можно не указывать в формах
        null=True,   # можно хранить NULL в базе
        related_name='children',  # доступ: category.children.all()
        verbose_name='Родительская категория'
    )

    class Meta:
        # Человеко-читаемое имя в админке
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'

    # Как объект отображается в строке (например в админке)
    def __str__(self):
        return self.name

    # Переопределяем сохранение модели
    def save(self, *args, **kwargs):
        # Если slug не задан или пустая строка
        if not self.slug:
            # Генерируем уникальный slug на основе имени
            self.slug = generate_unique_slug(self, self.name)

        # Вызываем стандартное сохранение Django
        super().save(*args, **kwargs)


# 📦 Модель продукта (абстрактный товар)
class Product(models.Model):
    # Название товара
    name = models.CharField('Название', max_length=255)

    # Slug для URL
    slug = models.SlugField('Слаг', unique=True, blank=True, null=True, db_index=True)

    # Описание товара
    description = models.TextField('Описание', blank=True)

    # Бренд (например Apple, Samsung)
    brand = models.CharField('Бренд', max_length=100)

    # Связь с категорией
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,  # при удалении категории удаляются товары
        related_name='products',   # доступ: category.products.all()
        verbose_name='Категория'
    )

    # Дата создания (устанавливается автоматически)
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)

    class Meta:
        verbose_name = 'Продукт'
        verbose_name_plural = 'Продукты'

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # Генерация slug при отсутствии
        if not self.slug:
            self.slug = generate_unique_slug(self, self.name)

        super().save(*args, **kwargs)


# 🧠 Вариант товара (SKU)
class ProductVariant(models.Model):
    # Связь с продуктом
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='variants'  # product.variants.all()
    )

    # Уникальный артикул (SKU)
    sku = models.CharField('SKU', max_length=100, unique=True)

    # Slug для URL варианта
    slug = models.SlugField(max_length=220, unique=True, blank=True, null=True, db_index=True)

    class Meta:
        verbose_name = 'Вариант продукта'
        verbose_name_plural = 'Варианты продукта'

    def __str__(self):
        return self.sku

    def save(self, *args, **kwargs):
        # Генерация slug если не задан
        if not self.slug:
            # Формируем строку из названия продукта + SKU
            base = f"{self.product.name}-{self.sku}"

            # Генерируем уникальный slug
            self.slug = generate_unique_slug(self, base)

        super().save(*args, **kwargs)


# ⚙ Атрибут (например Цвет, Память)
class Attribute(models.Model):
    # Название атрибута
    name = models.CharField('Название', max_length=100)

    class Meta:
        verbose_name='Атрибут'
        verbose_name_plural='Атрибуты'

    def __str__(self):
        return self.name


# 🔢 Значение атрибута (например Черный, 128GB)
class AttributeValue(models.Model):
    # Связь с атрибутом
    attribute = models.ForeignKey(
        Attribute,
        on_delete=models.CASCADE,
        related_name='values'  # attribute.values.all()
    )

    # Само значение
    value = models.CharField('Значение', max_length=100)

    class Meta:
        verbose_name='Значение атрибут'
        verbose_name_plural='Значения атрибутов'

    def __str__(self):
        # Пример: "Цвет: Черный"
        return f'{self.attribute.name}: {self.value}'


# 🔗 Связь Variant ↔ Атрибуты
class VariantAttribute(models.Model):
    # Вариант товара
    variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.CASCADE,
        related_name='attributes'  # variant.attributes.all()
    )

    # Атрибут (например Цвет)
    attribute = models.ForeignKey(Attribute, on_delete=models.CASCADE)

    # Значение (например Черный)
    value = models.ForeignKey(AttributeValue, on_delete=models.CASCADE)

    class Meta:
        verbose_name='Вариант атрибута'
        verbose_name_plural='Варианты атрибутов'

    def __str__(self):
        # Пример: "SKU123 - Цвет: Черный"
        return f'{self.variant} - {self.attribute}: {self.value.value}'


# Илья должен изменить
# 🖼 Изображения товара
class ProductImage(models.Model):

    # Какому товару принадлежит изображение
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='images'
    )

    # Сам файл изображения
    image = models.ImageField(
        upload_to='products/'
    )

    # Главное ли изображение
    is_main = models.BooleanField(default=False)

    # Порядок сортировки
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.product.name} Image"