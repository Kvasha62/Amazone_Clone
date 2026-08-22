# Шаг 9. Каталог товаров

Замени заглушку `src/pages/ProductListPage.tsx`:

```typescript
// src/pages/ProductListPage.tsx
// Список товаров с фильтрами, поиском и пагинацией.

import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import api from '../api/client';
import { CATALOG } from '../api/endpoints';

interface Product {
  id: number;
  name: string;
  slug: string;
  min_price: string;
  max_price: string;
  rating: string;
  reviews_count: number;
  main_image: string | null;
  primary_category: { name: string; slug: string } | null;
  brand: { name: string; slug: string } | null;
}

interface PaginatedResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: Product[];
}

export function ProductListPage() {
  const [products, setProducts] = useState<Product[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState('');
  const [isLoading, setIsLoading] = useState(true);

  const pageSize = 20;
  const totalPages = Math.ceil(totalCount / pageSize);

  useEffect(() => {
    fetchProducts();
  }, [currentPage, search, category]);

  const fetchProducts = async () => {
    setIsLoading(true);
    try {
      const params: Record<string, string | number> = { page: currentPage };
      if (search) params.search = search;
      if (category) params.primary_category__slug = category;

      const { data } = await api.get<PaginatedResponse>(CATALOG.PRODUCTS, { params });
      setProducts(data.results);
      setTotalCount(data.count);
    } catch (err) {
      console.error('Ошибка загрузки товаров:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setCurrentPage(1);
    fetchProducts();
  };

  return (
    <div>
      {/* Поиск */}
      <form onSubmit={handleSearch} style={{ display: 'flex', gap: '8px', marginBottom: '20px' }}>
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Искать товары..."
          style={{ flex: 1, padding: '10px', border: '1px solid #ccc', borderRadius: '4px' }}
        />
        <button type="submit" style={{ padding: '10px 20px', background: '#ffa500', border: 'none', borderRadius: '4px', cursor: 'pointer' }}>
          Найти
        </button>
      </form>

      {/* Результаты */}
      <div style={{ marginBottom: '12px', color: '#666' }}>
        Найдено: {totalCount} товаров
      </div>

      {isLoading ? (
        <div>Загрузка...</div>
      ) : (
        <>
          {/* Сетка товаров */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))',
            gap: '16px',
          }}>
            {products.map(product => (
              <Link
                key={product.id}
                to={`/products/${product.slug}`}
                style={{
                  textDecoration: 'none',
                  color: 'inherit',
                  border: '1px solid #ddd',
                  borderRadius: '8px',
                  padding: '12px',
                  transition: 'box-shadow 0.2s',
                }}
                onMouseEnter={(e) => (e.currentTarget.style.boxShadow = '0 2px 12px rgba(0,0,0,0.15)')}
                onMouseLeave={(e) => (e.currentTarget.style.boxShadow = 'none')}
              >
                {/* Картинка */}
                <div style={{
                  height: '180px',
                  background: '#f5f5f5',
                  borderRadius: '4px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  marginBottom: '8px',
                  overflow: 'hidden',
                }}>
                  {product.main_image ? (
                    <img src={product.main_image} alt={product.name} style={{ maxWidth: '100%', maxHeight: '100%', objectFit: 'contain' }} />
                  ) : (
                    <span style={{ fontSize: '48px' }}>📦</span>
                  )}
                </div>

                {/* Название */}
                <div style={{ fontWeight: 'bold', marginBottom: '4px', fontSize: '14px', lineHeight: '1.3' }}>
                  {product.name}
                </div>

                {/* Бренд */}
                {product.brand && (
                  <div style={{ color: '#888', fontSize: '12px' }}>{product.brand.name}</div>
                )}

                {/* Цена */}
                <div style={{ color: '#c00', fontWeight: 'bold', marginTop: '8px', fontSize: '18px' }}>
                  {product.min_price === product.max_price
                    ? `${product.min_price} ₽`
                    : `от ${product.min_price} ₽`
                  }
                </div>

                {/* Рейтинг */}
                <div style={{ fontSize: '13px', color: '#666', marginTop: '4px' }}>
                  ⭐ {parseFloat(product.rating).toFixed(1)} ({product.reviews_count})
                </div>
              </Link>
            ))}
          </div>

          {/* Пагинация */}
          {totalPages > 1 && (
            <div style={{ display: 'flex', justifyContent: 'center', gap: '8px', marginTop: '24px' }}>
              <button
                disabled={currentPage === 1}
                onClick={() => setCurrentPage(p => p - 1)}
                style={{ padding: '8px 16px', border: '1px solid #ddd', borderRadius: '4px', cursor: currentPage === 1 ? 'not-allowed' : 'pointer' }}
              >
                ← Назад
              </button>
              <span style={{ padding: '8px 16px' }}>
                Стр. {currentPage} из {totalPages}
              </span>
              <button
                disabled={currentPage === totalPages}
                onClick={() => setCurrentPage(p => p + 1)}
                style={{ padding: '8px 16px', border: '1px solid #ddd', borderRadius: '4px', cursor: currentPage === totalPages ? 'not-allowed' : 'pointer' }}
              >
                Вперёд →
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
```

---

### Итог шага 9
✅ Каталог товаров с пагинацией
✅ Поиск по названию
✅ Сетка карточек товаров

→ Переходи к шагу 10
