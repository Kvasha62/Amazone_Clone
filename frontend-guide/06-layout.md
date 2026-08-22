# Шаг 6. Layout — оболочка всех страниц

Создай файл `src/components/Layout.tsx`:

```typescript
// src/components/Layout.tsx
// Общий каркас: хедер + сайдбар корзины + основной контент + футер.

import { useEffect } from 'react';
import { Outlet, Link, useNavigate } from 'react-router-dom';
import { useAuthStore } from '../stores/authStore';
import { useCartStore } from '../stores/cartStore';

export function Layout() {
  const { user, isAuthenticated, logout, fetchUser } = useAuthStore();
  const { cart, isCartOpen, toggleCart, fetchCart } = useCartStore();
  const navigate = useNavigate();

  // При первой загрузке — получаем пользователя и корзину
  useEffect(() => {
    fetchUser();
    fetchCart();
  }, []);

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* ═══ ХЕДЕР ═══ */}
      <header style={{
        background: '#131921',
        color: 'white',
        padding: '10px 20px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
      }}>
        {/* Логотип */}
        <Link to="/" style={{ color: 'white', textDecoration: 'none', fontSize: '24px', fontWeight: 'bold' }}>
          🛒 Amazone
        </Link>

        {/* Поиск (пока заглушка) */}
        <input
          type="text"
          placeholder="Искать товары..."
          style={{ flex: 1, margin: '0 20px', padding: '8px 12px', borderRadius: '4px', border: 'none' }}
        />

        {/* Навигация */}
        <div style={{ display: 'flex', gap: '16px', alignItems: 'center' }}>
          <Link to="/products" style={{ color: 'white', textDecoration: 'none' }}>
            Каталог
          </Link>

          {isAuthenticated ? (
            <>
              <Link to="/wishlist" style={{ color: 'white', textDecoration: 'none' }}>
                ❤️ Избранное
              </Link>
              <Link to="/orders" style={{ color: 'white', textDecoration: 'none' }}>
                📦 Заказы
              </Link>
              <Link to="/profile" style={{ color: 'white', textDecoration: 'none' }}>
                👤 {user?.first_name || user?.username}
              </Link>
              <button
                onClick={handleLogout}
                style={{ background: 'none', border: 'none', color: '#ffa500', cursor: 'pointer' }}
              >
                Выйти
              </button>
            </>
          ) : (
            <Link to="/login" style={{ color: 'white', textDecoration: 'none' }}>
              Войти
            </Link>
          )}

          {/* Кнопка корзины */}
          <button
            onClick={toggleCart}
            style={{ background: 'none', border: 'none', color: 'white', cursor: 'pointer', fontSize: '18px' }}
          >
            🛒 {cart?.total_quantity || 0}
          </button>
        </div>
      </header>

      {/* ═══ БОКОВАЯ КОРЗИНА ═══ */}
      {isCartOpen && (
        <div style={{
          position: 'fixed',
          right: 0,
          top: 0,
          bottom: 0,
          width: '400px',
          background: 'white',
          boxShadow: '-2px 0 8px rgba(0,0,0,0.3)',
          zIndex: 1000,
          display: 'flex',
          flexDirection: 'column',
        }}>
          <div style={{ padding: '16px', borderBottom: '1px solid #ddd', display: 'flex', justifyContent: 'space-between' }}>
            <h3>Корзина ({cart?.total_quantity || 0})</h3>
            <button onClick={toggleCart} style={{ background: 'none', border: 'none', fontSize: '20px', cursor: 'pointer' }}>
              ✕
            </button>
          </div>

          <div style={{ flex: 1, overflowY: 'auto', padding: '16px' }}>
            {cart?.items?.length === 0 && <p style={{ color: '#888' }}>Корзина пуста</p>}
            {cart?.items?.map(item => (
              <div key={item.id} style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '12px', padding: '8px', borderBottom: '1px solid #eee' }}>
                <div>
                  <div style={{ fontWeight: 'bold' }}>{item.product_name}</div>
                  <div style={{ color: '#888', fontSize: '14px' }}>{item.sku}</div>
                  <div>{item.price} ₽ × {item.quantity} = <b>{item.total_price} ₽</b></div>
                </div>
                <button
                  onClick={() => useCartStore.getState().removeItem(item.id)}
                  style={{ background: 'none', border: 'none', color: 'red', cursor: 'pointer' }}
                >
                  🗑️
                </button>
              </div>
            ))}
          </div>

          {cart?.items?.length > 0 && (
            <div style={{ padding: '16px', borderTop: '1px solid #ddd' }}>
              <div style={{ fontSize: '18px', fontWeight: 'bold', marginBottom: '12px' }}>
                Итого: {cart?.total} ₽
              </div>
              <Link to="/checkout" onClick={toggleCart}>
                <button style={{
                  width: '100%', padding: '12px', background: '#ffa500',
                  border: 'none', borderRadius: '4px', fontSize: '16px', cursor: 'pointer',
                }}>
                  Оформить заказ
                </button>
              </Link>
            </div>
          )}
        </div>
      )}

      {/* ═══ ОСНОВНОЙ КОНТЕНТ ═══ */}
      <main style={{ flex: 1, padding: '20px', maxWidth: '1200px', margin: '0 auto', width: '100%' }}>
        <Outlet />
      </main>

      {/* ═══ ФУТЕР ═══ */}
      <footer style={{
        background: '#131921',
        color: '#999',
        padding: '20px',
        textAlign: 'center',
      }}>
        © 2026 Amazone Clone. Учебный проект.
      </footer>
    </div>
  );
}
```

---

### Создай файл `src/components/ProtectedRoute.tsx`:

```typescript
// src/components/ProtectedRoute.tsx
// Обёртка для страниц, требующих авторизацию.
// Если пользователь не авторизован — перенаправляем на /login.

import { Navigate, Outlet } from 'react-router-dom';
import { useAuthStore } from '../stores/authStore';

export function ProtectedRoute() {
  const { isAuthenticated, isLoading } = useAuthStore();

  if (isLoading) {
    return <div>Загрузка...</div>;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
}
```

---

### Создай ЗАГЛУШКИ для страниц (пока пустые):

```typescript
// src/pages/HomePage.tsx
export function HomePage() {
  return <h1>🏠 Главная страница</h1>;
}
```

```typescript
// src/pages/LoginPage.tsx
export function LoginPage() {
  return <h1>🔐 Страница входа</h1>;
}
```

```typescript
// src/pages/RegisterPage.tsx
export function RegisterPage() {
  return <h1>📝 Страница регистрации</h1>;
}
```

```typescript
// src/pages/ProfilePage.tsx
export function ProfilePage() {
  return <h1>👤 Личный кабинет</h1>;
}
```

```typescript
// src/pages/ProductListPage.tsx
export function ProductListPage() {
  return <h1>📦 Каталог товаров</h1>;
}
```

```typescript
// src/pages/ProductDetailPage.tsx
export function ProductDetailPage() {
  return <h1>📦 Карточка товара</h1>;
}
```

```typescript
// src/pages/CartPage.tsx
export function CartPage() {
  return <h1>🛒 Корзина</h1>;
}
```

```typescript
// src/pages/OrderCreatePage.tsx
export function OrderCreatePage() {
  return <h1>📋 Оформление заказа</h1>;
}
```

```typescript
// src/pages/OrderDetailPage.tsx
export function OrderDetailPage() {
  return <h1>📦 Детали заказа</h1>;
}
```

```typescript
// src/pages/OrderListPage.tsx
export function OrderListPage() {
  return <h1>📦 Мои заказы</h1>;
}
```

```typescript
// src/pages/WishlistPage.tsx
export function WishlistPage() {
  return <h1>❤️ Избранное</h1>;
}
```

---

### Итог шага 6
✅ Layout с хедером, корзиной, футером
✅ ProtectedRoute — защита страниц
✅ Все заглушки страниц созданы
✅ `npm run dev` показывает Layout с навигацией

→ Переходи к шагу 7
