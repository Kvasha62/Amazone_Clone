# Подробный отчёт по работе в GitHub — 30.08.2026

- **Дата:** 2026-08-30
- **Репозиторий:** `Kvasha62/Amazone_Clone`
- **Источник истины:** `origin/main`
- **Ветка на момент подготовки:** `arena/01a0540c-amazone-clone`
- **Режим:** read-only по коду; отчёт фиксирует фактическую активность `gh`/GitHub API.

Отчёт содержит **не только сводку**, а разбор **каждого файла** из слитых
в `main` за 30.08.2026 PR: **что это за файл, почему он менялся, как именно
он менялся**.

> В этот день в `main` влились PR **#16, #17, #18, #20, #21, #22, #23**.
> Номера **PR #19 нет** — #19 является Issue (границы цен), реализован PR #20.

---

## 0. Сводка по дням и PR

| PR | Название | Merged UTC | +/− | Файлов |
|----|----------|------------|-----|--------|
| #16 | `EDU-000 — Record source of truth audit` | 10:02 | +91 / 0 | 1 |
| #17 | `EDU-001: Synchronize payment webhook documentation` | 10:24 | +16 / −12 | 1 |
| #18 | `ARCH-001 Stage 2 — Block ProductVariant Admin price-relevant mutations` | 13:44 | +453 / −63 | 11 |
| #20 | `Admin: make Product min_price/max_price read-only (Issue #19)` | 14:32 | +466 / −11 | 4 |
| #21 | `ARCH-001 C1: Catalog ownership for Product review aggregates (Issue #7)` | 15:41 | +502 / −26 | 7 |
| #22 | `ARCH-001(H1): Prevent review aggregate lost updates` | 16:44 | +765 / −16 | 7 |
| #23 | `ARCH-001(H2): Harden admin review aggregates` | 18:16 | +1349 / −61 | 9 |

Итог: **7 PR, 40 файлов, +3642/−189**, **20 коммитов** в `main`.

---

## 1. PR #16 — EDU-000: Record source of truth audit

### 1.1. `docs/audit/EDU-000-source-of-truth.md` (added, +91)

**Почему:** Нужен traceable артефакт аудита «источника истины». Проверка
фактического состояния репозитория (ветки/commit, рабочее дерево,
нормативные документы) против заявленного; фиксировались только
подтверждённые read-only наблюдения.

**Как:**
- Зафиксированы метаданные аудита: источник `Kvasha62/Amazone_Clone`
  (`origin/main`), базовый commit `ba32...`, рабочая ветка
  `arena/01a051eb-amazone-clone`.
- Проверено состояние репозитория: `main` = `ba32...`, расхождений с
  рабочей веткой нет, рабочее дерево чистое.
- Перечислены нормативные документы: `DEVELOPMENT.md`, `ARCHITECTURE.md`,
  `ARCH-001-stage3.md`, ADR/case-study шаблоны, `DIARY.md`, `.github/`.
- Кратко зафиксирована архитектурная структура (Django, DRF, PostgreSQL,
  Redis+Celery, перечень приложений `apps/`, ключевые правила
  «View → Serializer → Service → ORM»).
- Зафиксированы **подтверждённые расхождения**:
  1. `AGENTS.md` отсутствует;
  2. `ARCH-001-stage3.md` ссылается на `ARCH-002`, но отдельного ADR
     `ARCH-002` нет.
- Отмечено наблюдение **«требует отдельной проверки»**: описание
  payment webhook в `ARCHITECTURE.md` (`AllowAny` без HMAC) расходится с
  кодом HMAC-SHA256; в EDU-000 оно **не** классифицировано как
  подтверждённое расхождение.
- Явно описаны ограничения: отчёт не утверждает, что расхождения
  исправлены, и что список полный; исходный код не менялся.

---

## 2. PR #17 — EDU-001: Synchronize payment webhook documentation

### 2.1. `ARCHITECTURE.md` (modified, +16/−12)

**Почему:** Наблюдение из EDU-000: документация описывала webhook как
`AllowAny` без HMAC, тогда как реализация использует
HMAC-SHA256/`PAYMENT_WEBHOOK_SECRET`. Документация должна отражать код.

**Как:**
- В разделе `payments` заменена строка «webhook endpoint is `AllowAny`
  with no HMAC verification» на корректное описание:
  - endpoint действительно `AllowAny` (провайдер шлёт запрос без JWT),
  - требуется проверка HMAC-SHA256 по заголовку `X-Webhook-Signature`,
    секрет — `PAYMENT_WEBHOOK_SECRET`.
- В таблицу переменных окружения добавлена строка
  `PAYMENT_WEBHOOK_SECRET | (empty) | Webhook HMAC secret`.
- Другие части `ARCHITECTURE.md` не менялись — PR строго про
  синхронизацию документации по webhook.

---

## 3. PR #18 — ARCH-001 Stage 2: Block ProductVariant Admin price-relevant mutations

Это самый первый «большой» PR дня. Он закрывает **ProductVariant**
Admin-обходы (is_active/delete) и заодно закрывает обход отмены заказа
через `transition_status(CANCELLED)` (EDU-002: утечка купонного слота).

### 3.1. `ARCHITECTURE.md` (modified, +18/−4)

**Почему:** документировать новые архитектурные правила: единственная
точка отмены и запрет Admin-мутаций price-relevant состояния вариантов.

**Как:**
- Добавлен блок **Cancellation entrypoint (EDU-002)**:
  `CANCELLED` достигается только через `OrderService.cancel()`;
  `transition_status()` отклоняет `CANCELLED`; staff
  `PATCH .../status/` с `cancelled` надо маршрутизировать в `cancel()`.
- Переписан абзац про trade-off: явная прямых `variant.is_active`
  изменений оставляет `min_price`/`max_price` устаревшими — это
  осознанный и документированный trade-off однонаправленной архитектуры.
- Добавлена таблица admin-поверхностей для price-relevant state
  (`ProductVariantAdmin`, `ProductVariantInline`) и запрещённых действий.

### 3.2. `apps/catalog/admin/product_admin.py` (modified, +12/−0)

**Почему:** inline-варианты в форме товара были вторым обходом:
`is_active` и удаление существующих вариантов меняют денормализованные
границы цен без `PricingService`.

**Как:**
- В `ProductVariantInline` добавлен docstring с правилом ARCH-001 Stage 2:
  `is_active` change/delete идут только через
  `PricingService.set_variant_active()`/`delete_variant()`.
- Добавлены `readonly_fields = ('is_active',)` — поле `is_active`
  больше не редактируется во inline.
- Добавлено `can_delete = False` — отключён флажок удаления существующих
  строк во inline. Новые варианты создавать по-прежнему можно.

### 3.3. `apps/catalog/admin/product_variant_admin.py` (modified, +54/−36)

**Почему:** основная админ-страница вариантов позволяла менять
`is_active` и удалять варианты в обход `PricingService`.

**Как:**
- Убраны «украшающие» комментарии-дубли кода (оставленные пояснения
  только по существу).
- Добавлен архитектурный docstring: `is_active`/delete price-relevant,
  легитимный путь — `PricingService`; `catalog` Admin не импортирует
  `PricingService`, поэтому Admin **запрещает** такие мутации.
- `readonly_fields` расширено: `slug`, `is_active`, `created_at`,
  `updated_at`.
- Добавлены guards:
  - `has_delete_permission(...) -> False` — скрывает удаление из UI;
  - `delete_model(...)` и `delete_queryset(...)` — поднимают
    `PermissionDenied` (одиночное и bulk удаление);
  - `save_model(...)` — на change сравнивает in-memory `is_active` с
    текущим значением в БД и поднимает `PermissionDenied` при
    изменении.

### 3.4. `apps/catalog/tests/test_admin_variant_guards.py` (added, +172)

**Почему:** регрессионные тесты должны доказывать, что Admin-обходы
закрыты, а легитимный `PricingService`-путь не сломан.

**Как:** добавлен набор `ProductVariantAdminGuardTests`:
- проверка readonly и отсутствия inline-delete;
- серверный отказ `save_model` при смене `is_active`;
- отказ `delete_model`/`delete_queryset`;
- проверка легитимного пути: `PricingService.set_variant_active()` и
  `delete_variant()` продолжают работать.

### 3.5. `apps/orders/services/order_service.py` (modified, +12/−10)

**Почему:** `transition_status()` принимал `CANCELLED` и выполнял
pseudo-отмену **без** оркестрации `cancel()` (не было coupon release/
inventory/payment). Это байпас `ARCH-001 stage 3` и утечка купонного
слота (EDU-002 B1).

**Как:**
- В `transition_status()` добавлена ранняя проверка:
  `new_status == CANCELLED → raise ValidationError(... только через cancel())`.
- Проверка стоит **до** `select_for_update()`, чтобы случайный вызов
  fail fast.
- В сообщении об ошибке допустимые статусы теперь исключают
  `CANCELLED`.
- Удалена ветка `elif new_status == CANCELLED: order.cancelled_at = now`
  — так как отмена больше не является переходом FSM.
- `cancelled_at` теперь устанавливается внутри `cancel()`.

### 3.6. `apps/orders/api_views/order_views.py` (modified, +15/−6)

**Почему:** staff endpoint `PATCH .../status/` вызывал
`transition_status()`, а значит всё ещё мог отменить заказ в обход
`cancel()`.

**Как:**
- В docstring потока изменён шаг 3:
  `CANCELLED → OrderService.cancel()`, иначе — `transition_status()`.
- В коде извлекается `new_status`; если это `CANCELLED` — вызывается
  `OrderService.cancel(order, user=...)`, иначе прежний
  `transition_status(...)`.
- После операции по-прежнему выполняется прежнее перечитывание с
  prefetch `with_items()`.

### 3.7. `apps/shipping/services/shipping_service.py` (modified, +21/−11)

**Почему:** `_sync_order_status()` при `RETURNED` вызывал
`transition_status(... CANCELLED)`. После того как `transition_status`
стал отвергать `CANCELLED`, этот вызов бросал `ValidationError`, который
был **съеден** try/except — статус заказа оставался stale.

**Как:**
- В `order_status_map` удалён ключ `returned`.
- Добавлен явный обработчик `shipment_status == 'returned'`:
  - если заказ ещё не `CANCELLED`, вызывается `OrderService.cancel()`;
  - пишется `logger.info` о синхронизации.
- Остальные переходы (`in_transit`→PROCESSING, `delivered`→DELIVERED)
  по-прежнему идут через `transition_status()`.
- try/except остаётся: ошибка синхронизации не должна откатывать
  транзакцию отправления, но теперь путь отмены корректен.

### 3.8. `apps/orders/tests/test_api.py` (modified, +60/−0)

**Почему:** регрессионные API-тесты должны подтверждать, что staff
`PATCH status=cancelled` теперь идёт через `cancel()` с корректным
coupon-поведением.

**Как:** добавлены два теста:
- `test_staff_status_cancelled_releases_pending_coupon`:
  PENDING-заказ с применённым купоном отменяется через endpoint;
  утверждается статус `CANCELLED`, `discount=0`, `total` восстановлен,
  `times_used=0`, `CouponUsage` удалён.
- `test_staff_status_cancelled_keeps_confirmed_coupon`:
  CONFIRMED-заказ отменяется, купон остаётся «consumed»
  (`times_used=1`, `CouponUsage` остаётся, скидка/сумма не сбрасываются).
- Добавлены импорты `Decimal`, `CouponUsage`, `create_test_coupon`,
  `OrderService`.

### 3.9. `apps/orders/tests/test_services.py` (modified, +8/−7)

**Почему:** старый тест `test_pending_to_cancelled` утверждал, что
`transition_status(PENDING→CANCELLED)` допустим — это противоречит
новому правилу.

**Как:**
- Удалён `test_pending_to_cancelled`.
- Добавлен `test_transition_status_rejects_cancelled`: вызов
  `transition_status(..., CANCELLED)` поднимает `ValidationError` с
  указанием `cancel()`, а заказ остаётся `PENDING`.

### 3.10. `apps/discounts/tests/test_services.py` (modified, +40/−0)

**Почему:** бывшая утечка была именно в купонной подсистеме — проверка,
что «ложная отмена» через `transition_status` не освобождает слот, а
легитимная отмена освобождает.

**Как:** добавлен
`test_transition_status_cancelled_rejects_and_keeps_coupon_slot`:
- применяется купон (`times_used=1`, `CouponUsage` есть);
- `transition_status(..., CANCELLED)` → `ValidationError`;
- заказ остаётся PENDING, скидка/сумма/`times_used`/`CouponUsage`
  неизменны;
- затем легитимный `cancel()` → статус CANCELLED, `discount=0`,
  `total` восстановлен, `times_used=0`, `CouponUsage` удалён.

### 3.11. `docs/architecture/ARCH-001-stage3.md` (modified, +17/−0)

**Почему:** спецификация купонной координации должна явно описывать
новое правило единственной точки отмены.

**Как:** добавлен раздел **Cancellation entrypoint**:
- `CANCELLED` достигается только через `OrderService.cancel()`;
- `transition_status()` **не принимает** `CANCELLED`;
- staff `PATCH .../status/` с `cancelled` обязан вызывать `cancel()`;
- остальные переходы — через `transition_status()`.

---

## 4. PR #20 — Admin: make Product min_price/max_price read-only (Issue #19)

Закрывает `Issue #19` — residual `M1` после PR #18: `ProductAdmin` умел
вручную менять `min_price`/`max_price`.

### 4.1. `apps/catalog/admin/product_admin.py` (modified, +45/−0)

**Почему:** admin-форма товара была вторым писателем денормализованных
границ цен, причём UI заявлял «пересчитываются автоматически», но
серверного запрета не было.

**Как:**
- Добавлена константа `PRODUCT_PRICE_BOUNDS_FIELDS = ('min_price', 'max_price')`.
- Метаданные в шапке файла дополнены ARCH-001 Stage 2 (M1 residual):
  единственный путь — `PricingService.recalculate_product_bounds() →
  CatalogService.set_product_prices()`; catalog Admin не импортирует
  pricing, потому просто запрещает запись.
- `readonly_fields` расширен: `min_price`, `max_price`.
- Fieldset «Цены (авто)»: новое описание «Только чтение… ручное
  изменение через Admin запрещено (ARCH-001 Stage 2)».
- Реализован `save_model()` (defense-in-depth):
  - на `change` сравнивает `obj.min_price/max_price` с текущими
    значениями в БД; при различии — `PermissionDenied`;
  - на `add` запрещает создание товара с непустыми границами;
  - легитимный путь остаётся вне Admin.

### 4.2. `apps/catalog/tests/test_admin_product_bounds.py` (modified, +266/−0)

**Почему:** полностью закрыть Issue #19 регрессионными тестами: оба
слоя защиты (readonly/UI и серверный guard) должны реально
отслеживаться.

**Как:** добавлены классы:
- `ProductAdminPriceBoundsReadOnlyTests`: readonly/config, отсутствие
  input в change/add формах, отсутствие input на rendered-страницах.
- `ProductAdminPriceBoundsGuardTests`: server-side отказ при изменении
  `min_price`, `max_price`, очистке в `NULL`, add-пути; безопасные поля
  сохраняются; crafted POST не меняет границы; легитимный
  `PricingService.set_price()`/`recalculate_product_bounds()` работает.
- `ProductBoundsAuthoritativePathStillWorksTests`: авторитетный
  `PricingService → CatalogService` путь не сломан.

### 4.3. `ARCHITECTURE.md` (modified, +18/−0)

**Почему:** документация должна отражать новую graницы защиты для
`Product.min_price`/`max_price`.

**Как:** В раздел **Admin (ARCH-001 Stage 2)** добавлена строка таблицы
для `ProductAdmin` (`min_price`/`max_price` change, Issue #19) и полное
описание двух слоёв защиты (readonly + `save_model` PermissionDenied),
плюс что raw ORM/shell остаются осознанным trade-off.

### 4.4. `DIARY.md` (modified, +60/−0)

**Почему:** вести образовательный/инженерный дневник работы по Issue #19.

**Как:** добавлен раздел **«Day 5 — 2026-08-30: Issue #19»** с контекстом,
что сделано (readonly + save_model + тесты + документация), результатом
проверки (`1048 tests, 0 failures`) и явным Out of scope
(`rating`/`reviews_count`/`views_count`, raw ORM, Order/EDU-002).

---

## 5. PR #21 — ARCH-001 C1: Catalog ownership for Product review aggregates

Этап **C1** — установить явный ownership-контракт
`reviews → catalog` для `Product.rating`/`reviews_count`.

### 5.1. `apps/catalog/services/catalog_service.py` (modified, +113/−0)

**Почему:** в `catalog` должен появиться **авторитетный service-level writer**
для его собственных денормализованных полей `rating`/`reviews_count`,
который может вызывать `reviews` без открытия обратной зависимости
`catalog → reviews`.

**Как:** добавлен статический метод
`CatalogService.set_review_stats(product, *, rating, reviews_count)`:
- принимает уже рассчитанные `rating`/`reviews_count` и **только пишет**
  их в `Product` (authoritative writer).
- Валидация:
  - `rating` приводится к `Decimal`, проверяется
    `is_finite()`, отбрасывается `NaN`/`Infinity`, `quantize(0.01)`,
    диапазон `0.00..5.00`;
  - `reviews_count` → целое, не меньше 0;
  - ошибки поднимаются как `ValidationError`, а не
    `decimal.InvalidOperation`.
- Сохраняет только `rating`, `reviews_count`, `updated_at` через
  `update_fields` — не полный `save()` товара (не трогает `name`,
  `min_price` и т.д.).
- Пишет `logger.debug('product_review_stats_updated', ...)`.
- Docstring фиксирует границы ответственности: `reviews` считает,
  `catalog` пишет; `catalog` НЕ читает `reviews`; на этом этапе
  Admin-поверхность объявлена residual H3.

### 5.2. `apps/reviews/services/review_service.py` (modified, +23/−9)

**Почему:** `ReviewService.recalculate_product_rating()` должен отказаться
от прямой мутации `Product` через методов-модели (`Product.update_rating()`)
и идти через catalog-owned контракт.

**Как:**
- Лениво импортируется `CatalogService`.
- Пересчитываются `AVG`/`COUNT` по одобренным `Review` (как раньше).
- Запись выполняется теперь через
  `CatalogService.set_review_stats(product, rating=avg, reviews_count=total)`.
- Docstring переписан: `reviews` владеет расчётом, `catalog` владеет
  записью; прямая мутация `product.rating`/`reviews_count` из reviews
  запрещена.

### 5.3. `apps/catalog/models/product.py` (modified, +3/−0)

**Почему:** модель должна отражать, что старый «наивный» комментарий об
автообновлении через атомарные методы больше неверен.

**Как:**
- Комментарий над денормализованными счётчиками заменён на перечисление
  авторитетных путей:
  `rating`/`reviews_count` — `CatalogService.set_review_stats()`
  (вызывается из `ReviewService`, C1), `views_count` —
  `increment_views()` или celery.
- Удалён метод `Product.update_rating()`:
  - это был cross-context mutation path (reviews вызывал метод
    catalog-модели);
  - вместо него добавлен развёрнутый комментарий о единственном
    service-level пути `ReviewService → CatalogService.set_review_stats()`.
- Аналогично уже удалён ранее `Product.recalculate_prices()` (Stage 2).

### 5.4. `apps/reviews/models/review.py` (modified, +4/−1)

**Почему:** комментарий модели отзыва описывал старое поведение
«автообновление через сигнал».

**Как:** заменён на:
- агрегаты обновляются при
  create/update/delete через явный сервисный контракт
  `ReviewService.recalculate_product_rating() →
  CatalogService.set_review_stats()` (ARCH-001 C1);
- сигналы для этой мутации не используются.

### 5.5. `apps/reviews/__init__.py` (modified, +2/−1)

**Почему:** синхронизировать описание приложения с новым ownership.

**Как:** строка про «автообновление denormalized rating/reviews_count»
заменена на «пересчёт через catalog-owned контракт
`CatalogService.set_review_stats()`».

### 5.6. `apps/reviews/tests/test_architecture.py` (added, +296)

**Почему:** архитектурная регрессия должна защищать контракт, а не только
функциональные тесты.

**Как:** добавлен новый файл с методикой `inspect.getsource` + файловый
скан. Основные группы:
- `CatalogSetReviewStatsTests`:
  - реально пишет поля, принимает нули, rejects out-of-bounds,
    rejects NaN/Infinity/1E+30, quantize 4.567→4.57, rejects negative
    count, использует `update_fields` (не перезаписывает stale name).
- `ReviewAggregateContractArchitectureTests`:
  - `recalculate_uses_catalog_contract_not_model_setter`;
  - `product_update_rating_method_removed`;
  - `review_service_does_not_directly_mutate_product_aggregates`
    (запрещены `product.rating =`, `product.reviews_count =`,
    `Product.objects.filter/update`);
  - `catalog_service_set_review_stats_is_the_writer`.
- `CrossContextDependencyDirectionTests`: `catalog → reviews` в
  production runtime отсутствует.
- `SingleServiceWriterScanTests`: file-scan production-кода, что
  service-level writer только `CatalogService.set_review_stats()`.

### 5.7. `ARCHITECTURE.md` (modified, +43/−6)

**Почему:** файл должен быть источником истины для нового
ownership-контракта (и старое описание «обновляется по сигналам» было
неверно).

**Как:**
- В таблице денормализованных полей замена «updated by Django signals»
  на описание `reviews` считает → `CatalogService.set_review_stats()` пишет.
- В разделе `reviews` добавлены строки: `reviews` владеет `Review` и
  расчётом; `catalog` владеет записью `Product.rating`/
  `reviews_count` через контракт `ReviewService → CatalogService`.
- В разделе **Review aggregates** (Cross-Domain Coordination) добавлен
  блок ownership `reviews → catalog` и удалён legacy-path.
- В `Denormalization Refresh` обновлено описание: теперь synchronous
  через `ReviewService` + `CatalogService.set_review_stats()` (C1, «no
  signals involved»).

---

## 6. PR #22 — ARCH-001(H1): Prevent review aggregate lost updates

Этап **H1** — клиентская конкурентность: агрегаты должны считаться под
row-lock, иначе при параллельных операциях над одним товаром второй
писатель затирает результат первого.

### 6.1. `apps/reviews/services/review_service.py` (modified, +57/−0)

**Почему:** добавить блокировку authoritative `Product` **до** расчёта
агрегатов.

**Как:**
- Добавлен `ReviewService._locked_product(product)`:
  - выполняет `Product.objects.select_for_update().get(pk=...)`;
  - большой docstring с объяснением lost update (READ COMMITTED):
    T1/T2 считают COUNT до COMMIT и оба пишут 1;
    с локом второй ждёт COMMIT первого, а затем его aggregate-SELECT
    видит полный закоммиченный набор;
  - объяснено, что lock-order безопасен: review-paths берут Product
    затем Review; `vote_helpful` лочит Review/vote, но никогда не
    лочит Product — цикла нет, deadlock невозможен;
  - `select_for_update` без транзакции → `TransactionManagementError`
    (сознательная защита).
- `recalculate_product_rating()` теперь:
  1. `locked_product = ReviewService._locked_product(product)`;
  2. считает агрегаты по `product=locked_product`;
  3. пишет через `CatalogService.set_review_stats(locked_product, ...)`.
- Обновлён docstring: полная цепочка
  `transaction.atomic (вызывающий) → LOCK Product → AVG/COUNT →
  CatalogService → catalog.Product`; метод не открывает свою
  транзакцию.

### 6.2. `apps/catalog/models/product.py` (modified, +5/−1)

**Почему:** комментарий модели должен отражать H1 (row-lock перед
расчётом).

**Как:** в комментарий к `rating`/`reviews_count` добавлено описание
ARCH-001 H1: перед расчётом ReviewService берёт `SELECT ... FOR UPDATE`
этой строки под `transaction.atomic`, конкурентные операции
сериализуются, lost update невозможен; `set_review_stats()` транзакцию
не открывает.

### 6.3. `apps/catalog/services/catalog_service.py` (modified, +6/−2)

**Почему:** чтобы контракт `set_review_stats()` не открывал свою
транзакцию и не брал lock — это обязанность вызывающего review-слоя.

**Как:** в docstring `set_review_stats()` обновлено:
- не открывает собственную транзакцию (никаких вложенных независимых);
- сам строк не лочит;
- H1: лок обеспечивает `ReviewService.recalculate_product_rating()`
  (`SELECT ... FOR UPDATE` на authoritative `Product`), запись
  выполняется уже под этим локом; lost update невозможен.

### 6.4. `apps/reviews/models/review.py` (modified, +4/−2)

**Почему:** отразить, что блокировка происходит перед расчётом.

**Как:** в описании цепочки добавлена строка
`→ LOCK Product (SELECT ... FOR UPDATE, до COMMIT вызывающей
транзакции) → AVG/COUNT одобренных Review`, и указано, что H1 исключает
lost update; сигналы не используются.

### 6.5. `apps/reviews/tests/test_concurrency.py` (added, +756)

**Почему:** H1 без реальных конкурентных тестов недоказуем; нужны
cross-connection тесты для PostgreSQL.

**Как:** добавлен большой файл конкурентных тестов:
- `concurrent create/create`, `create/delete`, `approve/approve`,
  `approve/reject`, `update/update`;
- смешанный all-paths stress-прогон;
- `.test_lock_blocking` — проверка, что второй поток блокируется на
  `select_for_update`;
- post-run invariants:
  `product.reviews_count == COUNT(approved)` и
  `product.rating == ROUND(AVG(approved))`;
- `skipUnlessDBFeature('has_select_for_update')` и/или отключение на
  SQLite.

### 6.6. `apps/reviews/tests/test_architecture.py` (modified, +37/−0)

**Почему:** source-guard должен проверять, что лок берётся перед
агрегатами, и что `set_review_stats` не открывает транзакцию.

**Как:** добавлены тесты:
- `test_recalculate_locks_product_before_aggregates`:
  `select_for_update` в `_locked_product`; `_locked_product` вызывается
  до `.aggregate(`; лок — на `catalog.Product`.
- `test_set_review_stats_does_not_open_its_own_transaction`:
  в `CatalogService.set_review_stats` нет `transaction.atomic` и
  `select_for_update`.

### 6.7. `ARCHITECTURE.md` (modified, +48/−0)

**Почему:** документация должна объяснить concurrency-правило H1 и его
покрытие.

**Как:**
- В таблицу рисков добавлены строки:
  - concurrent review create/update/delete/approve (lost update) —
    `select_for_update()` на `Product` (H1);
  - concurrent price/variant changes — `select_for_update()` на
    `Product` (Stage 2).
- Добавлен подраздел **Concurrency (ARCH-001 H1)**: список всех
  authoritative review paths (`create/update/delete/approve/reject`,
  `@transaction.atomic`), схема
  `atomic → lock Product → mutate Review → AVG/COUNT → set_review_stats`,
  объяснение lost update и почему READ COMMITTED при локе даёт свежий
  снапшот, deadlock-анализ, ссылка на `test_concurrency.py`.

---

## 7. PR #23 — ARCH-001(H2): Harden admin review aggregates

Финальный этап дня: закрыть **Admin-поверхность** для review-агрегатов —
`ProductAdmin` не должен писать `rating`/`reviews_count`, а `ReviewAdmin`
— обходить `ReviewService`.

### 7.1. `apps/catalog/admin/product_admin.py` (modified, +185/−37)

**Почему:** после C1/H1 service-level контракт защищён, но форма `Product`
все ещё могла писать `rating`/`reviews_count` напрямую; кроме того,
стандартный `obj.save()` на change мог перезаписать свежие агрегаты
stale-экземпляром или «воскресить» удалённую строку.

**Как:**
- Добавлены константы:
  - `PRODUCT_REVIEW_AGGREGATE_FIELDS = ('rating', 'reviews_count')`;
  - `PRODUCT_ADMIN_PROTECTED_FIELDS = price_bounds + review_aggregates`;
  - `PRODUCT_REVIEW_AGGREGATE_DEFAULTS = {rating: 0.00, reviews_count: 0}`;
  - `PRODUCT_ADMIN_MODEL_MANAGED_SAVE_FIELDS = (slug, published_at, updated_at)`.
- `readonly_fields` расширен: `rating`, `reviews_count`.
- Fieldset «Рейтинг» переименован в «Рейтинг / отзывы» с пояснением
  ARCH-001 H2: поля read-only, считается `ReviewService`, пишет
  `CatalogService.set_review_stats`; `views_count` не относится к H2.
- `save_model()` переписан:
  - **change path:** без `pk` → `PermissionDenied` (no insert);
    `_stored_product_values()` → если строка удалена → `PermissionDenied`;
    сравнение защищённых полей с сохранёнными → `PermissionDenied`;
    `_admin_change_update_fields()` формирует безопасный `update_fields`;
    `obj.save(update_fields=...)` вместо полного `save()`.
  - **add path:** непустые price bounds или непустые review-агрегаты →
    `PermissionDenied`.
- Добавлены helpers:
  - `_stored_product_values(obj)` — читает все concrete-поля из БД;
  - `_admin_change_update_fields(...)` — allowlist из реальных полей
    формы `ProductAdmin`, исключая `PRODUCT_ADMIN_PROTECTED_FIELDS`,
    плюс `updated_at` (и при необходимости `slug`, `published_at`);
  - `_product_admin_form_field_names(...)` — из формы или
    `get_form()`.
- Метаданные в шапке обновлены под H2.
- Явная цель: **не** импортировать `reviews`/`pricing` сервисы в Admin.

### 7.2. `apps/reviews/admin/review_admin.py` (modified, +131/−0)

**Почему:** `ReviewAdmin` с стандартным `save_model` создавал/мерил
отзывы и модерацию в обход `ReviewService` — значит, мог «распараллелить»
обновление `Product.rating`/`reviews_count` с другим писателем.

**Как:**
- Добавлены константы `REVIEW_AGGREGATE_SOURCE_FIELDS = ('product',
  'rating', 'is_approved')`, `REVIEW_ADMIN_IMMUTABLE_CHANGE_FIELDS =
  ('user', 'product')`, `REVIEW_ADMIN_DIRECT_FIELDS =
  (verified_purchase, helpful_yes, helpful_no)`.
- `get_readonly_fields(...)`: для существующего отзыва `user` и
  `product` read-only.
- `save_model(...)`:
  - **add:** `ReviewService.create_review(...)`; если submitted
    `is_approved=False`, затем `ReviewService.reject_review()`;
    `_save_direct_review_fields()`; refresh + `_copy_review_state()`.
  - **change:** проверка, что `user_id`/`product_id` не изменились
    (иначе `PermissionDenied`);
    изменения `rating/text/title` → `ReviewService.update_review()`;
    изменения approval → `approve_review()`/`reject_review()`;
    `_save_direct_review_fields()` — только `verified_purchase`,
    `helpful_yes`, `helpful_no` (вне агрегатного контракта), с
    явным `update_fields=[..., 'updated_at']`.
- `delete_model()` и `delete_queryset()` маршрутизируют через
  `ReviewService.delete_review(review, user=...)`.
- `_copy_review_state()` переносит все concrete field values обратно в
  `obj` (чтобы Admin-код видел реальное сохранённое состояние).
- Actions `approve_selected`/`reject_selected` теперь вызывают
  `ReviewService.approve_review()`/`reject_review()` per row.

### 7.3. `apps/catalog/tests/test_admin_product_review_stats.py` (added, +524)

**Почему:** H2-защита `ProductAdmin` должна быть проверена на трёх
уровнях: конфигурация форм, прямой guard, crafted POST, stale save,
concurrency, легитимный путь.

**Как:** новый файл, классы:
- `ProductAdminReviewAggregateReadOnlyTests`: readonly fields, нет
  input в change/add forms, rendered страницы.
- `ProductAdminReviewAggregateGuardTests`:
  - `save_model` отклоняет изменение rating и reviews_count;
  - отклоняет add с непустыми агрегатами;
  - позволяет безопасные поля (`name`/`description`) и сохраняет
    агрегаты;
  - тест `test_save_model_update_sql_excludes_protected_aggregate_fields`
    (через `CaptureQueriesContext`);
  - `test_save_model_change_without_pk_does_not_insert_product`;
  - `test_save_model_missing_row_does_not_full_save_or_recreate`;
  - `test_save_model_status_activation_still_sets_published_at`;
  - `test_crafted_admin_post_cannot_persist_review_aggregates` (e2e
    crafted POST).
- `ProductAdminReviewAggregateConcurrencyTests` (TransactionTestCase):
  `test_stale_product_admin_save_does_not_overwrite_review_stats` — stale
  Admin save не перезаписывает свежие сервисные агрегаты.
- `ProductReviewAggregateAuthoritativePathStillWorksTests`:
  `ReviewService` → `CatalogService` по-прежнему обновляет агрегаты.

### 7.4. `apps/reviews/tests/test_admin_review_aggregates.py` (added, +375)

**Почему:** `ReviewAdmin` должен проверяться функционально и по
`ModelAdmin`-хукам, чтобы `readonly_fields` не скрывал слабый путь.

**Как:** новый файл, классы:
- `ReviewAdminAggregateTestCase` — fixtures.
- `ReviewAdminConfigurationTests`: `user`/`product` read-only на
  existing review; add-форма принимает новые user/product/rating.
- `ReviewAdminSavePathTests`:
  - add/recalc aggregates; add unapproved не попадает в COUNT;
  - change rating → recalc;
  - direct `save_model` rating change;
  - change approval → recalc;
  - change text без изменения агрегатов;
  - `save_model` rejects product/user move.
- `ReviewAdminDeletePathTests`: single delete и bulk delete через
  ReviewService → агрегаты пересчитываются.
- `ReviewAdminActionTests`: `approve_selected`, `reject_selected` — per
  row через ReviewService.

### 7.5. `apps/reviews/services/review_service.py` (modified, +5/−5)

**Почему:** docstring метода должен упомянуть, что H2 защищает Admin от
обхода contract (после C1 указано residual H3).

**Как:** обновлён docstring `recalculate_product_rating()`: авторитетный
service-level путь — `CatalogService.set_review_stats()`; ARCH-001 H2
защищает Admin-поверхности от обхода service-level ownership (вместо
«Admin — отдельный residual H3, вне этапа C1»).

### 7.6. `apps/catalog/models/product.py` (modified, +2/−1)

**Почему:** комментарий в модели должен сказать, что H2 закрывает
Admin-обходы.

**Как:** заменено «Admin-поверхность — residual H3» на «ARCH-001 H2
закрывает ProductAdmin/ReviewAdmin обходы на Admin-поверхности».

### 7.7. `apps/catalog/services/catalog_service.py` (modified, +5/−3)

**Почему:** `set_review_stats` docstring нужно привести в соответствие с
закрытым Admin-обходом.

**Как:** в docstring: «Django Admin-форма остаётся отдельной поверхностью
... residual H3; Admin hardening вне C1» заменено на
«ARCH-001 H2 дополняет service-level ownership защитой Admin-поверхности:
ProductAdmin read-only + отказ forced save; ReviewAdmin направляет
aggregate-операции через ReviewService. Это не database-level
enforcement».

### 7.8. `apps/reviews/tests/test_architecture.py` (modified, +71/−6)

**Почему:** архитектурный guard должен теперь проверять и Admin-слои.

**Как:**
- Обновлён header-комментарий: Admin-поверхности больше не «residual
  H3», а покрыты поведенческими Admin-тестами и source-guard.
- Добавлен класс `AdminAggregateSurfaceArchitectureTests`:
  - `test_product_admin_review_aggregates_are_readonly_and_guarded`
    (check `PRODUCT_REVIEW_AGGREGATE_FIELDS` в readonly,
    `PRODUCT_ADMIN_PROTECTED_FIELDS`, `PermissionDenied`,
    `update_fields`);
  - `test_product_admin_does_not_import_reviews_service` (source-scan,
    запрещён `from apps.reviews`/`import apps.reviews`);
  - `test_review_admin_aggregate_paths_route_through_review_service`
    (source of `save_model`/`delete_*`/actions содержит
    `ReviewService.*`, но не `CatalogService.set_review_stats`).
- Обновлён `SingleServiceWriterScanTests` docstring: H2 Admin-поверхности
  защищаются поведенческими Admin-тестами; скан остаётся guard'ом
  service/runtime-кода.

### 7.9. `ARCHITECTURE.md` (modified, +54/−10)

**Почему:** документация должна описать H2 и связь с C1/H1.

**Как:**
- В описании `rating`/`reviews_count` («The Django Admin product form
  can still edit... H3») заменено на H2: форма read-only,
  `save_model` отклоняет, change-save через безопасный `update_fields`,
  stale-change отклоняется.
- В разделе Review aggregates добавлены H2-предложения: harden Admin
  surfaces для ProductAdmin и ReviewAdmin.
- Добавлен подраздел **Admin (ARCH-001 H2)**:
  - таблица Admin-поверхностей (ProductAdmin, ReviewAdmin add/change,
    reduce risk, H2 behavior);
  - схема `ReviewService → recalculate → CatalogService → Product`;
  - пояснение: ProductAdmin не пересчитывает агрегаты и не импортирует
    reviews, а запрещает; ReviewAdmin делегирует в ReviewService.
- Обновлена «Testing Strategy»: перечислены
  `test_admin_product_review_stats.py` и
  `test_admin_review_aggregates.py`.

---

## 8. Полный список изменённых файлов

| Файл | PR | Статус | +/− | Краткое «почему/как» |
|------|----|--------|-----|----------------------|
| `docs/audit/EDU-000-source-of-truth.md` | #16 | added | +91/0 | Аудит источника истины: расхождения, ограничения |
| `ARCHITECTURE.md` | #17 | modified | +16/−12 | Синхронизация webhook доки под HMAC |
| `ARCHITECTURE.md` | #18 | modified | +18/−4 | Единственная точка отмены + Admin-таблица variant |
| `apps/catalog/admin/product_admin.py` | #18 | modified | +12/0 | Inline variant: `is_active` readonly, `can_delete=False` |
| `apps/catalog/admin/product_variant_admin.py` | #18 | modified | +54/−36 | VariantAdmin guards: readonly/delete/save_model |
| `apps/catalog/tests/test_admin_variant_guards.py` | #18 | added | +172/0 | Guard-тесты variant Admin |
| `apps/discounts/tests/test_services.py` | #18 | modified | +40/0 | Regression coupon slot (B1) |
| `apps/orders/api_views/order_views.py` | #18 | modified | +15/−6 | `CANCELLED` → `cancel()` в endpoint |
| `apps/orders/services/order_service.py` | #18 | modified | +12/−10 | `transition_status` отвергает `CANCELLED` |
| `apps/orders/tests/test_api.py` | #18 | modified | +60/0 | API-тесты staff cancel coupon semantics |
| `apps/orders/tests/test_services.py` | #18 | modified | +8/−7 | `transition_status` rejects cancelled |
| `apps/shipping/services/shipping_service.py` | #18 | modified | +21/−11 | RETURNED → `cancel()` |
| `docs/architecture/ARCH-001-stage3.md` | #18 | modified | +17/0 | Cancellation entrypoint раздел |
| `ARCHITECTURE.md` | #20 | modified | +18/0 | Document Price bounds Admin guard (Issue #19) |
| `DIARY.md` | #20 | modified | +60/0 | Day 5 log Issue #19 |
| `apps/catalog/admin/product_admin.py` | #20 | modified | +45/0 | min/max read-only + save_model guard |
| `apps/catalog/tests/test_admin_product_bounds.py` | #20 | modified | +266/0 | Bounds tests (2 layer) |
| `ARCHITECTURE.md` | #21 | modified | +43/−6 | C1 ownership docs |
| `apps/catalog/models/product.py` | #21 | modified | +3/0 | Remove `update_rating`, doc ownership |
| `apps/catalog/services/catalog_service.py` | #21 | modified | +113/0 | `set_review_stats` writer + validation |
| `apps/reviews/__init__.py` | #21 | modified | +2/−1 | App docstring |
| `apps/reviews/models/review.py` | #21 | modified | +4/−1 | Model docstring (service contract) |
| `apps/reviews/services/review_service.py` | #21 | modified | +23/−9 | Recalculate → catalog contract |
| `apps/reviews/tests/test_architecture.py` | #21 | added | +296/0 | Architecture guard tests |
| `ARCHITECTURE.md` | #22 | modified | +48/0 | H1 concurrency docs |
| `apps/catalog/models/product.py` | #22 | modified | +5/−1 | H1 doc in model |
| `apps/catalog/services/catalog_service.py` | #22 | modified | +6/−2 | No own transaction in contract |
| `apps/reviews/models/review.py` | #22 | modified | +4/−2 | H1 doc in model |
| `apps/reviews/services/review_service.py` | #22 | modified | +57/0 | `_locked_product` + lock before aggregate |
| `apps/reviews/tests/test_architecture.py` | #22 | modified | +37/0 | Source guard H1 |
| `apps/reviews/tests/test_concurrency.py` | #22 | added | +756/0 | Concurrency tests |
| `ARCHITECTURE.md` | #23 | modified | +54/−10 | H2 Admin docs |
| `apps/catalog/admin/product_admin.py` | #23 | modified | +185/−37 | H2 ProductAdmin guard + safe update_fields |
| `apps/catalog/models/product.py` | #23 | modified | +2/−1 | H2 doc in model |
| `apps/catalog/services/catalog_service.py` | #23 | modified | +5/−3 | H2 doc in contract |
| `apps/catalog/tests/test_admin_product_review_stats.py` | #23 | added | +524/0 | ProductAdmin H2 tests |
| `apps/reviews/admin/review_admin.py` | #23 | modified | +131/0 | ReviewAdmin → ReviewService |
| `apps/reviews/services/review_service.py` | #23 | modified | +5/−5 | H2 doc in service |
| `apps/reviews/tests/test_admin_review_aggregates.py` | #23 | added | +375/0 | ReviewAdmin H2 tests |
| `apps/reviews/tests/test_architecture.py` | #23 | modified | +71/−6 | Admin surface architecture guard |

---

## 9. Выводы

1. День полностью посвящён архитектурной инициативе **ARCH-001**:
   владение и однонаправленность `reviews → catalog`, миграция с
   сигналов на явный сервисный контракт, конкурентность (H1), защита
   Admin-поверхности (H2) и закрытие обходов для ценовых границ и
   купонной отмены.
2. Основная синхронизация **код + тесты + документы** сохранялась внутри
   каждого PR: менялись модели/сервисы/Admin, добавлялись
   функциональные и архитектурные guard-тесты, одновременно
   обновлялись `ARCHITECTURE.md`, `DIARY.md`, `docs/architecture`.
3. Архитектурный стиль: авторитетный сервисный writer + Admin-запреты +
   двусторонние тесты (readonly/UI и серверный guard), чтобы снятие
   любой защиты ломало тесты.

## 10. Ограничения

- Отчёт описывает активность `main` за 30.08.2026 по данным
  `gh`/GitHub API.
- Ряд файлов, который был в `main` до 30.08.2026, изменился только в
  части указанных PR; в отчёте отражены только diff'ы в этот день.
- В отчёте не воспроизведены полностью огромные test-файлы
  (`test_concurrency.py`, `test_admin_product_review_stats.py`, и т.д.);
  описаны их логические блоки и назначение.
