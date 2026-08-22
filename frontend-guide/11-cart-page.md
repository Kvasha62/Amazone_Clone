# Шаг 11. Страница корзины

Замени заглушку `src/pages/CartPage.tsx`:

```typescript
// src/pages/CartPage.tsx
// Полная страница корзины: список товаров, изменение количества, итого.

import { useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useCartStore } from '../stores/cartStore';

export function CartPage() {
  const { cart, isLoading, fetchCart, updateItem, removeItem, clearCart } = useCartStore();
  const navigate = useNavigate();

  useEffect(() => {
    fetchCart();
  }, []);

  const handleQuantityChange = async (itemId: number, newQuantity: number) => {
    if (newQuantity < 1) return;
    try {
      await updateItem(itemId, newQuantity);
    } catch (err) {
      console.error('Ошибка обновления количества:', err);
    }
  };

  if (isLoading && !cart) return <div>Загрузка корзины...</div>;

  if (!cart || cart.items.length === 0) {
    return (
      <div style={{ textAlign: 'center', padding: '60px' }}>
        <h2>🛒 Корзина пуста</h2>
        <p style={{ color: '#888', marginBottom: '20px' }}>Добавьте товары из каталога</p>
        <Link to="/products">
          <button style={{
            padding: '12px 24px',
            background: '#ffa500',
            border: 'none',
            borderRadius: '4px',
            fontSize: '16px',
            cursor: 'pointer',
            fontWeight: 'bold',
          }}>
            Перейти в каталог
          </button>
        </Link>
      </div>
    );
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <h1>🛒 Корзина ({cart.total_quantity})</h1>
        <button
          onClick={clearCart}
          style={{ padding: '8px 16px', border: '1px solid #ccc', borderRadius: '4px', background: 'white', cursor: 'pointer' }}
        >
          Очистить корзину
        </button>
      </div>

      {/* Список товаров */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
        {cart.items.map(item => (
          <div key={item.id} style={{
            display: 'flex',
            alignItems: 'center',
            gap: '16px',
            padding: '16px',
            border: '1px solid #eee',
            borderRadius: '8px',
          }}>
            {/* Информация */}
            <div style={{ flex: 1 }}>
              <div style={{ fontWeight: 'bold', fontSize: '16px' }}>{item.product_name}</div>
              <div style={{ color: '#888', fontSize: '13px' }}>Артикул: {item.sku}</div>
              <div style={{ color: '#c00', marginTop: '4px' }}>{item.price} ₽ за шт.</div>
            </div>

            {/* Количество */}
            <div style={{ display: 'flex', alignItems: 'center', border: '1px solid #ddd', borderRadius: '4px' }}>
              <button
                onClick={() => handleQuantityChange(item.id, item.quantity - 1)}
                disabled={item.quantity <= 1}
                style={{ padding: '6px 10px', border: 'none', background: 'none', cursor: 'pointer', fontSize: '16px' }}
              >
                −
              </button>
              <span style={{ padding: '6px 12px', minWidth: '30px', textAlign: 'center' }}>{item.quantity}</span>
              <button
                onClick={() => handleQuantityChange(item.id, item.quantity + 1)}
                style={{ padding: '6px 10px', border: 'none', background: 'none', cursor: 'pointer', fontSize: '16px' }}
              >
                +
              </button>
            </div>

            {/* Итого за позицию */}
            <div style={{ fontWeight: 'bold', fontSize: '18px', minWidth: '100px', textAlign: 'right' }}>
              {item.total_price} ₽
            </div>

            {/* Удалить */}
            <button
              onClick={() => removeItem(item.id)}
              style={{ background: 'none', border: 'none', color: 'red', cursor: 'pointer', fontSize: '20px' }}
            >
              ✕
            </button>
          </div>
        ))}
      </div>

      {/* Итого */}
      <div style={{
        marginTop: '24px',
        padding: '20px',
        background: '#f9f9f9',
        borderRadius: '8px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
      }}>
        <div>
          <div style={{ fontSize: '14px', color: '#666' }}>Товаров: {cart.total_quantity}</div>
          <div style={{ fontSize: '24px', fontWeight: 'bold' }}>Итого: {cart.total} ₽</div>
        </div>

        <button
          onClick={() => navigate('/checkout')}
          style={{
            padding: '14px 32px',
            background: '#ffa500',
            border: 'none',
            borderRadius: '4px',
            fontSize: '18px',
            cursor: 'pointer',
            fontWeight: 'bold',
          }}
        >
          Оформить заказ →
        </button>
      </div>
    </div>
  );
}
```

---

### Итог шага 11
✅ Полная страница корзины
✅ Изменение количества +/-
✅ Удаление позиции
✅ Кнопка «Оформить заказ»
✅ Пустая корзина с кнопкой в каталог

→ Переходи к шагу 12
