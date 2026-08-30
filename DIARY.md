# 📒 Дневник действий — Amazon Clone

## 🗓️ День 1 — 2026-08-13

### Задача 1: Checkout — полноценное оформление заказа
**Приоритет:** 🔴 Критический  
**Статус:** ✅ Завершена  
**Что сделано:**
- Создан `frontend/src/types/checkout.ts` — типы Address, ShippingMethod, CalculatedShippingMethod, CouponPreview, CheckoutSummary, PaymentMethod, CheckoutStep
- Создан `frontend/src/api/addresses.ts` — CRUD для /users/addresses/
- Создан `frontend/src/api/shipping.ts` — методы и расчёт стоимости
- Создан `frontend/src/api/discounts.ts` — preview/apply/remove промокода
- Обновлён `frontend/src/api/index.ts` — реэкспорт новых API
- Обновлён `frontend/src/types/index.ts` — реэкспорт checkout
- Убран дублирующий `Address` из `user.ts` → теперь из `checkout.ts`
- Обновлён `frontend/src/types/order.ts` — добавлены ORDER_STATUS_MAP, ORDER_STATUS_COLOR
- **Полностью переписан `frontend/src/pages/Cart/CheckoutPage.tsx`** — 4 шага:
  - Шаг 1: Выбор/добавление адреса доставки
  - Шаг 2: Выбор способа доставки + расчёт стоимости
  - Шаг 3: Выбор способа оплаты + промокод
  - Шаг 4: Подтверждение заказа (итоги, состав, кнопка «Оформить»)
- TypeScript: 0 ошибок, Vite build: 147 модулей ✅

---

### Задача 2: Profile — полноценная страница профиля
**Приоритет:** 🔴 Критический  
**Статус:** ✅ Завершена  
**Что сделано:**
- Обновлён `frontend/src/types/user.ts` — добавлены UserProfile, UpdateProfileRequest, ChangePasswordRequest
- Создан `frontend/src/api/profile.ts` — getMe, updateProfile, changePassword
- Обновлён `frontend/src/api/index.ts` — реэкспорт profileApi
- **Полностью переписан `frontend/src/pages/Profile/ProfilePage.tsx`**:
  - Шапка профиля (аватар-инициал, ФИО, email, дата регистрации)
  - Быстрые ссылки (Заказы, Избранное)
  - 3 таба: Личные данные / Адреса / Пароль
  - Таб «Личные данные»: имя, фамилия, телефон, пол, часовой пояс, язык, подписка
  - Таб «Адреса»: список, добавить, редактировать, удалить, по умолчанию
  - Таб «Пароль»: смена пароля с валидацией
  - Кнопка «Выйти из аккаунта»
- TypeScript: 0 ошибок, Vite: 148 модулей ✅

---

### Задача 3: Фронтенд-тесты — Vitest + React Testing Library + MSW
**Приоритет:** 🔴 Критический  
**Статус:** ⚠️ Частично — работает после исправления addresses.ts  
**Что сделано:**
- Установлены: `vitest`, `@testing-library/react`, `@testing-library/jest-dom`, `@testing-library/user-event`, `jsdom`, `msw@2`
- Обновлён `vite.config.ts` — добавлен блок `test` (globals, jsdom, setupFiles)
- Создан `frontend/src/test/setup.ts` — jest-dom matchers + MSW server lifecycle
- Создан `frontend/src/test/msw-server.ts` — MSW setupServer для Node
- **Рабочие версии (workspace): 16 тестов:**
  - `formatPrice.test.ts` — 9 тестов (7 formatPrice + 2 formatPriceRange)
  - `formatDate.test.ts` — 2 теста
  - `authStore.test.ts` — 2 теста (initial state, logout)
  - `cartStore.test.ts` — 3 теста (initial, set cart, set isLoading)
- **Deploy-скрипт записал упрощённые версии: 12 тестов** (7+1+2+2)
- ⚠️ **BUG: addresses.ts сломан из-за PowerShell `${id}` expansion** (см. Баг #1)

---

### Задача 4: Поиск товаров — __icontains quick win
**Приоритет:** 🟡 Важный  
**Статус:** ✅ Уже реализовано!  
**Что обнаружено:**  
- `.search(query)` в `product_queryset.py` уже реализован: PostgreSQL → SearchVector+GIN, SQLite → `__icontains` fallback
- `ProductListView` уже принимает `?search=` query-параметр
- Frontend Header уже отправляет `?search=` → CatalogPage
- **Ничего добавлять не нужно** — поиск работает из коробки! ✅

---

### Задача 5: Docker Compose
**Приоритет:** 🟡 Важный  
**Статус:** ✅ Завершена  
**Что сделано:**
- Создан `docker-compose.yml` — 6 сервисов: PostgreSQL 18, Redis 7, Django backend, Celery worker, Celery beat, React frontend
- Создан `Dockerfile.backend` — Python 3.13 + psycopg3 + Pillow + Celery
- Создан `Dockerfile.frontend` — Node 22 + Vite dev server
- Создан `.dockerignore` — исключения из контекста сборки
- Health checks для db и redis, depends_on с condition
- Volume для pgdata и media

---

### Задача 6: Celery + Redis — базовая настройка
**Приоритет:** 🟡 Важный  
**Статус:** ✅ Завершена  
**Что сделано:**
- Создан `config/celery.py` — приложение Celery с Redis broker/backend, JSON-сериализация, auto-discover, beat schedule
- Обновлён `config/__init__.py` — загрузка Celery при старте Django
- Создан `apps/cart/tasks.py` — задачи cleanup_old_carts и send_abandoned_cart_reminders
- Обновлён `requirements.txt` — добавлены celery[redis]>=5.4, redis>=5.0
- Beat schedule: очистка корзин раз в сутки, напоминания каждый час
- 950 бэкенд-тестов пройдены ✅

---

### Задача 7: Email-уведомления — заглушка + настройка
**Приоритет:** 🟡 Важный  
**Статус:** ✅ Завершена (заглушка)  
**Что сделано:**
- Создан `apps/notifications/tasks.py` — Celery-задачи:
  - `send_email_notification` — универсальная отправка (заглушка → console backend)
  - `send_order_confirmation` — email при подтверждении заказа
  - `send_order_shipped` — email при отправке заказа
- Логика: создание Notification в БД + async send_email_notification.delay()
- Ready для интеграции с django-anymail / SMTP при подключении реального провайдера

---

### Задача 8: Баннеры на главной странице
**Приоритет:** 🟢 Улучшение  
**Статус:** ✅ Завершена  
**Что сделано:**
- **Переписан `frontend/src/pages/Home/HomePage.tsx`**:
  - Hero-карусель с 3 баннерами (авто-прокрутка каждые 5 сек)
  - Точки навигации + стрелки влево/вправо
  - Градиентные фоны (orange/red, gray, yellow/amber)
  - Секция «Рекомендуемые товары» (4 колонки)
  - Секция преимуществ (доставка, оплата, возврат, поддержка)
- TypeScript: 0 ошибок, Vite: 148 модулей ✅

---

### Задача 9: «Недавно просмотренные» товары
**Приоритет:** 🟢 Улучшение  
**Статус:** ✅ Завершена (заглушка fetch)  
**Что сделано:**
- Создан `frontend/src/store/recentlyViewedStore.ts` — localStorage slugs + fetchRecentlyViewed
- Обновлён `frontend/src/store/index.ts` — экспорт useRecentlyViewedStore
- Limit 20 товаров, при добавлении дедупликация
- ⚠️ `fetchRecentlyViewed` — заглушка, не обращается к API (нужен backend endpoint)
- TypeScript: 0 ошибок ✅

---

### Задача 10: Улучшение Orders — статусы с цветами + 404 страница
**Приоритет:** 🟢 Улучшение  
**Статус:** ✅ Завершена  
**Что сделано:**
- Обновлён `frontend/src/pages/Orders/OrderListPage.tsx` — цветные бейджи статусов (ORDER_STATUS_COLOR)
- Создан `frontend/src/pages/NotFound/NotFoundPage.tsx` — красивая 404 страница
- Обновлён `frontend/src/app/router.tsx` — добавлен маршрут `*` → NotFoundPage
- TypeScript: 0 ошибок, Vite: 149 модулей ✅

---

## 🐛 НАЙДЕННЫЕ БАГИ И ИСПРАВЛЕНИЯ

### Баг #1: PowerShell `${id}` expansion в deploy_all.ps1 (АКТУАЛЬНО!)
**Дата обнаружения:** 2026-08-13  
**Статус:** 🔴 Не исправлено на машине пользователя  
**Проблема:**
- `deploy_all.ps1` строки 264-266: внутри PowerShell here-string `@"..."@` использован JS template literal `` `/users/addresses/${id}/` ``
- PowerShell раскрывает `${id}` как свою переменную (пустую) → получается `/users/addresses//`
- Backtick `` ` `` перед `/` тоже поглощается как escape-символ PowerShell
- Результат: **Syntax error "a"** в addresses.ts → authStore и cartStore тесты не загружаются

**Ошибка vitest:**
```
ERROR: Syntax error "a"
addresses.ts:5:139:  api.patch<Address>(/users/addresses//, data)
                                            ^
```

**Исправление в deploy_all.ps1:**
- `` ` `` → ``` `` ``` (двойной backtick = литеральный backtick в PowerShell here-string)
- `${id}` → `` `${id} `` (backtick-dollar = литеральный $)
- Пример: `` ``/users/addresses/`${id}/`` `` → на диске: `` `/users/addresses/${id}/` ``

**Немедленное исправление на машине:**
- Запустить `fix_addresses.ps1` (использует `@'...'@` single-quoted here-string)
- Или вручную переписать `I:\NewPythonProjects\frontend\src\api\addresses.ts`

**Результат после исправления:** Vitest должен показать 12 тестов (deploy-версии) или 16 (workspace-версии)

---

### Баг #2: deploy_all.ps1 ParserError line 837 (ИСПРАВЛЕНО РАНЕЕ)
**Статус:** ✅ Исправлено  
**Проблема:** Hashtable array с `$` variable expansion внутри here-strings  
**Решение:** Убраны hashtable структуры, используется CF (Copy-File) для больших файлов

---

## 📊 ИТОГОВАЯ СВОДКА (актуально на 2026-08-13)

### Backend
| Метрика | Было | Стало |
|---------|------|-------|
| Тестов  | 950  | 950 (все ✅, 2 skipped PostgreSQL-only) |
| Celery задач | 0 | 3 (cleanup, reminders, email) |
| Docker   | нет  | docker-compose.yml + 2 Dockerfile |

### Frontend
| Метрика | Было | Стало |
|---------|------|-------|
| TypeScript ошибок | 0 | 0 ✅ |
| Vite модулей     | 144 | 149 |
| Vitest тестов    | 0   | 12 (deploy) / 16 (workspace) ⚠️ |
| Checkout шагов   | 1 (примитив) | 4 (адрес→доставка→оплата→подтверждение) |
| Profile табов    | 0 (только email) | 3 (данные+адреса+пароль) |
| Баннеров на главной | 1 (статика) | 3 (карусель с автопрокруткой) |
| 404 страница     | нет | ✅ |

### Vitest: текущее состояние на машине пользователя
```
 ✓ src/utils/__tests__/formatDate.test.ts (1 test)
 ✓ src/utils/__tests__/formatPrice.test.ts (7 tests)
 ❯ src/store/__tests__/authStore.test.ts (0 test) — FAIL: addresses.ts syntax error
 ❯ src/store/__tests__/cartStore.test.ts (0 test) — FAIL: addresses.ts syntax error
```
**После исправления addresses.ts:** все 4 файла загрузятся, 12 тестов пройдут ✅

### Новые файлы
**Frontend (13):**
- `src/types/checkout.ts` — типы для чекаута
- `src/api/addresses.ts` — CRUD адресов ⚠️ (сломан на машине пользователя)
- `src/api/shipping.ts` — расчёт доставки
- `src/api/discounts.ts` — промокоды
- `src/api/profile.ts` — профиль + смена пароля
- `src/store/recentlyViewedStore.ts` — недавно просмотренные
- `src/test/setup.ts` — Vitest setup
- `src/test/msw-server.ts` — MSW server
- `src/utils/__tests__/formatPrice.test.ts`
- `src/utils/__tests__/formatDate.test.ts`
- `src/store/__tests__/authStore.test.ts`
- `src/store/__tests__/cartStore.test.ts`
- `src/pages/NotFound/NotFoundPage.tsx`

**Backend (5):**
- `config/celery.py` — Celery конфигурация
- `apps/cart/tasks.py` — Celery задачи корзины
- `apps/notifications/tasks.py` — Celery задачи email
- `Dockerfile.backend` + `Dockerfile.frontend`
- `docker-compose.yml` + `.dockerignore`

---

## ⚠️ НЕ РЕШЕНО (известные ограничения)

1. **addresses.ts сломан на машине пользователя** — нужно запустить `fix_addresses.ps1`
2. **Миграция `0003_reviewhelpfulvote`** не применена на машине пользователя
3. **Celery/Redis не запущены** — требуется Redis server или Docker
4. **`recentlyViewedStore.ts` `fetchRecentlyViewed`** — заглушка, не обращается к API (нужен backend endpoint `/catalog/products/recently_viewed/` или bulk-slug lookup)
5. **Email tasks** — заглушки (console logging), нужна интеграция с SMTP/django-anymail
6. **Coupon apply/remove в CheckoutPage** — использует order_id, но заказ создаётся на финальном шаге (нужен рефакторинг flow)
7. **Deploy-скрипт тесты** — упрощённые версии (12 тестов вместо 16 из workspace)
8. **3 high severity vulnerabilities** в npm audit — зависимости Vite/esbuild

---

---

## 🗓️ День 2 — 2026-08-14

### Событие 1: `cd` не меняет диск на Windows
**Время:** ~19:20  
**Контекст:** Пользователь попробовал `cd I:\NewPythonProjects\frontend` — директория не сменилась  
**Причина:** Windows `cd` по умолчанию не переключает диск, только каталог на текущем диске  
**Решение:**
- В **cmd.exe**: `cd /d I:\NewPythonProjects\frontend`
- В **PowerShell**: `Set-Location -Path "I:\NewPythonProjects\frontend"` (обычно работает автоматически)
- Альтернатива: `I:` затем `cd \NewPythonProjects\frontend`
**Статус:** ✅ Разъяснено, не баг проекта

---

### Событие 2: Vitest — 2 failed test suites (addresses.ts syntax error)
**Время:** ~19:28  
**Контекст:** Пользователь запустил:
```cmd
npm install -D vitest @testing-library/react @testing-library/jest-dom @testing-library/user-event jsdom msw
npx vitest run
```
**Результат vitest:**
```
 ✓ src/utils/__tests__/formatDate.test.ts (1 test)  13ms
 ✓ src/utils/__tests__/formatPrice.test.ts (7 tests) 13ms
 ❯ src/store/__tests__/authStore.test.ts (0 test)     FAIL
 ❯ src/store/__tests__/cartStore.test.ts (0 test)     FAIL

Error: Transform failed with 1 error:
addresses.ts:5:139: ERROR: Syntax error "a"
  api.patch<Address>(/users/addresses//, data)
                                  ^
```
**Причина:** `deploy_all.ps1` записал `addresses.ts` через PowerShell here-string `@"..."@`:
- Backtick `` ` `` перед `/` **поглощён** как escape-символ PowerShell → исчез
- `${id}` **раскрылся** как PowerShell-переменная (пустая) → `/users/addresses//`
- Итог: JS template literals `` `/users/addresses/${id}/` `` превратились в `/users/addresses//`

**Затронутые строки (deploy_all.ps1):**
- Строка 264: `updateAddress` → `` `/users/addresses/${id}/` ``
- Строка 265: `deleteAddress` → `` `/users/addresses/${id}/` ``
- Строка 266: `setDefaultAddress` → `` `/users/addresses/${id}/default/` ``

**Статус:** 🔴 Обнаружен, исправление готово (см. Событие 3)

---

### Событие 3: Исправление deploy_all.ps1 — экранирование `${id}`
**Время:** ~19:35  
**Что сделано:**
1. **Исправлен `deploy_all.ps1`** в workspace — 3 строки addresses.ts:
   - `` ` `` → ``` `` ``` (двойной backtick = литерал в PowerShell here-string)
   - `${id}` → `` `${id} `` (backtick-dollar = литеральный $)
   - Пример: `` ``/users/addresses/`${id}/`` `` → на диске запишется: `` `/users/addresses/${id}/` ``
2. **Создан `fix_addresses.ps1`** — скрипт для немедленного исправления на машине пользователя:
   - Использует `@'...'@` — single-quoted here-string (НЕ раскрывает `$`)
   - Записывает правильный `addresses.ts` с полноценными JS template literals
3. **Проверены другие строки** `deploy_all.ps1` на наличие `${...}` — других проблемных мест нет
4. **Обновлён `DIARY.md`** — добавлен Баг #1 с полным описанием

**Статус:** ✅ Исправлено в workspace, ⚠️ не применено на машине пользователя

---

### Событие 4: Обновление дневника — полная актуализация
**Время:** ~19:40  
**Что сделано:**
- Перечитан весь DIARY.md (222 строки)
- Добавлена секция 🐛 НАЙДЕННЫЕ БАГИ И ИСПРАВЛЕНИЯ с Баг #1 и Баг #2
- Обновлена ИТОГОВАЯ СВОДКА с текущим состоянием Vitest
- Добавлен список НЕ РЕШЕНО (8 пунктов)
- Добавлены СЛЕДУЮЩИЕ ШАГИ (7 пунктов)

**Статус:** ✅ Завершено

---

### 📊 Сводка дня 2

| Метрика | Значение |
|---------|----------|
| Обнаружено багов | 1 (addresses.ts `${id}` expansion) |
| Исправлено багов (workspace) | 1 |
| Исправлено багов (машина) | 0 — ждёт `fix_addresses.ps1` |
| Vitest на машине | 8 passed / 2 suites failed |
| После исправления | 12 тестов в 4 файлах ✅ |
| Новых файлов | `fix_addresses.ps1` |
| Обновлено файлов | `deploy_all.ps1` (3 строки), `DIARY.md` |

---

## 🔍 АНАЛИЗ ПРОЕКТА — День 2 (2026-08-14)

### Текущее состояние проекта

**Backend (14 apps, 950 tests ✅):**
| App | Tests | Frontend API? |
|-----|-------|--------------|
| analytics | 54 | ❌ Нет |
| cart | 127 | ✅ Да |
| catalog | 125 | ✅ Да |
| discounts | 41 | ✅ Да (preview/apply/remove) |
| inventory | 44 | ❌ Нет |
| notifications | 32 | ❌ Нет |
| orders | 51 | ✅ Да |
| payments | 101 | ⚠️ Частично (webhook нет) |
| pricing | 55 | ❌ Нет |
| reviews | 79 | ✅ Да |
| shipping | 105 | ⚠️ Частично (только methods+calculate, shipments нет) |
| users | 102 | ✅ Да |
| wishlist | 34 | ✅ Да |
| core | — | ✅ health |

**Frontend (12 pages, 12 components, 8 stores, 13 API clients):**
| Страница | Строк | Статус |
|----------|-------|--------|
| ProductPage | 1034 | ✅ Полный Ozon-дизайн + отзывы |
| CheckoutPage | 513 | ✅ 4-шаговый |
| ProfilePage | 372 | ✅ 3 таба |
| CatalogPage | 115 | ✅ Фильтры + пагинация |
| HomePage | 148 | ✅ Баннеры + карусель |
| WishlistPage | 86 | ✅ API-connected |
| RegisterPage | 69 | ✅ |
| OrderListPage | 61 | ✅ Цветные статусы |
| CartPage | 54 | ✅ |
| LoginPage | 46 | ✅ |
| NotFoundPage | — | ✅ 404 |
| OrderDetailPage | 77 | ⚠️ Простой, без timeline |

### Выявленные пробелы

**🔴 Критические (UX сломан без этого):**
1. **Нет Error Boundary** — любая JS-ошибка в компоненте убивает всё приложение
2. **Нет Skeleton/Spinner при загрузке** — многие страницы показывают пустоту пока грузятся
3. **Нет Notifications/Toasts** — пользователь не видит результат действий (добавил в корзину, сохранил профиль, ошибка)
4. **Нет формы восстановления пароля** — `/auth/password-reset/` endpoint не подключён

**🟡 Важные (функции, которые ожидают пользователи):**
5. **Нет страницы уведомлений** — backend имеет 5 endpoints (list, unread, count, read-all, mark-read), но фронтенд не использует
6. **Нет Recently Viewed (по-настоящему)** — `fetchRecentlyViewed` заглушка, нужен backend endpoint
7. **Нет OrderDetailPage timeline** — страница деталей заказа примитивная (77 строк), нет истории статусов, товаров, отслеживания доставки
8. **Нет категории в навигации** — дерево категорий загружается, но нет sidebar меню или dropdown в Header
9. **Нет фильтрации по цене (range slider)** — Filters.tsx есть, но нет range-ползунка для min_price/max_price
10. **Нет Image Zoom** на ProductPage — у Ozon увеличение при наведении

**🟢 Улучшения (качество и масштабирование):**
11. **Нет React Query / SWR** — все загрузки через useEffect + useState, нет кэширования, рефETCHа, stale-while-revalidate
12. **Нет Zod / form validation** — формы валидируются вручную (if/else), нет schema validation
13. **Нет i18n** — всё на русском хардкоде, но тип проекта предполагает масштаб
14. **Нет SEO** — нет react-helmet, нет meta tags, нет Open Graph
15. **Нет E2E тестов** — только unit-тесты (Vitest), нет Playwright/Cypress
16. **Нет django-debug-toolbar** — нет профилирования SQL-запросов
17. **Нет django-storages / S3** — медиа-файлы только локально
18. **Нет PWA** — нет service worker, нет offline, нет install prompt
19. **Нет аналитики на фронтенде** — backend analytics app (8 endpoints, 54 теста) нигде не используется

---

## 📋 РЕКОМЕНДУЕМЫЕ ДАЛЬНЕЙШИЕ ДЕЙСТВИЯ

### Фаза 1: Стабилизация (⚡ сделать сейчас)

| # | Задача | Сложность | Время | Почему |
|---|--------|-----------|-------|--------|
| 1 | **React Error Boundary** | ⭐ | 30 мин | Без него любой render crash = белый экран |
| 2 | **Toast/Notification компонент** | ⭐⭐ | 1 ч | Пользователь не видит результат действий |
| 3 | **Skeleton загрузки** | ⭐⭐ | 1 ч | UX: вместо пустоты — серые плейсхолдеры |
| 4 | **fix_addresses.ps1 + применить миграции** | ⭐ | 10 мин | Блокирует тесты прямо сейчас |

### Фаза 2: Ключевые фичи (🛒 магазин выглядит как магазин)

| # | Задача | Сложность | Время | Почему |
|---|--------|-----------|-------|--------|
| 5 | **Страница уведомлений** | ⭐⭐ | 2 ч | Backend готов (5 endpoints), нужен UI |
| 6 | **OrderDetailPage — полный** | ⭐⭐⭐ | 3 ч | Timeline, товары, адрес, отмена, отслеживание |
| 7 | **Категории в навигации** | ⭐⭐ | 1.5 ч | CategoryTree уже есть в API |
| 8 | **Recently Viewed (backend endpoint)** | ⭐⭐ | 1.5 ч | Завершить фичу — нужен bulk-slug lookup |
| 9 | **Восстановление пароля** | ⭐⭐ | 2 ч | Критический UX-путь |

### Фаза 3: Улучшение качества (📈 масштабирование)

| # | Задача | Сложность | Время | Почему |
|---|--------|-----------|-------|--------|
| 10 | **TanStack Query** | ⭐⭐⭐ | 4 ч | Заменить useEffect+useState, кэш, refetch, SWR |
| 11 | **Zod + React Hook Form** | ⭐⭐⭐ | 3 ч | Schema validation для всех форм |
| 12 | **Price Range Slider** | ⭐⭐ | 1.5 ч | Фильтр по цене — базовая фича e-commerce |
| 13 | **django-debug-toolbar** | ⭐ | 30 мин | Профилирование SQL в dev |
| 14 | **E2E: Playwright** | ⭐⭐⭐ | 4 ч | Тест критических путей: регистрация→каталог→корзина→заказ |

### Фаза 4: Production-ready (🚀 деплой)

| # | Задача | Сложность | Время | Почему |
|---|--------|-----------|-------|--------|
| 15 | **SEO: react-helmet-async** | ⭐⭐ | 2 ч | Meta tags, Open Graph, title |
| 16 | **django-storages + S3/MinIO** | ⭐⭐⭐ | 3 ч | Медиа-файлы не на локальном диске |
| 17 | **SMTP / django-anymail** | ⭐⭐ | 1.5 ч | Реальная отправка email |
| 18 | **Analytics Dashboard** | ⭐⭐⭐ | 4 ч | Backend готов (8 endpoints), нужен frontend |
| 19 | **PWA** | ⭐⭐⭐ | 3 ч | Offline, install, push notifications |

---

## 📋 СЛЕДУЮЩИЕ ШАГИ (немедленные)

1. ✅ **Выполнено:** Реализованы все задачи Фазы 1 + Фазы 2
2. **Применить изменения на машине** — скопировать файлы из workspace
3. **Запустить fix_addresses.ps1** → исправить addresses.ts
4. **Применить миграцию:** `python manage.py migrate`
5. **Перезаполнить БД:** `python manage.py populate_admin --clear`
6. **Запустить dev:** `npm run dev` в cmd.exe
7. **Протестировать в браузере** — все новые страницы

---

## 🗓️ День 2 (продолжение) — Реализация Фазы 1 + Фазы 2

### ✅ Задача 1: React Error Boundary
**Время:** 19:45  
**Что сделано:**
- Создан `frontend/src/components/ui/ErrorBoundary.tsx` (115 строк)
  - Ловит JS-ошибки рендеринга — fallback UI вместо белого экрана
  - Кнопки «Попробовать снова» + «Обновить страницу»
  - Раскрываемые детали ошибки (dev mode)
  - Проп `name` для логирования, проп `fallback` для кастомного UI
  - TODO: интеграция с Sentry в продакшне
- Обновлён `App.tsx` — RouterProvider обёрнут в `<ErrorBoundary name="App">`
- Обновлён `components/ui/index.ts` — экспорт ErrorBoundary

---

### ✅ Задача 2: Toast/Notification компонент
**Время:** 19:50  
**Что сделано:**
- Создан `frontend/src/components/ui/Toast.tsx` (155 строк)
  - `useToastStore` — Zustand-стор (глобальный)
  - Удобный API: `toast.success('...')`, `toast.error('...')`, `toast.info('...')`, `toast.warning('...')`
  - `ToastContainer` — фиксированная позиция (top-right), z-50
  - Автозакрытие: success/info=4с, warning=5с, error=6с
  - Анимация выхода (opacity + translate)
  - Кнопка закрыть (×)
  - 4 типа с цветами: green/red/blue/yellow
- Обновлён `providers.tsx` — добавлен `<ToastContainer />`
- Обновлён `components/ui/index.ts` — экспорт ToastContainer, toast, useToastStore

---

### ✅ Задача 3: Skeleton компоненты
**Время:** 19:55  
**Что сделано:**
- Создан `frontend/src/components/ui/Skeleton.tsx` (130 строк)
  - `Skeleton` — базовый прямоугольник с pulse-анимацией
  - `SkeletonText` — несколько строк текста (последняя короче)
  - `SkeletonCard` — карточка товара в каталоге
  - `SkeletonProductPage` — полная страница товара (галерея+инфо+блок покупки)
  - `SkeletonOrder` — карточка заказа
  - Проп `circle` для аватаров
- Обновлён `components/ui/index.ts` — экспорт всех Skeleton компонентов

---

### ✅ Задача 5: Страница уведомлений
**Время:** 20:05  
**Что сделано:**
- Создан `frontend/src/api/notifications.ts` (85 строк)
  - 5 API-функций: getNotifications, getUnreadNotifications, getUnreadCount, markAllRead, markAsRead
  - Типы: NotificationItem, NotificationListResponse, UnreadCountResponse
- Создан `frontend/src/store/notificationStore.ts` (95 строк)
  - Zustand-стор: notifications, unreadCount, isLoading
  - fetchNotifications(page), fetchUnreadCount(), markAsRead(id), markAllRead()
  - startPolling() / stopPolling() — опрос unread_count каждые 30 сек
- Создан `frontend/src/pages/Notifications/NotificationPage.tsx` (190 строк)
  - Список уведомлений с пагинацией
  - Иконки по типу (order_confirmed=✅, order_shipped=📦 и т.д.)
  - Непрочитанные — голубой фон + синяя точка
  - Кнопка «Прочитать все» + «✓» на каждом
  - Ссылки на связанные объекты (заказ, товар)
  - Форматирование времени (timeAgo)
  - Skeleton при загрузке
- Обновлён `api/index.ts` — экспорт notificationsApi
- Обновлён `store/index.ts` — экспорт useNotificationStore

---

### ✅ Задача 6: Полный OrderDetailPage
**Время:** 20:15  
**Что сделано:**
- Переписан `frontend/src/pages/Orders/OrderDetailPage.tsx` (77 → 280 строк)
  - Timeline статусов (pending→confirmed→processing→shipped→delivered)
  - Товары заказа с мини-изображениями
  - Адрес доставки + примечание
  - Блок стоимости (подытог, доставка, скидка, итого)
  - Дата оформления + даты подтверждения/доставки/отмены
  - Кнопка «Отменить заказ» (для pending/confirmed)
  - Skeleton при загрузке
  - Цветные бейджи статусов (ORDER_STATUS_COLOR)

---

### ✅ Задача 7: Категории в навигации (Header)
**Время:** 20:20  
**Что сделано:**
- Переписан `frontend/src/components/layout/Header.tsx` (73 → 130 строк)
  - Выпадающее меню категорий (depth=1, максимум 8)
  - Закрытие по клику вне меню
  - Ссылка «Все категории →»
  - Бейдж уведомлений (🔔 + количество unreadCount)
  - Поллинг unread_count каждые 30 сек (startPolling/stopPolling)
  - Категории загружаются из catalogStore при первом рендере

---

### ✅ Задача 8: Recently Viewed — backend endpoint + frontend
**Время:** 20:30  
**Что сделано:**

**Backend:**
- Создан `apps/catalog/api_views/product_brief_views.py` (85 строк)
  - `ProductBySlugsView` — GET /api/v1/catalog/products/by-slugs/?slugs=slug1,slug2
  - AllowAny, максимум 20 slug'ов
  - Использует `Product.objects.for_list().filter(slug__in=slugs)`
  - Возвращает ProductListSerializer (тот же, что для каталога)
- Обновлён `apps/catalog/urls.py`:
  - Добавлен `products/by-slugs/` ПЕРЕД `products/<str:identifier>/`
  - Импорт ProductBySlugsView
- Обновлён `apps/catalog/api_views/__init__.py`:
  - Добавлен ProductBySlugsView в импорты и __all__

**Frontend:**
- Обновлён `frontend/src/api/catalog.ts`:
  - Добавлена `getProductsBySlugs(slugs: string[]): Promise<ProductListItem[]>`
- Переписан `frontend/src/store/recentlyViewedStore.ts` (30 → 80 строк):
  - `fetchRecentlyViewed()` — вызывает `catalogApi.getProductsBySlugs(slugs)`
  - Продукты сохраняются в порядке просмотренных (не API order)
  - `clearAll()` — очистка localStorage + стора

---

### ✅ Задача 9: Восстановление пароля
**Время:** 20:40  
**Что сделано:**

**Backend:**
- Создан `apps/users/api_views/password_reset_views.py` (120 строк)
  - `PasswordResetRequestView` — POST /api/v1/auth/password-reset/
    - Body: {email} → генерирует uid + token, логирует (TODO: Celery email)
    - Всегда 200 OK — не раскрывает существование email
  - `PasswordResetConfirmView` — POST /api/v1/auth/password-reset/confirm/
    - Body: {uid, token, new_password, new_password_confirm} → устанавливает новый пароль
    - Валидация: пароли совпадают, min 8 символов, токен действителен
  - Сериализаторы: PasswordResetRequestSerializer, PasswordResetConfirmSerializer
- Обновлён `apps/users/urls.py`:
  - Добавлены 2 маршрута: password-reset/ и password-reset/confirm/

**Frontend:**
- Создан `frontend/src/pages/Login/ForgotPasswordPage.tsx` (140 строк)
  - 3 шага: request email → confirm (uid + token + new password) → success
  - Валидация: пароли совпадают, min 8 символов
  - Toast-уведомления при каждом шаге
- Обновлён `router.tsx`:
  - Добавлен маршрут /forgot-password → ForgotPasswordPage
  - Добавлен маршрут /notifications → NotificationPage

---

### 📊 Сводка Фазы 1+2

| # | Задача | Файлы | Строк |
|---|--------|-------|-------|
| 1 | Error Boundary | 2 (new+edit) | 115 |
| 2 | Toast | 3 (new+edit) | 155 |
| 3 | Skeleton | 2 (new+edit) | 130 |
| 5 | Notifications page | 4 (new+edit) | 370 |
| 6 | OrderDetailPage | 1 (rewrite) | 280 |
| 7 | Header categories | 1 (rewrite) | 130 |
| 8 | Recently Viewed | 5 (new+edit) | 165+85 |
| 9 | Password Reset | 4 (new+edit) | 120+140 |
| **Итого** | **8 задач** | **22 файла** | **~1690 строк** |

### Новые файлы (10):
- `frontend/src/components/ui/ErrorBoundary.tsx`
- `frontend/src/components/ui/Toast.tsx`
- `frontend/src/components/ui/Skeleton.tsx`
- `frontend/src/api/notifications.ts`
- `frontend/src/store/notificationStore.ts`
- `frontend/src/pages/Notifications/NotificationPage.tsx`
- `frontend/src/pages/Login/ForgotPasswordPage.tsx`
- `apps/catalog/api_views/product_brief_views.py`
- `apps/users/api_views/password_reset_views.py`

### Обновлённые файлы (12):
- `frontend/src/app/App.tsx`
- `frontend/src/app/providers.tsx`
- `frontend/src/app/router.tsx`
- `frontend/src/components/layout/Header.tsx`
- `frontend/src/components/ui/index.ts`
- `frontend/src/store/index.ts`
- `frontend/src/store/recentlyViewedStore.ts`
- `frontend/src/api/catalog.ts`
- `frontend/src/api/index.ts`
- `frontend/src/pages/Orders/OrderDetailPage.tsx`
- `apps/catalog/urls.py`
- `apps/catalog/api_views/__init__.py`
- `apps/users/urls.py`

---

### ✅ Создан `deploy_all_v2.ps1` (591 строк)
**Время:** 20:55  
**Что сделано:**
- Полностью переписан deploy-скрипт с учётом всех новых файлов
- **Ключевое исправление:** все файлы с JS template literals (`${id}`, `${slug}`) копируются через CF (Copy-File), не inline
- Все inline-блоки используют `@'...'@` (single-quoted here-string) — PowerShell НЕ раскрывает `$`
- addresses.ts теперь inline через `@'...'@` — `${id}` не раскрывается!
- Включены все файлы из Фазы 1+2 + все предыдущие (Celery, Docker, Checkout, Profile, etc.)

**Deploy-файлы (18 штук, пользователь скачивает в C:\Deploy):**

| Файл | Размер | Назначение |
|------|--------|-----------|
| `deploy_all_v2.ps1` | 32 KB | Главный скрипт |
| `deploy_populate_admin.py` | 46 KB | Заполнение БД (admin) |
| `deploy_populate_full.py` | 49 KB | Заполнение БД (full) |
| `deploy_frontend_src_CheckoutPage.tsx` | 24 KB | CheckoutPage |
| `deploy_frontend_src_ProfilePage.tsx` | 17 KB | ProfilePage |
| `deploy_frontend_src_HomePage.tsx` | 6 KB | HomePage |
| `deploy_frontend_src_OrderDetailPage.tsx` | 14 KB | OrderDetailPage (НОВЫЙ) |
| `deploy_frontend_src_NotificationPage.tsx` | 9 KB | NotificationPage (НОВЫЙ) |
| `deploy_frontend_src_Header.tsx` | 7 KB | Header (НОВЫЙ) |
| `deploy_frontend_src_ForgotPasswordPage.tsx` | 6 KB | ForgotPassword (НОВЫЙ) |
| `deploy_frontend_src_ErrorBoundary.tsx` | 5 KB | ErrorBoundary (НОВЫЙ) |
| `deploy_frontend_src_Skeleton.tsx` | 5 KB | Skeleton (НОВЫЙ) |
| `deploy_frontend_src_Toast.tsx` | 6 KB | Toast (НОВЫЙ) |
| `deploy_frontend_src_api_notifications.ts` | 3 KB | notifications API (НОВЫЙ) |
| `deploy_frontend_src_notificationStore.ts` | 3 KB | notificationStore (НОВЫЙ) |
| `deploy_frontend_src_OrderListPage.tsx` | 3 KB | OrderListPage |
| `deploy_backend_product_brief_views.py` | 4 KB | ProductBySlugs (НОВЫЙ) |
| `deploy_backend_password_reset_views.py` | 7 KB | Password reset (НОВЫЙ) |

---

## 🗓️ День 2 (продолжение) — Аудит BACKEND_REVIEW.pdf

### Событие: Проверка отчёта аудита по реальному коду
**Время:** 21:00  
**Метод:** каждое утверждение отчёта сверено с исходным кодом

**Результат:**

| Утверждение | Вердикт |
|-------------|---------|
| #1 select_for_update + get_or_create | ✅ Верно — реальный баг |
| #2 Webhook открыт | ⚠️ Частично — осознанный mock |
| #3 JWT blacklist не подключён | ✅ Верно |
| #4 order_number race condition | ⚠️ Частично — UniqueConstraint есть |
| #5 Секреты в репо | ✅ Верно |
| **#6 Ценовой фильтр через JOIN** | **❌ НЕВЕРНО — код уже использует денормализацию!** |
| **#8 Поиск через __icontains** | **❌ НЕВЕРНО — код уже использует FTS на PostgreSQL!** |
| #9 Нет кэша | ✅ Верно |
| #10 Slug O(N) | ✅ Верно |
| #11 Оплата не сверяется | ✅ Верно |
| #12 confirm_payment Exception | ⚠️ Частично |
| #13 cart.tasks заглушки | ✅ Верно |
| #14 cancel без refund/release | ⚠️ Частично |

**Ключевая ошибка отчёта:** пункты 6 и 8 ссылаются на `apps/catalog/filters.py` — **этого файла не существует**. Фильтрация реализована через `product_queryset.py` и уже использует денормализацию и FTS.

---

## 🗓️ День 3 — 2026-08-23

### Событие: Проверка соответствия Workspace ↔ Kvasha62/Amazone_Clone
**Время:** 09:00  
**Результат:** Репозиторий приватный, проверить напрямую нельзя. Сравнил workspace с deploy-скриптом.

**Критические баги deploy_all_v2.ps1 — 4 файла НЕ деплоятся:**

| Файл | Почему критично |
|------|----------------|
| `src/api/catalog.ts` | Содержит `getProductsBySlugs()` — без него Recently Viewed сломан |
| `src/store/recentlyViewedStore.ts` | Реальный API-вызов — без него заглушка |
| `apps/reviews/migrations/0003_reviewhelpfulvote.py` | Миграция ReviewHelpfulVote — без неё helpful voting сломан |
| `src/pages/Orders/OrderListPage.tsx` | Цветные статусы — без них старая версия |

**Общий вывод:** deploy-скрипт = патч (только изменённые файлы). ~80% бэкенда и ~60% фронтенда НЕ покрываются. Работает только если на диске I:\ уже актуальная копия проекта.

## Day 4 — 2026-08-23: Заполнение репозитория заново

### Выполнено
1. **Исправлены все 6 багов из BACKEND_REVIEW.pdf:**
   - **#1** `inventory_service.py`: `select_for_update().get_or_create()` → разделены на `get_or_create()` + `select_for_update().get()`
   - **#3** JWT blacklist: добавлен `rest_framework_simplejwt.token_blacklist` в INSTALLED_APPS
   - **#4** order_number race condition: retry-цикл (3 попытки) при IntegrityError
   - **#11** Payment amount validation: `amount != order.total` → ValidationError
   - **#12** `confirm_payment`: `except Exception` → `except (DRFValidationError, DatabaseError)`
   - **#14** `OrderService.cancel`: добавлен вызов `PaymentService.refund_payment()` для SUCCEEDED платежей

2. **Тесты:** 950 pass, 0 failures, 2 skipped (PostgreSQL-only)

3. **Git инициализирован в workspace:**
   - 561 файл в коммите
   - Правильный .gitignore (исключает .cache, deploy_*, .env, db.sqlite3, node_modules, uploads/, ...)
   - Два коммита: initial + cleanup

4. **Архивы для пользователя:**
   - `amazone_clone.bundle` (799KB) — git bundle, можно `git clone` напрямую
   - `amazone_clone.tar.gz` (563KB) — tar-архив, можно распаковать
   - `deploy_all_v3.ps1` (3MB) — полный deploy-скрипт (541 файл)
   - `fill_repo.ps1` — мастер-скрипт для запуска на машине пользователя

### Инструкции для пользователя
1. Скачать `amazone_clone.bundle` из workspace
2. `git clone amazone_clone.bundle Amazone_Clone`
3. `cd Amazone_Clone && git remote set-url origin https://github.com/Kvasha62/Amazone_Clone.git`
4. `git push -u origin main`
5. Применить миграции: `python manage.py migrate`
6. Фронтенд: `cd I:\NewPythonProjects\frontend && npm install && npm run dev`

---

## Day 5 — 2026-08-30: Issue #19 — Admin: Product bounds read-only

### Контекст
PR #18 (ARCH-001 Stage 2) закрыл Admin-обход для `ProductVariant.is_active`
и удаления вариантов. Остался residual **M1**: `Product.min_price` /
`Product.max_price` можно было менять руками в `ProductAdmin` во fieldset
«Цены (авто)» — UI утверждал «пересчитываются автоматически», но
серверного запрета не было.

Авторитетный путь единственный:

```text
PricingService.recalculate_product_bounds(product)
    → CatalogService.set_product_prices(product, min_price, max_price)
    → Product.min_price / max_price
```

### Выполнено
1. **`apps/catalog/admin/product_admin.py`**
   - `min_price` / `max_price` добавлены в `readonly_fields`
     (+ константа `PRODUCT_PRICE_BOUNDS_FIELDS`);
     Django исключает их из генерируемой ModelForm → в форме нет
     `<input name="min_price">`.
   - `ProductAdmin.save_model()` — второй слой защиты (defense-in-depth):
     `PermissionDenied`, если сохранённые границы отличаются от
     хранимых в БД (change), либо если новый товар создаётся с
     непустыми границами (add).
   - Обновлён description fieldset-а «Цены (авто)».
   - **Без `catalog → pricing`**: Admin не импортирует `PricingService`
     и ничего не пересчитывает — он запрещает мутацию.

2. **Тесты** — `apps/catalog/tests/test_admin_product_bounds.py` (13 тестов):
   - конфигурация: readonly + отсутствие полей в форме change/add +
     рендер страницы без input-ов;
   - серверный отказ: `min_price`, `max_price`, очистка в NULL, add-путь;
     безопасные поля (`name`, `description`) по-прежнему сохраняются;
   - e2e: сфабрикованный POST формы изменения с `min_price`/`max_price`
     в payload — товар сохраняется, границы не меняются;
   - легитимный путь не сломан: `PricingService.set_price()` и
     `recalculate_product_bounds()` по-прежнему обновляют границы.

3. **Документация** — `ARCHITECTURE.md`: раздел «Admin (ARCH-001 Stage 2)»
   дополнен таблицей Admin-поверхностей и описанием двух слоёв защиты;
   в «Testing Strategy» добавлены Admin-guard тесты.

### Проверка
- `manage.py test` (PostgreSQL): **1048 tests, 0 failures**.
- Проверка осмысленности тестов: при снятии `readonly_fields` падают
  5 тестов конфигурации, при отключении `save_model` — 4 теста
  серверного отказа. Оба слоя реально отслеживаются.

### Out of scope (согласно issue)
`rating` / `reviews_count` / `views_count` в Admin, политика raw ORM/шелл-мутаций,
seed/инструменты заполнения, Order/EDU-002.
