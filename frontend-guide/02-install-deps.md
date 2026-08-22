# Шаг 2. Установка зависимостей

В папке `frontend`:

```bash
npm install axios react-router-dom zustand
```

Что это:

| Пакет | Зачем |
|-------|-------|
| `axios` | HTTP-запросы к бэкенду + JWT-интерцепторы |
| `react-router-dom` | Навигация между страницами (SPA) |
| `zustand` | Глобальное состояние (пользователь, корзина) |

---

### Настройка Vite proxy (чтобы не писать localhost:8000 в каждом запросе)

Замени содержимое `vite.config.ts`:

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      // Все запросы /api/* → пересылаются на Django
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      // Media-файлы (картинки товаров)
      '/media': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
```

Теперь вместо `http://localhost:8000/api/v1/...` можно писать просто `/api/v1/...`
и Vite сам пересылает запрос на Django.

---

### Итог шага 2
✅ Зависимости установлены
✅ Vite proxy настроен на Django

→ Переходи к шагу 3
