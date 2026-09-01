# ADR-003 — Serialize Product Price-Bound Recalculation

## Status

Accepted

## Context

`Product.min_price` and `Product.max_price` are denormalized values computed
from `Price` rows for active variants. Concurrent price updates, removals,
variant activation changes, or variant deletions for the same product can
otherwise calculate from incomplete committed state and publish stale bounds.

The price mutation and recomputation paths are already transactional. The
shared authoritative row is `catalog.Product`, not an individual `Price` or
variant row.

## Decision

Every authoritative price-bound path acquires `SELECT ... FOR UPDATE` on the
product row inside `transaction.atomic()` before it mutates price-relevant
state or calculates bounds. The lock is held through the calculation and the
catalog service write, until commit.

This pattern is used by `PricingService.set_price()`, `remove_price()`,
`set_variant_active()`, `delete_variant()`, and the public
`recalculate_product_bounds()` path. The lock order is product first, then
variant/price state.

## Consequences

### Positive

- Concurrent operations for one product are serialized.
- The bounds written at commit are calculated from a complete committed view
  of the relevant prices, avoiding lost updates.
- Direct recalculation callers, including seed commands, use the same guard.
- A consistent lock order avoids deadlocks between these pricing paths.

### Negative / Trade-offs

- Concurrent updates for the same product wait on the product lock.
- The lock is deliberately broader than one query because it protects a
  read-modify-write invariant.
- Bypassing the service layer with raw writes is outside this guarantee.

## Alternatives Considered

- Lock only the `Price` row being changed. Rejected because bound calculation
  is shared across all relevant prices and variants of one product.
- Recalculate after commit or in a signal. Rejected because it can expose
  stale denormalized bounds and hides the coordination path.
- Use `F()` expressions alone. Rejected because MIN/MAX is a recomputation
  over a set of rows, not a single-field increment.

## References

- `ARCHITECTURE.md` — “Concurrency & Transaction Safety” and
  “Cross-Domain Coordination / Price Bounds”.
- `apps/pricing/services/pricing_service.py` — `_locked_product()` and all
  authoritative price-bound paths.
- `apps/pricing/tests/test_services.py` — price-bound and concurrency
  coverage.
- Issue #24 (PROD-001).
