# Шаг 13. Оформление заказа

Замени заглушку `src/pages/OrderCreatePage.tsx`:

```typescript
// src/pages/OrderCreatePage.tsx
// Создание заказа из корзины: адрес доставки, купон, подтверждение.

import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api/client';
import { ORDER, DISCOUNT, SHIPPING, CART, USER } from '../api/endpoints';
import { useCartStore } from '../stores/cartStore';

interface Address {
  id: number;
  recipient_name: string;
  city: string;
  street: string;
  country: string;
  postal_code: string;
  is_default: boolean;
}

interface ShippingMethod {
  id: number;
  name: string;
  price: string;
  estimated_days: string;
}

export function OrderCreatePage() {
  const { cart, fetchCart } = useCartStore();
  const navigate = useNavigate();

  const [addresses, setAddresses] = useState<Address[]>([]);
  const [selectedAddress, setSelectedAddress] = useState<number | null>(null);
  const [shippingMethods, setShippingMethods] = useState<ShippingMethod[]>([]);
  const [selectedShipping, setSelectedShipping] = useState<number | null>(null);
  const [couponCode, setCouponCode] = useState('');
  const [discount, setDiscount] = useState<number>(0);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!cart || cart.items.length === 0) {
      navigate('/cart');
      return;
    }
    fetchAddresses();
    fetchShippingMethods();
  }, [cart]);

  const fetchAddresses = async () => {
    try {
      const { data } = await api.get(USER.ADDRESSES);
      const addrList = Array.isArray(data) ? data : data.results || [];
      setAddresses(addrList);
      const defaultAddr = addrList.find((a: Address) => a.is_default);
      if (defaultAddr) setSelectedAddress(defaultAddr.id);
      else if (addrList.length > 0) setSelectedAddress(addrList[0].id);
    } catch {
      // Нет адресов — пользователь добавит
    }
  };

  const fetchShippingMethods = async () => {
    try {
      const { data } = await api.get(SHIPPING.METHODS);
      const methods = Array.isArray(data) ? data : data.results || [];
      setShippingMethods(methods);
      if (methods.length > 0) setSelectedShipping(methods[0].id);
    } catch {
      // Нет методов доставки
    }
  };

  const handleApplyCoupon = async () => {
    if (!couponCode.trim()) return;
    try {
      const { data } = await api.post(DISCOUNT.PREVIEW, { code: couponCode });
      setDiscount(parseFloat(data.discount_amount || '0'));
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Купон не найден');
      setCouponCode('');
      setDiscount(0);
    }
  };

  const handleSubmit = async () => {
    if (!selectedAddress) {
      setError('Выберите адрес доставки');
      return;
    }

    setIsSubmitting(true);
    setError('');

    try {
      // 1. Применяем купон если есть
      if (couponCode && discount > 0) {
        await api.post(DISCOUNT.APPLY, { code: couponCode });
      }

      // 2. Создаём заказ
      const { data } = await api.post(ORDER.CREATE, {
        address_id: selectedAddress,
        shipping_method_id: selectedShipping,
      });

      // 3. Очищаем корзину локально
      await fetchCart();

      // 4. Переходим на страницу заказа
      navigate(`/orders/${data.order_number}`);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.response?.data?.non_field_errors?.[0] || 'Ошибка создания заказа');
    } finally {
      setIsSubmitting(false);
    }
  };

  const subtotal = parseFloat(cart?.total || '0');
  const total = subtotal - discount;

  return (
    <div style={{ maxWidth: '800px', margin: '0 auto' }}>
      <h1>📋 Оформление заказа</h1>

      {error && (
        <div style={{ background: '#ffe0e0', padding: '12px', borderRadius: '4px', marginBottom: '16px', color: '#c00' }}>
          {error}
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 300px', gap: '24px' }}>
        {/* Левая колонка */}
        <div>
          {/* Адрес доставки */}
          <div style={{ marginBottom: '24px' }}>
            <h3>📍 Адрес доставки</h3>
            {addresses.length === 0 ? (
              <div style={{ padding: '16px', background: '#f5f5f5', borderRadius: '4px' }}>
                <p>У вас нет сохранённых адресов.</p>
                <Link to="/profile" style={{ color: '#007185' }}>Добавить адрес в личном кабинете →</Link>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {addresses.map(addr => (
                  <label key={addr.id} style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    padding: '12px',
                    border: selectedAddress === addr.id ? '2px solid #ffa500' : '1px solid #ddd',
                    borderRadius: '4px',
                    cursor: 'pointer',
                  }}>
                    <input
                      type="radio"
                      name="address"
                      checked={selectedAddress === addr.id}
                      onChange={() => setSelectedAddress(addr.id)}
                    />
                    <div>
                      <strong>{addr.recipient_name}</strong>
                      <div>{addr.city}, {addr.street}, {addr.postal_code}</div>
                    </div>
                  </label>
                ))}
              </div>
            )}
          </div>

          {/* Способ доставки */}
          {shippingMethods.length > 0 && (
            <div style={{ marginBottom: '24px' }}>
              <h3>🚚 Способ доставки</h3>
              {shippingMethods.map(method => (
                <label key={method.id} style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '12px',
                  border: selectedShipping === method.id ? '2px solid #ffa500' : '1px solid #ddd',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  marginBottom: '8px',
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <input
                      type="radio"
                      name="shipping"
                      checked={selectedShipping === method.id}
                      onChange={() => setSelectedShipping(method.id)}
                    />
                    <span>{method.name}</span>
                  </div>
                  <div>
                    <strong>{method.price} ₽</strong>
                    <span style={{ color: '#888', marginLeft: '8px', fontSize: '13px' }}>{method.estimated_days}</span>
                  </div>
                </label>
              ))}
            </div>
          )}

          {/* Купон */}
          <div style={{ marginBottom: '24px' }}>
            <h3>🏷️ Промокод</h3>
            <div style={{ display: 'flex', gap: '8px' }}>
              <input
                type="text"
                value={couponCode}
                onChange={(e) => setCouponCode(e.target.value)}
                placeholder="Введите код купона"
                style={{ flex: 1, padding: '10px', border: '1px solid #ccc', borderRadius: '4px' }}
              />
              <button
                onClick={handleApplyCoupon}
                style={{ padding: '10px 16px', border: '1px solid #ccc', borderRadius: '4px', background: 'white', cursor: 'pointer' }}
              >
                Применить
              </button>
            </div>
            {discount > 0 && (
              <div style={{ color: '#007600', marginTop: '8px' }}>
                ✓ Скидка: {discount} ₽
              </div>
            )}
          </div>
        </div>

        {/* Правая колонка — итого */}
        <div>
          <div style={{ background: '#f9f9f9', padding: '20px', borderRadius: '8px', position: 'sticky', top: '20px' }}>
            <h3>Ваш заказ</h3>

            {cart?.items.map(item => (
              <div key={item.id} style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: '1px solid #eee', fontSize: '14px' }}>
                <span>{item.product_name} × {item.quantity}</span>
                <span>{item.total_price} ₽</span>
              </div>
            ))}

            <div style={{ borderTop: '2px solid #333', marginTop: '12px', paddingTop: '12px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                <span>Подытог:</span>
                <span>{subtotal.toFixed(2)} ₽</span>
              </div>
              {discount > 0 && (
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px', color: '#007600' }}>
                  <span>Скидка:</span>
                  <span>−{discount.toFixed(2)} ₽</span>
                </div>
              )}
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '20px', fontWeight: 'bold', marginTop: '8px' }}>
                <span>Итого:</span>
                <span>{total.toFixed(2)} ₽</span>
              </div>
            </div>

            <button
              onClick={handleSubmit}
              disabled={isSubmitting || !selectedAddress}
              style={{
                width: '100%',
                padding: '14px',
                background: isSubmitting || !selectedAddress ? '#ccc' : '#ffa500',
                border: 'none',
                borderRadius: '4px',
                fontSize: '18px',
                cursor: isSubmitting || !selectedAddress ? 'not-allowed' : 'pointer',
                fontWeight: 'bold',
                marginTop: '16px',
              }}
            >
              {isSubmitting ? 'Оформляем...' : 'Разместить заказ'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
```

---

### Итог шага 13
✅ Оформление заказа: адрес + доставка + купон
✅ Создание заказа через API
✅ Редирект на страницу заказа

→ Переходи к шагу 14
