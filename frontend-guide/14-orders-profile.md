# Шаг 14. Заказы + Личный кабинет

### `src/pages/OrderListPage.tsx`:

```typescript
// src/pages/OrderListPage.tsx
// Список заказов пользователя.

import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import api from '../api/client';
import { ORDER } from '../api/endpoints';

interface Order {
  id: number;
  order_number: string;
  status: string;
  total: string;
  subtotal: string;
  created_at: string;
  items_count: number;
}

const STATUS_LABELS: Record<string, { label: string; color: string }> = {
  PENDING:    { label: 'Ожидает',    color: '#ffa500' },
  CONFIRMED:  { label: 'Подтверждён', color: '#007185' },
  PROCESSING: { label: 'В обработке', color: '#0066cc' },
  SHIPPED:    { label: 'Отправлен',   color: '#6f42c1' },
  DELIVERED:  { label: 'Доставлен',   color: '#007600' },
  CANCELLED:  { label: 'Отменён',     color: '#c00' },
};

export function OrderListPage() {
  const [orders, setOrders] = useState<Order[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    fetchOrders();
  }, []);

  const fetchOrders = async () => {
    try {
      const { data } = await api.get(ORDER.LIST);
      setOrders(Array.isArray(data) ? data : data.results || []);
    } catch {
      console.error('Ошибка загрузки заказов');
    } finally {
      setIsLoading(false);
    }
  };

  if (isLoading) return <div>Загрузка...</div>;

  return (
    <div>
      <h1>📦 Мои заказы</h1>

      {orders.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '40px', color: '#888' }}>
          У вас пока нет заказов
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {orders.map(order => {
            const statusInfo = STATUS_LABELS[order.status] || { label: order.status, color: '#666' };
            return (
              <Link
                key={order.id}
                to={`/orders/${order.order_number}`}
                style={{
                  textDecoration: 'none',
                  color: 'inherit',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  padding: '16px',
                  border: '1px solid #eee',
                  borderRadius: '8px',
                }}
              >
                <div>
                  <div style={{ fontWeight: 'bold' }}>Заказ #{order.order_number}</div>
                  <div style={{ color: '#888', fontSize: '13px' }}>
                    {new Date(order.created_at).toLocaleDateString('ru-RU')}
                  </div>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                  <span style={{
                    padding: '4px 12px',
                    borderRadius: '12px',
                    background: `${statusInfo.color}20`,
                    color: statusInfo.color,
                    fontSize: '13px',
                    fontWeight: 'bold',
                  }}>
                    {statusInfo.label}
                  </span>
                  <span style={{ fontWeight: 'bold', fontSize: '18px' }}>{order.total} ₽</span>
                </div>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}
```

---

### `src/pages/OrderDetailPage.tsx`:

```typescript
// src/pages/OrderDetailPage.tsx
// Детали заказа: позиции, статус, доставка, оплата.

import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import api from '../api/client';
import { ORDER } from '../api/endpoints';

interface OrderItem {
  id: number;
  product_name: string;
  sku: string;
  unit_price: string;
  quantity: number;
  total_price: string;
}

interface Order {
  id: number;
  order_number: string;
  status: string;
  subtotal: string;
  delivery_cost: string;
  discount: string;
  total: string;
  created_at: string;
  items: OrderItem[];
  shipping_address: any;
}

const STATUS_LABELS: Record<string, { label: string; color: string }> = {
  PENDING:    { label: 'Ожидает',    color: '#ffa500' },
  CONFIRMED:  { label: 'Подтверждён', color: '#007185' },
  PROCESSING: { label: 'В обработке', color: '#0066cc' },
  SHIPPED:    { label: 'Отправлен',   color: '#6f42c1' },
  DELIVERED:  { label: 'Доставлен',   color: '#007600' },
  CANCELLED:  { label: 'Отменён',     color: '#c00' },
};

export function OrderDetailPage() {
  const { orderNumber } = useParams<{ orderNumber: string }>();
  const [order, setOrder] = useState<Order | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (orderNumber) fetchOrder();
  }, [orderNumber]);

  const fetchOrder = async () => {
    try {
      const { data } = await api.get(ORDER.DETAIL(orderNumber!));
      setOrder(data);
    } catch {
      console.error('Заказ не найден');
    } finally {
      setIsLoading(false);
    }
  };

  const handleCancel = async () => {
    if (!confirm('Вы уверены что хотите отменить заказ?')) return;
    try {
      await api.post(ORDER.CANCEL(orderNumber!));
      fetchOrder();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Не удалось отменить');
    }
  };

  if (isLoading) return <div>Загрузка...</div>;
  if (!order) return <div>Заказ не найден</div>;

  const statusInfo = STATUS_LABELS[order.status] || { label: order.status, color: '#666' };

  return (
    <div style={{ maxWidth: '700px', margin: '0 auto' }}>
      <Link to="/orders" style={{ color: '#007185', textDecoration: 'none' }}>← Мои заказы</Link>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '16px', marginBottom: '24px' }}>
        <h1>Заказ #{order.order_number}</h1>
        <span style={{
          padding: '6px 16px',
          borderRadius: '16px',
          background: `${statusInfo.color}20`,
          color: statusInfo.color,
          fontWeight: 'bold',
        }}>
          {statusInfo.label}
        </span>
      </div>

      <div style={{ color: '#888', fontSize: '13px', marginBottom: '16px' }}>
        {new Date(order.created_at).toLocaleString('ru-RU')}
      </div>

      {/* Товары */}
      <div style={{ border: '1px solid #eee', borderRadius: '8px', overflow: 'hidden', marginBottom: '24px' }}>
        {order.items.map(item => (
          <div key={item.id} style={{
            display: 'flex',
            justifyContent: 'space-between',
            padding: '12px 16px',
            borderBottom: '1px solid #eee',
          }}>
            <div>
              <div style={{ fontWeight: 'bold' }}>{item.product_name}</div>
              <div style={{ color: '#888', fontSize: '13px' }}>{item.sku} × {item.quantity}</div>
            </div>
            <div style={{ fontWeight: 'bold' }}>{item.total_price} ₽</div>
          </div>
        ))}
      </div>

      {/* Итого */}
      <div style={{ background: '#f9f9f9', padding: '16px', borderRadius: '8px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
          <span>Подытог:</span><span>{order.subtotal} ₽</span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
          <span>Доставка:</span><span>{order.delivery_cost} ₽</span>
        </div>
        {parseFloat(order.discount) > 0 && (
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px', color: '#007600' }}>
            <span>Скидка:</span><span>−{order.discount} ₽</span>
          </div>
        )}
        <div style={{ display: 'flex', justifyContent: 'space-between', fontWeight: 'bold', fontSize: '20px', borderTop: '1px solid #ddd', paddingTop: '8px', marginTop: '8px' }}>
          <span>Итого:</span><span>{order.total} ₽</span>
        </div>
      </div>

      {/* Кнопка отмены */}
      {['PENDING', 'CONFIRMED'].includes(order.status) && (
        <button
          onClick={handleCancel}
          style={{
            marginTop: '16px',
            padding: '10px 20px',
            background: 'white',
            border: '1px solid #c00',
            borderRadius: '4px',
            color: '#c00',
            cursor: 'pointer',
          }}
        >
          Отменить заказ
        </button>
      )}
    </div>
  );
}
```

---

### `src/pages/ProfilePage.tsx`:

```typescript
// src/pages/ProfilePage.tsx
// Личный кабинет: профиль + адреса.

import { useEffect, useState } from 'react';
import api from '../api/client';
import { USER } from '../api/endpoints';
import { useAuthStore } from '../stores/authStore';

interface Address {
  id: number;
  recipient_name: string;
  city: string;
  street: string;
  country: string;
  postal_code: string;
  is_default: boolean;
}

export function ProfilePage() {
  const { user, fetchUser } = useAuthStore();
  const [addresses, setAddresses] = useState<Address[]>([]);
  const [editData, setEditData] = useState({ first_name: '', last_name: '', phone: '' });
  const [isEditing, setIsEditing] = useState(false);
  const [showAddressForm, setShowAddressForm] = useState(false);
  const [newAddress, setNewAddress] = useState({ recipient_name: '', city: '', street: '', country: 'Россия', postal_code: '' });

  useEffect(() => {
    fetchAddresses();
    if (user) {
      setEditData({ first_name: user.first_name, last_name: user.last_name, phone: user.phone || '' });
    }
  }, [user]);

  const fetchAddresses = async () => {
    try {
      const { data } = await api.get(USER.ADDRESSES);
      setAddresses(Array.isArray(data) ? data : data.results || []);
    } catch {
      // Нет адресов
    }
  };

  const handleSaveProfile = async () => {
    try {
      await api.patch(USER.ME, editData);
      fetchUser();
      setIsEditing(false);
    } catch (err) {
      console.error('Ошибка сохранения:', err);
    }
  };

  const handleAddAddress = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.post(USER.ADDRESSES, newAddress);
      setShowAddressForm(false);
      setNewAddress({ recipient_name: '', city: '', street: '', country: 'Россия', postal_code: '' });
      fetchAddresses();
    } catch (err) {
      console.error('Ошибка добавления адреса:', err);
    }
  };

  const handleDeleteAddress = async (id: number) => {
    if (!confirm('Удалить адрес?')) return;
    try {
      await api.delete(USER.ADDRESS(id));
      fetchAddresses();
    } catch {
      // Ошибка удаления
    }
  };

  if (!user) return <div>Загрузка...</div>;

  return (
    <div style={{ maxWidth: '700px', margin: '0 auto' }}>
      {/* Профиль */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
        <h1>👤 Личный кабинет</h1>
        <button
          onClick={() => setIsEditing(!isEditing)}
          style={{ padding: '6px 12px', border: '1px solid #ccc', borderRadius: '4px', background: 'white', cursor: 'pointer' }}
        >
          {isEditing ? 'Отмена' : 'Редактировать'}
        </button>
      </div>

      <div style={{ background: '#f9f9f9', padding: '20px', borderRadius: '8px', marginBottom: '24px' }}>
        {isEditing ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <div>
              <label style={{ display: 'block', marginBottom: '4px', fontWeight: 'bold' }}>Имя</label>
              <input value={editData.first_name} onChange={e => setEditData({...editData, first_name: e.target.value})} style={{ width: '100%', padding: '8px', border: '1px solid #ccc', borderRadius: '4px', boxSizing: 'border-box' }} />
            </div>
            <div>
              <label style={{ display: 'block', marginBottom: '4px', fontWeight: 'bold' }}>Фамилия</label>
              <input value={editData.last_name} onChange={e => setEditData({...editData, last_name: e.target.value})} style={{ width: '100%', padding: '8px', border: '1px solid #ccc', borderRadius: '4px', boxSizing: 'border-box' }} />
            </div>
            <div>
              <label style={{ display: 'block', marginBottom: '4px', fontWeight: 'bold' }}>Телефон</label>
              <input value={editData.phone} onChange={e => setEditData({...editData, phone: e.target.value})} style={{ width: '100%', padding: '8px', border: '1px solid #ccc', borderRadius: '4px', boxSizing: 'border-box' }} />
            </div>
            <button onClick={handleSaveProfile} style={{ padding: '10px', background: '#ffa500', border: 'none', borderRadius: '4px', cursor: 'pointer', fontWeight: 'bold' }}>Сохранить</button>
          </div>
        ) : (
          <div>
            <div style={{ fontSize: '20px', fontWeight: 'bold', marginBottom: '8px' }}>{user.first_name} {user.last_name}</div>
            <div style={{ color: '#666' }}>📧 {user.email}</div>
            <div style={{ color: '#666' }}>👤 @{user.username}</div>
            {user.phone && <div style={{ color: '#666' }}>📱 {user.phone}</div>}
          </div>
        )}
      </div>

      {/* Адреса */}
      <div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
          <h2>📍 Адреса доставки</h2>
          <button
            onClick={() => setShowAddressForm(!showAddressForm)}
            style={{ padding: '6px 12px', background: '#ffa500', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
          >
            + Добавить
          </button>
        </div>

        {showAddressForm && (
          <form onSubmit={handleAddAddress} style={{ background: '#f9f9f9', padding: '16px', borderRadius: '8px', marginBottom: '12px' }}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
              <input placeholder="ФИО получателя" value={newAddress.recipient_name} onChange={e => setNewAddress({...newAddress, recipient_name: e.target.value})} required style={{ padding: '8px', border: '1px solid #ccc', borderRadius: '4px' }} />
              <input placeholder="Город" value={newAddress.city} onChange={e => setNewAddress({...newAddress, city: e.target.value})} required style={{ padding: '8px', border: '1px solid #ccc', borderRadius: '4px' }} />
              <input placeholder="Улица, дом, кв." value={newAddress.street} onChange={e => setNewAddress({...newAddress, street: e.target.value})} required style={{ padding: '8px', border: '1px solid #ccc', borderRadius: '4px' }} />
              <input placeholder="Почтовый индекс" value={newAddress.postal_code} onChange={e => setNewAddress({...newAddress, postal_code: e.target.value})} required style={{ padding: '8px', border: '1px solid #ccc', borderRadius: '4px' }} />
            </div>
            <button type="submit" style={{ marginTop: '12px', padding: '8px 16px', background: '#ffa500', border: 'none', borderRadius: '4px', cursor: 'pointer' }}>Сохранить адрес</button>
          </form>
        )}

        {addresses.length === 0 ? (
          <p style={{ color: '#888' }}>Нет сохранённых адресов</p>
        ) : (
          addresses.map(addr => (
            <div key={addr.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px', border: '1px solid #eee', borderRadius: '4px', marginBottom: '8px' }}>
              <div>
                <strong>{addr.recipient_name}</strong>
                {addr.is_default && <span style={{ color: '#007600', marginLeft: '8px', fontSize: '12px' }}>Основной</span>}
                <div style={{ color: '#666', fontSize: '14px' }}>{addr.city}, {addr.street}, {addr.postal_code}</div>
              </div>
              <button onClick={() => handleDeleteAddress(addr.id)} style={{ background: 'none', border: 'none', color: 'red', cursor: 'pointer' }}>Удалить</button>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
```

---

### Итог шага 14
✅ Список заказов со статусами
✅ Детали заказа с позициями
✅ Отмена заказа (если PENDING/CONFIRMED)
✅ Личный кабинет: редактирование профиля
✅ Управление адресами доставки

→ Переходи к шагу 15
