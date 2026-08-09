# QORE-CEO-GOVERNANCE-UX-001 — Safe Executive Governance Presentation

Status: **MISSION-05 DELIVERY 10 — GOVERNANCE UX CONTRACTS**

## Verified baseline

```text
main @ 27e3fafffe72970b890609883b9834bda95c38a1
```

MISSION-05 Delivery 9 is merged. MISSION-04 remains the canonical authority, replay, dispatch and audit foundation.

## Purpose

Define presentation semantics for already-authorized CEO governance actions without creating a second dispatcher or implying that an intent succeeded before a canonical Control Plane receipt exists.

## Lifecycle

The presentation lifecycle is closed:

```text
PENDING
APPLIED
NO_ACTION
BLOCKED
FAILED
OUTCOME_UNKNOWN
```

`PENDING` means only that an already-authorized governance intent is being represented. It contains no downstream receipt and is never treated as applied.

Terminal states derive only from the exact `ExecutiveControlReceipt`:

```text
APPLIED   -> APPLIED
NO_CHANGE -> NO_ACTION
BLOCKED   -> BLOCKED
FAILED    -> FAILED
```

The UX does not infer a successful mutation from optimism, local UI state, elapsed time, notification state or cached data.

## Ambiguous outcome containment

`OUTCOME_UNKNOWN` represents the safety-critical case where replay protection proves the exact control-dispatch identity was acquired, but no canonical control receipt is available to prove the downstream result.

It requires an exact `ExecutiveReplayClaimReceipt` with:

- `CONTROL_DISPATCH` operation;
- the same intent identity;
- the same executive principal;
- the same authority version;
- the same correlation identity;
- `ACQUIRED` status.

A duplicate or conflicting replay claim cannot masquerade as an ambiguous executed request.

Every governance UX state reports:

```text
automatic_redispatch_allowed = false
```

An ambiguous result therefore never becomes a reason to retry automatically. Recovery must follow the existing governed resilience/re-read rules.

## Exact binding

Terminal receipts must match the exact authorized intent on:

- intent ID;
- principal;
- action;
- target;
- authority version;
- correlation ID;
- chronology.

A receipt from another request fails closed.

## Presentation only

The contract contains no dispatch method, replay claim operation, provider connection, command port, mutation port, database, transport or platform UI type.

It may be rendered by Desktop, iOS or Android, but none of those platforms gains additional authority from the presentation state.

## Safety

The delivery introduces no:

- buy/sell/order entry;
- forced execution;
- Risk bypass;
- Portfolio bypass;
- Capital Protection bypass;
- Production activation;
- broker/provider credential;
- hidden retry;
- scheduler/thread/sleep;
- implicit clock;
- implicit identity generation.

Production remains closed.

MISSION-03 Gate #5 remains operationally blocked pending authorized OANDA Practice provisioning.

## Determinism

The implementation preserves:

- immutable `dataclass(frozen=True, slots=True)` values;
- explicit UUID identity;
- explicit timezone-aware timestamps;
- closed enums;
- canonical reason codes;
- deterministic receipt/replay binding;
- deterministic `logical_values()`.

## Tests

Contract tests prove:

- pending never claims success without a receipt;
- each canonical control receipt maps to exactly one UX phase;
- mismatched receipts fail closed;
- ambiguous outcome requires an exact acquired replay claim;
- duplicate replay cannot masquerade as executed ambiguity;
- automatic redispatch is always forbidden;
- no trading or dispatch surface enters the presentation contract.

## Quality gate

```bash
ruff check .
mypy src tests
pytest --cov=src/qore --cov-report=term-missing
```

No suppressions or quality-gate weakening are permitted.

## Next delivery

After merge and repository re-verification, continue with:

```text
QORE-CEO-DESKTOP-001
```

The Desktop reference composition must consume the same platform-neutral session, gateway, state-sync, Command Center view model, CIBO Widget and Governance UX contracts without direct Core access.
