# ЧАСТЬ 2. Установка зависимостей и настройка проекта

> **Цель:** Установить все npm-пакеты, настроить Vite-прокси, создать структуру папок, подключить Tailwind CSS.

---

## 2.1. Полный список зависимостей и ЗАЧЕМ каждый

Выполни в папке `frontend/`:

```bash
cd I:\NewPythonProjects\frontend
```

### Основные зависимости (runtime — попадут в production)

```bash
npm install react-router-dom axios zustand
```

| Пакет | Версия | Зачем | Аналог в Django |
|-------|--------|-------|-----------------|
| `react-router-dom` | 7.x | Навигация между страницами без перезагрузки | `django.urls.path()` |
| `axios` | 1.x | HTTP-запросы к Django API | `requests` в Python |
| `zustand` | 5.x | Глобальное хранилище состояния (auth, cart) | `request.user` в Django |

### Dev-зависимости (только для разработки)

```bash
npm install -D tailwindcss @tailwindcss/vite
```

| Пакет | Зачем |
|-------|-------|
| `tailwindcss` | CSS-фреймворк (utility-first) — пиши стили прямо в JSX |
| `@tailwindcss/vite` | Плагин Vite для Tailwind — мгновенная сборка |

---

## 2.2. Почему именно ЭТИ пакеты (а не другие)

### react-router-dom vs TanStack Router vs Next.js Router
- **react-router-dom** — стандарт де-факто, 90% React-проектов
- TanStack Router — новее, типизированнее, но сложнее
- Next.js Router — только для Next.js (SSR-фреймворк), нам не подходит
- **Выбор: react-router-dom** — проверенный, простой, огромная экосистема

### axios vs fetch
- **fetch** — встроенный в браузер, но:
  - Нет автоматического парсинга ошибок (надо проверять `response.ok`)
  - Нет интерцепторов (нельзя добавить токен в каждый запрос)
  - Нет таймаутов
  - Не отменяет запросы при размонтировании компонента
- **axios** — обёртка над fetch:
  - Интерцепторы → добавляем JWT-токен в каждый запрос автоматически
  - Автопарсинг JSON
  - Автообработка 401 → обновление токена
  - Таймауты, отмена запросов
- **Выбор: axios** — критично для JWT-авторизации

### zustand vs Redux vs Context API
- **Redux** — слишком много бойлерплейта (actions, reducers, selectors, middleware)
- **Context API** — встроенный, но: нет middleware, нет devtools, ре-рендерит ВСЕХ детей
- **zustand** — минималистичный, 1 файл на хранилище, встроенный devtools
- **Выбор: zustand** — проще Redux, мощнее Context

### Tailwind CSS vs CSS Modules vs Styled Components
- **CSS Modules** — отдельные `.module.css` файлы, OK но нет дизайн-системы
- **Styled Components** — CSS-in-JS, медленнее, больше кода
- **Tailwind CSS** — utility-first, пиши стили прямо в JSX:
  ```html
  <button className="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600">
    Войти
  </button>
  ```
- **Выбор: Tailwind** — быстрый, Amazon-подобный дизайн из коробки

---

## 2.3. Настройка Tailwind CSS

### Шаг 1: Подключи плагин в `vite.config.ts`

```ts
// vite.config.ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),        // ← Добавь эту строку
  ],
  server: {
    port: 5173,           // Порт React-сервера
    proxy: {              // ← ПРОКСИ (см. раздел 2.4 ниже)
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/media': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
```

### Шаг 2: Замени содержимое `src/index.css`

```css
/* src/index.css — ТОЛЬКО эта строка, всё остальное УДАЛИ */
@import "tailwindcss";
```

### Шаг 3: Проверь, что Tailwind работает

Замени `src/App.tsx`:

```tsx
function App() {
  return (
    <div className="min-h-screen bg-gray-100 flex items-center justify-center">
      <div className="bg-white p-8 rounded-xl shadow-lg text-center">
        <h1 className="text-3xl font-bold text-gray-900 mb-4">
          🛒 Amazon Clone
        </h1>
        <p className="text-gray-600">
          Tailwind работает! Если видишь стили — всё OK.
        </p>
      </div>
    </div>
  )
}

export default App
```

Запусти `npm run dev` — увидишь красивую карточку с тенями и скруглениями.

---

## 2.4. Vite Proxy — КАК React общается с Django

### Проблема без прокси

React (`localhost:5173`) делает запрос к Django (`localhost:8000`):

```tsx
fetch('http://localhost:8000/api/v1/health/')
```

Проблемы:
1. В **production** не будет `localhost:8000` — будет один домен
2. Код захардкожен на порт 8000 — придётся менять перед деплоем
3. Credentials (cookies) могут не передаваться между портами

### Решение: Vite Dev Proxy

Прокси — это **пересылка** запросов. React делает запрос НА СЕБЯ, а Vite пересылает его на Django:

```
React: fetch('/api/v1/health/')
  → Vite dev server (localhost:5173) перехватывает /api/*
    → пересылает на http://localhost:8000/api/v1/health/
      → Django обрабатывает и возвращает JSON
        → Vite возвращает JSON обратно в React
```

**Для React это выглядит так, будто API находится на том же домене!**

```tsx
// С прокси — НЕ нужно указывать http://localhost:8000
fetch('/api/v1/health/')

// БЕЗ прокси — пришлось бы хардкодить
fetch('http://localhost:8000/api/v1/health/')
```

### Конфигурация прокси (уже в vite.config.ts выше)

```ts
server: {
  proxy: {
    '/api': {                    // Все запросы /api/* → Django
      target: 'http://localhost:8000',
      changeOrigin: true,       // Подменяет Origin-заголовок
    },
    '/media': {                  // Картинки товаров → Django
      target: 'http://localhost:8000',
      changeOrigin: true,
    },
  },
},
```

**Что делает `changeOrigin: true`:**
- Без него: запрос идёт с заголовком `Origin: http://localhost:5173`
- С ним: запрос идёт с заголовком `Origin: http://localhost:8000`
- Это нужно, чтобы Django CORS не блокировал запросы от прокси

### Проверка прокси

Добавь в `src/App.tsx`:

```tsx
import { useEffect, useState } from 'react'

function App() {
  const [health, setHealth] = useState<string>('загрузка...')

  useEffect(() => {
    fetch('/api/v1/health/')
      .then(r => r.json())
      .then(data => setHealth(JSON.stringify(data)))
      .catch(err => setHealth(`Ошибка: ${err.message}`))
  }, [])

  return (
    <div className="min-h-screen bg-gray-100 flex items-center justify-center">
      <div className="bg-white p-8 rounded-xl shadow-lg text-center">
        <h1 className="text-3xl font-bold text-gray-900 mb-4">🛒 Amazon Clone</h1>
        <p className="text-gray-600">Health: {health}</p>
      </div>
    </div>
  )
}

export default App
```

Если видишь `{"status":"ok","version":"1.0.0","database":"ok"}` — **прокси работает!**

---

## 2.5. Структура папок React-проекта

Удали всё из `src/` и создай новую структуру:

```
src/
├── main.tsx                ← Точка входа (НЕ трогаем)
├── index.css               ← @import "tailwindcss" (НЕ трогаем)
├── App.tsx                 ← Корневой компонент с маршрутизацией
│
├── api/                    ← 📡 Всё связанное с API-запросами
│   ├── client.ts           ← Axios-инстанс (базовый URL + интерцепторы)
│   └── endpoints.ts        ← Все URL бэкенда в одном месте
│
├── stores/                 ← 📦 Глобальные хранилища (zustand)
│   ├── auth-store.ts       ← JWT-токены + пользователь
│   └── cart-store.ts       ← Корзина (позже)
│
├── pages/                  ← 📄 Страницы (по одной на маршрут)
│   ├── home-page.tsx       ← / (главная)
│   ├── login-page.tsx      ← /login
│   ├── register-page.tsx   ← /register
│   ├── catalog-page.tsx    ← /catalog
│   ├── product-page.tsx    ← /catalog/:slug
│   ├── cart-page.tsx       ← /cart
│   ├── profile-page.tsx    ← /profile
│   └── not-found-page.tsx  ← 404
│
├── components/             ← 🧩 Переиспользуемые компоненты
│   ├── layout/             ← Обёртки страниц
│   │   ├── header.tsx      ← Шапка (навбар)
│   │   └── footer.tsx      ← Подвал
│   ├── product/            ← Карточки товаров
│   │   └── product-card.tsx
│   └── ui/                 ← Базовые UI-элементы
│       ├── button.tsx
│       ├── input.tsx
│       └── loader.tsx
│
├── hooks/                  ← 🪝 Кастомные React-хуки
│   └── use-auth.ts         ← Хук для доступа к auth-store
│
└── lib/                    ← 🔧 Утилиты
    └── utils.ts            ← Вспомогательные функции
```

**Почему ТАКАЯ структура:**
- `api/` отдельно → если изменится бэкенд, меняешь только этот слой
- `stores/` отдельно → состояние отделено от UI
- `pages/` → одна страница = один файл = легко найти
- `components/` → переиспользуемые кусочки UI
- `hooks/` → логика, используемая в нескольких местах
- `lib/` → чистые функции (форматирование дат, цен)

Создай пустые файлы:

```bash
cd I:\NewPythonProjects\frontend\src
mkdir api stores pages components\layout components\product components\ui hooks lib
type nul > api\client.ts
type nul > api\endpoints.ts
type nul > stores\auth-store.ts
type nul > pages\home-page.tsx
type nul > pages\login-page.tsx
type nul > pages\catalog-page.tsx
type nul > components\layout\header.tsx
type nul > components\ui\button.tsx
type nul > components\ui\input.tsx
type nul > components\ui\loader.tsx
type nul > lib\utils.ts
```

---

## 2.6. Файл `.env` для React

Создай `frontend/.env`:

```env
# URL бэкенда — используется ТОЛЬКО в development
# В production этот файл НЕ нужен (nginx раздаёт и React, и API)
VITE_API_BASE_URL=
```

**Почему пустое значение:**
- С Vite Proxy все запросы идут через `/api/*` → относительный URL
- Пустое значение = запросы идут на тот же домен
- Если когда-нибудь понадобится внешний API → укажешь полный URL

**Правило Vite:** только переменные с префиксом `VITE_` доступны в коде:
```ts
// ✅ Работает
const url = import.meta.env.VITE_API_BASE_URL

// ❌ НЕ работает — не видна в коде
const secret = import.meta.env.SECRET_KEY  // undefined
```

---

### ✅ Итог части 2

- [x] `react-router-dom` — маршрутизация
- [x] `axios` — HTTP-запросы
- [x] `zustand` — глобальное состояние
- [x] `tailwindcss` — стили
- [x] Vite Proxy — React→Django без CORS-проблем
- [x] Структура папок создана
- [x] `.env` для React создан

**Далее: Часть 3 — Axios-клиент и все API-эндпоинты**
