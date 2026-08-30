# Architecture — Amazone Clone

> E-commerce platform with a **Django + DRF** backend.
> A **React + Vite** frontend is planned and documented in
> `frontend-guide/`, but its source is not yet committed.
> The design follows a **Service Layer**
> pattern with concurrency-safe state transitions.

---

## Table of Contents

1. [High-Level Overview](#high-level-overview)
2. [Technology Stack](#technology-stack)
3. [Project Structure](#project-structure)
4. [Architectural Principles](#architectural-principles)
5. [Domain Ownership](#domain-ownership)
6. [Historical Snapshot Invariants](#historical-snapshot-invariants)
7. [Django Apps — Current Implementation](#django-apps--current-implementation)
8. [Data Model](#data-model)
9. [API Reference](#api-reference)
10. [Authentication & Authorization](#authentication--authorization)
11. [Concurrency & Transaction Safety](#concurrency--transaction-safety)
12. [Cross-Domain Coordination](#cross-domain-coordination)
13. [Async Tasks (Celery)](#async-tasks-celery)
14. [Full-Text Search](#full-text-search)
15. [Frontend Architecture](#frontend-architecture)
16. [Docker & Infrastructure](#docker--infrastructure)
17. [Testing Strategy](#testing-strategy)
18. [Deployment](#deployment)
19. [Future Direction](#future-direction)

---

## High-Level Overview

```
┌─────────────────────────────────────────────────────────────────┐
│               React SPA — PLANNED, not yet committed            │
│  Vite · TypeScript · Tailwind · Zustand                         │
│  react-router-dom · Axios (JWT interceptor)                     │
└──────────────────────────┬──────────────────────────────────────┘
                           │  HTTP / JSON  (JWT Bearer)
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                       Django + DRF                              │
│                                                                 │
│  View → Serializer → Service → ORM                             │
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
└────────────┘ └────────────┘ └────────────┘
```

---

## Technology Stack

### Backend (pinned versions per `requirements.txt`)

| Layer          | Technology                         |
|----------------|------------------------------------|
| Language       | Python ≥ 3.13 (3.14 recommended for Django 6.1)                      |
| Framework      | Django ≥ 6.1, < 7.0                |
| API            | Django REST Framework ≥ 3.18       |
| Auth           | djangorestframework-simplejwt ≥ 5.3|
| API Docs       | drf-spectacular ≥ 0.30             |
| Filter         | django-filter ≥ 23.0               |
| Tree           | django-treebeard ≥ 4.7.1           |
| CORS           | django-cors-headers ≥ 4.3          |
| DB Adapter     | psycopg[binary] ≥ 3.3              |
| Database       | PostgreSQL (production)            |
| Cache/Broker   | Redis                              |
| Task Queue     | celery[redis] ≥ 5.4                |
| Images         | Pillow ≥ 10.0                      |

### Frontend (planned; versions per `package.json` — not yet in repository)

> The frontend is planned. `package.json` does not yet exist in this
> repository. The versions below are the target.

| Layer          | Technology                         |
|----------------|------------------------------------|
| UI Framework   | React 19                           |
| Build          | Vite 6                             |
| Type System    | TypeScript 5.8                     |
| Styling        | Tailwind CSS 4                     |
| State          | Zustand 5                          |
| Routing        | react-router-dom 7                 |

---

## Project Structure

```
Amazone_Clone/                   # Backend root (Django project)
├── config/                      # Project configuration
│   ├── settings.py              # Django settings (SQLite/PG, JWT, CORS, Celery)
│   ├── urls.py                  # Root URL config (all apps under /api/v1/)
│   ├── celery.py                # Celery app + beat schedule
│   ├── test_runner.py           # Custom AppDiscoverRunner
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

> **Current state:** frontend source is not committed yet. The structure
> below is the planned target; the build is documented step-by-step in
> `frontend-guide/`.

frontend/                        # Frontend root (React SPA) — PLANNED, not yet committed
├── src/
│   ├── api/                     # API client modules (Axios + JWT interceptor)
│   ├── app/                     # App entry, providers, router
│   ├── components/              # UI + layout components
│   ├── pages/                   # Route-level page components
│   ├── store/                   # Zustand stores
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
│   ├── factories.py
│   ├── test_models.py
│   ├── test_services.py
│   ├── test_api.py
│   ├── test_querysets.py
│   └── test_signals.py
├── urls.py                      # App URL routes
└── signals.py                   # Django signals (see § Cross-Domain Coordination)
```

---

## Architectural Principles

### 1. Service Layer Pattern

**Rule.** All business logic lives in **services**, never in views or
serializers.

```
Request → View → Serializer (validation) → Service (business logic) → ORM → Database
```

- **Views** handle HTTP, permissions, and response formatting — no
  business rules.
- **Serializers** validate input and format output — no business rules.
- **Services** contain all business rules: state transitions, stock
  reservation, payment processing, order creation.
- **ORM**: Business mutations and state transitions are performed by
  services. Query/read logic may live in QuerySets or Managers, but
  business rules and cross-domain state changes must not be
  implemented there.

📖 [Martin Fowler — Service Layer](https://martinfowler.com/eaaCatalog/serviceLayer.html)

### 2. Concurrency-Safe State Transitions

**Rule.** Service methods that modify concurrency-sensitive state must
use `@transaction.atomic` and `select_for_update()` on the rows they
modify.

**Concurrency-sensitive state** is state where a lost update or
read-write race would violate business invariants:

| State                              | Why concurrency-sensitive             |
|------------------------------------|---------------------------------------|
| `Stock.quantity` / `reserved`      | Two users checkout same variant       |
| `Cart` during merge                | Guest and user carts modified together |
| `Order._order_number_seq`          | Parallel order creation               |
| `Payment.status` on webhook        | Duplicate webhook delivery            |

Service methods that only insert new rows or modify single-user state
(e.g. creating a `Review`, updating `UserProfile`) do not require
`select_for_update()` but may still use `@transaction.atomic` for
atomicity.

### 3. BaseModel (Abstract Base Class)

**Rule.** All domain models inherit from `BaseModel` (except `User`
which inherits `AbstractUser`).

```python
class BaseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
```

### 4. Denormalization for Performance

**Current implementation.** The `Product` model stores pre-computed
aggregates to avoid expensive JOINs on every listing request:

| Field            | Source                                | Purpose                            |
|------------------|---------------------------------------|------------------------------------|
| `min_price`      | `MIN(variant.price.effective_price)`  | Sort/filter by price without JOIN  |
| `max_price`      | `MAX(variant.price.effective_price)`  | Price range display                |
| `rating`         | `AVG(review.rating)`                  | Sort by rating without JOIN        |
| `reviews_count`  | `COUNT(review)`                       | Display count without JOIN         |
| `views_count`    | `COUNT(product_view)`                 | Popularity sort without JOIN       |

`rating` and `reviews_count` are updated by Django signals on review
save (see [Cross-Domain Coordination](#cross-domain-coordination)).

`min_price` / `max_price` are updated exclusively through the explicit
cross-domain service contract (ARCH-001 Stage 2): `pricing` computes
the bounds from its own `Price` rows and writes them via
`CatalogService.set_product_prices()` — `pricing → catalog`, and
`catalog` never reads `pricing`. See
[Cross-Domain Coordination](#cross-domain-coordination).

### 5. Historical Snapshot Pattern

**Rule.** Order-related data must be snapshot at creation time so that
later changes to the source do not alter historical records.

See [Historical Snapshot Invariants](#historical-snapshot-invariants).

---

## Domain Ownership

Each Django app owns its domain models. Only the owning app's service
layer may mutate that model's state.

| Domain (app)   | Owns                                | May mutate via               |
|----------------|-------------------------------------|------------------------------|
| `catalog`      | `Product`, `ProductVariant`         | `CatalogService`             |
| `pricing`      | `Price`, `PriceHistory`             | `PricingService`             |
| `inventory`    | `Stock`, `StockMovement`            | `InventoryService`           |
| `cart`         | `Cart`, `CartItem`                  | `CartService`                |
| `orders`       | `Order`, `OrderItem`                | `OrderService`               |
| `payments`     | `Payment`, `PaymentEvent`           | `PaymentService`             |
| `shipping`     | `Shipment`, `ShippingMethod`, `ShippingZone` | `ShippingService`   |
| `reviews`      | `Review`, `ReviewHelpfulVote`, `ReviewImage` | `ReviewService`    |
| `discounts`    | `Campaign`, `Coupon`                | `DiscountService`            |
| `users`        | `User`, `Address`, `UserProfile`    | `UserService`, `AddressService`|
| `wishlist`     | `Wishlist`, `WishlistItem`          | `WishlistService`            |
| `notifications`| `Notification`                      | `NotificationService`        |
| `analytics`    | `ProductView`                       | `AnalyticsService`           |

**Rule.** If app A needs to trigger a state change in app B, app A must
call app B's service method — never app B's ORM directly.

**Example (current implementation):**
`OrderService._handle_inventory_transition()` calls
`InventoryService.reserve_stock()` / `release_stock()` /
`commit_stock()` — it never writes to `Stock` or `StockMovement`
directly.

---

## Historical Snapshot Invariants

The following data is **snapshotted** (copied by value) at order
creation time. Later mutations to the source **must not** affect
existing orders.

### `OrderItem.unit_price` — Price Snapshot

- Copied from `Price.effective_price` at checkout.
- If `Price.sale_price` changes after checkout, `OrderItem.unit_price`
  retains the original value.
- `Order.subtotal` and `Order.total` are recalculated from the
  snapshotted `unit_price` values, never from live prices.

### `Order.delivery_cost` — Shipping Cost Snapshot

- Copied from the shipping cost calculation at checkout.
- If `ShippingMethod.base_price` changes later, existing orders
  retain the original delivery cost.

### Order Address — Address Snapshot

- `Order.recipient_name`, `country`, `region`, `city`, `street`,
  `postal_code` are **plain fields** on `Order`, not FK to `Address`.
- If the user edits or deletes their `Address`, past orders retain
  the original delivery address.
- Rationale: legal correctness (receipts, returns, disputes).

### Cross-Domain Ownership Invariants

| Invariant                       | Enforcement                                     |
|---------------------------------|-------------------------------------------------|
| `Payment.user == Order.user`   | `create_payment()` validates `order.user_id == user.pk` |
| `Shipment.user == Order.user`  | `Shipment` created via `ShippingService` which receives the order (ownership checked) |

---

## Django Apps — Current Implementation

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
- JWT access + refresh with token blacklist (`ROTATE_REFRESH_TOKENS=True`)
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
- Celery task: `cleanup_expired_carts` (scheduled via beat)

### `orders` — Order Processing

| Model       | Description                                      |
|-------------|--------------------------------------------------|
| `Order`     | Status machine, address snapshot, order_number   |
| `OrderItem` | Per-variant line: unit_price snapshot, SKU       |

- **Status FSM**: `PENDING → CONFIRMED → PROCESSING → SHIPPED → DELIVERED`
  Any non-terminal state → `CANCELLED`
- `order_number`: auto-generated `ORD-000001` with retry on `IntegrityError`
- `_order_number_seq`: sequential counter with `UniqueConstraint`
- `OrderService.cancel()`: calls `InventoryService.release_stock()`
  and `PaymentService.refund_payment()` for succeeded payments

### `payments` — Payment Processing

| Model          | Description                                     |
|----------------|-------------------------------------------------|
| `Payment`      | Amount, status, provider, external_id, refund   |
| `PaymentEvent` | Audit log for every status change / webhook      |

- **Status FSM**: `PENDING → PROCESSING → SUCCEEDED / FAILED / CANCELLED`
- `SUCCEEDED → REFUNDED` (full or partial)
- `create_payment()`: validates `amount == order.total`
- `confirm_payment()`: catches `ValidationError` and `DatabaseError` specifically
- `handle_webhook()`: idempotent webhook processing

**Current implementation**: mock provider with `external_id = 'mock_<uuid>'`.
The webhook endpoint is `AllowAny` (no JWT — the provider sends the request
without user authentication) and requires HMAC-SHA256 verification via the
`X-Webhook-Signature` header, using `PAYMENT_WEBHOOK_SECRET`.

### `reviews` — Product Reviews

| Model              | Description                                    |
|--------------------|------------------------------------------------|
| `Review`           | Rating 1-5, text, is_approved flag             |
| `ReviewHelpfulVote`| Toggle helpful/unhelpful, unique per user+review|
| `ReviewImage`      | Review images                                  |

- One review per user per product (`UniqueConstraint`)
- Helpful voting: toggle logic (click again to remove vote)
- Sorting/filtering: `?ordering=-rating`, `?rating_gte=4&verified=true`
- Product `rating` / `reviews_count` updated on review save
  (see [Cross-Domain Coordination](#cross-domain-coordination))

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
- Celery task stubs for email delivery (console backend)

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
  ├──1:1── Wishlist ──1:N── WishlistItem ──→ ProductVariant
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

> Uniqueness invariants use `UniqueConstraint`; range/validity invariants
> use `CheckConstraint(condition=...)`.

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

The planned React API client (`client.ts`) will use an Axios interceptor that:
- Attaches the JWT `access` token to every request
- On 401 response, attempts silent refresh via the `refresh` token
- On refresh failure, redirects to `/login`
- Mutating methods (POST, PATCH, PUT, DELETE) **always** include the token
- Only safe GET requests to public endpoints may omit it

---

## Concurrency & Transaction Safety

### When to Use `select_for_update()`

`select_for_update()` is required only for **concurrency-sensitive
state** — rows where a lost update would violate a business invariant
(see Architectural Principles §2).

**Requires `select_for_update()`:**

| Operation                          | Rows locked                    |
|------------------------------------|--------------------------------|
| `InventoryService.reserve_stock()` | `Stock` row for each variant   |
| `InventoryService.release_stock()` | `Stock` row for each variant   |
| `InventoryService.commit_stock()`  | `Stock` row for each variant   |
| `CartService` during merge         | `Cart` row (user + guest)      |
| `OrderService.create_from_cart()`  | `Cart` row                     |
| `PaymentService` status transitions| `Payment` row                  |

**Does not require `select_for_update()`:**

| Operation                          | Reason                                 |
|------------------------------------|----------------------------------------|
| Creating a `Review`                | UniqueConstraint on user+product is sufficient |
| Updating `UserProfile`             | Single-user state, no contention       |
| Creating a `WishlistItem`          | The database uniqueness constraint protects the invariant; the service must handle concurrent IntegrityError appropriately |

### Pattern: `@transaction.atomic` + `select_for_update()`

```python
@staticmethod
@transaction.atomic
def reserve_stock(order):
    stock, _ = Stock.objects.get_or_create(variant=variant, defaults={...})
    stock = Stock.objects.select_for_update().get(pk=stock.pk)
    # ... business logic + F()-expression update ...
```

> **Important.** `select_for_update()` and `get_or_create()` are
> **incompatible** — `select_for_update()` can only lock existing rows.
> The correct pattern is `get_or_create()` first, then
> `select_for_update().get()`.

### Key Protections

| Scenario                    | Protection                                              |
|-----------------------------|---------------------------------------------------------|
| Two users checkout same item| `select_for_update()` locks the `Stock` row             |
| Parallel order numbering    | `UniqueConstraint` + retry loop on `IntegrityError`    |
| Cart merge race             | `select_for_update()` locks the `Cart` row             |
| Payment amount tampering    | `amount != order.total` → `ValidationError`            |
| Double webhook delivery     | Idempotent: already-SUCCEEDED → no-op                  |
| Stock reserved > quantity   | `CheckConstraint(reserved_quantity__lte=F('quantity'))` |

---

## Cross-Domain Coordination

### Current Mechanism: Service Calls

Cross-domain side effects are currently orchestrated by **explicit
service calls** within `@transaction.atomic` blocks:

```
OrderService.transition_status(CONFIRMED)
  → InventoryService.reserve_stock(order)

OrderService.cancel()
  → InventoryService.release_stock(order)
  → DiscountService.release_usage(usage)    # only on PENDING → CANCELLED
  → PaymentService.refund_payment(payment, ...)
```

**Cancellation entrypoint (EDU-002).** `CANCELLED` is reached only through
`OrderService.cancel()`. `transition_status()` rejects `CANCELLED` so it
cannot bypass coupon release, inventory, or payment refund orchestration.
Staff `PATCH /api/v1/orders/{order_number}/status/` with
`{"status": "cancelled"}` routes to `cancel()`; other status values still
use `transition_status()`.

Coupon coordination (`apply_coupon` / `remove_coupon` / `cancel`) follows the
same pattern: `OrderService` owns the transaction and locks
(`Order → Coupon → CouponUsage`), while `DiscountService` mutates only
discounts-owned usage state. See
`docs/architecture/ARCH-001-stage3.md` for the full contract.

This is the **primary** mechanism for cross-domain coordination.

### Price Bounds: `Product.min_price` / `max_price` (ARCH-001 Stage 2)

The denormalized price bounds have exactly one authoritative update path:

```
PricingService.recalculate_product_bounds(product)
  → computes MIN/MAX from its own `Price` rows (ACTIVE variants only)
  → CatalogService.set_product_prices(product, min_price, max_price)
  → catalog.Product
```

Dependency direction: `pricing → catalog` (one-way). `catalog` never
imports `pricing` and never queries price tables.

Variant state that affects the bounds (`is_active` change, variant
deletion) MUST be changed through explicit service calls:

```
PricingService.set_variant_active(variant, is_active=...)  # mutation via CatalogService + recompute
PricingService.delete_variant(variant)                     # mutation via CatalogService + recompute
```

**Concurrency.** Every authoritative price-update path —
`PricingService.set_price()`, `remove_price()`,
`set_variant_active()`, `delete_variant()`,
`recalculate_product_bounds()` (also used by seed commands;
`bulk_set_prices()` delegates to `set_price()`) — runs inside
`transaction.atomic()` and first acquires a row lock on the
authoritative `Product` (`SELECT ... FOR UPDATE`, held until COMMIT):

```
transaction.atomic()
    ↓ lock Product (select_for_update)
    ↓ mutate price-relevant state (Price / variant)
    ↓ calculate authoritative price bounds (pricing-owned)
    ↓ CatalogService.set_product_prices(...)
    ↓ commit
```

The lock covers the **whole** critical section (not just a single
SELECT), so concurrent operations on one `Product` are serialized and
the last committed writer always publishes bounds computed from a
complete, committed view of the `Price` rows — a stale
`min_price`/`max_price` (lost update) is impossible. Lock ordering is
consistent (`Product` first, then variant/price rows), which rules out
deadlocks between these paths. Covered by cross-connection concurrency
tests (`PriceBoundsConcurrencyTests`).

**Rule.** There is NO automatic cross-context reaction to catalog
state changes (no reverse dependency, no cross-context Django signal,
no global listener registry / event bus). Any such mechanism would
hide the cross-domain call path that this document requires to be
explicit. Changing `variant.is_active` directly (Django admin, raw
ORM) leaves `min_price`/`max_price` stale until the next pricing
operation — this is an accepted, documented trade-off of the one-way
architecture.

### Role of Django Signals

Django signals are allowed for local/same-domain housekeeping
and non-critical denormalization.
Cross-domain signals are legacy exceptions.
They MUST NOT be introduced for new cross-domain business workflows.
Existing cross-domain signals must be considered technical debt
and should be migrated to explicit service calls when practical.

**Status (after ARCH-001 Stage 1/2): completed for the
`catalog` ↔ `pricing` boundary.** The former cross-domain
`ProductVariant` signal wiring (`on_variant_change` on `post_save`,
`on_variant_delete` on `post_delete`) has been removed together with
the pricing-side price signals. An earlier revision of this document
claimed that `ProductVariant.post_save` created rows in `inventory`
and `pricing` — that was incorrect: the historical signal only
recomputed `Product.min_price` / `max_price` on `is_active` changes,
and `Price` / `Stock` provisioning has always been performed by
explicit calls to the pricing and inventory services. All signals
currently registered in the codebase are same-domain (logging and
local denormalization); no cross-context Django signal remains on
this boundary. See
[Cross-Domain Signal Migration](#cross-domain-signal-migration).

**Rule.** Django signals must **not** be used as the primary mechanism
for cross-domain business orchestration. They may be used for:

- Same-domain housekeeping (auto-creating related rows)
- Denormalization cache updates (non-critical, eventually consistent)
- Audit logging within the same domain

Cross-domain business rules (stock reservation on order confirmation,
refund on order cancellation) **must** go through explicit service calls
so that:
- The call is visible in the code path (not hidden in a signal)
- Failures can be caught and handled by the caller
- The transaction boundary is explicit

---

## Async Tasks (Celery)

### Configuration (Current)

- **Broker**: Redis
- **Backend**: Redis (task results)
- **Serialization**: JSON (not pickle — security)

### Registered Tasks

| Task                            | Module                  | Purpose                        |
|---------------------------------|-------------------------|--------------------------------|
| `cleanup_old_carts`             | `apps.cart.tasks`      | Remove expired inactive carts   |
| `send_abandoned_cart_reminders` | `apps.cart.tasks`      | Email nudge for abandoned carts|

> Beat schedule (intervals, crontab) is **runtime configuration**
> defined in `config/celery.py` and may be changed without a code
> deployment.

### Task Routing

| Queue     | Tasks                       |
|-----------|-----------------------------|
| `orders`  | `apps.orders.tasks.*`       |
| `cart`    | `apps.cart.tasks.*`         |
| `reviews` | `apps.reviews.tasks.*`      |

> Routing for `orders` and `reviews` queues is configured in
> `config/celery.py`, but only `cart` tasks are currently implemented
> (`cleanup_old_carts`, `send_abandoned_cart_reminders`).

---

## Full-Text Search

On PostgreSQL, the `Product` model uses a `SearchVectorField` with a
GIN index:

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

> **Current state:** the React frontend is planned and documented in
> `frontend-guide/`; no frontend source is committed to this repository yet.
> The sections below describe the target architecture, not current code.

### State Management (Zustand)

| Store                   | Purpose                                 |
|-------------------------|-----------------------------------------|
| `authStore`             | User, tokens, login/logout/refresh      |
| `cartStore`             | Cart items, add/remove/merge            |
| `catalogStore`          | Products, filters, pagination           |
| `wishlistStore`         | Wishlist items, add/remove              |
| `notificationStore`     | Notifications, polling                  |
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
- `Toast` / `ToastContainer` — notification toasts
- `Skeleton` — loading placeholders
- `Header` — categories dropdown, notification bell with badge
- `CartDrawer` — slide-out cart from any page

---

## Docker & Infrastructure

### `docker-compose.yml` Services

| Service      | Image             | Port  | Purpose                    |
|--------------|-------------------|-------|----------------------------|
| `db`         | `postgres`        | 5432  | Primary database           |
| `redis`      | `redis`           | 6379  | Cache + Celery broker      |
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

- Custom test runner: `config.test_runner.AppDiscoverRunner` — fixes
  `unittest.discover()` issues with nested `tests/` packages
- Throttling disabled in tests
- SQLite by default; PostgreSQL required for FTS and `select_for_update`

> Test count as of last measurement: ~950 tests, 0 failures, 2 skipped
> (PostgreSQL-only). This number will change as tests are added or
> refactored.

### Per-App Test Structure

```
tests/
├── factories.py          # create_test_user(), create_test_order(), ...
├── test_models.py        # Model field validation, constraints, methods
├── test_services.py      # Business logic (the bulk of tests)
├── test_api.py           # HTTP endpoint tests (permissions, status codes)
├── test_querysets.py     # QuerySet methods (.active(), .for_user(), ...)
└── test_signals.py       # Signal handlers
```

### Frontend (planned)

- Vitest + React Testing Library + MSW (Mock Service Worker)
- Test files in `__tests__/` directories and `*.test.ts` files
- Not yet implemented — will be added when frontend source is committed

---

## Deployment

### Local Development (Windows)

```powershell
# Backend
py -3 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver

# Frontend — planned, not yet committed (via cmd.exe — PowerShell may block npm)
# cmd /c "npm install"
# cmd /c "npm run dev"
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
| `PAYMENT_WEBHOOK_SECRET`| (empty)                         | Webhook HMAC secret      |
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
- [ ] Set `PAYMENT_WEBHOOK_SECRET` (webhook HMAC verification)
- [ ] Use gunicorn + nginx (not runserver)
- [ ] Enable psycopg3 connection pooling
- [ ] Set up SMTP or django-anymail for email
- [ ] Add rate limiting on payment webhook endpoint

---

## Future Direction

The following are **recommendations** for future evolution. They are
**not currently implemented** and should not be assumed to exist.

### Payment Gateway Abstraction

**Current state**: `PaymentService` uses a mock provider
(`external_id = 'mock_<uuid>'`). There is no `PaymentGateway`
interface or adapter pattern.

**Recommended direction**: Introduce a `PaymentGateway` protocol
(abstraction) with concrete adapters:

```
apps/payments/
├── gateways/
│   ├── base.py          # PaymentGateway protocol (ABC)
│   ├── mock.py          # MockGateway (current behavior)
│   ├── yookassa.py      # YooKassaGateway (future)
│   └── stripe.py        # StripeGateway (future)
```

Each adapter implements `create()`, `confirm()`, `cancel()`,
`refund()`, `verify_webhook()`. HMAC-SHA256 verification of the
webhook endpoint is already implemented; this abstraction would
specialize it per provider.

### Domain Events

**Current state**: Cross-domain coordination uses explicit service
calls (see [Cross-Domain Coordination](#cross-domain-coordination)).

**Recommended direction**: For cases where synchronous coupling is
undesirable (e.g. sending notification emails should not block order
confirmation), introduce lightweight domain events dispatched after
`transaction.atomic` commit:

```python
# Potential future API (not implemented):
@transaction.atomic
def confirm(order):
    # ... business logic ...
    dispatch_event(OrderConfirmed(order))


# Handler (async, via Celery):
@on_event(OrderConfirmed)
def handle(order):
    NotificationService.send_order_confirmed(order)
```

This would replace the current `try/except` pattern in
`OrderService._handle_inventory_transition()` for non-critical
side effects.

### DTO / Projections

**Current state**: Serializers read from ORM models directly, which
can lead to N+1 queries if not carefully managed.

**Recommended direction**: For complex read models (order detail,
product page), consider explicit read-model DTOs or projection
classes that encapsulate the exact query and shape, separate from
write-model serializers.

### Cross-Domain Signal Migration

**Status: completed (ARCH-001 Stage 1/2).** This section previously
described a `ProductVariant.post_save` signal as the "current state"
that auto-creates `Stock` and `Price` rows. That description was
outdated and, historically, inaccurate: the removed signal never
created `Stock` or `Price` rows — it only recomputed price bounds on
`is_active` changes. The signal has been deleted and replaced with
explicit service calls.

Actual architecture (as implemented):

- **No cross-domain `ProductVariant` signal exists.** Creating,
  saving, or deleting a `ProductVariant` triggers no automatic
  reaction in `pricing` or `inventory` and does not recompute
  `Product.min_price` / `max_price`.
- **`Price` provisioning** is an explicit pricing-service operation:
  `PricingService.set_price()` — atomic, locks the authoritative
  `Product` row, writes `Price` + `PriceHistory`, then republishes
  the bounds (`bulk_set_prices()` delegates to `set_price()`).
- **`Stock` provisioning** is an explicit inventory-service
  operation: `InventoryService.get_or_create_stock()` /
  `InventoryService.restock()`.
- **Price bounds are owned by `pricing`**: 
  `PricingService.recalculate_product_bounds()` computes MIN/MAX from
  its own `Price` rows and publishes them through the single catalog
  mutation point `CatalogService.set_product_prices()`.
- **The dependency is one-way `pricing → catalog`.** The reverse
  `catalog → pricing` dependency does not exist in application code
  (models / services / signals / API views / admin): `catalog` never
  imports `pricing` at runtime and never queries price tables. The
  only catalog-package references to pricing are demo/seed management
  commands (`populate_*`), which are outside the runtime dependency
  graph.

Variant lifecycle changes that affect the bounds go through the
explicit service calls documented in
[Cross-Domain Coordination](#cross-domain-coordination)
(`PricingService.set_variant_active()`,
`PricingService.delete_variant()`).

Regression coverage: `apps/catalog/tests/test_signals.py`
(`VariantPriceWiringRemovedTests`) asserts that variant save/delete
and product cascade delete do not trigger price recomputation or
write `Product` price bounds.

### Webhook Security

**Current state**: `POST /api/v1/payments/webhook/` is `AllowAny`
(no JWT) and requires HMAC-SHA256 verification via the
`X-Webhook-Signature` header. The signature is recomputed over the raw
body with `PAYMENT_WEBHOOK_SECRET` and compared timing-safe
(`hmac.compare_digest`). A missing or invalid signature — or a missing
secret — is rejected with `403 Forbidden`.

**Recommended direction**: Specialize webhook signature verification
per provider (YooKassa, Stripe) through the `PaymentGateway` abstraction.

### Denormalization Refresh

**Current state**: `Product.rating` / `reviews_count` are updated
synchronously by `ReviewService.recalculate_product_rating()`;
`Product.min_price` / `max_price` are updated synchronously through
the pricing contract — `PricingService.recalculate_product_bounds()`
→ `CatalogService.set_product_prices()` (ARCH-001 Stage 2; no signals
involved on this path).

**Recommended direction**: For high-write scenarios, decouple
denormalization updates via Celery tasks to avoid write amplification
on the `Product` row.
