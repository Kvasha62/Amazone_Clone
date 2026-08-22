# Шаг 15. Главная страница + финал

Замени `src/pages/HomePage.tsx`:

```typescript
// src/pages/HomePage.tsx
// Главная страница: hero-баннер + популярные товары.

import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import api from '../api/client';
import { CATALOG } from '../api/endpoints';

interface Product {
  id: number;
  name: string;
  slug: string;
  min_price: string;
  rating: string;
  reviews_count: number;
  main_image: string | null;
  brand: { name: string } | null;
}

export function HomePage() {
  const [featured, setFeatured] = useState<Product[]>([]);

  useEffect(() => {
    api.get(CATALOG.PRODUCTS, { params: { page_size: 8 } })
      .then(({ data }) => setFeatured(data.results || []))
      .catch(() => {});
  }, []);

  return (
    <div>
      {/* Hero-баннер */}
      <div style={{
        background: 'linear-gradient(135deg, #131921 0%, #232f3e 100%)',
        color: 'white',
        padding: '60px 40px',
        borderRadius: '8px',
        marginBottom: '32px',
        textAlign: 'center',
      }}>
        <h1 style={{ fontSize: '36px', marginBottom: '12px' }}>Добро пожаловать в Amazone</h1>
        <p style={{ fontSize: '18px', color: '#ffa500', marginBottom: '24px' }}>Лучшие товары по лучшим ценам</p>
        <Link to="/products">
          <button style={{
            padding: '14px 32px',
            background: '#ffa500',
            border: 'none',
            borderRadius: '4px',
            fontSize: '18px',
            cursor: 'pointer',
            fontWeight: 'bold',
          }}>
            Перейти в каталог →
          </button>
        </Link>
      </div>

      {/* Популярные товары */}
      <h2 style={{ marginBottom: '16px' }}>🔥 Популярные товары</h2>

      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))',
        gap: '16px',
      }}>
        {featured.map(product => (
          <Link
            key={product.id}
            to={`/products/${product.slug}`}
            style={{
              textDecoration: 'none',
              color: 'inherit',
              border: '1px solid #ddd',
              borderRadius: '8px',
              padding: '12px',
            }}
          >
            <div style={{
              height: '160px',
              background: '#f5f5f5',
              borderRadius: '4px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              marginBottom: '8px',
            }}>
              {product.main_image ? (
                <img src={product.main_image} alt={product.name} style={{ maxWidth: '100%', maxHeight: '100%', objectFit: 'contain' }} />
              ) : (
                <span style={{ fontSize: '48px' }}>📦</span>
              )}
            </div>
            <div style={{ fontWeight: 'bold', fontSize: '14px', marginBottom: '4px' }}>{product.name}</div>
            {product.brand && <div style={{ color: '#888', fontSize: '12px' }}>{product.brand.name}</div>}
            <div style={{ color: '#c00', fontWeight: 'bold', marginTop: '4px' }}>{product.min_price} ₽</div>
            <div style={{ fontSize: '12px', color: '#666' }}>⭐ {parseFloat(product.rating).toFixed(1)} ({product.reviews_count})</div>
          </Link>
        ))}
      </div>
    </div>
  );
}
```

---

### Базовый CSS — замени `src/index.css`:

```css
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  color: #0f1111;
  background: #eaeded;
}

a {
  text-decoration: none;
}

button:hover {
  opacity: 0.9;
}

input:focus {
  outline: 2px solid #ffa500;
  border-color: #ffa500 !important;
}
```

---

## 🎉 ФИНАЛ — проверка всего проекта

### Убедись что у тебя есть все файлы:

```
frontend/
├── src/
│   ├── api/
│   │   ├── client.ts          ← axios + JWT
│   │   └── endpoints.ts       ← все URL
│   ├── stores/
│   │   ├── authStore.ts        ← пользователь
│   │   └── cartStore.ts        ← корзина
│   ├── components/
│   │   ├── Layout.tsx          ← хедер + корзина + футер
│   │   └── ProtectedRoute.tsx  ← защита страниц
│   ├── pages/
│   │   ├── HomePage.tsx        ← главная
│   │   ├── LoginPage.tsx       ← вход
│   │   ├── RegisterPage.tsx    ← регистрация
│   │   ├── ProductListPage.tsx ← каталог
│   │   ├── ProductDetailPage.tsx ← карточка
│   │   ├── CartPage.tsx        ← корзина
│   │   ├── OrderCreatePage.tsx ← оформление
│   │   ├── OrderListPage.tsx   ← мои заказы
│   │   ├── OrderDetailPage.tsx ← детали заказа
│   │   ├── WishlistPage.tsx    ← избранное
│   │   └── ProfilePage.tsx     ← личный кабинет
│   ├── router.tsx              ← маршруты
│   ├── main.tsx                ← точка входа
│   └── index.css               ← стили
├── vite.config.ts              ← proxy на Django
└── package.json
```

### Запуск:

```bash
# Терминал 1 — бэкенд:
cd I:\NewPythonProjects\Amazone_Clone
python manage.py runserver

# Терминал 2 — фронтенд:
cd I:\NewPythonProjects\frontend
npm run dev
```

### Что должно работать:
1. http://localhost:5173 → Главная с каталогом
2. http://localhost:5173/login → Вход по email
3. http://localhost:5173/register → Регистрация
4. http://localhost:5173/products → Каталог с поиском
5. http://localhost:5173/products/slug → Карточка товара
6. Кнопка «В корзину» → боковая панель корзины
7. http://localhost:5173/cart → Полная страница корзины
8. http://localhost:5173/checkout → Оформление заказа
9. http://localhost:5173/orders → Мои заказы
10. http://localhost:5173/profile → Личный кабинет

---

## 🚀 Что делать дальше (улучшения):

| Что | Зачем |
|-----|-------|
| Tailwind CSS | Красивые стили без inline |
| Ant Design / MUI | Готовые компоненты |
| @tanstack/react-query | Кэширование API-запросов |
| React Hook Form | Удобные формы |
| WebSocket | Real-time уведомления |
| Lazy loading | Подгрузка страниц по требованию |
