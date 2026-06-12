# ==============================================================================
# apps/catalog/models/product_image.py — Изображение товара
# ==============================================================================
# Хранение изображений с поддержкой:
#   - Порядка сортировки (order) — drag-and-drop в admin
#   - Главного изображения (is_main) → денормализуется на Product.main_image
#   - Alt-текста для SEO и accessibility
#
# Инварианты:
#   - Только ОДНО главное изображение на товар (UniqueConstraint с condition)
#   - При установке is_main=True → Product.main_image обновляется через signal
#   - При удалении главного изображения → Product.main_image очищается
# ==============================================================================

from django.db import models
from django.db.models import Q

from apps.core.models import BaseModel


class ProductImage(BaseModel):
    """
    Изображение товара.

    Инварианты:
      - У товара может быть только ОДНО главное изображение (is_main=True).
        Гарантируется UniqueConstraint с condition.
      - При установке is_main=True автоматически обновляется
        Product.main_image через signal (см. apps.catalog.signals).
      - При удалении главного изображения Product.main_image очищается.

    order — ручная сортировка в карточке товара (drag-and-drop).
    """

    product = models.ForeignKey(
        'catalog.Product',
        on_delete=models.CASCADE,      # Товар удалён → изображения удалены
        related_name='images',         # product.images.all()
        verbose_name='Товар',
    )

    image = models.ImageField(
        'Изображение',
        # upload_to — каталог в MEDIA_ROOT.
        # %Y/%m/ — группировка по месяцам:
        #   media/products/2024/06/photo1.jpg
        # Предотвращает >10K файлов в одной директории.
        upload_to='products/%Y/%m/',
    )

    alt = models.CharField(
        'Alt-текст',
        max_length=255,
        blank=True,
        help_text=(
            'Описание изображения для SEO и доступности. '
            'Пустое поле = будет использовано название товара.'
        ),
    )

    # ------------------------------------------------------------------
    # is_main — флаг главного изображения
    # ------------------------------------------------------------------
    # Только одно изображение товара может быть is_main=True.
    # Гарантируется UniqueConstraint с condition=Q(is_main=True).
    # ------------------------------------------------------------------
    is_main = models.BooleanField(
        'Главное изображение',
        default=False,
    )

    # ------------------------------------------------------------------
    # order — ручная сортировка
    # ------------------------------------------------------------------
    # Меньшее значение = показывается раньше.
    # Используется для drag-and-drop в admin и в карточке товара.
    # ------------------------------------------------------------------
    order = models.PositiveIntegerField(
        'Порядок сортировки',
        default=0,
    )

    class Meta:
        verbose_name = 'Изображение товара'
        verbose_name_plural = 'Изображения товаров'
        # Сначала по order (ручная сортировка),
        # потом по PK (стабильный порядок для одинаковых order)
        ordering = ('order', 'pk')

        indexes = [
            # Частичный индекс для быстрого поиска главного изображения.
            # Запрос: ProductImage.objects.filter(product=X, is_main=True)
            models.Index(
                fields=['product', 'is_main'],
                name='productimage_product_main_idx',
            ),
        ]

        constraints = [
            # ----------------------------------------------------------
            # Partial Unique Index — только одно is_main=True на товар.
            #
            # condition=Q(is_main=True) означает:
            #   индекс содержит ТОЛЬКО строки где is_main=True.
            #   Строки с is_main=False в индекс не попадают
            #   → нет ограничения на количество не-главных изображений.
            #
            # PostgreSQL реализует это как:
            #   CREATE UNIQUE INDEX ... WHERE is_main = true;
            # ----------------------------------------------------------
            models.UniqueConstraint(
                fields=['product'],
                condition=Q(is_main=True),
                name='unique_main_product_image',
            ),
        ]

    def __str__(self) -> str:
        # Безопасный __str__ — избегаем N+1.
        # Если product не загружен (нет select_related) — fallback на PK.
        product_name = getattr(self.product, 'name', None)
        if product_name:
            return f'{product_name} — img #{self.pk}'
        return f'Изображение #{self.pk} (товар {self.product_id})'

    @property
    def display_alt(self) -> str:
        """
        Alt-текст или название товара как fallback.

        Если alt не заполнен — используем название товара.
        Это лучше чем пустой alt (SEO + accessibility).
        """
        return self.alt or getattr(self.product, 'name', '')
