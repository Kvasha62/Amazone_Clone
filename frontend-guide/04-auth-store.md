# Шаг 4. Auth Store (Zustand)

Создай файл `src/stores/authStore.ts`:

```typescript
// src/stores/authStore.ts
// Глобальное хранилище пользователя.
// Zustand — простой state manager (замена Redux/Context).

import { create } from 'zustand';
import api from '../api/client';
import { AUTH, USER } from '../api/endpoints';

// ── Типы ──

interface UserProfile {
  timezone: string;
  language: string;
  avatar: string | null;
}

interface User {
  id: number;
  email: string;
  username: string;
  first_name: string;
  last_name: string;
  phone: string;
  profile: UserProfile | null;
}

interface AuthState {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;

  // Действия
  login: (email: string, password: string) => Promise<void>;
  register: (data: RegisterData) => Promise<void>;
  logout: () => void;
  fetchUser: () => Promise<void>;
}

interface RegisterData {
  email: string;
  username: string;
  password: string;
  password_confirm: string;
  first_name?: string;
  last_name?: string;
}

// ── Store ──

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isLoading: true,
  isAuthenticated: false,

  login: async (email, password) => {
    const { data } = await api.post(AUTH.LOGIN, { email, password });

    // Сохраняем токены
    localStorage.setItem('access_token', data.access);
    localStorage.setItem('refresh_token', data.refresh);

    // Получаем профиль пользователя
    const { data: user } = await api.get(USER.ME);

    set({
      user,
      isAuthenticated: true,
      isLoading: false,
    });
  },

  register: async (registerData) => {
    await api.post(AUTH.REGISTER, registerData);
    // После регистрации автоматически логиним
    await useAuthStore.getState().login(registerData.email, registerData.password);
  },

  logout: () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    set({
      user: null,
      isAuthenticated: false,
      isLoading: false,
    });
  },

  fetchUser: async () => {
    const token = localStorage.getItem('access_token');
    if (!token) {
      set({ isLoading: false });
      return;
    }

    try {
      const { data } = await api.get(USER.ME);
      set({
        user: data,
        isAuthenticated: true,
        isLoading: false,
      });
    } catch {
      // Токен невалидный
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      set({
        user: null,
        isAuthenticated: false,
        isLoading: false,
      });
    }
  },
}));
```

---

### Создай файл `src/stores/cartStore.ts`:

```typescript
// src/stores/cartStore.ts
// Глобальное хранилище корзины.

import { create } from 'zustand';
import api from '../api/client';
import { CART } from '../api/endpoints';

interface CartItem {
  id: number;
  product_name: string;
  sku: string;
  price: string;
  quantity: number;
  total_price: string;
  variant_id: number;
}

interface Cart {
  id: number;
  items: CartItem[];
  total_quantity: number;
  total: string;
}

interface CartState {
  cart: Cart | null;
  isCartOpen: boolean;  // для боковой панели корзины
  isLoading: boolean;

  fetchCart: () => Promise<void>;
  addItem: (variantId: number, quantity?: number) => Promise<void>;
  updateItem: (itemId: number, quantity: number) => Promise<void>;
  removeItem: (itemId: number) => Promise<void>;
  clearCart: () => Promise<void>;
  toggleCart: () => void;
}

export const useCartStore = create<CartState>((set, get) => ({
  cart: null,
  isCartOpen: false,
  isLoading: false,

  fetchCart: async () => {
    try {
      const { data } = await api.get(CART.CART);
      set({ cart: data });
    } catch {
      // Гостевая корзина может не существовать — это нормально
    }
  },

  addItem: async (variantId, quantity = 1) => {
    set({ isLoading: true });
    const { data } = await api.post(CART.ITEMS, {
      variant_id: variantId,
      quantity,
    });
    set({ cart: data, isLoading: false });
  },

  updateItem: async (itemId, quantity) => {
    set({ isLoading: true });
    const { data } = await api.patch(CART.ITEM(itemId), { quantity });
    set({ cart: data, isLoading: false });
  },

  removeItem: async (itemId) => {
    set({ isLoading: true });
    const { data } = await api.delete(CART.ITEM(itemId));
    set({ cart: data, isLoading: false });
  },

  clearCart: async () => {
    const { data } = await api.delete(CART.CART);
    set({ cart: data });
  },

  toggleCart: () => set((state) => ({ isCartOpen: !state.isCartOpen })),
}));
```

---

### Итог шага 4
✅ `src/stores/authStore.ts` — пользователь (login/logout/register/fetchUser)
✅ `src/stores/cartStore.ts` — корзина (add/remove/update/clear)

→ Переходи к шагу 5
