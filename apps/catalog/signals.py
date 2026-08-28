# ────────────────────────────────────────────────────────────
# signals.py — сигналы для автоматического обновления
# денормализованных данных и поискового индекса.
#
# ЧЕТЫРЕ ГРУППЫ СИГНАЛОВ:
#   1. Главное изображение → Product.main_image
#   2. Уведомление о price-relevant изменении варианта
#      (через контракт каталога, БЕЗ чтения pricing)
#   3. Пересчёт main_image / search_vector при изменении вариантов
#   4. Обновление search_vector при изменении name/description
#
# АРХИТЕКТУРНЫЙ ПРИНЦИП:
#   Сигналы — автоматические обработчики событий ORM.
#   Когда модель сохраняется/удаляется → сигнал запускается.
#
#   ARCH-001 Stage 2: сигналы каталога НЕ пересчитывают цены сами.
#   Изменение price-relevant состояния варианта (is_active, удаление)
#   уходит в контракт notify_price_relevant_state_changed(): границы
#   рассчитывает bounded context `pricing` (PricingService), записывает
#   CatalogService.set_product_prices(). catalog не импортирует pricing —
#   зависимость однонаправленная (pricing → catalog). Cross-context
#   Django-сигналов нет: этот файл содержит только LOCAL-сигналы каталога.
#
# ВНИМАНИЕ: сигналы выполняются СИНХРОННО в том же процессе.
# Для высоконагруженных проектов → вынести в Celery tasks.
#
# ЧТО БУДЕТ, ЕСЛИ УДАЛИТЬ ФАЙЛ:
#   - main_image не обновляется автоматически → пустые карточки
#   - price-relevant изменения вариантов не доходят до пересчёта
#     min_price/max_price → устаревшие цены
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
# 2. Уведомление о price-relevant изменении варианта
# ==========================================================

# ARCH-001 Stage 2: каталог НЕ пересчитывает цены сам и НЕ читает
# pricing.Price. При изменении состояния варианта, влияющем на цены
# (is_active, удаление), каталог уведомляет слушателей через контракт
# notify_price_relevant_state_changed(). Слушателя регистрирует
# bounded context `pricing` в своём AppConfig.ready()
# (PricingService.recalculate_product_bounds) — направление
# зависимости pricing → catalog, без Django-сигналов между контекстами.
#
# Cross-context сигналы вида sender='pricing.Price' ЗАПРЕЩЕНЫ
# архитектурой (Issue #7, раздел Signals) и не используются.


def _notify_price_relevant_state_changed(variant):
    """
    Уведомляет контракт каталога: price-relevant состояние варианта
    изменилось (is_active / удаление варианта).

    Раньше (до ARCH-001 Stage 2) здесь вызывался
    product.recalculate_prices(), который читал цены pricing через
    ORM-lookup по вариантам (JOIN на таблицу цен pricing) —
    запрещённая обратная зависимость catalog → pricing. Теперь
    каталог только уведомляет слушателей: границы рассчитывает
    pricing, записывает CatalogService.set_product_prices().

    ПОЧЕМУ try/except Product.DoesNotExist:
        Вариант может быть «сиротой» (product удалён, но variant остался).
        Это защита от ошибки в таких случаях.
    """
    from apps.catalog.models import Product
    from apps.catalog.services.catalog_service import (
        notify_price_relevant_state_changed,
    )

    try:
        product = Product.objects.get(pk=variant.product_id)
    except Product.DoesNotExist:
        # Товар удалён — пересчитывать нечего.
        return
    # Синхронный вызов контракта: слушатель (pricing) пересчитает
    # min/max из своих Price и передаст их CatalogService.
    notify_price_relevant_state_changed(product)


# ==========================================================
# 3. Уведомление при изменении варианта (is_active / удаление)
# ==========================================================

@receiver(post_save, sender='catalog.ProductVariant')
def on_variant_change(sender, instance, **kwargs):
    """
    При изменении is_active у варианта — уведомляем о price-relevant
    изменении (границы min_price/max_price пересчитает pricing).

    Деактивация варианта может изменить min_price / max_price.

    ПОЧЕМУ НЕ ПРИ СОЗДАНИИ:
        Новый вариант ещё не имеет цены (price = None).
        Пересчёт сейчас бесполезен — prices уже актуальны.
        Цены обновятся когда к варианту привяжут Price
        (через PricingService.set_price).

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
            _notify_price_relevant_state_changed(instance)


# При удалении варианта — всегда уведомляем (вариант исчез из расчёта).
@receiver(post_delete, sender='catalog.ProductVariant')
def on_variant_delete(sender, instance, **kwargs):
    """
    При удалении варианта — уведомляем о price-relevant изменении.

    ПОЧЕМУ БЕЗ ПРОВЕРКИ:
        Удалённый вариант больше не участвует в min/max расчёте.
        Всегда уведомляем — удаление варианта всегда влияет на цены.
    """
    _notify_price_relevant_state_changed(instance)


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
