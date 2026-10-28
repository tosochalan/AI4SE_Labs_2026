# NFFH Architecture Discussion Notes — Skill Run

## Scope and source

This is a fresh architecture run based only on `data/NFFH.txt` for system requirements. The architecture-decision-record skill and its ADR template guided the structure. The pre-skill comparison baseline files were not read or changed.

NFFH connects consumers with local agricultural companies. Requirements cover registration/login and persistent sessions for users, company/product discovery, carts and pickup-day orders, farmer inventory and order views, administrator maintenance/reporting, and opening company locations in Google Maps. Payment, delivery, performance targets, and deployment constraints are not specified.

## Three materially distinct options discussed

1. **Modular monolith + one transactional database (proposed recommendation):** one deployable application with logical identity, catalog/inventory, cart/order, company/area, and admin modules. Best-supported initial fit because ordering and stock changes can share a transaction and operations stay comparatively simple. Requires strict module/access boundaries, idempotent checkout, and concurrency-safe stock updates.
2. **Independently deployed domain services:** separately owned identity, catalog/inventory, order, and admin/reporting services with their own data and APIs/events. Offers independent deployment and scaling if justified by team or measured load; adds distributed checkout, eventual consistency, event/retry/reconciliation, and operational burdens not established by the source requirements.
3. **Managed backend / BaaS:** managed identity and data APIs, policy-scoped reads, and trusted server-side functions for checkout and privileged changes. May accelerate delivery and reduce routine infrastructure work if a chosen platform proves its transaction, authorization, quota, recovery, and portability characteristics. Direct data access and policy mistakes are significant risks.

## Recommendation and unresolved trade-offs

Option 1 is recommended **Proposed**, not approved. The source describes coherent marketplace workflows but supplies no evidence that independent deployments or a specific managed platform are needed. The proposal depends on transactional database support and every stock/order write path following the same safeguards.

Important questions remain: multi-company cart/order behavior; pickup-day and capacity rules; stock reservation, cancellation, and expiry semantics; the meaning of “hot”; user/company verification and deletion behavior; reporting freshness; non-functional targets; and platform/team constraints.

## Interaction record

- **User request:** asked for a fresh NFFH architecture assignment run, exactly three materially distinct viable architectures, a complete Proposed ADR, and new discussion notes; explicitly prohibited reading or editing the baseline notes and ADR.
- **Assistant work recorded here:** loaded and read the architecture-decision-record skill, its template, and `data/NFFH.txt`; then prepared the three-option comparison and proposed ADR. No decision approval was provided.
- No precise elapsed time, token count, or reliable wall-clock duration for the work was measured; this note intentionally does not claim such metrics.
