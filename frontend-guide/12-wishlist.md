# Шаг 12. Wishlist (Избранное)

Замени заглушку `src/pages/WishlistPage.tsx`:

```typescript
// src/pages/WishlistPage.tsx
// Избранные товары: список, переместить в корзину, удалить.

import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import api from '../api/client';
import { WISHLIST, CART } from '../api/endpoints';

interface WishlistItem {
  id: number;
  variant_id: number;
  product_name: string;
  sku: string;
  price: string;
  image: string | null;
  added_at: string;
}

interface Wishlist {
  id: number;
  items_count: number;
  items: WishlistItem[];
}

export function WishlistPage() {
  const [wishlist, setWishlist] = useState<Wishlist | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [movingId, setMovingId] = useState<number | null>(null);

  useEffect(() => {
    fetchWishlist();
  }, []);

  const fetchWishlist = async () => {
    setIsLoading(true);
    try {
      const { data } = await api.get(WISHLIST.DETAIL);
      setWishlist(data);
    } catch {
      console.error('Ошибка загрузки избранного');
    } finally {
      setIsLoading(false);
    }
  };

  const handleRemove = async (itemId: number) => {
    try {
      await api.delete(WISHLIST.REMOVE(itemId));
      fetchWishlist(); // Обновляем список
    } catch (err) {
      console.error('Ошибка удаления из избранного:', err);
    }
  };

  const handleMoveToCart = async (variantId: number) => {
    setMovingId(variantId);
    try {
      await api.post(WISHLIST.MOVE_TO_CART, { variant_id: variantId });
      fetchWishlist();
    } catch (err) {
      console.error('Ошибка перемещения в корзину:', err);
    } finally {
      setMovingId(null);
    }
  };

  if (isLoading) return <div>Загрузка...</div>;

  return (
    <div>
      <h1>❤️ Избранное ({wishlist?.items_count || 0})</h1>

      {!wishlist || wishlist.items.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '40px' }}>
          <p style={{ color: '#888', marginBottom: '16px' }}>Список избранного пуст</p>
          <Link to="/products">
            <button style={{
              padding: '12px 24px',
              background: '#ffa500',
              border: 'none',
              borderRadius: '4px',
              fontSize: '16px',
              cursor: 'pointer',
            }}>
              Перейти в каталог
            </button>
          </Link>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {wishlist.items.map(item => (
            <div key={item.id} style={{
              display: 'flex',
              alignItems: 'center',
              gap: '16px',
              padding: '16px',
              border: '1px solid #eee',
              borderRadius: '8px',
            }}>
              {/* Фото */}
              <div style={{
                width: '80px',
                height: '80px',
                background: '#f5f5f5',
                borderRadius: '4px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                overflow: 'hidden',
                flexShrink: 0,
              }}>
                {item.image ? (
                  <img src={item.image} alt="" style={{ maxWidth: '100%', maxHeight: '100%', objectFit: 'contain' }} />
                ) : (
                  <span style={{ fontSize: '32px' }}>📦</span>
                )}
              </div>

              {/* Информация */}
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 'bold' }}>{item.product_name}</div>
                <div style={{ color: '#888', fontSize: '13px' }}>Артикул: {item.sku}</div>
                <div style={{ color: '#c00', fontWeight: 'bold', marginTop: '4px' }}>{item.price} ₽</div>
              </div>

              {/* Действия */}
              <div style={{ display: 'flex', gap: '8px' }}>
                <button
                  onClick={() => handleMoveToCart(item.variant_id)}
                  disabled={movingId === item.variant_id}
                  style={{
                    padding: '8px 16px',
                    background: movingId === item.variant_id ? '#ccc' : '#ffa500',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: movingId === item.variant_id ? 'not-allowed' : 'pointer',
                  }}
                >
                  {movingId === item.variant_id ? '...' : '🛒 В корзину'}
                </button>
                <button
                  onClick={() => handleRemove(item.id)}
                  style={{
                    padding: '8px 16px',
                    border: '1px solid #ccc',
                    borderRadius: '4px',
                    background: 'white',
                    cursor: 'pointer',
                  }}
                >
                  ✕
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
```

---

### Итог шага 12
✅ Страница избранного
✅ Перемещение в корзину
✅ Удаление из избранного

→ Переходи к шагу 13
