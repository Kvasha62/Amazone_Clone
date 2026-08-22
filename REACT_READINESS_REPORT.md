# 🚀 Backend → React: Отчёт готовности

**Дата:** 2026-06-12
**Тесты:** 898 тестов, 0 failures, 2 skipped (PostgreSQL-only)
**Миграции:** Все применены ✅

---

## ✅ Что УЖЕ ГОТОВО для React

### 1. CORS — React может делать запросы к Django
- `django-cors-headers` установлен и настроен
- `CORS_ALLOW_ALL_ORIGINS = True` в DEBUG-режиме
- Разрешены `localhost:3000` (CRA) и `localhost:5173` (Vite)
- JWT-заголовок `Authorization` в `CORS_ALLOW_HEADERS`
- `CORS_ALLOW_CREDENTIALS = True` (для кук, если нужны)

### 2. JWT-авторизация по EMAIL (не username)
- `POST /api/v1/auth/login/` — `{email, password}` → `{access, refresh}`
- `POST /api/v1/auth/register/` — `{email, username, password, password_confirm}`
- `POST /api/v1/auth/refresh/` — `{refresh}` → `{access}`
- `POST /api/v1/auth/change-password/`
- Access token: 15 мин, Refresh: 7 дней
- Rotate + Blacklist включены

### 3. JSON-only API (без HTML-рендера)
- `DEFAULT_RENDERER_CLASSES = (JSONRenderer,)`
- React получает чистый JSON, без лишнего HTML

### 4. Throttling (защита от спама)
- Anon: 60/мин, User: 120/мин
- Автоматически отключается в тестах

### 5. Media-файлы в DEV
- `MEDIA_URL = /media/`
- `static(settings.MEDIA_URL, ...)` в urls.py при `DEBUG=True`
- Картинки товаров, аватары доступны по `http://localhost:8000/media/...`

### 6. Health-check
- `GET /api/v1/health/` → `{"status": "ok", "version": "1.0.0", "database": "ok"}`
- React может проверять жив ли бэкенд при запуске

### 7. API-документация (Swagger)
- `GET /api/v1/schema/` — OpenAPI 3.0 схема
- `GET /api/v1/docs/` — Swagger UI (интерактивная документация)

### 8. .env поддержка
- `python-dotenv` установлен
- `.env.example` — шаблон
- `.env` в `.gitignore`

### 9. Пагинация
- `PageNumberPagination`, `PAGE_SIZE = 20`
- Все списочные эндпоинты возвращают `{count, next, previous, results}`

---

## 📋 Полная карта API-эндпоинтов

### Auth (публичные)
| Метод | URL | Описание |
|-------|-----|----------|
| POST | `/api/v1/auth/register/` | Регистрация |
| POST | `/api/v1/auth/login/` | JWT login (email + password) |
| POST | `/api/v1/auth/refresh/` | Обновить access token |
| POST | `/api/v1/auth/change-password/` | Смена пароля |

### Users (авторизованные)
| Метод | URL | Описание |
|-------|-----|----------|
| GET/PATCH/DELETE | `/api/v1/users/me/` | Профиль пользователя |
| GET/POST | `/api/v1/users/addresses/` | Список/создание адресов |
| GET/PATCH/DELETE | `/api/v1/users/addresses/{id}/` | Детали адреса |
| POST | `/api/v1/users/addresses/{id}/default/` | Сделать основным |

### Catalog (публичные/авторизованные)
| Метод | URL | Описание |
|-------|-----|----------|
| GET | `/api/v1/catalog/products/` | Список товаров (фильтры, поиск, пагинация) |
| GET | `/api/v1/catalog/products/{slug_or_uuid}/` | Карточка товара |
| GET | `/api/v1/catalog/categories/` | Дерево категорий |
| GET | `/api/v1/catalog/categories/{slug}/` | Детали категории |
| GET | `/api/v1/catalog/brands/` | Список брендов |
| GET | `/api/v1/catalog/brands/{slug}/` | Детали бренда |

### Cart (AllowAny + авторизованные)
| Метод | URL | Описание |
|-------|-----|----------|
| GET | `/api/v1/cart/` | Получить корзину |
| DELETE | `/api/v1/cart/` | Очистить корзину |
| POST | `/api/v1/cart/items/` | Добавить товар |
| PATCH | `/api/v1/cart/items/{id}/` | Изменить количество |
| DELETE | `/api/v1/cart/items/{id}/` | Удалить позицию |
| POST | `/api/v1/cart/merge/` | Слить гостевую корзину |

### Orders (авторизованные)
| Метод | URL | Описание |
|-------|-----|----------|
| GET | `/api/v1/orders/` | Список заказов |
| GET | `/api/v1/orders/{order_number}/` | Детали заказа |
| POST | `/api/v1/orders/create/` | Создать из корзины |
| POST | `/api/v1/orders/{order_number}/cancel/` | Отменить |

### Payments
| Метод | URL | Описание |
|-------|-----|----------|
| GET | `/api/v1/payments/` | Список платежей |
| GET | `/api/v1/payments/{payment_number}/` | Детали платежа |
| POST | `/api/v1/payments/{payment_number}/confirm/` | Подтвердить |
| POST | `/api/v1/payments/{payment_number}/refund/` | Возврат |
| POST | `/api/v1/payments/webhook/` | Webhook платёжной системы |

### Reviews (публичные GET, авторизованные POST)
| Метод | URL | Описание |
|-------|-----|----------|
| GET | `/api/v1/reviews/` | Список отзывов |
| POST | `/api/v1/reviews/` | Создать отзыв |
| GET/PATCH/DELETE | `/api/v1/reviews/{id}/` | Детали/обновление/удаление |

### Discounts (авторизованные)
| Метод | URL | Описание |
|-------|-----|----------|
| GET | `/api/v1/discounts/coupons/` | Список купонов |
| POST | `/api/v1/discounts/apply/` | Применить купон |
| POST | `/api/v1/discounts/remove/` | Убрать купон |
| POST | `/api/v1/discounts/preview/` | Предпросмотр скидки |

### Shipping
| Метод | URL | Описание |
|-------|-----|----------|
| GET | `/api/v1/shipping/methods/` | Методы доставки |
| POST | `/api/v1/shipping/calculate/` | Расчёт стоимости |
| GET | `/api/v1/shipping/shipments/` | Список отправок |
| GET | `/api/v1/shipping/shipments/{id}/` | Детали отправки |

### Wishlist (авторизованные)
| Метод | URL | Описание |
|-------|-----|----------|
| GET | `/api/v1/wishlist/` | Список желаний |
| POST | `/api/v1/wishlist/add/` | Добавить товар |
| DELETE | `/api/v1/wishlist/remove/{id}/` | Удалить товар |
| POST | `/api/v1/wishlist/move-to-cart/` | Переместить в корзину |
| POST | `/api/v1/wishlist/clear/` | Очистить |

### Notifications (авторизованные)
| Метод | URL | Описание |
|-------|-----|----------|
| GET | `/api/v1/notifications/` | Все уведомления |
| GET | `/api/v1/notifications/unread/` | Непрочитанные |
| GET | `/api/v1/notifications/unread-count/` | Кол-во непрочитанных |
| POST | `/api/v1/notifications/{id}/read/` | Пометить прочитанным |
| POST | `/api/v1/notifications/read-all/` | Прочитать все |

### Analytics (staff only)
| Метод | URL | Описание |
|-------|-----|----------|
| GET | `/api/v1/analytics/dashboard/` | Дашборд |
| GET | `/api/v1/analytics/sales/` | Сводка продаж |
| GET | `/api/v1/analytics/sales/timeline/` | Таймлайн |
| GET | `/api/v1/analytics/top-products/` | Топ товаров |
| GET | `/api/v1/analytics/top-categories/` | Топ категорий |
| GET | `/api/v1/analytics/top-customers/` | Топ клиентов |
| GET | `/api/v1/analytics/conversion/` | Конверсия |
| GET | `/api/v1/analytics/most-viewed/` | Самые просматриваемые |

### System
| Метод | URL | Описание |
|-------|-----|----------|
| GET | `/api/v1/health/` | Health-check |
| GET | `/api/v1/schema/` | OpenAPI схема |
| GET | `/api/v1/docs/` | Swagger UI |

---

## ⚠️ Что желательно ДОБАВИТЬ перед React (но не блокирует старт)

### 🟡 Приоритет 1 — для полноценного SPA-опыта

1. **Logout endpoint** — Сейчас нет `POST /api/v1/auth/logout/` для blacklist refresh-токена. React при logout должен инвалидировать refresh-токен на бэкенде.
   ```python
   # apps/users/api_views/jwt_email_views.py
   class LogoutView(APIView):
       permission_classes = (IsAuthenticated,)
       def post(self, request):
           try:
               refresh = request.data['refresh']
               token = RefreshToken(refresh)
               token.blacklist()
           except Exception:
               pass
           return Response({'detail': 'Logged out'})
   ```

2. **Forgot password / Reset password** — Стандартный флоу для e-commerce. Отправка email со ссылкой на сброс пароля.

3. **Social auth (Google/GitHub)** — `django-allauth` или `dj-rest-auth`. Многие пользователи ожидают «Войти через Google».

### 🟡 Приоритет 2 — для e-commerce

4. **Order tracking** — Публичный endpoint `GET /api/v1/orders/track/{tracking_number}/` без авторизации (для гостей).

5. **Product search enhancements** — Добавить `?q=`, `?min_price=`, `?max_price=`, `?rating_gte=` фильтры в ProductListView. Проверить что фильтры уже подключены (`django_filters`).

6. **Cart для гостей по session** — Уже реализовано! `CartView` с `AllowAny` создаёт гостевую корзину. Но при merge нужна сессия — React должен отправлять `sessionid` куку или `X-Session-Key` заголовок.

### 🟡 Приоритет 3 — nice to have

7. **WebSocket** — Для real-time уведомлений и отслеживания заказа. `django-channels` + Redis.

8. **Image upload endpoint** — Для отзывов (ReviewImage), аватаров.

9. **Export endpoints** — CSV/XLSX экспорт для аналитики.

---

## 🛠️ С чего НАЧАТЬ React

### Шаг 0: Запустить бэкенд
```bash
cd I:\NewPythonProjects\Amazone_Clone
python manage.py migrate          # Применить миграции
python manage.py createsuperuser  # Создать админа
python manage.py runserver        # http://localhost:8000
```

Проверить:
- http://localhost:8000/api/v1/health/ → `{"status": "ok"}`
- http://localhost:8000/api/v1/docs/  → Swagger UI

### Шаг 1: Создать React-проект
```bash
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install axios react-router-dom zustand
# или: npm install @tanstack/react-query
```

### Шаг 2: Настроить API-клиент (axios)
```typescript
// src/api/client.ts
import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:8000/api/v1',
  headers: { 'Content-Type': 'application/json' },
});

// Автоподстановка JWT
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Авто-refresh при истёкшем access
api.interceptors.response.use(
  (res) => res,
  async (error) => {
    if (error.response?.status === 401) {
      const refresh = localStorage.getItem('refresh_token');
      if (refresh) {
        const { data } = await axios.post(
          'http://localhost:8000/api/v1/auth/refresh/',
          { refresh }
        );
        localStorage.setItem('access_token', data.access);
        error.config.headers.Authorization = `Bearer ${data.access}`;
        return axios(error.config);
      }
    }
    return Promise.reject(error);
  }
);

export default api;
```

### Шаг 3: Порядок разработки экранов

| Приоритет | Экран | API-эндпоинты |
|-----------|-------|---------------|
| 1️⃣ | Login / Register | `auth/login/`, `auth/register/`, `auth/refresh/` |
| 2️⃣ | Каталог товаров | `catalog/products/`, `catalog/categories/` |
| 3️⃣ | Карточка товара | `catalog/products/{slug}/`, `reviews/` |
| 4️⃣ | Корзина | `cart/`, `cart/items/` |
| 5️⃣ | Оформление заказа | `orders/create/`, `shipping/calculate/`, `discounts/apply/` |
| 6️⃣ | Личный кабинет | `users/me/`, `orders/`, `users/addresses/` |
| 7️⃣ | Wishlist | `wishlist/`, `wishlist/add/` |
| 8️⃣ | Уведомления | `notifications/` |
| 9️⃣ | Админ: Аналитика | `analytics/dashboard/`, `analytics/sales/` |

---

## 📦 Рекомендуемый стек React

| Категория | Библиотека | Зачем |
|-----------|-----------|-------|
| Сборка | Vite | Быстрый dev-server |
| Роутинг | React Router v7 | SPA-навигация |
| Состояние | Zustand или Jotai | Глобальный store (корзина, пользователь) |
| Серверное состояние | @tanstack/react-query | Кэширование, refetch, optimistic updates |
| HTTP-клиент | Axios | Интерцепторы для JWT |
| UI-компоненты | Ant Design или MUI | Готовые компоненты e-commerce |
| Стили | Tailwind CSS | Утилитарные классы |
| Формы | React Hook Form + Zod | Валидация форм |

---

**Вывод: Бэкенд полностью готов к разработке React-фронтенда.** Все 14 модулей работают, 898 тестов зелёные, CORS настроен, JWT по email работает, API-документация доступна. Можно стартовать.
