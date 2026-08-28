# ==============================================================================
# apps/catalog/models/product_variant.py — Вариант товара
# ==============================================================================
# Вариант — конкретное исполнение товара.
#
# Пример:
#   Product: «iPhone 15 Pro»
#     ├─ Variant «iPhone 15 Pro 128GB Титановый»  (SKU: IP15P-128-T)
#     ├─ Variant «iPhone 15 Pro 256GB Титановый»  (SKU: IP15P-256-T)
#     └─ Variant «iPhone 15 Pro 512GB Белый»       (SKU: IP15P-512-W)
#
# Варианты отличаются через EAV-атрибуты (VariantAttribute):
#   Память=128, Цвет=Титановый и т.д.
#
# Каждый вариант имеет:
#   - SKU — уникальный складской артикул
#   - barcode — штрихкод для сканера
#   - Габариты (длина/ширина/высота/вес) — для расчёта доставки
#   - slug — для URL варианта (если нужен)
#   - Связь с ценой: variant.price (OneToOne, pricing-модуль)
#   - Связь со стоком: variant.stock (OneToOne, inventory-модуль)
# ==============================================================================

from django.core.validators import MinValueValidator
from django.db import models

from apps.catalog.services.slug_service import generate_unique_slug
from apps.core.models import BaseModel


class ProductVariant(BaseModel):

    # ------------------------------------------------------------------
    # product — товар, которому принадлежит вариант
    # ------------------------------------------------------------------
    # on_delete=CASCADE — если товар удалён, все варианты удаляются.
    # (Вариант без товара не имеет смысла.)
    # related_name='variants' — product.variants.all()
    # ------------------------------------------------------------------
    product = models.ForeignKey(
        'catalog.Product',
        on_delete=models.CASCADE,
        related_name='variants',
        verbose_name='Товар',
    )

    # ------------------------------------------------------------------
    # sku — уникальный складской артикул
    # ------------------------------------------------------------------
    # unique=True — каждый SKU встречается ровно один раз.
    # Используется для:
    #   - Складского учёта (приёмка, отгрузка)
    #   - Быстрого поиска в admin
    #   - Интеграции с 1C / ERP
    # ------------------------------------------------------------------
    sku = models.CharField(
        'Артикул (SKU)',
        max_length=100,
        unique=True,
    )

    # ------------------------------------------------------------------
    # barcode — штрихкод (EAN-13, UPC-A и т.д.)
    # ------------------------------------------------------------------
    # db_index=True — сканирование на складе: поиск по штрихкоду.
    # blank=True — не у всех вариантов есть штрихкод.
    # ------------------------------------------------------------------
    barcode = models.CharField(
        'Штрихкод',
        max_length=100,
        blank=True,
        db_index=True,
    )

    # ------------------------------------------------------------------
    # is_active — видимость варианта в каталоге
    # ------------------------------------------------------------------
    # False = вариант снят с продажи, но сохраняется для аналитики
    # (исторические заказы ссылаются на этот вариант).
    # ------------------------------------------------------------------
    is_active = models.BooleanField(
        'Активен',
        default=True,
        db_index=True,
    )

    # ------------------------------------------------------------------
    # Габариты — для расчёта стоимости доставки
    # ------------------------------------------------------------------
    # null=True, blank=True — не у всех товаров есть габариты
    #   (цифровые товары, услуги).
    # MinValueValidator(0) — защита от отрицательных значений.
    # ------------------------------------------------------------------
    length = models.DecimalField(
        'Длина',
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        null=True,
        blank=True,
    )

    width = models.DecimalField(
        'Ширина',
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        null=True,
        blank=True,
    )

    height = models.DecimalField(
        'Высота',
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        null=True,
        blank=True,
    )

    weight = models.DecimalField(
        'Вес',
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        null=True,
        blank=True,
    )

    # ------------------------------------------------------------------
    # slug — URL-friendly идентификатор варианта
    # ------------------------------------------------------------------
    # blank=True, null=True — slug опционален для вариантов.
    # Не все проекты показывают варианты по отдельному URL.
    # ------------------------------------------------------------------
    slug = models.SlugField(
        'Слаг',
        max_length=220,
        unique=True,
        blank=True,
        null=True,
    )

    class Meta:
        verbose_name = 'Вариант товара'
        verbose_name_plural = 'Варианты товара'
        ordering = ('-created_at',)

        indexes = [
            # ----------------------------------------------------------
            # Составной индекс для каталога: «варианты данного товара,
            # сначала активные». Типичный запрос:
            #   SELECT * FROM variants
            #   WHERE product_id = X AND is_active = TRUE
            # ----------------------------------------------------------
            models.Index(
                fields=['product', 'is_active'],
                name='variant_product_active_idx',
            ),
        ]

    def __str__(self):
        return self.sku

    def _get_old_is_active(self) -> bool | None:
        """
        Возвращает is_active варианта НА МОМЕНТ ПЕРЕД последним save().

        Вызывается сигналом on_variant_change (apps/catalog/signals.py)
        СРАЗУ ПОСЛЕ save(): post_save срабатывает, когда строка в БД уже
        обновлена, поэтому прежнее значение нужно зафиксировать ДО записи
        (см. save()). Значение «до последнего save» и позволяет сигналу
        детектировать реальное изменение is_active.

        ARCH-001 Stage 2: метод упоминался сигналом, но не существовал —
        любой UPDATE варианта падал бы с AttributeError (латентный баг,
        не покрытый тестами). Реализация читает только СВОЮ таблицу
        (catalog-local, без обращения к pricing).

        Returns:
            bool — is_active до последнего save();
            None — вариант ещё ни разу не сохранялся
                   («старого» значения нет).
        """
        cached = getattr(self, '_old_is_active_cached', None)
        if cached is not None:
            return cached
        # Инстанс не проходил через save() в этом процессе (загружен
        # из БД запросом) → читаем сохранённое значение напрямую.
        if self._state.adding or self.pk is None:
            return None
        return (
            ProductVariant.objects
            .filter(pk=self.pk)
            .values_list('is_active', flat=True)
            .first()
        )

    def save(self, *args, **kwargs):
        # ------------------------------------------------------------------
        # Авто-генерация slug из «Название товара — SKU».
        #
        # Пример: «iPhone 15 Pro-IP15P-128-T»
        #
        # Вызывается в save() (а не в migration) потому что:
        #   - slug зависит от product.name — неизвестен при migration.
        #   - product.name может быть длинным — slug обрезается.
        # ------------------------------------------------------------------
        if not self.slug:
            self.slug = generate_unique_slug(
                self,
                f'{self.product.name}-{self.sku}',
            )
        # ARCH-001 Stage 2: фиксируем сохранённое в БД is_active ДО записи —
        # post_save (on_variant_change) вызовет _get_old_is_active() уже
        # после UPDATE, и прежнее значение можно взять только отсюда.
        self._old_is_active_cached = (
            None if self._state.adding
            else ProductVariant.objects
            .filter(pk=self.pk)
            .values_list('is_active', flat=True)
            .first()
        )
        super().save(*args, **kwargs)
