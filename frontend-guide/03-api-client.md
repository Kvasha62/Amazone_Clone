# Шаг 3. API-клиент (axios + JWT)

Создай файл `src/api/client.ts`:

```typescript
// src/api/client.ts
// Единый HTTP-клиент для всех запросов к бэкенду.
// Автоматически добавляет JWT-токен и обновляет его при истечении.

import axios from 'axios';

const API_BASE = '/api/v1';

// ── Создаём экземпляр axios ──
const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
});

// ── Request interceptor: подставляем JWT ──
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// ── Response interceptor: авто-refresh при 401 ──
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // Если access токен истёк — пробуем обновить через refresh
    if (
      error.response?.status === 401 &&
      !originalRequest._retry &&
      !originalRequest.url?.includes('/auth/login/')
    ) {
      originalRequest._retry = true;

      const refreshToken = localStorage.getItem('refresh_token');
      if (refreshToken) {
        try {
          const { data } = await axios.post(`${API_BASE}/auth/refresh/`, {
            refresh: refreshToken,
          });

          localStorage.setItem('access_token', data.access);

          // Если бэкенд вернул новый refresh (ROTATE_REFRESH_TOKENS=True)
          if (data.refresh) {
            localStorage.setItem('refresh_token', data.refresh);
          }

          // Повторяем оригинальный запрос с новым токеном
          originalRequest.headers.Authorization = `Bearer ${data.access}`;
          return api(originalRequest);
        } catch {
          // Refresh тоже истёк — разлогиниваем
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
          window.location.href = '/login';
        }
      } else {
        // Нет refresh токена — на страницу логина
        window.location.href = '/login';
      }
    }

    return Promise.reject(error);
  }
);

export default api;
```

---

### Создай файл `src/api/endpoints.ts` — все URL в одном месте:

```typescript
// src/api/endpoints.ts
// Все пути к API-эндпоинтам в одном файле.
// Если на бэкенде изменится URL — меняем только здесь.

export const AUTH = {
  LOGIN: '/auth/login/',
  REGISTER: '/auth/register/',
  REFRESH: '/auth/refresh/',
  CHANGE_PASSWORD: '/auth/change-password/',
} as const;

export const USER = {
  ME: '/users/me/',
  ADDRESSES: '/users/addresses/',
  ADDRESS: (id: number) => `/users/addresses/${id}/`,
  ADDRESS_DEFAULT: (id: number) => `/users/addresses/${id}/default/`,
} as const;

export const CATALOG = {
  PRODUCTS: '/catalog/products/',
  PRODUCT: (slug: string) => `/catalog/products/${slug}/`,
  CATEGORIES: '/catalog/categories/',
  CATEGORY: (slug: string) => `/catalog/categories/${slug}/`,
  BRANDS: '/catalog/brands/',
  BRAND: (slug: string) => `/catalog/brands/${slug}/`,
} as const;

export const CART = {
  CART: '/cart/',
  ITEMS: '/cart/items/',
  ITEM: (id: number) => `/cart/items/${id}/`,
  MERGE: '/cart/merge/',
} as const;

export const ORDER = {
  LIST: '/orders/',
  DETAIL: (orderNumber: string) => `/orders/${orderNumber}/`,
  CREATE: '/orders/create/',
  CANCEL: (orderNumber: string) => `/orders/${orderNumber}/cancel/`,
} as const;

export const REVIEW = {
  LIST: '/reviews/',
  DETAIL: (id: number) => `/reviews/${id}/`,
} as const;

export const WISHLIST = {
  DETAIL: '/wishlist/',
  ADD: '/wishlist/add/',
  REMOVE: (id: number) => `/wishlist/remove/${id}/`,
  MOVE_TO_CART: '/wishlist/move-to-cart/',
  CLEAR: '/wishlist/clear/',
} as const;

export const NOTIFICATION = {
  LIST: '/notifications/',
  UNREAD: '/notifications/unread/',
  UNREAD_COUNT: '/notifications/unread-count/',
  MARK_READ: (id: number) => `/notifications/${id}/read/`,
  READ_ALL: '/notifications/read-all/',
} as const;

export const SHIPPING = {
  METHODS: '/shipping/methods/',
  CALCULATE: '/shipping/calculate/',
} as const;

export const DISCOUNT = {
  COUPONS: '/discounts/coupons/',
  APPLY: '/discounts/apply/',
  REMOVE: '/discounts/remove/',
  PREVIEW: '/discounts/preview/',
} as const;

export const HEALTH = '/health/' as const;
```

---

### Проверка

Временно добавь в `src/App.tsx`:

```typescript
import { useEffect } from 'react';
import api from './api/client';
import { HEALTH } from './api/endpoints';

function App() {
  useEffect(() => {
    api.get(HEALTH).then(res => {
      console.log('Backend health:', res.data);
    });
  }, []);

  return <h1>Amazon Clone</h1>;
}

export default App;
```

Запусти бэкенд + фронтенд:
```bash
# Терминал 1 (бэкенд):
cd I:\NewPythonProjects\Amazone_Clone
python manage.py runserver

# Терминал 2 (фронтенд):
cd I:\NewPythonProjects\frontend
npm run dev
```

Открой http://localhost:5173 → F12 → Console → должно быть:
```
Backend health: {status: "ok", version: "1.0.0", database: "ok"}
```

---

### Итог шага 3
✅ `src/api/client.ts` — axios-клиент с JWT
✅ `src/api/endpoints.ts` — все URL
✅ F12 Console показывает `{status: "ok"}`

→ Переходи к шагу 4
