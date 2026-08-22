# Шаг 5. Роутинг (React Router)

Создай файл `src/router.tsx`:

```typescript
// src/router.tsx
// Все маршруты приложения.

import { createBrowserRouter } from 'react-router-dom';
import { Layout } from './components/Layout';
import { HomePage } from './pages/HomePage';
import { LoginPage } from './pages/LoginPage';
import { RegisterPage } from './pages/RegisterPage';
import { ProfilePage } from './pages/ProfilePage';
import { ProductListPage } from './pages/ProductListPage';
import { ProductDetailPage } from './pages/ProductDetailPage';
import { CartPage } from './pages/CartPage';
import { OrderCreatePage } from './pages/OrderCreatePage';
import { OrderDetailPage } from './pages/OrderDetailPage';
import { OrderListPage } from './pages/OrderListPage';
import { WishlistPage } from './pages/WishlistPage';
import { ProtectedRoute } from './components/ProtectedRoute';

export const router = createBrowserRouter([
  {
    path: '/',
    element: <Layout />,
    children: [
      // Публичные страницы
      { index: true, element: <HomePage /> },
      { path: 'products', element: <ProductListPage /> },
      { path: 'products/:slug', element: <ProductDetailPage /> },
      { path: 'login', element: <LoginPage /> },
      { path: 'register', element: <RegisterPage /> },

      // Защищённые страницы (только для авторизованных)
      {
        element: <ProtectedRoute />,
        children: [
          { path: 'profile', element: <ProfilePage /> },
          { path: 'cart', element: <CartPage /> },
          { path: 'checkout', element: <OrderCreatePage /> },
          { path: 'orders', element: <OrderListPage /> },
          { path: 'orders/:orderNumber', element: <OrderDetailPage /> },
          { path: 'wishlist', element: <WishlistPage /> },
        ],
      },
    ],
  },
]);
```

---

### Обнови `src/main.tsx`:

```typescript
// src/main.tsx
import React from 'react';
import ReactDOM from 'react-dom/client';
import { RouterProvider } from 'react-router-dom';
import { router } from './router';
import './index.css';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <RouterProvider router={router} />
  </React.StrictMode>
);
```

---

### Итог шага 5
✅ `src/router.tsx` — все маршруты
✅ `src/main.tsx` — использует RouterProvider

→ Переходи к шагу 6
