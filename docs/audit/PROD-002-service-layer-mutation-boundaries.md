# PROD-002 — Service Layer mutation boundaries audit

- **Issue:** #26
- **Date:** 2026-09-01
- **Mode:** read-only inventory first → minimal fixes for confirmed `violation` only
- **Normative refs:** `ARCHITECTURE.md` (Service Layer, Domain Ownership), ADR-001 (seed tooling exception), ARCH-001 H2 (Admin aggregate guards)

## Classification rules

| Label | Meaning |
|-------|---------|
| `allowed` | Mutation lives in the owning app's Service Layer, or is a model-local invariant / same-domain housekeeping already approved by ARCHITECTURE.md |
| `violation` | Business state change from API / admin / task / signal / management command that bypasses the owning Service Layer |
| `exception` | Documented infrastructure / bootstrap / framework path outside the runtime business contract (seed commands, model.save slug helpers, search-vector denormalization, UserProfile auto-create signal) |

## Scope covered

All apps under `apps/`: analytics, cart, catalog, core, discounts, inventory, notifications, orders, payments, pricing, reviews, shipping, users, wishlist.

Entrypoints scanned:

- `api_views/`
- `admin/`
- `signals.py`
- `tasks.py`
- `management/commands/`
- webhooks (`payments` webhook view)
- serializers / managers / querysets / models (for direct mutations)

ORM patterns searched: `.save(`, `.delete(`, `.objects.create(`, `.update(`, `bulk_create`, `bulk_update`, `get_or_create`, `update_or_create`, queryset `.update`/`.delete`.

## Inventory summary

| Class | Count |
|-------|------:|
| Mutation paths audited | **68** |
| `allowed` | **47** |
| `violation` (confirmed, fixed) | **14** |
| `exception` (documented, left) | **7** groups / bootstrap surfaces |

Exact line-level inventory of the 68 paths is summarized by surface below. Seed/populate command internal ORM calls are counted as **one exception group per command** (ADR-001 tooling), not as dozens of individual product-row writes.

### API views

| Path | Classification | Notes |
|------|----------------|-------|
| Most domain API views → `*Service.*` | `allowed` | cart, catalog, orders, payments, reviews, shipping, wishlist, discounts, inventory, analytics, notifications, users profile/address |
| `payments.PaymentWebhookView` → `PaymentService.handle_webhook` | `allowed` | HMAC then service |
| `users.RegisterView` → direct `User.objects.create_user` | **violation → fixed** | now `UserService.register` |
| `users.ChangePasswordView` → `user.set_password` + `save` | **violation → fixed** | now `UserService.change_password` |
| `users.PasswordResetConfirmView` → `set_password` + `save` | **violation → fixed** | now `UserService.reset_password` |
| Read-only `objects.get` in views | `allowed` | lookup only, no mutation |

### Admin

| Path | Classification | Notes |
|------|----------------|-------|
| `ReviewAdmin` / `ProductAdmin` / `ProductVariantAdmin` guards | `allowed` | ARCH-001 H2 / Stage 2 |
| `OrderAdmin` confirm/cancel actions → `OrderService` | `allowed` | |
| `OrderAdmin` form `status` editable | **violation → fixed** | `status` readonly |
| `ShipmentAdmin` form `status`/`shipping_cost` editable | **violation → fixed** | readonly |
| `StockAdmin` `quantity`/`reserved_quantity` editable | **violation → fixed** | readonly |
| `PriceAdmin` `price`/`sale_price` editable | **violation → fixed** | readonly |
| `CouponAdmin` `times_used` editable | **violation → fixed** | readonly |
| `NotificationAdmin` `status`/`sent_at`/`read_at` editable | **violation → fixed** | readonly |
| `CartAdmin.deactivate_selected` queryset.update | **violation → fixed** | `CartService.deactivate_carts` |
| `CategoryAdmin` activate/deactivate bulk + tree form | `exception` | treebeard MoveNodeForm ownership; no CatalogService category mutators; bulk is_active is catalog housekeeping without cross-domain side effects |
| Default ModelAdmin for Brand/Tag/Campaign/Zone/Method CRUD | `exception` | reference data CRUD without dedicated service mutators; no concurrency-sensitive counters |

### Tasks

| Path | Classification | Notes |
|------|----------------|-------|
| `notifications.send_email_notification` → `notif.save` | **violation → fixed** | `NotificationService.mark_sent` |
| `notifications.send_order_confirmation/shipped` → `Notification.objects.create` | **violation → fixed** | `NotificationService.create` |
| `notifications.send_password_reset_email` | `allowed` | email only, no ORM write |
| `cart.cleanup_old_carts` → management command | `allowed` after command fix | |
| `cart.send_abandoned_cart_reminders` | `allowed` | read-only stub |

### Management commands

| Path | Classification | Notes |
|------|----------------|-------|
| `orders.cleanup_stale_orders` → `OrderService.cancel` | `allowed` | |
| `payments.cleanup_stale_payments` → `PaymentService.cancel_payment` | `allowed` | |
| `inventory.check_low_stock` | `allowed` | read-only |
| `cart.cleanup_expired_carts` direct delete/update | **violation → fixed** | `CartService.cleanup_expired_carts` |
| `shipping.cleanup_stale_shipments` direct `shipment.save` | **violation → fixed** | `ShippingService.return_stale_preparing` → `transition_status` |
| `catalog.populate_*` seed ORM | `exception` | ADR-001 bootstrap tooling |

### Signals

| Path | Classification | Notes |
|------|----------------|-------|
| `users.create_user_profile` get_or_create | `exception` | same-domain profile bootstrap (ARCHITECTURE.md) |
| `catalog` main_image + search_vector `.update` | `exception` | same-domain denormalization (ARCHITECTURE.md) |
| `cart` user_logged_in → `CartService.merge_*` | `allowed` | |
| Other domain signals | `allowed` | logging only |

### Models / managers

| Path | Classification | Notes |
|------|----------------|-------|
| Model `.save()` slug / number generators | `exception` | local invariants (Order number, Product slug, Address is_default, Category tree cache) |
| Services' own ORM writes | `allowed` | Service Layer |

## Fixes applied (14 violations)

1. `RegisterView` → `UserService.register`
2. `ChangePasswordView` → `UserService.change_password`
3. `PasswordResetConfirmView` → `UserService.reset_password` (new service method)
4. `send_email_notification` → `NotificationService.mark_sent` (new)
5. `send_order_confirmation` → `NotificationService.create`
6. `send_order_shipped` → `NotificationService.create`
7. `cleanup_expired_carts` → `CartService.cleanup_expired_carts` (new)
8. `CartAdmin.deactivate_selected` → `CartService.deactivate_carts` (new)
9. `cleanup_stale_shipments` → `ShippingService.return_stale_preparing` (new)
10. `OrderAdmin.status` readonly
11. `ShipmentAdmin` status/cost/timestamps readonly
12. `StockAdmin` quantity/reserved readonly
13. `PriceAdmin` price fields readonly
14. `CouponAdmin.times_used` + `NotificationAdmin` status fields readonly

## Exceptions left documented (not rewritten)

1. Seed/populate management commands (ADR-001 tooling).
2. `users` post_save → `UserProfile` auto-create.
3. `catalog` signals: `main_image` + `search_vector` denormalization.
4. Model-local `save()` helpers (slugs, order/payment numbers, Address default invariant, Category treebeard caches).
5. CategoryAdmin treebeard form + bulk is_active (no service mutator; no cross-domain side effects).
6. Reference-data Admin CRUD without dedicated services (Brand, Tag, Campaign, ShippingZone/Method config).
7. Raw ORM/shell outside application entrypoints (accepted trade-off in ARCHITECTURE.md).

## Regression tests added

- `apps/users/tests/test_service_layer_boundaries.py`
- `apps/notifications/tests/test_service_layer_boundaries.py`
- `apps/cart/tests/test_service_layer_boundaries.py`
- `apps/shipping/tests/test_service_layer_boundaries.py`
- `apps/core/tests/test_admin_mutation_guards.py`

## Out of scope (per issue)

- New features, style refactors, frontend, API/model/migration changes beyond the boundary fixes above.
- New ADR (existing ADR-001 + ARCHITECTURE.md already cover seed tooling and signal roles).
