# ЧАСТЬ 5. React Router: маршрутизация и макет приложения

> **Цель:** Настроить маршрутизацию (переходы между страницами) и создать макет с шапкой и подвалом.

---

## 5.1. Как работает маршрутизация в React (vs Django)

**Django (server-side):**
```
Пользователь: http://site.com/catalog/
  → Django получает запрос
  → urls.py: path('catalog/', CatalogView)
  → Рендерит HTML на сервере
  → Отправляет готовую HTML-страницу
```

**React (client-side):**
```
Пользователь: http://site.com/catalog/
  → Vite отдаёт index.html (ВСЕГДА одну и ту же)
  → React Router видит URL = /catalog/
  → Рендерит <CatalogPage /> компонент
  → Меняет DOM БЕЗ перезагрузки страницы
```

**Ключевое отличие:** в React НЕТ запроса к серверу при переходе между страницами. URL меняется через JavaScript History API.

---

## 5.2. Установка React Router

Уже установлено в Части 2 (`react-router-dom`). Проверь:

```bash
npm list react-router-dom
# → react-router-dom@7.x.x
```

---

## 5.3. Файл `src/App.tsx` — маршруты

```tsx
// src/App.tsx
// 🗺️ Корневой компонент: определяет все маршруты приложения.
// React Router v7: <Routes> + <Route> = декларативная маршрутизация.

import { Routes, Route } from 'react-router-dom'
import { BrowserRouter } from 'react-router-dom'

// Импортируем компоненты (создадим ниже)
import MainLayout from './components/layout/main-layout'
import HomePage from './pages/home-page'
import LoginPage from './pages/login-page'
import RegisterPage from './pages/register-page'
import CatalogPage from './pages/catalog-page'
import ProductPage from './pages/product-page'
import CartPage from './pages/cart-page'
import ProfilePage from './pages/profile-page'
import NotFoundPage from './pages/not-found-page'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Маршруты С макетом (шапка + подвал) */}
        <Route element={<MainLayout />}>
          <Route path="/" element={<HomePage />} />
          <Route path="/catalog" element={<CatalogPage />} />
          <Route path="/catalog/:slug" element={<ProductPage />} />
          <Route path="/cart" element={<CartPage />} />
          <Route path="/profile" element={<ProfilePage />} />
        </Route>

        {/* Маршруты БЕЗ макета (отдельные страницы входа) */}
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />

        {/* 404 — любой неизвестный URL */}
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
```

**Разбор:**

| Элемент | Что делает |
|---------|------------|
| `<BrowserRouter>` | Обёртка — включает React Router для всего приложения |
| `<Routes>` | Контейнер для маршрутов — выберет ОДИН подходящий |
| `<Route path="/catalog" element={...}>` | При URL `/catalog` → рендерит `<CatalogPage />` |
| `<Route path="/catalog/:slug">` | `:slug` — динамический параметр → `/catalog/galaxy-s24` |
| `<Route element={<MainLayout />}>` | Layout-маршрут — оборачивает дочерние страницы в макет |
| `<Route path="*">` | Fallback — если ни один маршрут не совпал |

---

## 5.4. Layout-маршрут — КАК это работает

`<MainLayout />` — это обёртка, которая добавляет шапку и подвал ко ВСЕМ вложенным страницам:

```tsx
// Компонент MainLayout использует <Outlet /> — «дырку»,
// куда React Router вставит текущую страницу.

<div>
  <Header />          ← Шапка (на каждой странице)
  <main>
    <Outlet />        ← СЮДА вставится HomePage / CatalogPage / и т.д.
  </main>
  <Footer />          ← Подвал (на каждой странице)
</div>
```

---

## 5.5. Файл `src/components/layout/main-layout.tsx`

```tsx
// src/components/layout/main-layout.tsx
// 🏗️ Основной макет: шапка + контент + подвал.

import { Outlet } from 'react-router-dom'
import Header from './header'
import Footer from './footer'

export default function MainLayout() {
  return (
    <div className="min-h-screen flex flex-col bg-gray-50">
      {/* Шапка — фиксированная вверху */}
      <Header />

      {/* Контент страницы — растягивается на всё доступное пространство */}
      <main className="flex-1">
        <Outlet />
      </main>

      {/* Подвал — внизу */}
      <Footer />
    </div>
  )
}
```

---

## 5.6. Файл `src/components/layout/header.tsx` — ШАПКА

```tsx
// src/components/layout/header.tsx
// 🔝 Шапка сайта: логотип, поиск, навигация, корзина, профиль.

import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../../hooks/use-auth'

export default function Header() {
  const { user, isAuthenticated, logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/')  // После выхода — на главную
  }

  return (
    <header className="bg-gray-900 text-white sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">

        {/* Логотип */}
        <Link to="/" className="text-2xl font-bold text-orange-400 no-underline">
          🛒 Amazone
        </Link>

        {/* Навигация */}
        <nav className="flex items-center gap-6">
          <Link
            to="/catalog"
            className="text-gray-300 hover:text-white transition-colors no-underline"
          >
            Каталог
          </Link>

          {/* Корзина */}
          <Link
            to="/cart"
            className="text-gray-300 hover:text-white transition-colors no-underline relative"
          >
            🛒 Корзина
          </Link>

          {/* Профиль / Вход */}
          {isAuthenticated ? (
            <div className="flex items-center gap-4">
              <Link
                to="/profile"
                className="text-gray-300 hover:text-white transition-colors no-underline"
              >
                👤 {user?.username}
              </Link>
              <button
                onClick={handleLogout}
                className="text-gray-400 hover:text-white text-sm"
              >
                Выйти
              </button>
            </div>
          ) : (
            <Link
              to="/login"
              className="bg-orange-500 hover:bg-orange-600 text-white px-4 py-2 rounded-lg no-underline"
            >
              Войти
            </Link>
          )}
        </nav>
      </div>
    </header>
  )
}
```

**Разбор:**
- `<Link to="/catalog">` — ссылка БЕЗ перезагрузки страницы (вместо `<a href>`)
- `useNavigate()` — программный переход (после logout)
- `useAuth()` — доступ к состоянию авторизации из zustand-стора
- `isAuthenticated ? ... : ...` — условный рендеринг (залогинен / гость)

---

## 5.7. Файл `src/components/layout/footer.tsx`

```tsx
// src/components/layout/footer.tsx
// 🔽 Подвал сайта.

export default function Footer() {
  return (
    <footer className="bg-gray-900 text-gray-400 py-8 mt-12">
      <div className="max-w-7xl mx-auto px-4 text-center">
        <p>© 2026 Amazone Clone. Учебный проект.</p>
      </div>
    </footer>
  )
}
```

---

## 5.8. Временные заглушки для страниц

Пока страницы не реализованы — создай заглушки:

```tsx
// src/pages/home-page.tsx
export default function HomePage() {
  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <h1 className="text-4xl font-bold mb-4">🛒 Добро пожаловать в Amazone!</h1>
      <p className="text-gray-600">Главная страница (будет реализована позже)</p>
    </div>
  )
}
```

```tsx
// src/pages/catalog-page.tsx
export default function CatalogPage() {
  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold">Каталог товаров</h1>
      <p className="text-gray-500">Будет реализовано в следующих частях</p>
    </div>
  )
}
```

```tsx
// src/pages/product-page.tsx
import { useParams } from 'react-router-dom'
export default function ProductPage() {
  const { slug } = useParams()
  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold">Товар: {slug}</h1>
    </div>
  )
}
```

```tsx
// src/pages/cart-page.tsx
export default function CartPage() {
  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold">🛒 Корзина</h1>
    </div>
  )
}
```

```tsx
// src/pages/profile-page.tsx
export default function ProfilePage() {
  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold">👤 Профиль</h1>
    </div>
  )
}
```

```tsx
// src/pages/not-found-page.tsx
import { Link } from 'react-router-dom'
export default function NotFoundPage() {
  return (
    <div className="max-w-7xl mx-auto px-4 py-20 text-center">
      <h1 className="text-6xl font-bold text-gray-300 mb-4">404</h1>
      <p className="text-xl text-gray-500 mb-8">Страница не найдена</p>
      <Link to="/" className="text-orange-500 hover:underline">
        На главную
      </Link>
    </div>
  )
}
```

---

## 5.9. Как происходит переход между страницами

### Способ 1: `<Link>` — ссылка

```tsx
// Пользователь кликает — переход без перезагрузки
<Link to="/catalog">Каталог</Link>
```

### Способ 2: `useNavigate()` — программный переход

```tsx
import { useNavigate } from 'react-router-dom'

function LoginButton() {
  const navigate = useNavigate()

  const handleLogin = async () => {
    await login(email, password)
    navigate('/profile')    // ← Перейти на /profile после входа
  }

  return <button onClick={handleLogin}>Войти</button>
}
```

### Способ 3: `redirect()` в loader/action

```tsx
// Если пользователь не авторизован — перенаправить на /login
if (!isAuthenticated) {
  return <Navigate to="/login" replace />
}
```

---

## 5.10. Как React Router обрабатывает URL

```
URL в браузере         React Router           Рендерится
─────────────────     ──────────────         ───────────────
/                      <HomePage />          Главная
/catalog               <CatalogPage />       Каталог
/catalog/galaxy-s24   <ProductPage />       slug="galaxy-s24"
/cart                  <CartPage />          Корзина
/login                 <LoginPage />         Вход (без макета!)
/register              <RegisterPage />      Регистрация (без макета!)
/abrakadabra           <NotFoundPage />      404
```

**Обрати внимание:** `/login` и `/register` НЕ оборачиваются в `MainLayout` — у них свой дизайн (без шапки/подвала).

---

## 5.11. Проверка: запусти приложение

```bash
npm run dev
```

1. `http://localhost:5173` → Главная с шапкой «🛒 Amazone» и кнопкой «Войти»
2. Кликни «Каталог» → URL меняется на `/catalog` БЕЗ перезагрузки
3. Кликни «Войти» → переход на `/login` (без шапки/подвала)
4. Введи несуществующий URL → страница 404

---

### ✅ Итог части 5

- [x] `react-router-dom` настроен в `App.tsx`
- [x] Layout-маршрут `<MainLayout>` добавляет шапку и подвал
- [x] `<Header />` показывает навигацию, корзину, профиль/кнопку входа
- [x] `<Outlet />` — место для вставки текущей страницы
- [x] `<Link>` — переходы без перезагрузки
- [x] Динамический маршрут `/catalog/:slug` для карточки товара
- [x] Страница 404 для неизвестных URL

**Далее: Часть 6 — Страницы входа и регистрации**
