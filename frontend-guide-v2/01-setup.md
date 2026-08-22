# ЧАСТЬ 1. Подготовка окружения и создание React-проекта

> **Цель:** Рядом с Django-проектом появится папка `frontend/` с работающим React-приложением, которое открывается на `http://localhost:5173`.

---

## 1.1. Структура папок — КАК всё будет расположено

```
I:\NewPythonProjects\Amazone_Clone\     ← ТВОЯ ПАПКА ПРОЕКТА
├── .venv\                               ← Python-окружение Django
├── apps\                                ← Django-приложения
├── config\                              ← Django-настройки
├── manage.py
├── frontend\                            ← ⭐ РЕАКТ БУДЕТ ЗДЕСЬ
│   ├── src\
│   ├── public\
│   ├── package.json
│   └── ...
└── .env
```

**Почему РЯДОМ, а НЕ ВНУТРИ Django?**
- Django и React — два **отдельных** приложения
- Django = бэкенд (порт 8000), React = фронтенд (порт 5173)
- Они общаются по HTTP (fetch/axios), не через файловую систему
- Каждый имеет свой `package.json` / `requirements.txt`
- Размещение рядом = чистое разделение ответственности

---

## 1.2. Проверка: что уже готово на бэкенде

Перед началом УБЕДИСЬ что Django-сервер работает:

```bash
cd I:\NewPythonProjects\Amazone_Clone
.venv\Scripts\activate
python manage.py runserver
```

Открой в браузере:
- `http://localhost:8000/api/v1/health/` → должен вернуть `{"status": "ok"}`
- `http://localhost:8000/admin/` → должна открыться админка
- `http://localhost:8000/api/v1/docs/` → Swagger UI

Если всё ок — бэкенд готов к подключению React.

---

## 1.3. Установка Node.js

React требует Node.js. Проверь, установлен ли он:

```bash
node --version
```

Если команда не найдена — скачай и установи:
1. Иди на https://nodejs.org/
2. Скачай **LTS-версию** (рекомендуемую, не Current)
3. Установи — все галочки по умолчанию
4. Перезапусти терминал
5. Проверь:

```bash
node --version     # → v20.x.x или v22.x.x
npm --version      # → 10.x.x
```

---

## 1.4. Создание React-проекта через Vite

**Почему Vite, а не Create React App (CRA)?**
- CRA — **устарел** (официально deprecated с 2023 года)
- Vite — в 10-30 раз быстрее при сборке
- Vite — стандарт индустрии в 2026 году
- У Vite мгновенный Hot Module Replacement (HMR) — изменения видны за 50мс

Открой **НОВЫЙ терминал** (Django-сервер пусть работает в первом):

```bash
cd I:\NewPythonProjects
npm create vite@latest frontend -- --template react-ts
```

Разбор команды:
- `npm create vite@latest` — запуск инструмента создания проекта
- `frontend` — имя папки (можешь назвать как хочешь)
- `--template react-ts` — шаблон React + TypeScript

**Почему TypeScript?**
- Ловит ошибки ДО запуска (в редакторе)
- Автодополнение для API-ответов
- Индустриальный стандарт в 2026 году
- Без TS: `user.nme` → undefined в рантайме
- С TS: `user.nme` → красная волна в редакторе СРАЗУ

---

## 1.5. Установка зависимостей

```bash
cd I:\NewPythonProjects\frontend
npm install
```

Эта команда:
1. Читает `package.json`
2. Скачивает все пакеты в `node_modules/`
3. Создаёт `package-lock.json` (точные версии)

---

## 1.6. Запуск React

```bash
npm run dev
```

В терминале появится:

```
  VITE v6.x.x  ready in 300 ms

  ➜  Local:   http://localhost:5173/
  ➜  Network: http://192.168.x.x:5173/
```

Открой `http://localhost:5173` — увидишь страницу Vite + React с логотипом.

**Останови сервер:** Ctrl+C в терминале

---

## 1.7. Что создал Vite — обзор файлов

```
frontend/
├── index.html              ← HTML-шаблон (единственная HTML-страница!)
├── package.json            ← Зависимости и скрипты
├── tsconfig.json           ← Настройки TypeScript
├── vite.config.ts          ← Настройки Vite
├── public/
│   └── vite.svg            ← Статические файлы (копируются как есть)
└── src/
    ├── main.tsx            ← ТОЧКА ВХОДА — React монтируется сюда
    ├── App.tsx             ← Корневой компонент
    ├── App.css             ← Стили корневого компонента
    ├── index.css           ← Глобальные стили
    └── vite-env.d.ts       ← Типы для Vite
```

**Как это работает (цепочка запуска):**

```
1. index.html ← Vite отдаёт этот файл браузеру
2. <script type="module" src="/src/main.tsx"> ← браузер загружает
3. main.tsx:   ReactDOM.createRoot(...).render(<App />) ← React рендерит
4. App.tsx:    return <h1>Hello</h1> ← компонент отрисовывается
```

**Ключевое отличие от Django:**
- Django: каждый URL → отдельная HTML-страница (server-side rendering)
- React: ОДНА HTML-страница (index.html), всё остальное — JavaScript меняет DOM

Это называется **SPA** (Single Page Application).

---

## 1.8. Скрипты в package.json

```json
{
  "scripts": {
    "dev":      "vite",           // ← Запуск dev-сервера (порт 5173)
    "build":    "tsc && vite build",  // ← Сборка для production
    "preview":  "vite preview"    // ← Превью production-сборки
  }
}
```

- `npm run dev` — разработка (живой сервер, HMR)
- `npm run build` — сборка → папка `dist/` (готовые HTML+JS+CSS)
- `npm run preview` — превью того, что получится в production

---

## 1.9. Проверка: два сервера работают одновременно

Теперь у тебя работает **два сервера**:

| Сервер | Порт | Технология | Назначение |
|--------|------|------------|------------|
| Django | 8000 | Python | API (JSON-данные) |
| Vite | 5173 | Node.js | React (HTML+JS+CSS) |

```bash
# Терминал 1 — Django
cd I:\NewPythonProjects\Amazone_Clone
.venv\Scripts\activate
python manage.py runserver

# Терминал 2 — React
cd I:\NewPythonProjects\frontend
npm run dev
```

Проверь:
- `http://localhost:8000/api/v1/health/` → JSON от Django ✅
- `http://localhost:5173` → React-страница ✅

---

## 1.10. Почему React НЕ может получить данные от Django ПРЯМО СЕЙЧАС

Попробуй открыть в React файл `src/App.tsx` и добавить:

```tsx
// ПОПЫТКА 1 — НЕ СРАБОТАЕТ (пока)
useEffect(() => {
  fetch('http://localhost:8000/api/v1/health/')
    .then(r => r.json())
    .then(data => console.log(data))
    .catch(err => console.error(err));
}, []);
```

Результат в консоли браузера:
```
Access to fetch at 'http://localhost:8000/api/v1/health/' from origin
'http://localhost:5173' has been blocked by CORS policy
```

**Почему?** Браузер запрещает кросс-доменные запросы из соображений безопасности:
- React работает на `localhost:5173` (origin)
- Django работает на `localhost:8000` (другой origin)
- Разные порты = разные origins = **CORS блокировка**

**НО!** Мы уже настроили CORS на бэкенде в `config/settings.py`:
```python
CORS_ALLOW_ALL_ORIGINS = True  # В DEBUG-режиме
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",  # ← Vite!
]
```

Значит, если Django-сервер запущен с `DEBUG=True` (по умолчанию), CORS **уже работает**. Ошибка выше возникнет только если Django не запущен.

---

### ✅ Итог части 1

- [x] Node.js установлен
- [x] React-проект создан через Vite
- [x] `npm run dev` запускает React на порту 5173
- [x] Django работает на порту 8000
- [x] CORS настроен — React может делать запросы к Django
- [x] Понимание: SPA = одна HTML-страница, всё остальное — JavaScript

**Далее: Часть 2 — Установка зависимостей и настройка проекта**
