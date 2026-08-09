# QORE-HOSTING-COMMERCIAL-SUSPENSION-001 — Commercial Safe Suspension

## Status

**MISSION-08 DELIVERY 9 — NON-PRODUCTION CONTRACTS**

This delivery defines the account/runtime-scoped Managed Hosting commercial suspension boundary. It composes payment standing with explicit open-position count to determine whether the hosted runtime may accept new trading work or must preserve only an already-authorized position lifecycle.

It does not mutate Billing, close positions, stop processes, connect to providers or set a Hosting price.

## Product separation

Managed Hosting remains a separate commercial product from the Client Execution Agent and Client Widget.

A Hosting payment or entitlement failure applies to the hosted execution-runtime service only. It does not suspend the Widget and does not rewrite the Core Decision or account strategy.

## Canonical safe-suspension sequence

```text
HOSTING PAYMENT FAILED
 -> block new trades for hosted runtime
 -> if an authorized position is open: SUSPEND_PENDING_FLAT
 -> preserve only the already-authorized position lifecycle/protection
 -> once FLAT: SUSPENDED
 -> hosted runtime may then be stopped/decommissioned by the deployment boundary
```

Billing never receives authority to close or liquidate a trade.

## States

`HostingCommercialState` is closed:

```text
ACTIVE
SUSPEND_PENDING_FLAT
SUSPENDED
UNKNOWN
```

Only `ACTIVE` permits new trading work from the commercial Hosting perspective.

`UNKNOWN` fails closed for new trades. If an authorized position is already open, UNKNOWN preserves the existing lifecycle rather than abandoning protection. If flat, UNKNOWN may be operationally stopped but does not masquerade as a paid/active service.

## Runtime disposition

The commercial boundary emits only one of:

```text
KEEP_ACTIVE
PRESERVE_POSITION_LIFECYCLE
MAY_STOP_WHEN_FLAT
```

These are infrastructure/commercial dispositions, not process-control commands and not trading actions.

`MAY_STOP_WHEN_FLAT` does not stop a runtime by itself. Deployment control remains a separate Hosting Orchestrator responsibility.

## Position lifecycle preservation

`PRESERVE_POSITION_LIFECYCLE` means the runtime may continue only lifecycle/protection actions that were already authorized by the existing position policy and causal execution chain. It cannot originate a new position, strategy, signal or discretionary trade.

The existing invariant remains:

```text
NO CORE DECISION -> NO NEW TRADING ACTION
```

Commercial suspension cannot create a Core Decision and cannot grant execution authority.

## Inputs and evidence

Evaluation binds:

- canonical `TradingAccountId`;
- canonical `ExecutionRuntimeReference`;
- canonical opaque `ProductEntitlementReference`;
- existing `CommercialPaymentStanding` (`CURRENT`, `PAYMENT_FAILED`, `UNKNOWN`);
- explicit non-negative open-position count;
- explicit timezone-aware evaluation time;
- opaque Hosting commercial evidence reference.

No payment method, raw provider credential, broker account number or secret value is retained.

## Pricing boundary

This delivery does not confirm, infer or hardcode a Managed Hosting price. Hosting pricing remains separate and unconfirmed unless a future explicit commercial validation delivery establishes it.

## Isolation

The commercial Hosting snapshot exposes no:

- `close_position` / liquidation authority;
- `submit_order`;
- `mark_paid`;
- Widget suspension;
- risk mutation;
- broker/provider connection;
- retry or redispatch.

## MISSION-08 relationship

This is Delivery 9 of 11. The next ordered delivery is `QORE-MISSION08-E2E-OFFLINE-001`.

MISSION-03 issue #146 remains an external OANDA Practice evidence blocker. MISSION-06 and Production remain CLOSED. Native Broker and Regional Futures remain outside MISSION-08.

## Quality gate

The exact PR head must pass the unchanged repository gate:

```bash
ruff check .
mypy src tests
pytest --cov=src/qore --cov-report=term-missing
```

No `type: ignore`, cast workaround, suppression, test removal or gate weakening is authorized.
