# ЧАСТЬ 7. Каталог товаров и карточка товара

> **Цель:** Страница каталога с фильтрами + пагинацией + карточка товара с вариантами и отзывами.

---

## 7.1. Файл `src/pages/catalog-page.tsx` — ПОЛНЫЙ код

```tsx
// src/pages/catalog-page.tsx
// 📦 Страница каталога: список товаров + фильтры + пагинация.
//
// Django API: GET /api/v1/catalog/products/
//   ?category=smartfony      — фильтр по категории (slug)
//   &brand=samsung           — фильтр по бренду (slug)
//   &min_price=10000         — минимальная цена
//   &max_price=50000         — максимальная цена
//   &search=galaxy           — полнотекстовый поиск
//   &ordering=-min_price     — сортировка
//   &page=2                  — страница пагинации
//
// Ответ (Django PageNumberPagination):
//   {
//     "count": 150,
//     "next": "...?page=3",
//     "previous": "...?page=1",
//     "results": [ ...товары... ]
//   }

import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import apiClient from '../api/client'
import { API } from '../api/endpoints'
import type { Product, PaginatedResponse, Category, Brand } from '../api/types'

export default function CatalogPage() {
  // ── URL-параметры (фильтры хранятся в URL) ──
  const [searchParams, setSearchParams] = useSearchParams()
  const page = Number(searchParams.get('page')) || 1
  const categorySlug = searchParams.get('category') || ''
  const brandSlug = searchParams.get('brand') || ''
  const minPrice = searchParams.get('min_price') || ''
  const maxPrice = searchParams.get('max_price') || ''
  const searchQuery = searchParams.get('search') || ''

  // ── Состояние ──
  const [products, setProducts] = useState<Product[]>([])
  const [totalCount, setTotalCount] = useState(0)
  const [categories, setCategories] = useState<Category[]>([])
  const [brands, setBrands] = useState<Brand[]>([])
  const [loading, setLoading] = useState(true)

  const pageSize = 20  // должно совпадать с PAGE_SIZE в Django

  // ── Загрузка товаров ──
  useEffect(() => {
    setLoading(true)
    apiClient.get<PaginatedResponse<Product>>(API.catalog.products, {
      params: {
        page,
        category: categorySlug || undefined,
        brand: brandSlug || undefined,
        min_price: minPrice || undefined,
        max_price: maxPrice || undefined,
        search: searchQuery || undefined,
      }
    })
      .then(({ data }) => {
        setProducts(data.results)
        setTotalCount(data.count)
      })
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [page, categorySlug, brandSlug, minPrice, maxPrice, searchQuery])

  // ── Загрузка категорий и брендов (один раз) ──
  useEffect(() => {
    apiClient.get<Category[]>(API.catalog.categories)
      .then(({ data }) => setCategories(data))
      .catch(console.error)

    apiClient.get<Brand[]>(API.catalog.brands)
      .then(({ data }) => setBrands(data))
      .catch(console.error)
  }, [])

  // ── Обновление фильтра → сброс на страницу 1 ──
  const updateFilter = (key: string, value: string) => {
    const params = new URLSearchParams(searchParams)
    if (value) {
      params.set(key, value)
    } else {
      params.delete(key)
    }
    params.delete('page')  // Сброс пагинации при смене фильтра
    setSearchParams(params)
  }

  // ── Пагинация ──
  const totalPages = Math.ceil(totalCount / pageSize)

  const goToPage = (p: number) => {
    const params = new URLSearchParams(searchParams)
    params.set('page', String(p))
    setSearchParams(params)
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold mb-6">Каталог товаров</h1>

      <div className="flex gap-8">
        {/* ── Левая колонка: фильтры ── */}
        <aside className="w-64 shrink-0">
          {/* Поиск */}
          <div className="mb-4">
            <input
              type="text"
              placeholder="Поиск..."
              value={searchQuery}
              onChange={(e) => updateFilter('search', e.target.value)}
              className="w-full px-4 py-2 border rounded-lg"
            />
          </div>

          {/* Категории */}
          <div className="mb-4">
            <h3 className="font-semibold mb-2">Категории</h3>
            <select
              value={categorySlug}
              onChange={(e) => updateFilter('category', e.target.value)}
              className="w-full px-3 py-2 border rounded-lg"
            >
              <option value="">Все категории</option>
              {categories.map(cat => (
                <option key={cat.id} value={cat.slug}>{cat.name}</option>
              ))}
            </select>
          </div>

          {/* Бренды */}
          <div className="mb-4">
            <h3 className="font-semibold mb-2">Бренды</h3>
            <select
              value={brandSlug}
              onChange={(e) => updateFilter('brand', e.target.value)}
              className="w-full px-3 py-2 border rounded-lg"
            >
              <option value="">Все бренды</option>
              {brands.map(b => (
                <option key={b.id} value={b.slug}>{b.name}</option>
              ))}
            </select>
          </div>

          {/* Цена */}
          <div className="mb-4">
            <h3 className="font-semibold mb-2">Цена</h3>
            <div className="flex gap-2">
              <input
                type="number"
                placeholder="от"
                value={minPrice}
                onChange={(e) => updateFilter('min_price', e.target.value)}
                className="w-1/2 px-3 py-2 border rounded-lg"
              />
              <input
                type="number"
                placeholder="до"
                value={maxPrice}
                onChange={(e) => updateFilter('max_price', e.target.value)}
                className="w-1/2 px-3 py-2 border rounded-lg"
              />
            </div>
          </div>
        </aside>

        {/* ── Правая колонка: товары ── */}
        <div className="flex-1">
          {/* Результатов */}
          <p className="text-gray-500 mb-4">
            Найдено: {totalCount} товаров
          </p>

          {/* Загрузка */}
          {loading ? (
            <div className="text-center py-12 text-gray-400">
              Загрузка...
            </div>
          ) : products.length === 0 ? (
            <div className="text-center py-12 text-gray-400">
              Товары не найдены
            </div>
          ) : (
            <>
              {/* Сетка товаров */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                {products.map(product => (
                  <ProductCard key={product.uuid} product={product} />
                ))}
              </div>

              {/* Пагинация */}
              {totalPages > 1 && (
                <div className="flex justify-center gap-2 mt-8">
                  <button
                    onClick={() => goToPage(page - 1)}
                    disabled={page <= 1}
                    className="px-4 py-2 border rounded-lg disabled:opacity-50"
                  >
                    ←
                  </button>
                  {Array.from({ length: totalPages }, (_, i) => i + 1)
                    .filter(p => Math.abs(p - page) <= 2)
                    .map(p => (
                      <button
                        key={p}
                        onClick={() => goToPage(p)}
                        className={`px-4 py-2 border rounded-lg ${
                          p === page ? 'bg-orange-500 text-white' : ''
                        }`}
                      >
                        {p}
                      </button>
                    ))
                  }
                  <button
                    onClick={() => goToPage(page + 1)}
                    disabled={page >= totalPages}
                    className="px-4 py-2 border rounded-lg disabled:opacity-50"
                  >
                    →
                  </button>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  )
}

// ── Карточка товара (мини-версия для списка) ──
function ProductCard({ product }: { product: Product }) {
  return (
    <Link
      to={`/catalog/${product.slug}`}
      className="block bg-white rounded-xl border border-gray-200 overflow-hidden
                 hover:shadow-lg transition-shadow no-underline"
    >
      {/* Картинка */}
      <div className="aspect-square bg-gray-100 flex items-center justify-center">
        {product.main_image_url ? (
          <img
            src={product.main_image_url}
            alt={product.name}
            className="w-full h-full object-cover"
          />
        ) : (
          <span className="text-4xl text-gray-300">📦</span>
        )}
      </div>

      {/* Информация */}
      <div className="p-4">
        <h3 className="font-semibold text-gray-900 mb-1 line-clamp-2">
          {product.name}
        </h3>
        {product.brand_name && (
          <p className="text-sm text-gray-500 mb-2">{product.brand_name}</p>
        )}
        <div className="flex items-baseline gap-2">
          <span className="text-lg font-bold text-gray-900">
            {product.min_price} ₽
          </span>
          {product.max_price && product.max_price !== product.min_price && (
            <span className="text-sm text-gray-400">
              — {product.max_price} ₽
            </span>
          )}
        </div>
        {product.reviews_count > 0 && (
          <p className="text-sm text-yellow-500 mt-1">
            ⭐ {product.rating} ({product.reviews_count})
          </p>
        )}
      </div>
    </Link>
  )
}
```

---

## 7.2. Как работают фильтры через URL-параметры

**Почему фильтры хранятся в URL, а не в React state:**

```
URL: /catalog?category=smartfony&brand=samsung&min_price=10000

Плюсы:
✅ Пользователь может скопировать URL и отправить другу
✅ Кнопка «Назад» в браузере работает корректно
✅ При обновлении страницы фильтры сохраняются
✅ SEO-friendly (каждый фильтр = свой URL)
```

**`useSearchParams()`** — React Router хук для работы с URL-параметрами:

```tsx
const [searchParams, setSearchParams] = useSearchParams()

// Читаем: ?category=smartfony
const category = searchParams.get('category')  // "smartfony"

// Пишем: меняем фильтр
const params = new URLSearchParams(searchParams)
params.set('category', 'noutbuki')
params.delete('page')  // Сброс пагинации
setSearchParams(params)  // URL обновляется → useEffect перезапускается
```

---

## 7.3. Файл `src/pages/product-page.tsx` — карточка товара

```tsx
// src/pages/product-page.tsx
// 🛍️ Детальная карточка товара: фото, варианты, цена, описание, отзывы.

import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import apiClient from '../api/client'
import { API } from '../api/endpoints'
import type { ProductDetail } from '../api/types'

export default function ProductPage() {
  const { slug } = useParams<{ slug: string }>()
  const [product, setProduct] = useState<ProductDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedVariantId, setSelectedVariantId] = useState<number | null>(null)

  // ── Загрузка товара ──
  useEffect(() => {
    if (!slug) return

    setLoading(true)
    apiClient.get<ProductDetail>(API.catalog.productDetail(slug))
      .then(({ data }) => {
        setProduct(data)
        // Выбираем первый активный вариант по умолчанию
        const firstActive = data.variants.find(v => v.is_active)
        if (firstActive) setSelectedVariantId(firstActive.id)
      })
      .catch((err) => {
        setError(err.response?.status === 404
          ? 'Товар не найден'
          : 'Ошибка загрузки товара')
      })
      .finally(() => setLoading(false))
  }, [slug])

  if (loading) return <div className="text-center py-20">Загрузка...</div>
  if (error) return <div className="text-center py-20 text-red-500">{error}</div>
  if (!product) return null

  const selectedVariant = product.variants.find(v => v.id === selectedVariantId)

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">

      {/* Хлебные крошки */}
      <nav className="text-sm text-gray-500 mb-6">
        <a href="/catalog" className="hover:text-orange-500">Каталог</a>
        <span className="mx-2">/</span>
        <span>{product.name}</span>
      </nav>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">

        {/* ── Левая часть: изображения ── */}
        <div>
          {/* Главное изображение */}
          <div className="aspect-square bg-gray-100 rounded-xl overflow-hidden mb-4">
            {product.main_image_url ? (
              <img
                src={product.main_image_url}
                alt={product.name}
                className="w-full h-full object-cover"
              />
            ) : (
              <div className="flex items-center justify-center h-full text-6xl text-gray-300">
                📦
              </div>
            )}
          </div>

          {/* Миниатюры */}
          {product.images.length > 1 && (
            <div className="flex gap-2 overflow-x-auto">
              {product.images.map(img => (
                <img
                  key={img.id}
                  src={img.image}
                  alt={img.alt}
                  className={`w-20 h-20 object-cover rounded-lg border-2 cursor-pointer
                    ${img.is_main ? 'border-orange-500' : 'border-gray-200'}`}
                />
              ))}
            </div>
          )}
        </div>

        {/* ── Правая часть: информация ── */}
        <div>
          <h1 className="text-3xl font-bold mb-2">{product.name}</h1>

          {/* Бренд */}
          {product.brand_name && (
            <p className="text-gray-500 mb-4">Бренд: {product.brand_name}</p>
          )}

          {/* Рейтинг */}
          {product.reviews_count > 0 && (
            <div className="flex items-center gap-2 mb-4">
              <span className="text-yellow-500">⭐ {product.rating}</span>
              <span className="text-gray-400">({product.reviews_count} отзывов)</span>
            </div>
          )}

          {/* Цена */}
          <div className="mb-6">
            {selectedVariant?.price ? (
              <span className="text-3xl font-bold">{selectedVariant.price} ₽</span>
            ) : product.min_price ? (
              <span className="text-3xl font-bold">
                {product.min_price}
                {product.max_price && product.max_price !== product.min_price && (
                  <> — {product.max_price}</>
                )} ₽
              </span>
            ) : (
              <span className="text-gray-400">Цена не указана</span>
            )}
          </div>

          {/* Выбор варианта */}
          {product.variants.filter(v => v.is_active).length > 1 && (
            <div className="mb-6">
              <h3 className="font-semibold mb-2">Вариант:</h3>
              <div className="flex gap-2">
                {product.variants.filter(v => v.is_active).map(variant => (
                  <button
                    key={variant.id}
                    onClick={() => setSelectedVariantId(variant.id)}
                    className={`px-4 py-2 border rounded-lg transition
                      ${variant.id === selectedVariantId
                        ? 'border-orange-500 bg-orange-50 text-orange-700'
                        : 'border-gray-200 hover:border-gray-400'}`}
                  >
                    {variant.sku}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Кнопка «В корзину» */}
          <button
            onClick={() => {
              // TODO: реализовать добавление в корзину (следующие шаги)
              alert(`Добавить в корзину: вариант ${selectedVariantId}`)
            }}
            disabled={!selectedVariantId}
            className="w-full bg-orange-500 hover:bg-orange-600 disabled:bg-gray-300
                       text-white font-semibold py-4 rounded-xl text-lg transition"
          >
            🛒 Добавить в корзину
          </button>

          {/* Описание */}
          {product.description && (
            <div className="mt-8">
              <h3 className="font-semibold mb-2">Описание</h3>
              <p className="text-gray-600 whitespace-pre-line">
                {product.description}
              </p>
            </div>
          )}

          {/* Теги */}
          {product.tags.length > 0 && (
            <div className="mt-6 flex gap-2 flex-wrap">
              {product.tags.map(tag => (
                <span
                  key={tag.id}
                  className="px-3 py-1 bg-gray-100 text-gray-600 rounded-full text-sm"
                >
                  #{tag.name}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
```

---

## 7.4. Как загружаются картинки товаров

Django хранит картинки в `media/`:
```
http://localhost:8000/media/products/2026/06/galaxy-s24.jpg
```

Vite Proxy перенаправляет `/media/*` на Django:
```
React: <img src="/media/products/2026/06/galaxy-s24.jpg" />
  → Vite Proxy: localhost:5173 → localhost:8000
  → Django: отдаёт файл
```

**Поэтому в React используем ОТНОСИТЕЛЬНЫЙ путь:**

```tsx
// ✅ ПРАВИЛЬНО — через Vite Proxy
<img src="/media/products/2026/06/galaxy-s24.jpg" />

// ❌ НЕПРАВИЛЬНО — хардкод порта
<img src="http://localhost:8000/media/products/2026/06/galaxy-s24.jpg" />
```

---

## 7.5. Схема: запрос данных каталога

```
React: useEffect → apiClient.get('/catalog/products/', { params })
  │
  ├── Vite Proxy: /api/v1/catalog/products/ → Django
  │
  ├── Request-интерцептор: добавляет Authorization: Bearer <token>
  │   (если пользователь залогинен)
  │
  ├── Django:
  │   ├── CatalogListView.get()
  │   ├── CatalogService.get_product_listing(...)
  │   ├── ProductQuerySet.catalog()  → SELECT + JOIN + WHERE
  │   ├── PageNumberPagination       → 20 товаров на страницу
  │   └── Response: { count, next, previous, results }
  │
  └── React: setProducts(data.results)
      └── Рендер: <ProductCard /> × 20
```

---

## 7.6. Проверка: открой каталог

1. Django + React запущены
2. `http://localhost:5173/catalog` → список товаров
3. Выбери категорию → URL обновляется, товары фильтруются
4. Кликни на товар → `/catalog/galaxy-s24` → карточка товара
5. Выбери вариант → цена обновляется
6. Кнопка «В корзину» → пока alert (реализуем позже)

---

### ✅ Итог части 7

- [x] Страница каталога с сеткой товаров
- [x] Фильтры: категория, бренд, цена, поиск
- [x] Фильтры хранятся в URL (useSearchParams)
- [x] Пагинация (← 1 2 3 →)
- [x] Карточка товара с изображениями, вариантами, ценой
- [x] Хлебные крошки
- [x] Картинки через Vite Proxy (/media/*)

**Это основа! Далее по тому же принципу:**
- **Корзина** — CartPage + CartStore (zustand)
- **Wishlist** — WishlistPage + API-вызовы
- **Профиль** — MeView + Address
- **Оформление заказа** — OrderCreate
- **Отзывы** — ReviewCreate + ReviewList

Все они строятся по одному шаблону:
`useEffect` → `apiClient.get/post` → `setState` → `render`
