# ЧАСТЬ 6. Страницы входа и регистрации

> **Цель:** Полностью рабочие формы логина и регистрации, которые общаются с Django API.

---

## 6.1. Файл `src/pages/login-page.tsx` — ПОЛНЫЙ код

```tsx
// src/pages/login-page.tsx
// 🔐 Страница входа: email + пароль → JWT-токены.

import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/use-auth'

export default function LoginPage() {
  const navigate = useNavigate()
  const { login } = useAuth()

  // ── Состояние формы ──
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)

  // ── Обработка отправки формы ──
  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()          // Не перезагружать страницу!
    setError(null)              // Сбросить предыдущую ошибку
    setIsLoading(true)

    try {
      // login() внутри:
      // 1. POST /api/v1/auth/login/ {email, password}
      // 2. Сохраняет access + refresh в localStorage
      // 3. GET /api/v1/users/me/ → загружает профиль
      await login(email, password)

      // Успешный вход → на главную
      navigate('/')
    } catch (err: unknown) {
      // Django возвращает ошибки в формате:
      // { detail: "Неверные учётные данные" }          → 401
      // { email: ["Обязательное поле"] }               → 400
      const axiosErr = err as { response?: { data?: Record<string, string | string[]> } }
      if (axiosErr.response?.data) {
        const data = axiosErr.response.data

        // Одиночная ошибка (detail)
        if (data.detail) {
          setError(data.detail as string)
        }
        // Ошибки по полям (email, password)
        else {
          const messages = Object.values(data).flat().join(' ')
          setError(messages)
        }
      } else {
        setError('Не удалось подключиться к серверу')
      }
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-100">
      <div className="bg-white p-8 rounded-xl shadow-lg w-full max-w-md">

        {/* Заголовок */}
        <h1 className="text-2xl font-bold text-center mb-6">
          Вход в аккаунт
        </h1>

        {/* Ошибка */}
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-4">
            {error}
          </div>
        )}

        {/* Форма */}
        <form onSubmit={handleSubmit} className="space-y-4">

          {/* Email */}
          <div>
            <label
              htmlFor="email"
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              Email
            </label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="w-full px-4 py-2 border border-gray-300 rounded-lg
                         focus:ring-2 focus:ring-orange-500 focus:border-orange-500
                         outline-none transition"
              placeholder="you@example.com"
            />
          </div>

          {/* Пароль */}
          <div>
            <label
              htmlFor="password"
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              Пароль
            </label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="w-full px-4 py-2 border border-gray-300 rounded-lg
                         focus:ring-2 focus:ring-orange-500 focus:border-orange-500
                         outline-none transition"
              placeholder="••••••••"
            />
          </div>

          {/* Кнопка */}
          <button
            type="submit"
            disabled={isLoading}
            className="w-full bg-orange-500 hover:bg-orange-600 disabled:bg-orange-300
                       text-white font-semibold py-3 rounded-lg transition"
          >
            {isLoading ? 'Входим...' : 'Войти'}
          </button>
        </form>

        {/* Ссылка на регистрацию */}
        <p className="text-center text-gray-500 mt-6">
          Нет аккаунта?{' '}
          <Link to="/register" className="text-orange-500 hover:underline">
            Зарегистрируйтесь
          </Link>
        </p>
      </div>
    </div>
  )
}
```

---

## 6.2. Разбор: КАК работает форма входа

### Шаг за шагом:

```
1. Пользователь вводит email + пароль
2. Нажимает «Войти» → handleSubmit()
3. e.preventDefault()         ← НЕ перезагружать страницу!
4. login(email, password)     ← вызов zustand-действия
5. Внутри login():
   a. POST /api/v1/auth/login/ { email, password }
   b. Django: authenticate(email=..., password=...)
      ├── Успешно → { access: "eyJ...", refresh: "eyJ..." }
      └── Неуспешно → 401 { detail: "Неверные учётные данные" }
   c. При успехе: localStorage.setItem('access_token', ...)
   d. loadProfile() → GET /api/v1/users/me/
6. navigate('/')              ← перейти на главную
```

### Обработка ошибок:

Django может вернуть ошибки в ДВУХ форматах:

```json
// 401 — неверные учётные данные
{ "detail": "Неверные учётные данные." }

// 400 — пустое поле, невалидный email и т.д.
{ "email": ["Обязательное поле."], "password": ["Обязательное поле."] }
```

Код обрабатывает оба:
```tsx
if (data.detail) {
  setError(data.detail)           // Одиночная ошибка
} else {
  const messages = Object.values(data).flat().join(' ')
  setError(messages)              // Ошибки по полям → одна строка
}
```

---

## 6.3. Файл `src/pages/register-page.tsx` — ПОЛНЫЙ код

```tsx
// src/pages/register-page.tsx
// 📝 Страница регистрации: email + username + пароль + подтверждение.

import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/use-auth'
import type { RegisterRequest } from '../api/types'

// Утилита: извлечь текст ошибки из ответа Django
function getErrorMessage(data: Record<string, string | string[]>): string {
  if (data.detail) return data.detail as string
  return Object.entries(data)
    .map(([field, messages]) => {
      const label = field === 'password_confirm' ? 'Подтверждение пароля'
                  : field === 'email' ? 'Email'
                  : field === 'username' ? 'Имя пользователя'
                  : field === 'password' ? 'Пароль'
                  : field
      return `${label}: ${(Array.isArray(messages) ? messages : [messages]).join(', ')}`
    })
    .join('; ')
}

export default function RegisterPage() {
  const navigate = useNavigate()
  const { register } = useAuth()

  // ── Состояние формы ──
  const [form, setForm] = useState({
    email: '',
    username: '',
    password: '',
    password_confirm: '',
  })
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)

  // ── Обновление полей ──
  const handleChange = (field: keyof typeof form, value: string) => {
    setForm(prev => ({ ...prev, [field]: value }))
  }

  // ── Обработка отправки ──
  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError(null)
    setIsLoading(true)

    // Клиентская валидация: пароли совпадают?
    if (form.password !== form.password_confirm) {
      setError('Пароли не совпадают')
      setIsLoading(false)
      return
    }

    try {
      // register() внутри:
      // 1. POST /api/v1/auth/register/ {email, username, password, password_confirm}
      // 2. Автоматический login()
      await register(form as RegisterRequest)
      navigate('/')
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: Record<string, string | string[]> } }
      if (axiosErr.response?.data) {
        setError(getErrorMessage(axiosErr.response.data))
      } else {
        setError('Не удалось подключиться к серверу')
      }
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-100">
      <div className="bg-white p-8 rounded-xl shadow-lg w-full max-w-md">

        <h1 className="text-2xl font-bold text-center mb-6">
          Создать аккаунт
        </h1>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-4">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">

          {/* Email */}
          <div>
            <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1">
              Email
            </label>
            <input
              id="email"
              type="email"
              value={form.email}
              onChange={(e) => handleChange('email', e.target.value)}
              required
              className="w-full px-4 py-2 border border-gray-300 rounded-lg
                         focus:ring-2 focus:ring-orange-500 focus:border-orange-500
                         outline-none transition"
            />
          </div>

          {/* Username */}
          <div>
            <label htmlFor="username" className="block text-sm font-medium text-gray-700 mb-1">
              Имя пользователя
            </label>
            <input
              id="username"
              type="text"
              value={form.username}
              onChange={(e) => handleChange('username', e.target.value)}
              required
              className="w-full px-4 py-2 border border-gray-300 rounded-lg
                         focus:ring-2 focus:ring-orange-500 focus:border-orange-500
                         outline-none transition"
            />
          </div>

          {/* Пароль */}
          <div>
            <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-1">
              Пароль
            </label>
            <input
              id="password"
              type="password"
              value={form.password}
              onChange={(e) => handleChange('password', e.target.value)}
              required
              minLength={8}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg
                         focus:ring-2 focus:ring-orange-500 focus:border-orange-500
                         outline-none transition"
            />
          </div>

          {/* Подтверждение пароля */}
          <div>
            <label htmlFor="password_confirm" className="block text-sm font-medium text-gray-700 mb-1">
              Подтвердите пароль
            </label>
            <input
              id="password_confirm"
              type="password"
              value={form.password_confirm}
              onChange={(e) => handleChange('password_confirm', e.target.value)}
              required
              minLength={8}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg
                         focus:ring-2 focus:ring-orange-500 focus:border-orange-500
                         outline-none transition"
            />
          </div>

          {/* Кнопка */}
          <button
            type="submit"
            disabled={isLoading}
            className="w-full bg-orange-500 hover:bg-orange-600 disabled:bg-orange-300
                       text-white font-semibold py-3 rounded-lg transition"
          >
            {isLoading ? 'Создаю аккаунт...' : 'Зарегистрироваться'}
          </button>
        </form>

        <p className="text-center text-gray-500 mt-6">
          Уже есть аккаунт?{' '}
          <Link to="/login" className="text-orange-500 hover:underline">
            Войдите
          </Link>
        </p>
      </div>
    </div>
  )
}
```

---

## 6.4. Полный цикл регистрации — что происходит

```
Пользователь вводит:                           Django получает:
────────────────────                           ─────────────────

email:        ivan@mail.ru         ──────►     email
username:     ivan2026             ──────►     username
password:     ••••••••             ──────►     password
password_confirm: ••••••••         ──────►     password_confirm

                                               ↓ Django проверяет:
                                               • email уникален?
                                               • username уникален?
                                               • password == password_confirm?
                                               • password >= 8 символов?

                                               ↓ Создаёт:
                                               User(email, username)
                                               Profile(user)
                                               Cart(user)

                                               ↓ Возвращает:
                                               { id, email, username }

                                               ↓ Автоматический login():
                                               POST /auth/login/ { email, password }
                                               → { access, refresh }
                                               → localStorage
                                               → GET /users/me/
                                               → Zustand: user = { id, email, username }
                                               → navigate('/')
```

---

## 6.5. Проверка: протестируй вход и регистрацию

1. Запусти Django: `python manage.py runserver`
2. Запусти React: `npm run dev`
3. Открой `http://localhost:5173/register`
4. Заполни форму → нажми «Зарегистрироваться»
5. После успеха → перенаправление на главную, в шапке видно «👤 ivan2026»
6. Нажми «Выйти»
7. Перейди на `/login`
8. Введи email + пароль → нажми «Войти»
9. После успеха → главная с именем в шапке

**Отладка:**
- Открой DevTools (F12) → вкладка Network → увидишь все API-запросы
- Вкладка Console → ошибки JavaScript
- Вкладка Application → Local Storage → `access_token`, `refresh_token`

---

## 6.6. Частые проблемы и решения

| Проблема | Причина | Решение |
|----------|---------|---------|
| `Network Error` | Django не запущен | `python manage.py runserver` |
| `401 Unauthorized` | Токен истёк | Интерцептор обновит автоматически |
| `400 Bad Request` | Неверные данные | Проверь `error` в форме |
| `CORS error` | Vite Proxy не настроен | Проверь `vite.config.ts` |
| Пустая страница | Ошибка в `main.tsx` | Открой Console → читай ошибку |
| Редирект на /login после обновления | `initAuth()` не вызван | Проверь `main.tsx` |

---

### ✅ Итог части 6

- [x] Страница входа с email + пароль
- [x] Страница регистрации с 4 полями
- [x] Обработка ошибок Django (400 и 401)
- [x] Клиентская валидация (пароли совпадают)
- [x] Автоматический вход после регистрации
- [x] После входа → редирект на главную
- [x] Шапка показывает username / кнопку «Войти»

**Далее: Часть 7 — Каталог товаров и карточка товара**
