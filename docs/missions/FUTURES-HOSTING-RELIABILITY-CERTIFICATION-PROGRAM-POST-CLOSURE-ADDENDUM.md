# Futures & Hosting Reliability Program — Post-Closure Addendum

## Status

**POST-CLOSURE RECORD — NON-PRODUCTION ONLY**

The mandatory Futures & Hosting Reliability Certification Program was already closed before this addendum.

This record exists because optional Delivery 13, `QORE-FUTURES-TRADOVATE-CANDIDATE-001`, was implemented later as a separate post-closure candidate evaluation.

The historical closure remains valid exactly as written for the state that existed when Delivery 17 merged.

## Post-closure change

After program closure, the optional candidate delivery was implemented and merged through PR #233.

Canonical implementation:

```text
docs/architecture/QORE-FUTURES-TRADOVATE-CANDIDATE-001.md
src/qore/infrastructure/futures_tradovate_candidate.py
tests/infrastructure/test_futures_tradovate_candidate.py
```

The candidate is limited to deterministic/offline evaluation and DEMO/SIMULATION translation shape.

It does not claim:

- authenticated Tradovate operational evidence;
- a real Tradovate market-data session;
- an actual Tradovate DEMO order;
- operational ACK/fill/reject evidence;
- Tradovate Production readiness;
- Tradovate LIVE execution authorization.

## Mandatory-provider status remains unchanged

The minimum mandatory provider set remains exactly:

```text
TradeStation
IBKR
tastytrade
```

Tradovate remains an optional fourth candidate and does not replace any mandatory provider.

## Authority invariants remain unchanged

```text
NO CORE DECISION -> NO NEW TRADING ACTION
```

Core continues to connect directly to zero concrete broker APIs.

The Tradovate candidate only translates already-authorized canonical execution requests and contains no network send surface.

Reliability authority also remains unchanged:

```text
NO RELIABILITY EVIDENCE -> NO INFRASTRUCTURE ACTION
```

The candidate adds no failover authority, provider-switch authority, execution lease authority or infrastructure remediation authority.

## External blocker remains independent

Issue #146 — MISSION-03 Gate #5 OANDA Practice operational evidence — remains independent and must still satisfy its own authenticated evidence criteria.

The optional Tradovate candidate cannot substitute for OANDA Practice evidence and does not advance MISSION-03 Gates #5 through #9.

## Production boundary

After the post-closure optional candidate integration:

```text
Mandatory Futures/Hosting program = COMPLETED
Optional Tradovate candidate      = OFFLINE EVALUATED
Tradovate operational evidence    = REQUIRED
MISSION-03 Gate #5 / issue #146   = OPEN/BLOCKED
Production                        = CLOSED
Futures Production                = CLOSED
Native Broker Production          = CLOSED
Real capital                      = CLOSED
```

## Governance rule

Any future promotion of Tradovate beyond offline candidate status requires a new explicit repository delivery with its own operational evidence contract and unchanged QORE Quality Gate.

No post-closure addendum may retroactively rewrite historical CI evidence, merge SHAs, certification claims or the state that existed at original program closure.
