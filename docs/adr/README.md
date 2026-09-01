# Architecture Decision Records

ADRs record architectural decisions that have meaningful long-term consequences.
They document the implemented architecture; an ADR does not itself introduce a
new design or change application behavior.

## Records

- [ADR-001 — Pricing-to-Catalog Dependency Direction](ADR-001-pricing-to-catalog-dependency.md)
- [ADR-002 — Reject Cross-Domain ProductVariant Signals](ADR-002-reject-cross-domain-product-variant-signals.md)
- [ADR-003 — Serialize Product Price-Bound Recalculation](ADR-003-serialize-price-bound-recalculation.md)
- [ADR-004 — Serialize Review Aggregate Recalculation](ADR-004-serialize-review-aggregate-recalculation.md)
- [ADR-005 — Authenticate and Idempotently Process Payment Webhooks](ADR-005-secure-idempotent-payment-webhooks.md)

## Naming

```text
ADR-001-short-description.md
ADR-002-short-description.md
```

## Lifecycle

```text
Proposed -> Accepted -> Superseded / Rejected
```

## Template

Copy `ADR-TEMPLATE.md` and assign the next number.

## Rule

An ADR explains **why** a decision was made. Implementation details belong in
the relevant Issue, PR, or code documentation.
