# ARCH-001 H2 — Work Report

- **Дата:** 2026-08-30
- **Тип работы:** Work report
- **Этап:** ARCH-001 H2 — Django Admin hardening for product review aggregates
- **Репозиторий:** `Kvasha62/Amazone_Clone`
- **Ветка на момент отчёта:** `arena/01a0540c-amazone-clone`
- **Базовый commit:** `38648bd` (merge of `arena/01a0538f-amazone-clone`)

## 1. Контекст

`Product.rating` и `Product.reviews_count` — денормализованные
review-агрегаты. Единственный авторитетный сервисный путь их записи:

```text
ReviewService.recalculate_product_rating()
    → CatalogService.set_review_stats(product, rating, reviews_count)
    → Product.rating / Product.reviews_count
```

Django Admin является не вычислительным слоем агрегатов, а
операционной поверхностью. ARCH-001 H2 закрывает возможность обойти
этот контракт через Admin:

- `ProductAdmin` не должен становиться вторым писателем
  `Product.rating` / `Product.reviews_count`;
- `ReviewAdmin` не должен писать агрегаты мимо `ReviewService`.

## 2. Выполнено

### 2.1. `ProductAdmin` — запрет записи review-агрегатов

Файл: `apps/catalog/admin/product_admin.py`

- Добавлены константы:
  - `PRODUCT_REVIEW_AGGREGATE_FIELDS = ('rating', 'reviews_count')`;
  - `PRODUCT_REVIEW_AGGREGATE_DEFAULTS`;
  - `PRODUCT_ADMIN_PROTECTED_FIELDS` (объединяет price bounds и
    review-агрегаты);
  - `PRODUCT_ADMIN_MODEL_MANAGED_SAVE_FIELDS`
    (`slug`, `published_at`, `updated_at`).
- `rating` / `reviews_count` добавлены в `readonly_fields` и показаны
  в отдельном read-only fieldset «Рейтинг / отзывы».
- `save_model()` реализует второй слой защиты (defense-in-depth):
  - на `change` сравнивает in-memory защищённые поля с текущими
    значениями в БД и поднимает `PermissionDenied` при изменении;
  - отказывает в `change` без `pk` (не даёт Django выполнить
    full-row insert);
  - отказывает в `save_model()` для устаревшей строки, если целевая
    запись уже удалена;
  - на `add` запрещает создание товара с непустыми защищёнными
    значениями;
  - на `change` сохраняет только поля, реально принадлежащие форме
    `ProductAdmin`, исключая защищённые поля, плюс обязательные
    model-managed поля (`updated_at`, а при необходимости `slug`,
    `published_at`) через `update_fields` — без полного `obj.save()`.
- Service-level пути остаются вне Admin: `ProductAdmin` не импортирует
  `reviews`/`pricing` сервисы, а только запрещает мутации.

### 2.2. `ReviewAdmin` — маршрутизация через `ReviewService`

Файл: `apps/reviews/admin/review_admin.py`

- Добавлены константы:
  - `REVIEW_AGGREGATE_SOURCE_FIELDS = ('product', 'rating', 'is_approved')`;
  - `REVIEW_ADMIN_IMMUTABLE_CHANGE_FIELDS = ('user', 'product')`;
  - `REVIEW_ADMIN_DIRECT_FIELDS`
    (`verified_purchase`, `helpful_yes`, `helpful_no`).
- Для существующего отзыва `user` и `product` становятся read-only;
  `save_model()` поднимает `PermissionDenied` при попытке переноса
  отзыва на другой товар или пользователя (нет service-level операции
  переноса).
- `save_model()`:
  - add — `ReviewService.create_review()`, при необходимости затем
    `ReviewService.reject_review()`;
  - change — изменения текста/названия/рейтинга через
    `ReviewService.update_review()`, изменения статуса через
    `ReviewService.approve_review()` / `reject_review()`;
  - поля вне агрегатного контракта сохраняются отдельным
    `update_fields`-вызовом (`_save_direct_review_fields`).
- `delete_model()` и `delete_queryset()` маршрутизируют удаление через
  `ReviewService.delete_review()`.
- Экшены `approve_selected` / `reject_selected` вызывают
  `ReviewService.approve_review()` / `reject_review()` per row.

## 3. Тесты

### `apps/catalog/tests/test_admin_product_review_stats.py`

Покрывает конфигурацию Admin и серверный guard:

- поля объявлены readonly;
- change/add формы и rendered страница не содержат input-ов для
  `rating` / `reviews_count`;
- `save_model()` отклоняет изменение `rating` и `reviews_count`;
- `save_model()` отклоняет add с непустыми агрегатами;
- безопасные поля товара по-прежнему сохраняются, агрегаты не
  затрагиваются;
- SQL `UPDATE` для change исключает защищённые агрегатные поля
  (используется `update_fields`);
- change без `pk` не приводит к insert;
- stale change для удалённой строки отклоняется;
- активация товара всё ещё проставляет `published_at`;
- crafted Admin POST не может записать review-агрегаты;
- stale Admin save не перезаписывает свежие агрегаты ReviewService;
- авторитетный путь (`ReviewService` → `CatalogService`) по-прежнему
  работает.

### `apps/reviews/tests/test_admin_review_aggregates.py`

Покрывает маршрутизацию `ReviewAdmin` через `ReviewService`:

- `user` / `product` read-only для существующего отзыва;
- add через Admin пересчитывает агрегаты;
- add неодобренного отзыва не попадает в агрегат;
- change рейтинга, approval, text-editing, direct `save_model()` —
  через ReviewService;
- переходы approve/reject пересчитывают агрегаты;
- перенос отзыва на другой product/user отклонён;
- single delete, bulk delete, approve/reject actions пересчитывают
  агрегаты.

## 4. Проверка

- `ProductAdmin` имеет двухслойную защиту: UI/readonly + серверный
  guard в `save_model()`.
- `ReviewAdmin` не имеет прямого пути записи `Product.rating` /
  `Product.reviews_count`: все агрегато-затрагивающие операции идут
  через существующие методы `ReviewService`.
- Состав проверок соответствует существующему в репозитории набору
  Admin-guard тестов (см. раздел «Testing Strategy» в
  `ARCHITECTURE.md`).

> Примечание: в рамках подготовки данного отчёта отдельный полный
> прогон `manage.py test` не выполнялся. Для повторной верификации
> рекомендуется прогнать:
>
> ```text
> python manage.py test apps.catalog.tests.test_admin_product_review_stats apps.reviews.tests.test_admin_review_aggregates
> ```
>
> а для полной проверки — весь набор на PostgreSQL.

## 5. Out of scope

- Политика raw ORM / shell-мутаций агрегатов (осознанный trade-off
  однонаправленной архитектуры).
- Ценовые bounds `Product.min_price` / `max_price` — это отдельный
  контракт ARCH-001 Stage 2 и не входит в H2.
- Перенос существующего отзыва между пользователями/товарами как
  полноценная service-level операция.
