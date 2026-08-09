# QORE-CEO-COMMAND-CENTER-VIEW-MODEL-001 — Platform-Neutral Command Center View Model

Status: **MISSION-05 DELIVERY 9 — PLATFORM-NEUTRAL EXECUTIVE VIEW COMPOSITION**

## Verified baseline

```text
main @ c5dbb183fd8de4d4feb9709fe2bf24bcd2ed802c
```

The baseline already contains MISSION-05 Deliveries 1–8, including the client surface/session/gateway boundaries, explicit state freshness, deterministic notifications, evidence-backed CIBO dialogue and the cross-platform CIBO Widget.

## Purpose

Compose existing client-safe executive state into one deterministic navigation/view model shared by Desktop, iOS and Android without creating a second governance, authority, state-sync or read-model system.

The view model is presentation composition only.

## Canonical navigation

The contract defines the Command Center sections in one stable order:

```text
HOME
CIBO
MARKETS
TRADERS
VALIDATION_LAB
TRADE_FORENSICS
PORTFOLIO
CEO_ACCOUNTS
RISK
NEWS
AUDIT
SYSTEM
GOVERNANCE
CORPORATE_PROFIT_VAULT
```

Platform clients may render this order using different navigation components, but they must not reinterpret scope or authority semantics.

## Existing read-scope binding

Supported sections bind only to already-existing `ExecutiveReadScope` values.

Examples:

```text
CIBO                  -> CIBO_STATE
MARKETS               -> MARKETS
TRADERS               -> TRADERS
VALIDATION_LAB        -> VALIDATION_LAB
TRADE_FORENSICS       -> TRADE_FORENSICS
PORTFOLIO             -> PORTFOLIO
CEO_ACCOUNTS          -> CEO_ACCOUNTS
RISK                   -> RISK
AUDIT                  -> AUDIT
SYSTEM                 -> SYSTEM_HEALTH
GOVERNANCE             -> GOVERNANCE
CORPORATE_PROFIT_VAULT -> CORPORATE_PROFIT_VAULT
```

The delivery deliberately does not invent a new `NEWS` read scope. Because no canonical `ExecutiveReadScope.NEWS` exists in the verified baseline, `NEWS` is represented explicitly as unsupported rather than being mapped to an unrelated scope.

`HOME` is an aggregate presentation section and therefore does not fabricate a read scope of its own.

## State semantics

Each read-backed section is one of:

```text
AVAILABLE
MISSING
```

`AVAILABLE` requires the exact `ExecutiveClientStateView` for that canonical scope.

`MISSING` contains no fabricated client state. It never implies CURRENT.

Sections without a canonical read scope use:

```text
UNSUPPORTED
```

This preserves the MISSION-05 rule that stale, unavailable, unknown or absent client state cannot be silently upgraded into an assumed-current precondition.

The embedded `ExecutiveClientStateView` remains the source of CURRENT / STALE / UNAVAILABLE / UNKNOWN semantics; this delivery does not create a parallel freshness model.

## CIBO Widget composition

The view model may embed an existing `CiboWidgetState`.

The widget must:

- belong to the exact same `ExecutiveClientSurfaceId`;
- not have an observation timestamp later than the containing Command Center view model.

The view model does not add command methods to the widget and does not reinterpret widget attention or evidence semantics.

## Economic separation

`CEO_ACCOUNTS` and `CORPORATE_PROFIT_VAULT` remain separate sections backed by separate canonical read scopes.

The view model must not merge balances, ledgers, account identities or state from these domains into one economic object.

This preserves the existing rule that the Corporate Profit Vault remains isolated from Core/proprietary account state.

## Determinism

The implementation uses:

- immutable `dataclass(frozen=True, slots=True)` values;
- explicit view-model identity;
- explicit timezone-aware observation time;
- deterministic canonical section order;
- duplicate read scopes rejected;
- exact scope binding;
- deterministic `logical_values()`;
- no implicit clock or identity generation.

## Platform boundary

The view model contains no:

- SwiftUI type;
- UIKit type;
- Jetpack Compose type;
- Android View type;
- browser DOM type;
- desktop window type;
- networking client;
- provider/broker client.

Desktop, iOS and Android consume this logical state and adapt only presentation/layout behavior.

## Safety

The view model exposes no:

- buy/sell command;
- submit/cancel order;
- forced trade;
- Risk bypass;
- Portfolio bypass;
- Capital Protection bypass;
- broker/provider credential;
- Production activation.

Presentation does not confer authority.

MISSION-03 Gate #5 remains blocked until OANDA Practice credentials are provisioned through an authorized secret boundary. Nothing in this delivery changes that gate.

Production remains closed.

## Tests

Contract tests verify:

- canonical navigation order;
- exact existing read-scope mapping;
- explicit unsupported NEWS state rather than invented scope;
- missing scopes do not masquerade as current state;
- duplicate scopes fail closed;
- CEO Accounts and Corporate Profit Vault remain separate;
- CIBO Widget surface and chronology binding;
- no platform-specific or trading-execution surface enters the contract.

## Quality gate

```bash
ruff check .
mypy src tests
pytest --cov=src/qore --cov-report=term-missing
```

No suppression or quality-gate weakening is permitted.

## Next delivery

After merge and repository re-verification, continue with:

```text
QORE-CEO-GOVERNANCE-UX-001
```

That delivery must present pending/current/result governance state without implying success before a deterministic Control Plane receipt exists and without automatic redispatch after an ambiguous outcome.
