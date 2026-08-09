# QORE-CLIENT-TRIAL-LICENSING-001 — Trial & Licensing

## Status

**IMPLEMENTED — NON-PRODUCTION COMMERCIAL ENTITLEMENT CONTRACTS; PRODUCTIVE BILLING CLOSED**

Opening baseline:

```text
main @ 624dc14e33bd7833a4c5ab00d6fc03b480d6c71a
```

MISSION-07 Delivery 8 defines account-scoped EA trial/licensing semantics while preserving execution safety.

## Trial start invariant

The 14-day trial does **not** start at download, install, registration, device activation or runtime deployment.

It starts only from explicit `FirstEligibleLiveExecutionEvidence` whose eligibility is:

```text
ELIGIBLE_LIVE
```

The evidence binds account, entitlement, originating Core Decision, execution receipt, timestamp and opaque evidence reference.

## Immutable trial origin

After first start:

```text
trial_started_at = first eligible live execution time
trial_expires_at = trial_started_at + 14 days
```

Both timestamps and the first-live evidence reference are immutable historical facts. A second start attempt fails closed.

The license snapshot intentionally has no device/runtime/VPS/terminal identifier. Reinstalling or moving the EA cannot reset the account-scoped trial.

## License states

```text
TRIAL_PENDING
TRIAL_ACTIVE
LICENSED
SUSPEND_PENDING_FLAT
SUSPENDED
UNKNOWN
```

Only `TRIAL_ACTIVE` and `LICENSED` allow **new** trade entitlement.

The existing Client Execution Agent still performs all Core Decision/security/account/policy/risk gates; licensing never becomes strategic trading authority.

## Safe expiration / non-payment

If trial entitlement expires or commercial standing becomes `PAYMENT_FAILED`/`UNKNOWN`:

```text
open_positions > 0 -> SUSPEND_PENDING_FLAT
open_positions == 0 -> SUSPENDED
```

`SUSPEND_PENDING_FLAT` blocks new entries while preserving lifecycle management for positions already authorized before suspension.

Billing/licensing has no method to close, liquidate, retry or redispatch a trade.

## Execution-agent projection

`project_agent_entitlement(...)` converts licensing state into the existing `ClientAgentEntitlementSnapshot`:

- TRIAL_ACTIVE / LICENSED -> ENABLED
- every other state -> BLOCKED

This composes with the existing Agent contract instead of introducing a second execution authorization language.

## Pricing boundary

No USD 29 amount is stored here.

Price belongs to the later versioned Products & Plans catalog. Licensing owns entitlement state and trial chronology, not mutable commercial pricing.

## Tests

The delivery verifies:

- trial starts only on ELIGIBLE_LIVE evidence;
- download/install/registration concepts cannot start it;
- 14-day timestamps cannot be reset;
- device/VPS/runtime changes cannot reset account trial;
- expiry with open positions yields SUSPEND_PENDING_FLAT;
- payment failure blocks entries and transitions to SUSPENDED only when flat;
- unknown commercial state fails closed;
- paid activation preserves original trial history;
- no price, Billing, close-trade or submit-order authority exists.

## Non-goals

No payment processor, invoices, product catalog, broker IO, automatic close, Widget, Hosting, Futures, Production, MISSION-06 activation or MISSION-03 #146 closure.

## Next delivery

After exact-head CI GREEN and merge:

```text
QORE-COMMERCIAL-PRODUCTS-PLANS-001
```