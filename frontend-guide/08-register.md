# Шаг 8. Страница Register

Замени заглушку `src/pages/RegisterPage.tsx`:

```typescript
// src/pages/RegisterPage.tsx
// Форма регистрации: email + username + пароль + подтверждение.

import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuthStore } from '../stores/authStore';

export function RegisterPage() {
  const [form, setForm] = useState({
    email: '',
    username: '',
    first_name: '',
    last_name: '',
    password: '',
    password_confirm: '',
  });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const register = useAuthStore((s) => s.register);
  const navigate = useNavigate();

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setForm({ ...form, [e.target.name]: e.target.value });
    // Убираем ошибку при вводе
    if (errors[e.target.name]) {
      setErrors({ ...errors, [e.target.name]: '' });
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrors({});
    setIsSubmitting(true);

    try {
      await register(form);
      navigate('/');
    } catch (err: any) {
      const data = err.response?.data;
      if (typeof data === 'object') {
        // Django возвращает ошибки по полям: {email: ["..."], password: ["..."]}
        const fieldErrors: Record<string, string> = {};
        for (const [field, messages] of Object.entries(data)) {
          if (Array.isArray(messages)) {
            fieldErrors[field] = messages[0];
          } else if (typeof messages === 'string') {
            fieldErrors[field] = messages;
          }
        }
        setErrors(fieldErrors);
      } else {
        setErrors({ non_field: 'Ошибка регистрации' });
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const inputStyle = {
    width: '100%',
    padding: '10px',
    border: '1px solid #ccc',
    borderRadius: '4px',
    boxSizing: 'border-box' as const,
  };

  const labelStyle = { display: 'block', marginBottom: '4px', fontWeight: 'bold' as const };

  return (
    <div style={{ maxWidth: '400px', margin: '40px auto' }}>
      <h2>Регистрация</h2>

      {errors.non_field && (
        <div style={{ background: '#ffe0e0', padding: '12px', borderRadius: '4px', marginBottom: '16px', color: '#c00' }}>
          {errors.non_field}
        </div>
      )}

      <form onSubmit={handleSubmit}>
        <div style={{ marginBottom: '12px' }}>
          <label style={labelStyle}>Email *</label>
          <input type="email" name="email" value={form.email} onChange={handleChange} required style={inputStyle} />
          {errors.email && <div style={{ color: '#c00', fontSize: '13px' }}>{errors.email}</div>}
        </div>

        <div style={{ marginBottom: '12px' }}>
          <label style={labelStyle}>Имя пользователя *</label>
          <input type="text" name="username" value={form.username} onChange={handleChange} required style={inputStyle} />
          {errors.username && <div style={{ color: '#c00', fontSize: '13px' }}>{errors.username}</div>}
        </div>

        <div style={{ display: 'flex', gap: '12px', marginBottom: '12px' }}>
          <div style={{ flex: 1 }}>
            <label style={labelStyle}>Имя</label>
            <input type="text" name="first_name" value={form.first_name} onChange={handleChange} style={inputStyle} />
          </div>
          <div style={{ flex: 1 }}>
            <label style={labelStyle}>Фамилия</label>
            <input type="text" name="last_name" value={form.last_name} onChange={handleChange} style={inputStyle} />
          </div>
        </div>

        <div style={{ marginBottom: '12px' }}>
          <label style={labelStyle}>Пароль *</label>
          <input type="password" name="password" value={form.password} onChange={handleChange} required style={inputStyle} />
          {errors.password && <div style={{ color: '#c00', fontSize: '13px' }}>{errors.password}</div>}
        </div>

        <div style={{ marginBottom: '12px' }}>
          <label style={labelStyle}>Подтвердите пароль *</label>
          <input type="password" name="password_confirm" value={form.password_confirm} onChange={handleChange} required style={inputStyle} />
          {errors.password_confirm && <div style={{ color: '#c00', fontSize: '13px' }}>{errors.password_confirm}</div>}
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
          {isSubmitting ? 'Регистрация...' : 'Зарегистрироваться'}
        </button>
      </form>

      <p style={{ marginTop: '16px', textAlign: 'center' }}>
        Уже есть аккаунт? <Link to="/login" style={{ color: '#007185' }}>Войти</Link>
      </p>
    </div>
  );
}
```

---

### Итог шага 8
✅ Форма регистрации работает
✅ После регистрации — автоматический логин + редирект
✅ Ошибки по полям показываются

→ Переходи к шагу 9
