# ADR-004 — Serialize Review Aggregate Recalculation

## Status

Accepted

## Context

`reviews` calculates the average rating and approved-review count, while
`catalog` owns the denormalized `Product.rating` and `Product.reviews_count`
fields. Creating, editing, deleting, approving, or rejecting reviews can
change those aggregates. Concurrent aggregate operations on one product can
otherwise overwrite a result calculated before another transaction commits.

A review's unique user/product constraint protects duplicate review creation,
but it does not protect the aggregate read-modify-write sequence.

## Decision

Run aggregate-affecting review service methods in `transaction.atomic()` and
lock the authoritative `Product` row with `SELECT ... FOR UPDATE` before
calculating approved-review `AVG`/`COUNT` values. The lock remains in force
through `CatalogService.set_review_stats()` until the caller's transaction
commits.

`ReviewService` owns the aggregate calculation; `CatalogService` is the
single service-level writer of the catalog fields. The legacy
`Product.update_rating()` path is absent, and review signals are not used for
this mutation.

## Consequences

### Positive

- Aggregate-changing operations for one product serialize and do not lose an
  approved review in the published count or average.
- Calculation ownership and field-write ownership remain explicit.
- The catalog service contract prevents a second review-side ORM writer.
- Existing cross-connection tests exercise the protected paths and the final
  aggregate invariant.

### Negative / Trade-offs

- Concurrent review moderation or edits for the same product can wait on the
  product lock.
- The review service intentionally depends on catalog's public contract.
- Raw ORM writes outside the service/admin paths are not covered by this
  application-level protocol.

## Alternatives Considered

- Rely only on the review uniqueness constraint. Rejected because it does not
  serialize aggregate recomputation.
- Update product aggregates directly from `reviews`. Rejected because the
  fields belong to catalog.
- Recompute through a cross-domain signal or asynchronous task. Rejected
  because the current invariant requires an explicit, synchronous
  transactional write path.

## References

- `ARCHITECTURE.md` — “Cross-Domain Coordination” and “Concurrency &
  Transaction Safety”.
- `apps/reviews/services/review_service.py` — `_locked_product()` and
  `recalculate_product_rating()`.
- `apps/catalog/services/catalog_service.py` — `set_review_stats()`.
- `apps/reviews/tests/test_concurrency.py` and
  `apps/reviews/tests/test_architecture.py` — locking and ownership coverage.
- Issue #24 (PROD-001).
