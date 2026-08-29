# ARCH-001 Stage 3 — Coupon Application Coordination

This document supplements `ARCHITECTURE.md` for the Discounts → Orders boundary.

## Ownership

- `discounts` owns `Coupon`, `CouponUsage`, and `Coupon.times_used`.
- `orders` owns `Order.discount` and `Order.total`.
- `DiscountService` validates/calculates discounts and mutates only discounts-owned usage state.
- `OrderService` owns the transaction, Order locks, and Order mutations.

## Coupon usage

`CouponUsage` records an active application:

- `coupon` → `discounts.Coupon`, `PROTECT`
- `order` → `orders.Order`, `PROTECT`
- `user` → `AUTH_USER_MODEL`, `PROTECT`
- `UNIQUE(coupon, order)` prevents duplicate application to one order.
- `(coupon, user)` is indexed for per-user counting.
- `order` is indexed for reverse lookup during removal/cancellation.

`Coupon.times_used` is the denormalized count of active `CouponUsage` rows.
The authoritative mutation paths are `DiscountService.register_usage()` and
`DiscountService.release_usage()`.

## Transaction and lock ordering

Every coupon mutation follows:

```text
Order → Coupon → CouponUsage
```

`OrderService.apply_coupon()` locks the Order first, then the Coupon, validates
fresh limits, counts per-user usage, registers usage, and mutates the Order.
`remove_coupon()` and cancellation use the same prefix and lock the Usage row
only after the Coupon row is held.

The Coupon row is the serialization point for global and per-user usage limits.
The global limit also has a conditional `UPDATE` as defense in depth.

## Semantics

Usage represents an active application, not a lifetime redemption:

- apply: `times_used + 1`
- remove: `times_used - 1`
- cancel: `times_used - 1`
- apply again after remove/cancel: allowed when limits permit

A legacy order with `discount > 0` but no `CouponUsage` is handled gracefully by
remove; it is logged and the discount is cleared without guessing a coupon.

## Cross-context rules

`DiscountService` never mutates `orders.Order` and does not own the outer
transaction. `OrderService` does not directly write `Coupon` or `CouponUsage`;
it calls the discounts-owned usage contracts.

HTTP apply/remove endpoints call `OrderService`. Preview remains a pure
`DiscountService` operation.
