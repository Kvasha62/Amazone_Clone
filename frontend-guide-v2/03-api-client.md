# ЧАСТЬ 3. Axios-клиент: единственная точка входа для всех API-запросов

> **Цель:** Создать настроенный axios-инстанс, который АВТОМАТИЧЕСКИ прикрепляет JWT-токен к каждому запросу и АВТОМАТИЧЕСКИ обновляет токен при 401.

---

## 3.1. Зачем нужен axios-клиент (а не просто `fetch`)

Представь: у тебя 50 API-вызовов в приложении. Без axios-клиента:

```tsx
// ❌ ПЛОХО — каждый запрос вручную добавляет токен
fetch('/api/v1/cart/', {
  headers: { Authorization: `Bearer ${localStorage.getItem('access')}` }
})
```

Проблемы:
1. **Дублирование** — токен добавляется в КАЖДЫЙ fetch
2. **Забудешь** — в каком-то запросе не добавишь → 401
3. **Обновление токена** — при 401 надо ловить, обновлять, повторять — везде!
4. **Изменение** — если формат заголовка изменится — меняй 50 мест

С axios-клиентом:

```tsx
// ✅ ХОРОШО — токен добавляется АВТОМАТИЧЕСКИ
apiClient.get('/cart/')
```

---

## 3.2. Файл `src/api/client.ts` — ПОЛНЫЙ код

```ts
// src/api/client.ts
// 📡 Единственная точка входа для ВСЕХ API-запросов.
// Axios-инстанс с:
//   1. Базовым URL (через Vite Proxy)
//   2. Автоматическим прикреплением JWT-токена
//   3. Автоматическим обновлением токена при 401
//   4. Очередью запросов на время обновления токена

import axios, { type InternalAxiosRequestConfig } from 'axios'

// ──────────────────────────────────────────────
// 1. Создаём axios-инстанс
// ──────────────────────────────────────────────

const apiClient = axios.create({
  baseURL: '/api/v1',       // ← Через Vite Proxy → http://localhost:8000/api/v1
  timeout: 10_000,          // 10 секунд — таймаут запроса
  headers: {
    'Content-Type': 'application/json',   // Django ждёт JSON
  },
})

// ──────────────────────────────────────────────
// 2. REQUEST-интерцептор: добавляем JWT-токен
// ──────────────────────────────────────────────
// Выполняется ДО каждого запроса.
// Читает access-токен из localStorage и добавляет в заголовок.

apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = localStorage.getItem('access_token')
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// ──────────────────────────────────────────────
// 3. RESPONSE-интерцептор: обновляем токен при 401
// ──────────────────────────────────────────────
// Выполняется ПОСЛЕ каждого ответа.
// Если Django вернул 401 (токен истёк):
//   a. Пробуем обновить токен через /auth/refresh/
//   b. Если успешно — повторяем оригинальный запрос
//   c. Если неуспешно — разлогиниваем пользователя

let isRefreshing = false           // Флаг: идёт ли обновление токена прямо сейчас
let failedQueue: Array<{           // Очередь запросов, которые ждали обновления
  resolve: (value: unknown) => void
  reject: (reason?: unknown) => void
}> = []

// Обрабатываем очередь: если токен обновился — повторяем все запросы
function processQueue(error: unknown, token: string | null = null) {
  failedQueue.forEach(({ resolve, reject }) => {
    if (token) {
      resolve(token)
    } else {
      reject(error)
    }
  })
  failedQueue = []  // Очищаем очередь
}

apiClient.interceptors.response.use(
  (response) => response,  // Успешный ответ — пропускаем без изменений
  async (error) => {
    const originalRequest = error.config

    // Если НЕ 401 — просто пробрасываем ошибку
    if (error.response?.status !== 401) {
      return Promise.reject(error)
    }

    // Если это УЖЕ повторный запрос (после обновления токена) — не зацикливаемся
    if (originalRequest._retry) {
      // Токен не удалось обновить — разлогиниваем
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      window.location.href = '/login'  // Редирект на страницу входа
      return Promise.reject(error)
    }

    // Если обновление токена УЖЕ идёт (другой запрос инициировал) — встаём в очередь
    if (isRefreshing) {
      return new Promise((resolve, reject) => {
        failedQueue.push({ resolve, reject })
      }).then((token) => {
        originalRequest.headers.Authorization = `Bearer ${token}`
        return apiClient(originalRequest)  // Повторяем оригинальный запрос
      })
    }

    // Начинаем обновление токена
    originalRequest._retry = true
    isRefreshing = true

    try {
      const refreshToken = localStorage.getItem('refresh_token')
      if (!refreshToken) {
        throw new Error('Нет refresh-токена')
      }

      // ⚠️ ВАЖНО: используем СВЕЖИЙ axios (не apiClient!),
      // чтобы не зациклить интерцепторы
      const { data } = await axios.post('/api/v1/auth/refresh/', {
        refresh: refreshToken,
      })

      // Сохраняем новые токены
      localStorage.setItem('access_token', data.access)
      if (data.refresh) {
        localStorage.setItem('refresh_token', data.refresh)
      }

      // Обновляем заголовок в оригинальном запросе
      originalRequest.headers.Authorization = `Bearer ${data.access}`

      // Обрабатываем очередь ожидания
      processQueue(null, data.access)

      // Повторяем оригинальный запрос с новым токеном
      return apiClient(originalRequest)
    } catch (refreshError) {
      // Не удалось обновить — разлогиниваем
      processQueue(refreshError, null)
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      window.location.href = '/login'
      return Promise.reject(refreshError)
    } finally {
      isRefreshing = false
    }
  }
)

export default apiClient
```

---

## 3.3. Разбор: КАК работает обновление токена

Сценарий: пользователь открыл страницу, access-токен истёк через 15 минут.

```
1. React: apiClient.get('/cart/')
2. Request-интерцептор: добавляет Authorization: Bearer <старый_токен>
3. Django: проверяет токен → ИСТЁК → возвращает 401
4. Response-интерцептор: ловит 401
5. Response-интерцептор: POST /auth/refresh/ { refresh: <refresh_токен> }
6. Django: возвращает { access: <новый_токен>, refresh: <новый_refresh> }
7. Response-интерцептор: сохраняет новые токены в localStorage
8. Response-интерцептор: повторяет apiClient.get('/cart/') с новым токеном
9. Django: токен валидный → возвращает данные корзины
10. React: получает данные — пользователь НИЧЕГО НЕ ЗАМЕТИЛ
```

**Очередь (failedQueue) зачем:**

Если одновременно ушло 3 запроса и все получили 401:
- Без очереди: 3 запроса попытаются обновить токен → 3 запроса к /auth/refresh/
- С очередью: первый запрос обновляет токен, остальные ЖДУТ и повторяются с новым токеном

---

## 3.4. Файл `src/api/endpoints.ts` — все URL бэкенда

```ts
// src/api/endpoints.ts
// 📋 Все URL бэкенда в одном месте.
// Если URL изменится — меняешь только здесь.

export const API = {
  // ── Auth ──
  auth: {
    login:    '/auth/login/',           // POST {email, password} → {access, refresh}
    register: '/auth/register/',         // POST {email, username, password, password_confirm}
    refresh:  '/auth/refresh/',          // POST {refresh} → {access, refresh}
    password: '/auth/change-password/',  // POST {old_password, new_password, new_password_confirm}
  },

  // ── Users ──
  users: {
    me:       '/users/me/',              // GET/PATCH/DELETE — профиль
    addresses:      '/users/addresses/', // GET/POST
    addressDetail:  (id: number) => `/users/addresses/${id}/`,     // GET/PATCH/DELETE
    addressDefault: (id: number) => `/users/addresses/${id}/default/`, // POST
  },

  // ── Catalog ──
  catalog: {
    products:        '/catalog/products/',                    // GET (фильтры, пагинация)
    productDetail:   (slugOrUuid: string) => `/catalog/products/${slugOrUuid}/`, // GET
    productCreate:   '/catalog/products/create/',             // POST (staff)
    productUpdate:   (uuid: string) => `/catalog/products/${uuid}/update/`, // PATCH (staff)
    categories:      '/catalog/categories/',                  // GET (дерево)
    categoryDetail:  (slug: string) => `/catalog/categories/${slug}/`, // GET
    brands:          '/catalog/brands/',                      // GET
    brandDetail:     (slug: string) => `/catalog/brands/${slug}/`, // GET
  },

  // ── Cart ──
  cart: {
    base:      '/cart/',                // GET (получить), DELETE (очистить)
    items:     '/cart/items/',           // POST (добавить)
    itemDetail: (id: number) => `/cart/items/${id}/`, // PATCH/DELETE
    merge:     '/cart/merge/',           // POST {session_key}
  },

  // ── Wishlist ──
  wishlist: {
    base:  '/wishlist/',                // GET (список)
    items: '/wishlist/items/',           // POST (добавить)
    itemDetail: (id: number) => `/wishlist/items/${id}/`, // DELETE
    moveToCart: '/wishlist/move-to-cart/', // POST
    clear: '/wishlist/clear/',           // POST
  },

  // ── Orders ──
  orders: {
    list:     '/orders/',               // GET
    create:   '/orders/create/',         // POST {cart, address_id, ...}
    detail:   (id: number) => `/orders/${id}/`, // GET
    cancel:   (id: number) => `/orders/${id}/cancel/`, // POST
  },

  // ── Reviews ──
  reviews: {
    list:    (productId: number) => `/reviews/?product=${productId}`, // GET
    create:  '/reviews/',                // POST
    detail:  (id: number) => `/reviews/${id}/`, // PATCH/DELETE
  },

  // ── Payments ──
  payments: {
    create:   (orderId: number) => `/payments/create/`,  // POST {order}
    detail:   (id: number) => `/payments/${id}/`,        // GET
  },

  // ── Notifications ──
  notifications: {
    list:    '/notifications/',          // GET
    markRead: (id: number) => `/notifications/${id}/read/`, // POST
    markAllRead: '/notifications/read-all/', // POST
  },

  // ── Health ──
  health: '/health/',                    // GET → {status, version, database}
} as const
```

**Почему функции, а не строки для динамических URL:**

```ts
// ❌ ПЛОХО — хардкод в каждом компоненте
fetch(`/catalog/products/${slug}/`)

// ✅ ХОРОШО — единая точка правки
apiClient.get(API.catalog.productDetail(slug))
```

---

## 3.5. Типы для API-ответов — `src/api/types.ts`

```ts
// src/api/types.ts
// 📝 TypeScript-типы для ВСЕХ ответов бэкенда.
// Это «контракт» между Django и React.

// ── Auth ──
export interface LoginRequest {
  email: string
  password: string
}

export interface RegisterRequest {
  email: string
  username: string
  password: string
  password_confirm: string
}

export interface AuthTokens {
  access: string
  refresh: string
}

export interface RegisterResponse {
  id: number
  email: string
  username: string
}

// ── User ──
export interface User {
  id: number
  email: string
  username: string
  first_name: string
  last_name: string
}

// ── Catalog ──
export interface Product {
  uuid: string
  name: string
  slug: string
  description?: string
  min_price?: string
  max_price?: string
  rating: string
  reviews_count: number
  main_image_url?: string
  brand_name?: string
  status: string
}

export interface ProductDetail extends Product {
  images: ProductImage[]
  variants: ProductVariant[]
  tags: Tag[]
  meta_title?: string
  meta_description?: string
}

export interface ProductImage {
  id: number
  image: string
  alt: string
  is_main: boolean
  order: number
}

export interface ProductVariant {
  id: number
  sku: string
  slug?: string
  price?: string
  stock_quantity?: number
  is_active: boolean
}

export interface Category {
  id: number
  name: string
  slug: string
  url_path?: string
  depth?: number
  is_active: boolean
  children?: Category[]
}

export interface Brand {
  id: number
  name: string
  slug: string
  logo?: string
}

export interface Tag {
  id: number
  name: string
  slug: string
}

// ── Cart ──
export interface CartItem {
  id: number
  product_name: string
  sku: string
  price: string | null
  quantity: number
  total_price: string | null
}

export interface Cart {
  id: number
  items: CartItem[]
  total_quantity: number
  total: string
}

// ── Paginated response (Django PageNumberPagination) ──
export interface PaginatedResponse<T> {
  count: number        // Всего объектов
  next: string | null  // URL следующей страницы
  previous: string | null  // URL предыдущей страницы
  results: T[]         // Массив объектов текущей страницы
}
```

---

## 3.6. Пример использования: запрос к API

```tsx
// src/pages/catalog-page.tsx
import { useEffect, useState } from 'react'
import apiClient from '../api/client'
import { API } from '../api/endpoints'
import type { Product, PaginatedResponse } from '../api/types'

function CatalogPage() {
  const [products, setProducts] = useState<Product[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // apiClient автоматически:
    // 1. Добавит /api/v1 префикс
    // 2. Прикрепит JWT-токен из localStorage
    // 3. При 401 — обновит токен и повторит запрос
    apiClient.get<PaginatedResponse<Product>>(API.catalog.products, {
      params: {
        category: 'smartfony',
        min_price: 10000,
        max_price: 50000,
        page: 1,
      }
    })
      .then(({ data }) => {
        setProducts(data.results)   // Товары текущей страницы
        console.log('Всего:', data.count)  // Общее количество
      })
      .catch((error) => {
        console.error('Ошибка загрузки:', error)
      })
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div>Загрузка...</div>

  return (
    <div className="grid grid-cols-4 gap-4">
      {products.map(p => (
        <div key={p.uuid} className="border rounded-lg p-4">
          <h3 className="font-bold">{p.name}</h3>
          <p className="text-gray-500">{p.brand_name}</p>
          <p className="text-xl font-bold">{p.min_price} ₽</p>
        </div>
      ))}
    </div>
  )
}

export default CatalogPage
```

---

## 3.7. Формат ответов Django — ЧТО ожидать

### Успешный ответ (200, 201):

```json
// GET /api/v1/catalog/products/?page=1
{
  "count": 150,
  "next": "http://localhost:8000/api/v1/catalog/products/?page=2",
  "previous": null,
  "results": [
    {
      "uuid": "a1b2c3d4-...",
      "name": "Galaxy S24",
      "slug": "galaxy-s24",
      "min_price": "59990.00",
      "max_price": "89990.00",
      "rating": "4.50",
      "reviews_count": 23,
      "main_image_url": "/media/products/2026/06/s24.jpg",
      "brand_name": "Samsung"
    }
  ]
}
```

### Ошибка валидации (400):

```json
// POST /api/v1/auth/register/ с неправильными данными
{
  "email": ["Пользователь с таким email уже существует."],
  "password_confirm": ["Пароли не совпадают."]
}
```

### Ошибка авторизации (401):

```json
// Запрос с истёкшим токеном
{
  "detail": "Given token not valid for any token type",
  "code": "token_not_valid",
  "messages": [
    {
      "token_class": "AccessToken",
      "token_type": "access",
      "message": "Token is expired"
    }
  ]
}
```

### Не найдено (404):

```json
{
  "detail": "Вариант товара не найден или неактивен."
}
```

---

### ✅ Итог части 3

- [x] `apiClient` — axios-инстанс с базовым URL `/api/v1`
- [x] Request-интерцептор — автоматически добавляет `Authorization: Bearer <token>`
- [x] Response-интерцептор — при 401 обновляет токен и повторяет запрос
- [x] Очередь failedQueue — несколько 401 → одно обновление токена
- [x] `endpoints.ts` — все URL в одном месте
- [x] `types.ts` — TypeScript-типы для ответов Django
- [x] Понимание формата ответов Django

**Далее: Часть 4 — Auth Store (Zustand) и JWT-авторизация**
