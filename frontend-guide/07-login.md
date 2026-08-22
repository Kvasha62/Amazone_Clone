# Шаг 7. Страница Login

Замени заглушку `src/pages/LoginPage.tsx`:

```typescript
// src/pages/LoginPage.tsx
// Форма входа: email + password → JWT-токены.

import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuthStore } from '../stores/authStore';

export function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const login = useAuthStore((s) => s.login);
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsSubmitting(true);

    try {
      await login(email, password);
      navigate('/');
    } catch (err: any) {
      const detail = err.response?.data?.detail || err.response?.data?.non_field_errors?.[0] || 'Ошибка входа';
      setError(detail);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div style={{ maxWidth: '400px', margin: '40px auto' }}>
      <h2>Вход</h2>

      {error && (
        <div style={{ background: '#ffe0e0', padding: '12px', borderRadius: '4px', marginBottom: '16px', color: '#c00' }}>
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit}>
        <div style={{ marginBottom: '12px' }}>
          <label style={{ display: 'block', marginBottom: '4px', fontWeight: 'bold' }}>
            Email
          </label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            style={{ width: '100%', padding: '10px', border: '1px solid #ccc', borderRadius: '4px', boxSizing: 'border-box' }}
            placeholder="ivan@example.com"
          />
        </div>

        <div style={{ marginBottom: '12px' }}>
          <label style={{ display: 'block', marginBottom: '4px', fontWeight: 'bold' }}>
            Пароль
          </label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            style={{ width: '100%', padding: '10px', border: '1px solid #ccc', borderRadius: '4px', boxSizing: 'border-box' }}
            placeholder="Введите пароль"
          />
        </div>

        <button
          type="submit"
          disabled={isSubmitting}
          style={{
            width: '100%',
            padding: '12px',
            background: isSubmitting ? '#ccc' : '#ffa500',
            border: 'none',
            borderRadius: '4px',
            fontSize: '16px',
            cursor: isSubmitting ? 'not-allowed' : 'pointer',
            fontWeight: 'bold',
          }}
        >
          {isSubmitting ? 'Входим...' : 'Войти'}
        </button>
      </form>

      <p style={{ marginTop: '16px', textAlign: 'center' }}>
        Нет аккаунта? <Link to="/register" style={{ color: '#007185' }}>Зарегистрироваться</Link>
      </p>
    </div>
  );
}
```

---

### Проверка

1. Запусти бэкенд: `python manage.py runserver`
2. Запусти фронтенд: `npm run dev`
3. Открой http://localhost:5173/login
4. Введи email и пароль пользователя (созданного через `createsuperuser`)
5. После входа должен редирект на главную, хедер покажет имя

---

### Итог шага 7
✅ Форма логина работает
✅ JWT-токены сохраняются в localStorage
✅ После входа — редирект на главную
✅ Ошибка показывается при неверных данных

→ Переходи к шагу 8
