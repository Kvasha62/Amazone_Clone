# Architecture — Amazone Clone

> E-commerce platform built on **Django 6.1 + DRF 3.18** backend and
> **React 19 + Vite 6** frontend.  The design follows a strict
> **Service Layer** pattern with pessimistic locking for all mutating
> operations.

---

## Table of Contents

1. [High-Level Overview](#high-level-overview)
2. [Technology Stack](#technology-stack)
3. [Project Structure](#project-structure)
4. [Architectural Principles](#architectural-principles)
5. [Django Apps](#django-apps)
6. [Data Model](#data-model)
7. [API Reference](#api-reference)
8. [Authentication & Authorization](#authentication--authorization)
9. [Concurrency & Transaction Safety](#concurrency--transaction-safety)
10. [Async Tasks (Celery)](#async-tasks-celery)
11. [Full-Text Search](#full-text-search)
12. [Frontend Architecture](#frontend-architecture)
13. [Docker & Infrastructure](#docker--infrastructure)
14. [Testing Strategy](#testing-strategy)
15. [Deployment](#deployment)

---

## High-Level Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        React 19 SPA                             │
│  Vite 6 · TypeScript 5.8 · Tailwind 4 · Zustand 5             │
│  react-router-dom 7 · Axios (JWT interceptor)                  │
└──────────────────────────┬──────────────────────────────────────┘
                           │  HTTP / JSON  (JWT Bearer)
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Django 6.1 + DRF 3.18                       │
│                                                                 │
│  View → Serializer → Service → ORM                             │
│                     ╷           ╷                                │
│              @transaction.atomic  select_for_update()           │
│                                                                 │
│  ┌──────┐ ┌───────┐ ┌───────┐ ┌───────┐ ┌────────┐ ┌───────┐  │
│  │users │ │catalog│ │ cart  │ │orders │ │payments│ │reviews │  │
│  └──────┘ └───────┘ └───────┘ └───────┘ └────────┘ └───────┘  │
│  ┌──────┐ ┌───────┐ ┌───────┐ ┌───────┐ ┌────────┐ ┌───────┐  │
│  │inven.│ │pricing│ │discou.│ │shippi.│ │wishlist│ │analyt. │  │
│  └──────┘ └───────┘ └───────┘ └───────┘ └────────┘ └───────┘  │
└──────┬──────────────┬──────────────┬────────────────────────────┘
       │              │              │
       ▼              ▼              ▼
┌────────────┐ ┌────────────┐ ┌────────────┐
│ PostgreSQL │ │   Redis    │ │  Celery     │
│    18      │ │    7       │ │  worker+beat│
└────────────┘ └────────────┘ └────────────┘
```

---

## Technology Stack

| Layer          | Technology                         | Version   |
|----------------|------------------------------------|-----------|
| Language       | Python                             | 3.13.5    |
| Framework      | Django                             | 6.1       |
| API            | Django REST Framework              | 3.18      |
| Auth           | djangorestframework-simplejwt      | 5.5+      |
| API Docs       | drf-spectacular (OpenAPI 3)        | 0.30+     |
| Filter         | django-filter                      | 23+       |
| Tree           | django-treebeard (MP_Node)         | 7+        |
| CORS           | django-cors-headers                | 4.3+      |
| DB Adapter     | psycopg[binary] (psycopg3)         | 3.3+      |
| Database       | PostgreSQL                         | 18        |
| Cache/Broker   | Redis                              | 7         |
| Task Queue     | Celery                             | 5.4+      |
| Images         | Pillow                             | 10+       |
| Env            | python-dotenv                      | 1.0+      |
| Frontend       | React                              | 19        |
| Build          | Vite                               | 6         |
| Type System    | TypeScript                         | 5.8       |
| Styling        | Tailwind CSS                       | 4         |
| State          | Zustand                            | 5         |
| Routing        | react-router-dom                   | 7.18      |
| Testing (BE)   | Django TestCase + custom runner    | —         |
| Testing (FE)   | Vitest + React Testing Library     | —         |

---

## Project Structure

```
Amazone_Clone/                   # Backend root (Django project)
├── config/                      # Project configuration
│   ├── settings.py              # Django settings (SQLite/PG, JWT, CORS, Celery)
│   ├── urls.py                  # Root URL config (all apps mounted under /api/v1/)
│   ├── celery.py                # Celery app + beat schedule
│   ├── test_runner.py           # Custom AppDiscoverRunner (Python 3.13+ fix)
│   ├── asgi.py / wsgi.py        # ASGI/WSGI entry points
│   └── __init__.py              # Loads celery app
│
├── apps/                        # All Django applications
│   ├── core/                    # Base model, health-check
│   ├── users/                   # User, Address, UserProfile, JWT auth
│   ├── catalog/                 # Product, Category (treebeard), Brand, Variant
│   ├── inventory/               # Stock, StockMovement (reserve/release/commit)
│   ├── pricing/                 # Price, PriceHistory
│   ├── cart/                    # Cart, CartItem (merge guest→user)
│   ├── orders/                  # Order, OrderItem (FSM status machine)
│   ├── payments/                # Payment, PaymentEvent (webhook, refund)
│   ├── reviews/                 # Review, ReviewHelpfulVote, ReviewImage
│   ├── discounts/               # Campaign, Coupon
│   ├── shipping/                # ShippingMethod, ShippingZone, Shipment
│   ├── wishlist/                # Wishlist, WishlistItem
│   ├── notifications/           # Notification
│   └── analytics/               # ProductView (tracking)
│
├── manage.py
├── requirements.txt
├── .env.example
├── .gitignore
├── Dockerfile.backend
├── Dockerfile.frontend
├── docker-compose.yml
└── .dockerignore

frontend/                        # Frontend root (React SPA)
├── src/
│   ├── api/                     # API client modules (Axios + JWT interceptor)
│   ├── app/                     # App entry, providers, router
│   ├── components/              # UI + layout components
│   ├── pages/                   # Route-level page components
│   ├── store/                   # Zustand stores (auth, cart, catalog, …)
│   ├── types/                   # TypeScript interfaces
│   ├── hooks/                   # Custom React hooks
│   ├── utils/                   # Formatters, helpers
│   └── styles/                  # Tailwind CSS
├── package.json
├── vite.config.ts               # @/ alias, proxy to :8000
└── tsconfig.json
```

### Uniform App Structure

Every Django app under `apps/` follows the same internal layout:

```
apps/<app_name>/
├── __init__.py
├── apps.py                      # AppConfig
├── constants.py                 # App-level constants (limits, statuses, choices)
├── models/
│   ├── __init__.py              # Re-exports all models
│   └── <model_name>.py          # One file per model
├── managers/                    # Custom managers + querysets
├── querysets/                   # Reusable queryset methods
├── services/                    # Business logic (Service Layer)
├── api_views/                   # DRF API views
├── serializers/                 # DRF serializers
├── admin/                       # Django admin configuration
├── migrations/
├── tests/                       # Unit + integration tests
│   ├── factories.py             # Test data helpers
│   ├── test_models.py
│   ├── test_services.py
│   ├── test_api.py
│   ├── test_querysets.py
│   └── test_signals.py
├── urls.py                      # App URL routes
└── signals.py                   # Django signals (post_save, etc.)
```

---

## Architectural Principles

### 1. Service Layer Pattern

All business logic lives in **services**, never in views or serializers.

```
Request → View → Serializer (validation) → Service (business logic) → ORM → Database
```

- **Views** handle HTTP, permissions, and response formatting.
- **Serializers** validate input and format output.
- **Services** contain all business rules: state transitions, stock
  reservation, payment processing, order creation.
- **ORM** is accessed only from services.

📖 [Martin Fowler — Service Layer](https://martinfowler.com/eaaCatalog/serviceLayer.html)

### 2. Transaction Safety

Every mutating service method is decorated with `@transaction.atomic`
and uses `select_for_update()` for pessimistic row-level locking:

```python
@staticmethod
@transaction.atomic
def reserve_stock(order):
    stock = Stock.objects.select_for_update().get(pk=stock.pk)
    Stock.objects.filter(pk=stock.pk).update(
        reserved_quantity=F('reserved_quantity') + quantity,
    )
```

This guarantees that concurrent requests serialize correctly at the
database level — no race conditions, no phantom reads.

### 3. BaseModel (Abstract Base Class)

All domain models inherit from `BaseModel` (except `User` which inherits
`AbstractUser`):

```python
class BaseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
```

### 4. Denormalization for Performance

The `Product` model stores pre-computed aggregates to avoid expensive
JOINs on every listing request:

| Field            | Source                                | Purpose                            |
|------------------|---------------------------------------|------------------------------------|
| `min_price`      | `MIN(variant.price.effective_price)`  | Sort/filter by price without JOIN  |
| `max_price`      | `MAX(variant.price.effective_price)`  | Price range display                |
| `rating`         | `AVG(review.rating)`                  | Sort by rating without JOIN        |
| `reviews_count`  | `COUNT(review)`                       | Display count without JOIN         |
| `views_count`    | `COUNT(product_view)`                 | Popularity sort without JOIN       |

### 5. Snapshot Pattern

Order copies address and price data at creation time (not FK):

- **Address snapshot**: if the user changes their address, past orders
  retain the original delivery address — critical for legal compliance.
- **Price snapshot**: `OrderItem.unit_price` is copied from
  `Price.effective_price` at checkout — if the price changes later,
  the order total remains correct.

---

## Django Apps

### `core` — Foundation

- `BaseModel`: abstract base with `created_at`, `updated_at`
- Health-check endpoint: `GET /api/v1/health/`

### `users` — Authentication & Profile

| Model          | Description                              |
|----------------|------------------------------------------|
| `User`         | Custom user (email as USERNAME_FIELD)    |
| `Address`      | Delivery addresses (multiple per user)   |
| `UserProfile`  | Extended profile (phone, avatar, prefs)  |

- Custom `EmailOrUsernameModelBackend` for login by email or username
- JWT access (15 min) + refresh (7 days) with token blacklist
- Password reset flow (request + confirm)

### `catalog` — Products & Categories

| Model              | Description                                       |
|--------------------|---------------------------------------------------|
| `Category`         | Tree structure via django-treebeard `MP_Node`      |
| `Product`          | Main entity: UUID, slug, status, denormalized data|
| `ProductVariant`   | SKU-level items (color, size, etc.)               |
| `Brand`            | Product brands                                    |
| `Tag`              | Product tags (M2M)                                |
| `Attribute`        | Dynamic attributes (weight, diagonal, etc.)       |
| `AttributeValue`   | Attribute values (e.g. "256 GB")                  |
| `VariantAttribute` | Links variant to attribute + value                |
| `ProductImage`     | Product images with `is_main` flag                |

- `Category` uses **Materialized Path** (`django-treebeard.MP_Node`):
  creation only via `Category.add_root()` / `parent.add_child()`
- `Product.search_vector`: PostgreSQL `SearchVectorField` + GIN index
  for full-text search (falls back to `TextField` on SQLite)

### `inventory` — Stock Management

| Model           | Description                                  |
|-----------------|----------------------------------------------|
| `Stock`         | Per-variant stock: `quantity`, `reserved`    |
| `StockMovement` | Audit log: IN, OUT, RESERVE, RELEASE, ADJUST |

- `CheckConstraint`: `reserved_quantity ≤ quantity`, both ≥ 0
- Operations: `reserve_stock()`, `release_stock()`, `commit_stock()`,
  `restock()`, `adjust_stock()`

### `pricing` — Dynamic Pricing

| Model          | Description                                |
|----------------|--------------------------------------------|
| `Price`        | Per-variant: `base_price`, `sale_price`    |
| `PriceHistory` | Price change audit log                     |

- `effective_price` property: returns `sale_price` if set, else `base_price`

### `cart` — Shopping Cart

| Model      | Description                                    |
|------------|------------------------------------------------|
| `Cart`     | Per-user or per-session, `is_active` flag      |
| `CartItem` | Variant + quantity, unique per cart+variant     |

- Guest cart keyed by `session_key_hash` (nullable, `None` for user carts)
- `merge()`: merges guest cart into user cart on login
- Celery task: `cleanup_expired_carts` (daily at 03:00)

### `orders` — Order Processing

| Model       | Description                                      |
|-------------|--------------------------------------------------|
| `Order`     | Status machine, address snapshot, order_number   |
| `OrderItem` | Per-variant line: unit_price snapshot, SKU       |

- **Status FSM**: `PENDING → CONFIRMED → PROCESSING → SHIPPED → DELIVERED`
  Any non-terminal state → `CANCELLED`
- `order_number`: auto-generated `ORD-000001` with retry on `IntegrityError`
- `_order_number_seq`: sequential counter with `UniqueConstraint`
- `OrderService.cancel()`: releases stock reservation + initiates refund

### `payments` — Payment Processing

| Model          | Description                                     |
|----------------|-------------------------------------------------|
| `Payment`      | Amount, status, provider, external_id, refund   |
| `PaymentEvent` | Audit log for every status change / webhook      |

- **Status FSM**: `PENDING → PROCESSING → SUCCEEDED / FAILED / CANCELLED`
- `SUCCEEDED → REFUNDED` (full or partial)
- `create_payment()`: validates `amount == order.total` (prevents paying $1 for $1000 order)
- `confirm_payment()`: catches specific exceptions (`ValidationError`, `DatabaseError`)
- `handle_webhook()`: idempotent webhook processing
- Mock provider with `external_id = 'mock_<uuid>'`

### `reviews` — Product Reviews

| Model              | Description                                    |
|--------------------|------------------------------------------------|
| `Review`           | Rating 1-5, text, is_approved flag             |
| `ReviewHelpfulVote`| Toggle helpful/unhelpful, unique per user+review|
| `ReviewImage`      | Review images                                  |

- One review per user per product (`UniqueConstraint`)
- Helpful voting: toggle logic (click again to remove vote)
- Sorting: `?ordering=-rating`, filtering: `?rating_gte=4&verified=true`
- Product `rating` / `reviews_count` updated on review save

### `discounts` — Campaigns & Coupons

| Model      | Description                                   |
|------------|-----------------------------------------------|
| `Campaign` | Time-bounded promotion with discount rules     |
| `Coupon`   | Code-based discounts, usage limits             |

### `shipping` — Delivery

| Model            | Description                                  |
|------------------|----------------------------------------------|
| `ShippingMethod` | Delivery method with zone-based pricing       |
| `ShippingZone`   | Geographic zone (country/region)             |
| `Shipment`       | Order shipment with tracking number          |

### `wishlist` — Favorites

| Model          | Description                    |
|----------------|--------------------------------|
| `Wishlist`     | Per-user wishlist              |
| `WishlistItem` | Product reference + added_at   |

- Move to cart functionality

### `notifications` — User Notifications

| Model          | Description                            |
|----------------|----------------------------------------|
| `Notification` | Type, status (unread/read), payload    |

- Endpoints: list, mark read, mark all read, unread count
- Celery task stubs for email delivery

### `analytics` — Product Views

| Model          | Description                            |
|----------------|----------------------------------------|
| `ProductView`  | Track product detail page views        |

- Dashboard endpoints: top products, sales timeline, conversion rates
- Staff-only access

---

## Data Model

### Entity-Relationship Overview

```
User ──1:N── Address
  │
  ├──1:1── UserProfile
  ├──1:1── Wishlist ──1:N── WishlistItem ──→ Product
  ├──1:N── Cart ──1:N── CartItem ──→ ProductVariant ──→ Price
  ├──1:N── Order ──1:N── OrderItem ──→ ProductVariant
  ├──1:N── Review ──→ Product
  ├──1:N── Notification
  └──1:N── Payment ──1:N── PaymentEvent

Product ──M:N── Category (treebeard MP_Node)
  │
  ├──1:N── ProductVariant ──1:1── Stock
  │                      └──1:1── Price ──1:N── PriceHistory
  ├──1:N── ProductImage
  ├──M:N── Tag
  └──M:1── Brand

ProductVariant ──1:N── VariantAttribute ──→ Attribute + AttributeValue

Order ──→ Payment
Order ──→ Shipment ──→ ShippingMethod ──→ ShippingZone

Stock ──1:N── StockMovement (audit)
```

### Key Constraints

| Table              | Constraint                                  | Purpose                        |
|--------------------|---------------------------------------------|--------------------------------|
| `cart_cart`        | `unique_active_user_cart`                   | One active cart per user       |
| `cart_cartitem`    | `unique_cart_variant`                       | No duplicate variants in cart  |
| `orders_order`     | `_order_number_seq` unique                  | No duplicate order numbers     |
| `orders_orderitem` | `unique_order_sku`                          | No duplicate SKUs in order     |
| `reviews_review`   | `unique_user_product_review`                | One review per user per product|
| `review_helpful`   | `unique_user_review_helpful_vote`           | One vote per user per review   |
| `inventory_stock`  | `stock_reserved_lte_quantity`               | Reserved cannot exceed quantity|
| `inventory_stock`  | `stock_quantity_non_negative`               | Quantity ≥ 0                   |
| `payments_payment` | `payment_refund_lte_amount`                 | Refund cannot exceed payment   |

> All constraints use `CheckConstraint(condition=...)` — the
> `condition=` keyword is correct for Django 4.2, 5.0, and 6.1.

---

## API Reference

All endpoints are under `/api/v1/`. Authentication is JWT Bearer token
unless noted otherwise.

| Prefix                   | App          | Key Endpoints                                        |
|--------------------------|--------------|------------------------------------------------------|
| `/api/v1/auth/`          | users        | login, refresh, register, change-password            |
| `/api/v1/users/`         | users        | me, addresses CRUD                                   |
| `/api/v1/catalog/`       | catalog      | products CRUD, categories tree, brands, by-slugs     |
| `/api/v1/cart/`          | cart         | get, add item, update, remove, merge guest→user      |
| `/api/v1/orders/`        | orders       | list, create, detail, cancel, status (staff)         |
| `/api/v1/payments/`      | payments     | create, webhook, refund, cancel                      |
| `/api/v1/reviews/`       | reviews      | list/create, detail/update, helpful toggle            |
| `/api/v1/inventory/`     | inventory    | stock list, detail, restock, adjust, movements       |
| `/api/v1/pricing/`       | pricing      | price detail, history, bulk update (staff)           |
| `/api/v1/discounts/`     | discounts    | coupon list, apply, remove, preview                  |
| `/api/v1/shipping/`      | shipping     | methods, calculate cost, shipments, tracking         |
| `/api/v1/wishlist/`      | wishlist     | list, add, remove, move-to-cart, clear               |
| `/api/v1/notifications/` | notifications| list, unread, mark read, mark all read               |
| `/api/v1/analytics/`     | analytics    | dashboard, top products, sales timeline (staff)      |
| `/api/v1/health/`        | core         | Health check (public)                                |
| `/api/v1/schema/`        | drf-spectacular| OpenAPI 3 schema (JSON)                            |
| `/api/v1/docs/`          | drf-spectacular| Swagger UI                                          |

### Pagination

All list endpoints use `PageNumberPagination` with `PAGE_SIZE = 20`.

### Filtering & Sorting

- **django-filter**: field-based filtering (`?rating_gte=4`, `?status=active`)
- **OrderingFilter**: `?ordering=-created_at`, `?ordering=price`
- **Search**: `?search=iphone` — uses PostgreSQL FTS on `search_vector`

---

## Authentication & Authorization

### JWT Flow

```
1. POST /api/v1/auth/login/  {email, password}
   → {access: "eyJ...", refresh: "eyJ..."}

2. Subsequent requests:
   Authorization: Bearer <access_token>

3. POST /api/v1/auth/refresh/  {refresh}
   → {access: "eyJ...", refresh: "eyJ..."}   (ROTATE_REFRESH_TOKENS=True)

4. Old refresh token → blacklisted (BLACKLIST_AFTER_ROTATION=True)
```

### Permission Levels

| Level             | Description                          | Used by                          |
|-------------------|--------------------------------------|----------------------------------|
| `AllowAny`        | No authentication required           | Product listing, reviews GET     |
| `IsAuthenticated` | Valid JWT required                   | Cart, orders, wishlist, profile  |
| `IsAdminUser`     | JWT + `is_staff=True`               | Inventory, analytics, pricing    |

### Frontend Interceptor

The React API client (`client.ts`) uses an Axios interceptor that:
- Attaches the JWT `access` token to every request
- On 401 response, attempts silent refresh via the `refresh` token
- On refresh failure, redirects to `/login`
- Mutating methods (POST, PATCH, PUT, DELETE) **always** include the token
- Only safe GET requests to public endpoints may omit it

---

## Concurrency & Transaction Safety

### Pattern: `@transaction.atomic` + `select_for_update()`

All mutating service methods follow this pattern:

```python
@staticmethod
@transaction.atomic
def some_mutation(...):
    obj = Model.objects.select_for_update().get(pk=pk)
    # ... business logic ...
    Model.objects.filter(pk=pk).update(field=F('field') + delta)
```

### Key Protections

| Scenario                    | Protection                                              |
|-----------------------------|---------------------------------------------------------|
| Two users checkout same item| `select_for_update()` locks the `Stock` row             |
| Parallel order numbering    | `UniqueConstraint` + retry loop on `IntegrityError`    |
| Cart merge race             | `select_for_update()` locks the `Cart` row             |
| Payment amount tampering    | `amount != order.total` → `ValidationError`            |
| Double webhook delivery     | Idempotent: already-SUCCEEDED → no-op                  |
| Stock reserved > quantity   | `CheckConstraint(reserved_quantity__lte=F('quantity'))` |

### `select_for_update()` + `get_or_create()` Fix

These two methods are **incompatible**: `select_for_update()` can only
lock existing rows. The correct pattern is:

```python
stock, created = Stock.objects.get_or_create(variant=variant, defaults={...})
stock = Stock.objects.select_for_update().get(pk=stock.pk)
```

---

## Async Tasks (Celery)

### Configuration

- **Broker**: Redis (`redis://localhost:6379/0`)
- **Backend**: Redis (task results stored 1 hour)
- **Serialization**: JSON (not pickle — security)
- **Concurrency**: 4 workers

### Beat Schedule (Periodic Tasks)

| Task                            | Schedule   | Purpose                        |
|---------------------------------|------------|--------------------------------|
| `cleanup_old_carts`             | Daily 03:00| Remove expired inactive carts   |
| `send_abandoned_cart_reminders` | Hourly     | Email nudge for abandoned carts|

### Task Routing

| Queue     | Tasks                       |
|-----------|-----------------------------|
| `orders`  | `apps.orders.tasks.*`       |
| `cart`    | `apps.cart.tasks.*`         |
| `reviews` | `apps.reviews.tasks.*`      |

---

## Full-Text Search

On PostgreSQL, the `Product` model uses a `SearchVectorField` with a
GIN index for sub-millisecond full-text search:

```python
search_vector = SearchVectorField(null=True, blank=True, editable=False)
# + GinIndex(fields=['search_vector'], name='product_search_gin')
```

The `ProductQuerySet.search()` method uses:

```python
qs = qs.filter(search_vector=query)
```

On SQLite, `SearchVectorField` falls back to `TextField` and search
uses `__icontains` instead.

---

## Frontend Architecture

### State Management (Zustand 5)

| Store                   | Purpose                                 |
|-------------------------|-----------------------------------------|
| `authStore`             | User, tokens, login/logout/refresh      |
| `cartStore`             | Cart items, add/remove/merge            |
| `catalogStore`          | Products, filters, pagination           |
| `wishlistStore`         | Wishlist items, add/remove              |
| `notificationStore`     | Notifications, polling every 30s        |
| `recentlyViewedStore`   | Recently viewed products (localStorage) |

### API Client Architecture

```
src/api/
├── client.ts         # Axios instance + JWT interceptor
├── api.ts            # isPublicRequest() helper
├── auth.ts           # login, register, refresh, change-password
├── catalog.ts        # products, categories, brands, by-slugs
├── cart.ts           # cart CRUD
├── orders.ts         # order CRUD
├── reviews.ts        # reviews CRUD + helpful
├── addresses.ts      # address CRUD
├── shipping.ts       # shipping methods + calculate
├── discounts.ts      # coupon apply/remove/preview
├── wishlist.ts       # wishlist CRUD
├── notifications.ts  # notifications + mark-read
├── profile.ts        # user profile + password
└── index.ts          # re-exports
```

### Key Pages

| Route                | Page                | Description                          |
|----------------------|---------------------|--------------------------------------|
| `/`                  | `HomePage`          | Banners, featured, recently viewed   |
| `/catalog`           | `CatalogPage`       | Product grid + filters + pagination  |
| `/products/:slug`    | `ProductPage`       | Ozon-style: images, variants, reviews|
| `/cart`              | `CartPage`          | Cart drawer + checkout               |
| `/checkout`          | `CheckoutPage`      | 4-step: address → delivery → payment → confirm |
| `/orders`            | `OrderListPage`     | Order history                        |
| `/orders/:number`    | `OrderDetailPage`   | Timeline, items, address, cancel     |
| `/profile`           | `ProfilePage`       | 3 tabs: info / addresses / password  |
| `/wishlist`          | `WishlistPage`      | Wishlist grid                        |
| `/notifications`     | `NotificationPage`  | Notifications list + mark read       |
| `/login`             | `LoginPage`         | Email login                          |
| `/register`          | `RegisterPage`      | Registration                         |
| `/forgot-password`   | `ForgotPasswordPage`| 3-step password reset                |
| `*`                  | `NotFoundPage`      | 404                                  |

### UI Components

- `ErrorBoundary` — catches render errors, shows fallback UI
- `Toast` / `ToastContainer` — notification toasts (success/error/info)
- `Skeleton` — loading placeholders (card, text, product page)
- `Header` — categories dropdown, notification bell with badge
- `CartDrawer` — slide-out cart from any page

---

## Docker & Infrastructure

### `docker-compose.yml` Services

| Service      | Image             | Port  | Purpose                    |
|--------------|-------------------|-------|----------------------------|
| `db`         | `postgres:18`     | 5432  | Primary database           |
| `redis`      | `redis:7-alpine`  | 6379  | Cache + Celery broker      |
| `backend`    | custom build      | 8000  | Django (runserver dev)     |
| `celery`     | custom build      | —     | Celery worker              |
| `celery-beat`| custom build      | —     | Periodic task scheduler    |
| `frontend`   | custom build      | 5173  | Vite dev server            |

### Health Checks

- PostgreSQL: `pg_isready`
- Redis: `redis-cli ping`
- Backend: `GET /api/v1/health/`

### Volumes

- `pgdata` — persistent PostgreSQL data
- `media` — uploaded product images

---

## Testing Strategy

### Backend

- **950 tests**, 0 failures, 2 skipped (PostgreSQL-only)
- Custom test runner: `config.test_runner.AppDiscoverRunner` — fixes
  `unittest.discover()` issues with nested `tests/` packages on
  Python 3.13+
- Throttling disabled in tests (`DEFAULT_THROTTLE_RATES = None`)
- SQLite by default; PostgreSQL required for FTS and `select_for_update`

### Per-App Test Structure

```
tests/
├── factories.py          # create_test_user(), create_test_order(), ...
├── test_models.py        # Model field validation, constraints, methods
├── test_services.py      # Business logic (the bulk of tests)
├── test_api.py           # HTTP endpoint tests (permissions, status codes)
├── test_querysets.py     # QuerySet methods (.active(), .for_user(), ...)
└── test_signals.py       # Signal handlers (auto-stock, auto-price, ...)
```

### Frontend

- Vitest + React Testing Library + MSW (Mock Service Worker)
- Test files in `__tests__/` directories and `*.test.ts` files
- Key tests: `authStore`, `cartStore`, `formatPrice`, `formatDate`

---

## Deployment

### Local Development (Windows)

```powershell
# Backend
py -3.13 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver

# Frontend (via cmd.exe — PowerShell blocks npm)
cmd /c "npm install"
cmd /c "npm run dev"
```

### Docker

```bash
docker compose up -d          # Start all services
docker compose up -d db redis # Only database + Redis
docker compose logs -f backend# View Django logs
docker compose down           # Stop
```

### Environment Variables

| Variable               | Default                          | Purpose                  |
|------------------------|----------------------------------|--------------------------|
| `DB_ENGINE`            | `django.db.backends.sqlite3`     | Database backend         |
| `DB_NAME`              | `amazone_clone`                  | Database name            |
| `DB_USER` / `DB_PASS`  | `postgres` / empty               | DB credentials           |
| `DB_HOST` / `DB_PORT`  | `localhost` / `5432`             | DB connection            |
| `DJANGO_SECRET_KEY`    | insecure default                 | Secret key               |
| `DJANGO_DEBUG`         | `True`                           | Debug mode               |
| `REDIS_URL`            | `redis://localhost:6379/0`       | Celery broker            |
| `CORS_ALLOW_ALL_ORIGINS`| `True` (debug)                  | CORS policy              |
| `THROTTLE_ANON`        | `60/min`                         | Anon rate limit          |
| `THROTTLE_USER`        | `120/min`                        | Authenticated rate limit |

### Production Checklist

- [ ] Set `DJANGO_DEBUG=False`
- [ ] Generate strong `DJANGO_SECRET_KEY`
- [ ] Use PostgreSQL (not SQLite)
- [ ] Set `CORS_ALLOW_ALL_ORIGINS=False` + whitelist origins
- [ ] Add HMAC verification to payment webhook
- [ ] Use gunicorn + nginx (not runserver)
- [ ] Enable psycopg3 connection pooling
- [ ] Set up SMTP or django-anymail for email
- [ ] Add rate limiting on payment webhook endpoint
