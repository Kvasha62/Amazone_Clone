# Шаг 10. Карточка товара

Замени заглушку `src/pages/ProductDetailPage.tsx`:

```typescript
// src/pages/ProductDetailPage.tsx
// Детальная страница товара: фото, цена, добавить в корзину, отзывы.

import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import api from '../api/client';
import { CATALOG, REVIEW, CART } from '../api/endpoints';
import { useCartStore } from '../stores/cartStore';
import { useAuthStore } from '../stores/authStore';

interface Variant {
  id: number;
  sku: string;
  name: string;
  price: string;
  effective_price: string;
  sale_price: string | null;
  is_active: boolean;
  attributes: { name: string; value: string }[];
}

interface Image {
  id: number;
  image: string;
  is_main: boolean;
}

interface Product {
  id: number;
  name: string;
  slug: string;
  description: string;
  rating: string;
  reviews_count: number;
  views_count: number;
  min_price: string;
  max_price: string;
  main_image: string | null;
  brand: { name: string; slug: string } | null;
  primary_category: { name: string; slug: string } | null;
  images: Image[];
  variants: Variant[];
}

interface Review {
  id: number;
  user: { username: string };
  rating: number;
  text: string;
  created_at: string;
  verified_purchase: boolean;
  helpful_yes: number;
  helpful_no: number;
}

export function ProductDetailPage() {
  const { slug } = useParams<{ slug: string }>();
  const [product, setProduct] = useState<Product | null>(null);
  const [reviews, setReviews] = useState<Review[]>([]);
  const [selectedVariant, setSelectedVariant] = useState<Variant | null>(null);
  const [quantity, setQuantity] = useState(1);
  const [isLoading, setIsLoading] = useState(true);
  const addItem = useCartStore((s) => s.addItem);
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);

  useEffect(() => {
    if (slug) {
      fetchProduct();
      fetchReviews();
    }
  }, [slug]);

  const fetchProduct = async () => {
    setIsLoading(true);
    try {
      const { data } = await api.get<Product>(CATALOG.PRODUCT(slug!));
      setProduct(data);
      // Выбираем первый активный вариант по умолчанию
      const activeVariant = data.variants?.find(v => v.is_active);
      if (activeVariant) setSelectedVariant(activeVariant);
    } catch {
      console.error('Товар не найден');
    } finally {
      setIsLoading(false);
    }
  };

  const fetchReviews = async () => {
    try {
      const { data } = await api.get(REVIEW.LIST, {
        params: { product_slug: slug, page_size: 10 },
      });
      // data может быть списком или пагинированным ответом
      setReviews(Array.isArray(data) ? data : data.results || []);
    } catch {
      // Отзывы могут отсутствовать — это нормально
    }
  };

  const handleAddToCart = async () => {
    if (!selectedVariant) return;
    try {
      await addItem(selectedVariant.id, quantity);
      alert('Добавлено в корзину!');
    } catch (err) {
      console.error('Ошибка добавления в корзину:', err);
    }
  };

  if (isLoading) return <div>Загрузка...</div>;
  if (!product) return <div>Товар не найден</div>;

  return (
    <div>
      {/* Хлебные крошки */}
      <div style={{ fontSize: '13px', color: '#888', marginBottom: '16px' }}>
        <Link to="/" style={{ color: '#007185' }}>Главная</Link> /{' '}
        <Link to="/products" style={{ color: '#007185' }}>Каталог</Link> /{' '}
        {product.primary_category && (
          <>{product.primary_category.name} / </>
        )}
        {product.name}
      </div>

      <div style={{ display: 'flex', gap: '32px', flexWrap: 'wrap' }}>
        {/* ═══ ФОТО ═══ */}
        <div style={{ flex: '1 1 400px', maxWidth: '500px' }}>
          <div style={{
            width: '100%',
            height: '400px',
            background: '#f5f5f5',
            borderRadius: '8px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            overflow: 'hidden',
          }}>
            {product.main_image ? (
              <img src={product.main_image} alt={product.name} style={{ maxWidth: '100%', maxHeight: '100%', objectFit: 'contain' }} />
            ) : (
              <span style={{ fontSize: '100px' }}>📦</span>
            )}
          </div>

          {/* Миниатюры */}
          {product.images && product.images.length > 1 && (
            <div style={{ display: 'flex', gap: '8px', marginTop: '8px', overflowX: 'auto' }}>
              {product.images.map(img => (
                <img key={img.id} src={img.image} alt="" style={{ width: '60px', height: '60px', objectFit: 'cover', borderRadius: '4px', border: img.is_main ? '2px solid #ffa500' : '1px solid #ddd' }} />
              ))}
            </div>
          )}
        </div>

        {/* ═══ ИНФОРМАЦИЯ ═══ */}
        <div style={{ flex: '1 1 300px' }}>
          <h1 style={{ fontSize: '24px', marginBottom: '8px' }}>{product.name}</h1>

          {product.brand && (
            <div style={{ color: '#888', marginBottom: '8px' }}>
              Бренд: <Link to={`/products?brand=${product.brand.slug}`} style={{ color: '#007185' }}>{product.brand.name}</Link>
            </div>
          )}

          {/* Рейтинг */}
          <div style={{ marginBottom: '12px' }}>
            {'⭐'.repeat(Math.round(parseFloat(product.rating)))} {parseFloat(product.rating).toFixed(1)} ({product.reviews_count} отзывов)
          </div>

          {/* Цена */}
          <div style={{ fontSize: '28px', fontWeight: 'bold', color: '#c00', marginBottom: '16px' }}>
            {selectedVariant
              ? `${selectedVariant.effective_price} ₽`
              : `${product.min_price} — ${product.max_price} ₽`
            }
            {selectedVariant?.sale_price && (
              <span style={{ textDecoration: 'line-through', color: '#888', fontSize: '18px', marginLeft: '8px' }}>
                {selectedVariant.price} ₽
              </span>
            )}
          </div>

          {/* Выбор варианта */}
          {product.variants && product.variants.filter(v => v.is_active).length > 1 && (
            <div style={{ marginBottom: '16px' }}>
              <label style={{ fontWeight: 'bold', display: 'block', marginBottom: '8px' }}>Вариант:</label>
              <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                {product.variants.filter(v => v.is_active).map(variant => (
                  <button
                    key={variant.id}
                    onClick={() => setSelectedVariant(variant)}
                    style={{
                      padding: '8px 16px',
                      border: selectedVariant?.id === variant.id ? '2px solid #ffa500' : '1px solid #ddd',
                      borderRadius: '4px',
                      cursor: 'pointer',
                      background: selectedVariant?.id === variant.id ? '#fff3e0' : 'white',
                    }}
                  >
                    {variant.name || variant.sku}
                    <div style={{ fontSize: '13px', color: '#666' }}>{variant.effective_price} ₽</div>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Количество + кнопка */}
          <div style={{ display: 'flex', gap: '12px', alignItems: 'center', marginBottom: '20px' }}>
            <div style={{ display: 'flex', alignItems: 'center', border: '1px solid #ddd', borderRadius: '4px' }}>
              <button onClick={() => setQuantity(q => Math.max(1, q - 1))} style={{ padding: '8px 12px', border: 'none', background: 'none', cursor: 'pointer', fontSize: '18px' }}>
                −
              </button>
              <span style={{ padding: '8px 16px', minWidth: '40px', textAlign: 'center' }}>{quantity}</span>
              <button onClick={() => setQuantity(q => q + 1)} style={{ padding: '8px 12px', border: 'none', background: 'none', cursor: 'pointer', fontSize: '18px' }}>
                +
              </button>
            </div>

            <button
              onClick={handleAddToCart}
              disabled={!selectedVariant}
              style={{
                flex: 1,
                padding: '12px',
                background: selectedVariant ? '#ffa500' : '#ccc',
                border: 'none',
                borderRadius: '4px',
                fontSize: '16px',
                cursor: selectedVariant ? 'pointer' : 'not-allowed',
                fontWeight: 'bold',
              }}
            >
              🛒 Добавить в корзину
            </button>
          </div>

          {/* Описание */}
          <div style={{ borderTop: '1px solid #ddd', paddingTop: '16px' }}>
            <h3>Описание</h3>
            <p style={{ lineHeight: '1.6', color: '#333' }}>{product.description || 'Нет описания'}</p>
          </div>
        </div>
      </div>

      {/* ═══ ОТЗЫВЫ ═══ */}
      <div style={{ marginTop: '32px', borderTop: '1px solid #ddd', paddingTop: '16px' }}>
        <h2>Отзывы ({product.reviews_count})</h2>

        {reviews.length === 0 ? (
          <p style={{ color: '#888' }}>Пока нет отзывов</p>
        ) : (
          reviews.map(review => (
            <div key={review.id} style={{ borderBottom: '1px solid #eee', padding: '12px 0' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                <div>
                  <strong>{review.user.username}</strong>
                  {review.verified_purchase && (
                    <span style={{ color: '#007600', fontSize: '12px', marginLeft: '8px' }}>✓ Покупка подтверждена</span>
                  )}
                </div>
                <div style={{ color: '#888', fontSize: '13px' }}>
                  {new Date(review.created_at).toLocaleDateString('ru-RU')}
                </div>
              </div>
              <div>{'⭐'.repeat(review.rating)}{'☆'.repeat(5 - review.rating)}</div>
              {review.text && <p style={{ margin: '8px 0' }}>{review.text}</p>}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
```

---

### Итог шага 10
✅ Карточка товара с фото, ценой, вариантами
✅ Кнопка «Добавить в корзину»
✅ Отзывы под товаром
✅ Хлебные крошки

→ Переходи к шагу 11
