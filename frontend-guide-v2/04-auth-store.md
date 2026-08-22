# ЧАСТЬ 4. Auth Store: JWT-авторизация через Zustand

> **Цель:** Глобальное хранилище авторизации. Компоненты могут узнать «залогинен ли пользователь» и «кто он» без prop-drilling.

---

## 4.1. Проблема: КАК React знает, что пользователь залогинен?

В Django всё просто:
```python
# Django — сервер хранит сессию
if request.user.is_authenticated:
    username = request.user.username
```

React — **другая модель**:
- React работает в **браузере** — нет серверных сессий
- После перезагрузки страницы React «забывает» всё
- Нужно ХРАНИТЬ состояние авторизации ГДЕ-ТО

**Два места хранения:**

| Место | Плюсы | Минусы |
|-------|-------|--------|
| `localStorage` | Переживает перезагрузку страницы | XSS-уязвимость (JS может прочитать) |
| Память React (state) | Безопасно от XSS | Пропадает при перезагрузке |

**Наше решение:** комбинация обоих:
- `localStorage` — храним **только токены** (access + refresh)
- Zustand store — храним **данные пользователя** (email, username)
- При загрузке приложения — проверяем токен в localStorage, если есть — загружаем профиль

---

## 4.2. Файл `src/stores/auth-store.ts` — ПОЛНЫЙ код

```ts
// src/stores/auth-store.ts
// 📦 Глобальное хранилище авторизации.
// Zustand-стор — доступен из ЛЮБОГО компонента без prop-drilling.
//
// СОСТОЯНИЕ (state):
//   user: User | null        — данные пользователя (null = не залогинен)
//   isAuthenticated: boolean — залогинен ли?
//   isLoading: boolean       — идёт ли загрузка профиля?
//
// ДЕЙСТВИЯ (actions):
//   login(email, password)   — войти → сохранить токены → загрузить профиль
//   register(data)           — зарегистрироваться → автоматически войти
//   logout()                 — выйти → удалить токены → очистить профиль
//   loadProfile()            — загрузить /users/me/ по существующему токену
//   initAuth()               — проверить токен при старте приложения

import { create } from 'zustand'
import apiClient from '../api/client'
import { API } from '../api/endpoints'
import type { User, LoginRequest, RegisterRequest, AuthTokens } from '../api/types'

// ──────────────────────────────────────────────
// Интерфейс хранилища
// ──────────────────────────────────────────────

interface AuthState {
  // State (данные)
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean

  // Actions (действия)
  login: (email: string, password: string) => Promise<void>
  register: (data: RegisterRequest) => Promise<void>
  logout: () => void
  loadProfile: () => Promise<void>
  initAuth: () => Promise<void>
}

// ──────────────────────────────────────────────
// Создание хранилища
// ──────────────────────────────────────────────

export const useAuthStore = create<AuthState>((set, get) => ({

  // ── Начальное состояние ──
  user: null,
  isAuthenticated: false,
  isLoading: false,

  // ── ВХОД ──
  // 1. POST /auth/login/ {email, password}
  // 2. Сохраняем токены в localStorage
  // 3. Загружаем профиль /users/me/
  login: async (email: string, password: string) => {
    set({ isLoading: true })

    try {
      // Шаг 1: Получаем токены
      const { data: tokens } = await apiClient.post<AuthTokens>(
        API.auth.login,
        { email, password } as LoginRequest,
      )

      // Шаг 2: Сохраняем в localStorage
      localStorage.setItem('access_token', tokens.access)
      localStorage.setItem('refresh_token', tokens.refresh)

      // Шаг 3: Загружаем профиль
      await get().loadProfile()

    } catch (error) {
      // Очищаем токены при ошибке
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      set({ user: null, isAuthenticated: false, isLoading: false })
      throw error  // Пробрасываем ошибку в компонент (для показа сообщения)
    }
  },

  // ── РЕГИСТРАЦИЯ ──
  // 1. POST /auth/register/ {email, username, password, password_confirm}
  // 2. Автоматический вход после регистрации
  register: async (data: RegisterRequest) => {
    set({ isLoading: true })

    try {
      // Шаг 1: Регистрация
      await apiClient.post(API.auth.register, data)

      // Шаг 2: Автоматический вход
      await get().login(data.email, data.password)

    } catch (error) {
      set({ isLoading: false })
      throw error
    }
  },

  // ── ВЫХОД ──
  logout: () => {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    set({ user: null, isAuthenticated: false, isLoading: false })
    // Редирект делаем в компоненте, не в сторе
  },

  // ── ЗАГРУЗКА ПРОФИЛЯ ──
  // GET /users/me/ → {id, email, username, first_name, last_name}
  loadProfile: async () => {
    try {
      const { data: user } = await apiClient.get<User>(API.users.me)
      set({ user, isAuthenticated: true, isLoading: false })
    } catch {
      // Не удалось загрузить профиль → токен невалидный
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      set({ user: null, isAuthenticated: false, isLoading: false })
    }
  },

  // ── ИНИЦИАЛИЗАЦИЯ АВТОРИЗАЦИИ ──
  // Вызывается ОДИН раз при запуске приложения (в main.tsx).
  // Проверяет: есть ли access-токен в localStorage?
  //   Да → загружаем профиль (токен мог устареть — проверим)
  //   Нет → пользователь не залогинен
  initAuth: async () => {
    const accessToken = localStorage.getItem('access_token')

    if (!accessToken) {
      // Токена нет — пользователь не залогинен
      set({ user: null, isAuthenticated: false, isLoading: false })
      return
    }

    // Токен есть — пробуем загрузить профиль
    // Если токен устарел — axios-интерцептор попробует обновить его
    set({ isLoading: true })
    await get().loadProfile()
  },
}))
```

---

## 4.3. Разбор: КАК работает Zustand

Zustand — это **глобальное хранилище**, доступное из любого компонента:

```tsx
// Компонент А — читает состояние
function Header() {
  const user = useAuthStore(state => state.user)
  return <div>{user ? `Привет, ${user.username}` : 'Войдите'}</div>
}

// Компонент Б — вызывает действие
function LoginButton() {
  const login = useAuthStore(state => state.login)
  return <button onClick={() => login('email', 'pass')}>Войти</button>
}

// Компонент В — подписан ТОЛЬКО на isAuthenticated (оптимизация!)
function ProtectedRoute() {
  const isAuthenticated = useAuthStore(state => state.isAuthenticated)
  if (!isAuthenticated) return <Navigate to="/login" />
  return <Outlet />
}
```

**Почему `state => state.user`, а не `useAuthStore()`:**
- `useAuthStore()` — подписка на ВСЁ хранилище → ре-рендер при ЛЮБОМ изменении
- `useAuthStore(state => state.user)` — подписка ТОЛЬКО на user → ре-рендер только при изменении user

---

## 4.4. Инициализация авторизации при запуске — `src/main.tsx`

```tsx
// src/main.tsx
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App.tsx'
import './index.css'
import { useAuthStore } from './stores/auth-store'

// ── Инициализация авторизации ДО рендера ──
// Проверяем токен в localStorage и загружаем профиль.
// После этого React рендерит приложение с правильным состоянием.
const initApp = async () => {
  await useAuthStore.getState().initAuth()

  createRoot(document.getElementById('root')!).render(
    <StrictMode>
      <App />
    </StrictMode>,
  )
}

initApp()
```

**Что происходит при загрузке:**

```
1. Пользователь открывает localhost:5173
2. main.tsx: initAuth()
3. Проверяем localStorage: есть ли access_token?
   ├── НЕТ → isAuthenticated = false → показываем страницу как для гостя
   └── ДА → loadProfile()
       ├── GET /users/me/ с токеном → успешный ответ → user = {email, ...}
       │   └── isAuthenticated = true → показываем страницу как для пользователя
       └── 401 (токен устарел) → интерцептор обновляет → повторный запрос
           ├── Успешно → user загружен
           └── Неуспешно → logout → показываем как для гостя
4. React рендерит <App /> с актуальным состоянием
```

---

## 4.5. Хук `useAuth` — удобная обёртка

```ts
// src/hooks/use-auth.ts
// 🪝 Удобный хук для доступа к авторизации.
// Скрывает прямую работу с zustand-стором.

import { useAuthStore } from '../stores/auth-store'

export function useAuth() {
  const user = useAuthStore(state => state.user)
  const isAuthenticated = useAuthStore(state => state.isAuthenticated)
  const isLoading = useAuthStore(state => state.isLoading)
  const login = useAuthStore(state => state.login)
  const register = useAuthStore(state => state.register)
  const logout = useAuthStore(state => state.logout)

  return {
    user,
    isAuthenticated,
    isLoading,
    login,
    register,
    logout,
  }
}
```

Использование в компоненте:

```tsx
function Header() {
  const { user, isAuthenticated, logout } = useAuth()

  if (!isAuthenticated) {
    return <a href="/login">Войти</a>
  }

  return (
    <div>
      <span>{user?.username}</span>
      <button onClick={logout}>Выйти</button>
    </div>
  )
}
```

---

## 4.6. Полный цикл JWT-авторизации (схема)

```
┌──────────────────────────────────────────────────────────────┐
│                    РЕГИСТРАЦИЯ                               │
│                                                              │
│  React                        Django                         │
│  ─────                        ──────                         │
│  POST /auth/register/                                        │
│  {email, username, password,    ──────►  Создаёт User,       │
│   password_confirm}                      Profile, Cart       │
│                                          возвращает {id,...} │
│  ◄─────────────────────────────────────                      │
│                                                              │
│  Затем: POST /auth/login/ автоматически                      │
│  (см. ниже)                                                  │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│                    ВХОД                                      │
│                                                              │
│  React                        Django                         │
│  ─────                        ──────                         │
│  POST /auth/login/                                           │
│  {email, password}              ──────►  authenticate()      │
│                                          проверяет email+pwd │
│                                          генерирует JWT      │
│  ◄── {access: "eyJ...",      ──────────  возвращает токены   │
│       refresh: "eyJ..."}                                     │
│                                                              │
│  localStorage:                                               │
│    access_token  = "eyJ..."  (15 мин)                        │
│    refresh_token = "eyJ..."  (7 дней)                        │
│                                                              │
│  GET /users/me/                                              │
│  Authorization: Bearer eyJ...    ──────►  возвращает профиль │
│  ◄── {id, email, username}      ──────                       │
│                                                              │
│  Zustand store:                                              │
│    user = {id, email, username}                              │
│    isAuthenticated = true                                    │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│                 ОБНОВЛЕНИЕ ТОКЕНА                            │
│                                                              │
│  (происходит АВТОМАТИЧЕСКИ через axios-интерцептор)         │
│                                                              │
│  Любой API-запрос → 401 (токен истёк)                       │
│       ↓                                                      │
│  POST /auth/refresh/ {refresh: "eyJ..."}                     │
│       ↓                                                      │
│  Django: проверяет refresh-токен                             │
│       ├── Валидный → {access: "новый", refresh: "новый"}     │
│       │   ↓                                                  │
│       │   Сохраняем новые токены в localStorage              │
│       │   Повторяем оригинальный запрос с новым access       │
│       │                                                      │
│       └── Невалидный → logout → /login                       │
└──────────────────────────────────────────────────────────────┘
```

---

## 4.7. Сроки жизни JWT-токенов

| Токен | Срок | Где хранится | Зачем |
|-------|------|--------------|-------|
| **Access** | 15 минут | localStorage | Доступ к API (в заголовке каждого запроса) |
| **Refresh** | 7 дней | localStorage | Получить новый access-токен |

**Почему access живёт только 15 минут:**
- Если украдут access → злоумышленник имеет доступ 15 минут
- Если украдут refresh → 7 дней доступа (хуже!)
- Компромисс: короткий access = ограниченный ущерб

**Что происходит после 7 дней бездействия:**
1. Refresh-токен тоже истекает
2. Axios-интерцептор не может обновить access
3. Пользователь разлогинивается → редирект на `/login`

---

### ✅ Итог части 4

- [x] Zustand store для авторизации создан
- [x] `login()` — POST /auth/login/ + сохранение токенов + загрузка профиля
- [x] `register()` — POST /auth/register/ + автоматический вход
- [x] `logout()` — удаление токенов + очистка состояния
- [x] `initAuth()` — проверка токена при старте приложения
- [x] `loadProfile()` — GET /users/me/ для получения данных пользователя
- [x] `useAuth` хук — удобный доступ к состоянию авторизации
- [x] Понимание полного цикла JWT (login → access → 401 → refresh → retry)

**Далее: Часть 5 — React Router и макет приложения**
