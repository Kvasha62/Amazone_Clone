# ────────────────────────────────────────────────────────────
# signals.py — сигналы для автоматического обновления
# денормализованных данных и поискового индекса.
#
# ТРИ ГРУППЫ СИГНАЛОВ (только LOCAL внутри catalog):
#   1. Главное изображение → Product.main_image
#   2. Пояснение: price-relevant изменения вариантов ОБРАБАТЫВАЮТСЯ
#      НЕ сигналами (явные service-вызовы, см. блок ниже)
#   3. Обновление search_vector при изменении name/description
#
# АРХИТЕКТУРНЫЙ ПРИНЦИП:
#   Сигналы — автоматические обработчики событий ORM.
#   Когда модель сохраняется/удаляется → сигнал запускается.
#
#   ARCH-001 Stage 2: здесь НЕТ никакой ценовой логики. Пересчёт
#   Product.min_price/max_price — cross-domain операция (вариант —
#   catalog, цены — pricing), выполняется ТОЛЬКО явными service-
#   вызовами PricingService (см. ARCHITECTURE.md → Cross-Domain
#   Coordination). Все сигналы этого файла — LOCAL внутри catalog.
#
# ВНИМАНИЕ: сигналы выполняются СИНХРОННО в том же процессе.
# Для высоконагруженных проектов → вынести в Celery tasks.
#
# ЧТО БУДЕТ, ЕСЛИ УДАЛИТЬ ФАЙЛ:
#   - main_image не обновляется автоматически → пустые карточки
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
# 2. Price-relevant изменения вариантов — НАМЕРЕННО НЕ ЗДЕСЬ
# ==========================================================

# ARCH-001 Stage 2: автоматической реакции на изменение is_active /
# удаление варианта НЕТ. Пересчёт Product.min_price/max_price — это
# cross-domain операция: состояние варианта принадлежит `catalog`,
# цены — `pricing`. Любая механика автоматической реакции требует
# либо reverse dependency (catalog → pricing), либо cross-context
# Django signal, либо глобальный registry/event bus — все три формы
# запрещены архитектурой (ARCHITECTURE.md → Cross-Domain Coordination:
# primary mechanism — explicit service calls; сигналы — только
# same-domain).
#
# ЕДИНСТВЕННЫЙ легитимный путь изменения price-relevant состояния
# варианта — явные сервисные вызовы (видимая точка в коде, явная
# транзакция):
#
#   PricingService.set_variant_active(variant, is_active=...)   # True→False / False→True
#   PricingService.delete_variant(variant)                      # удаление варианта
#
# Оба метода: мутация через CatalogService (catalog-owned) + пересчёт
# границ PricingService.recalculate_product_bounds (pricing-owned) →
# CatalogService.set_product_prices (единственная точка mutation
# Product.min_price/max_price). Поток: pricing → catalog.
#
# Изменение is_active напрямую (admin/raw ORM) оставляет min/max
# устаревшими до следующей операции с ценами — осознанный trade-off,
# задокументированный в ARCHITECTURE.md.


# ==========================================================
# 3. Search vector обновление
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
