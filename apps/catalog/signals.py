# ────────────────────────────────────────────────────────────
# signals.py — сигналы для автоматического обновления
# денормализованных данных и поискового индекса.
#
# ЧЕТЫРЕ ГРУППЫ СИГНАЛОВ:
#   1. Главное изображение → Product.main_image
#   2. Пересчёт min_price/max_price при изменении цен
#   3. Пересчёт min_price/max_price при изменении вариантов
#   4. Обновление search_vector при изменении name/description
#
# АРХИТЕКТУРНЫЙ ПРИНЦИП:
#   Сигналы — автоматические обработчики событий ORM.
#   Когда модель сохраняется/удаляется → сигнал запускается.
#   Без сигналов: пришлось бы вручную вызывать
#   product.recalculate_prices() после каждого изменения варианта.
#   Забыл один раз → цены устарели → баг в каталоге.
#
# ВНИМАНИЕ: сигналы выполняются СИНХРОННО в том же процессе.
# Для высоконагруженных проектов → вынести в Celery tasks.
#
# ЧТО БУДЕТ, ЕСЛИ УДАЛИТЬ ФАЙЛ:
#   - main_image не обновляется автоматически → пустые карточки
#   - min_price/max_price не пересчитываются → устаревшие цены
#   - search_vector не обновляется → поиск не находит новые товары
# ────────────────────────────────────────────────────────────

# logging — для отладки сигналов (logging.debug(...)).
import logging

# F — объект для атомарных операций на уровне SQL:
# UPDATE SET field = field + 1 (без race conditions).
from django.db.models import F

# post_save — сигнал после .save() модели.
# post_delete — сигнал после .delete() модели.
from django.db.models.signals import post_save, post_delete

# receiver — декоратор для подключения обработчика сигнала.
from django.dispatch import receiver

# Логгер модуля.
logger = logging.getLogger(__name__)


# ==========================================================
# 1. Главное изображение → Product.main_image
# ==========================================================

# @receiver(post_save, sender='catalog.ProductImage')
# Подключается к сигналу post_save модели ProductImage.
# sender='catalog.ProductImage' — строковая ссылка (lazy),
# чтобы избежать циклического импорта.
# Вызывается КАЖДЫЙ раз когда ProductImage.save() завершается.
@receiver(post_save, sender='catalog.ProductImage')
def sync_product_main_image(sender, instance, **kwargs):
    """
    При установке is_main=True — обновляем Product.main_image.
    При сбросе is_main=False — очищаем Product.main_image, если это было оно.

    ПОЧЕМУ НЕ В МОДЕЛИ ProductImage.save():
        Принцип разделения ответственности:
        ProductImage не должен знать о структуре Product.
        Сигнал — слабая связность (loose coupling).

    ПОЧЕМУ Product.objects.filter(pk=...).update(), А НЕ product.save():
        .update() — прямой SQL UPDATE без вызова save() модели.
        Если использовать product.main_image = image; product.save() →
        сработает сигнал post_save на Product → обновится search_vector →
        лишняя работа. .update() обходит сигналы — оптимальнее.
    """
    # Lazy-импорт — разрываем потенциальный цикл.
    from apps.catalog.models import Product

    # instance — объект ProductImage, который сохранили.
    image = instance
    # image.product — FK к товару (обратная навигация).
    product = image.product

    if image.is_main:
        # Устанавливаем главное изображение товара.
        # .filter(pk=product.pk).update(main_image=image) —
        # SQL: UPDATE catalog_product SET main_image_id = X WHERE id = Y
        # Без: product.main_image устареет — будет показываться старое изображение.
        Product.objects.filter(pk=product.pk).update(main_image=image)
        logger.debug(
            'main_image_set',
            extra={'product_id': product.pk, 'image_id': image.pk},
        )
    else:
        # Если это изображение БЫЛО главным — снимаем.
        # filter(main_image=image) — проверяем что main_image
        # указывает именно на ЭТО изображение (не на другое).
        Product.objects.filter(
            pk=product.pk,
            main_image=image,
        ).update(main_image=None)


# @receiver(post_delete, sender='catalog.ProductImage')
# Срабатывает при удалении изображения.
@receiver(post_delete, sender='catalog.ProductImage')
def clear_product_main_image_on_delete(sender, instance, **kwargs):
    """
    При удалении главного изображения — очищаем Product.main_image.

    ПОЧЕМУ ЭТО НУЖНО:
        Если удалить ProductImage, на который ссылается Product.main_image,
        останется «висячая» ссылка (dangling FK) → ProductDetailSerializer
        обратится к product.main_image → DoesNotExist → 500.
        Сигнал очищает ссылку ДО того как кто-то к ней обратится.

    ПОЧЕМУ filter(main_image=instance), А НЕ ПРОСТО filter(pk=...):
        Только если удалённое изображение ЯВЛЯЛОСЬ главным.
        Если это было НЕ главное — main_image менять не нужно.
    """
    from apps.catalog.models import Product

    Product.objects.filter(
        pk=instance.product_id,
        main_image=instance,
    ).update(main_image=None)


# ==========================================================
# 2. Пересчёт min_price / max_price при изменении цен
# ==========================================================

# Этот сигнал подключается к модели цены варианта (pricing-модуль).
# Имя модели зависит от вашего apps.pricing — укажите правильное.
#
# Если pricing-модуль ещё не готов, закомментируйте signal ниже
# и вызывайте product.recalculate_prices() вручную из сервиса.


def _recalculate_product_prices(variant):
    """
    Пересчитывает min_price / max_price у товара,
    которому принадлежит variant.

    Вспомогательная функция — вызывается из нескольких сигналов.

    ПОЧЕМУ НЕ @staticmethod В КЛАССЕ:
        Это внутренняя функция (underscore prefix), не часть API.
        Используется только внутри этого файла.

    ПОЧЕМУ try/except Product.DoesNotExist:
        Вариант может быть «сиротой» (product удалён, но variant остался).
        Это защита от ошибки в таких случаях.
    """
    from apps.catalog.models import Product

    try:
        product = Product.objects.get(pk=variant.product_id)
    except Product.DoesNotExist:
        # Товар удалён — ничего пересчитывать.
        return
    # product.recalculate_prices() — метод модели Product:
    # агрегирует min/max из активных вариантов и обновляет поля.
    product.recalculate_prices()


# Сигналы для pricing-модуля ЗАКОММЕНТИРОВАНЫ:
# они подключатся когда pricing app будет готов.
# Это сделано чтобы catalog работал независимо от pricing.
#
# @receiver(post_save, sender='pricing.ProductVariantPrice')
# def on_price_change(sender, instance, **kwargs):
#     """Пересчитываем цены товара при изменении цены варианта."""
#     variant = instance.variant
#     _recalculate_product_prices(variant)
#
#
# @receiver(post_delete, sender='pricing.ProductVariantPrice')
# def on_price_delete(sender, instance, **kwargs):
#     """Пересчитываем цены товара при удалении цены варианта."""
#     variant = instance.variant
#     _recalculate_product_prices(variant)


# ==========================================================
# 3. Пересчёт min_price / max_price при изменении варианта
# ==========================================================

@receiver(post_save, sender='catalog.ProductVariant')
def on_variant_change(sender, instance, **kwargs):
    """
    При изменении is_active у варианта — пересчитываем цены товара.
    Деактивация варианта может изменить min_price / max_price.

    ПОЧЕМУ НЕ ПРИ СОЗДАНИИ:
        Новый вариант ещё не имеет цены (price = None).
        Пересчёт сейчас бесполезен — prices уже актуальны.
        Цены обновятся когда к варианту привяжут Price (через pricing signal).

    ПОЧЕМУ ПРОВЕРЯЕМ _get_old_is_active:
        variant.save() вызывается при ЛЮБОМ изменении (имя, вес, SKU...).
        Если is_active не менялся — пересчёт не нужен (лишний SQL).
        Проверяем только изменение is_active → оптимально.
    """
    # created=False — только при ОБНОВЛЕНИИ, не при создании.
    if not kwargs.get('created', False):
        # _get_old_is_active() — метод модели ProductVariant:
        # сравнивает текущее is_active с сохранённым ранее значением.
        old = instance._get_old_is_active()
        # old is not None — защита при первом сохранении (нет «старого» значения).
        # old != instance.is_active — значение ИЗМЕНИЛОСЬ.
        if old is not None and old != instance.is_active:
            _recalculate_product_prices(instance)


# При удалении варианта — всегда пересчитываем (вариант исчез из расчёта).
@receiver(post_delete, sender='catalog.ProductVariant')
def on_variant_delete(sender, instance, **kwargs):
    """
    При удалении варианта — пересчитываем цены товара.

    ПОЧЕМУ БЕЗ ПРОВЕРКИ:
        Удалённый вариант больше не участвует в min/max расчёте.
        Всегда пересчитываем — удаление варианта всегда влияет на цены.
    """
    _recalculate_product_prices(instance)


# ==========================================================
# 4. Search vector обновление
# ==========================================================

@receiver(post_save, sender='catalog.Product')
def update_product_search_vector(sender, instance, **kwargs):
    """
    Обновляет search_vector при изменении name / description.

    Использует PostgreSQL to_tsvector — работает быстро,
    но для высоконагруженных проектов лучше вынести в celery-задачу.

    ПОЧЕМУ НЕ В МОДЕЛИ Product.save():
        to_tsvector — PostgreSQL-специфичная операция.
        Размещение в сигнале isolates эту логику от модели.
        Плюс: можно легко отключить (закомментировать @receiver).

    ПОЧЕМУ ПРОВЕРКА update_fields:
        product.save() вызывается часто (инкремент просмотров, пересчёт цен).
        Без проверки: каждый save() пересчитывает search_vector
        (полный текстовый анализ name + description) — дорого!
        Проверяем: если save() затронул только views_count — пропускаем.

    СОВМЕСТИМОСТЬ С SQLITE:
        SearchVector работает ТОЛЬКО с PostgreSQL.
        При использовании SQLite (тесты, локальная разработка) —
        операция silently пропускается (поиск недоступен, но БД не падает).
        Это безопасно: в production всегда PostgreSQL.
    """
    # kwargs.get('update_fields') — список полей, которые были сохранены.
    # Если save() без update_fields → None (сохранены все поля) → обновляем.
    changed_fields = kwargs.get('update_fields')
    if changed_fields and 'name' not in changed_fields and 'description' not in changed_fields:
        # Сохранение затронуло другие поля (views_count, rating и т.д.)
        # search_vector обновлять не нужно — возвращаемся.
        return

    from django.db import connection

    # Проверяем что БД — PostgreSQL. SQLite не поддерживает SearchVector.
    # При тестировании на SQLite → пропускаем (поиск недоступен, но без краша).
    # В production всегда PostgreSQL → поиск работает.
    if connection.vendor != 'postgresql':
        logger.debug(
            'search_vector_skip',
            extra={'reason': f'Unsupported DB vendor: {connection.vendor}'},
        )
        return

    from django.contrib.postgres.search import SearchVector

    from apps.catalog.models import Product

    # Product.objects.filter(pk=...).update(search_vector=...)
    # Используем .update(), не instance.search_vector = ...; instance.save()
    # Причины:
    #   1) .update() — один SQL-запрос (без загрузки Python-объекта)
    #   2) .update() не триггерит post_save снова (нет рекурсии!)
    #   3) SearchVector() — SQL-выражение, вычисляется на стороне PostgreSQL
    Product.objects.filter(pk=instance.pk).update(
        search_vector=(
            # SearchVector('name', weight='A') — имя товара вес A (наивысший).
            # weight='A' — при ранжировании имя важнее описания.
            # config='russian' — словарь для русского языка (стемминг: «телефон» = «телефоны»).
            SearchVector('name', weight='A', config='russian')
            # + (плюс) — объединяет два вектора в один.
            # weight='B' — описание менее важно при ранжировании.
            # Если name и description содержат одно слово —
            # рейтинг будет выше чем если слово только в description.
            + SearchVector('description', weight='B', config='russian')
        )
    )
