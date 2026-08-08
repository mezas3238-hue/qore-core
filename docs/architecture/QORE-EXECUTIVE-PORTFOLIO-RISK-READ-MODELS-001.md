# QORE-EXECUTIVE-PORTFOLIO-RISK-READ-MODELS-001 — Portfolio & Risk Projections

Status: **PREPARATION READY — CAPITAL ACCOUNT ACTIVATION REMAINS CLOSED**

## Verified base

```text
main @ 1ae543f1b763910d3aad82ef0aa643a2b481f090
```

No open pull request or later main change altered this direction before branch creation.

## Purpose

Define executive projections for the two canonical governance surfaces that already have concrete
repository contracts:

```text
PORTFOLIO
RISK
```

This delivery deliberately does **not** fabricate `CAPITAL_STATE` or `CEO_ACCOUNTS` monetary data.
The verified repository currently has no canonical balance/equity/PnL/drawdown/account snapshot
contract from which those surfaces can be projected.

Repository truth therefore requires:

```text
no canonical financial source contract
        ↓
no invented monetary executive state
        ↓
CAPITAL_STATE / CEO_ACCOUNTS remain gated
```

## Portfolio projection

Current Portfolio contracts model `AllocationIntent` and `PortfolioTarget`: logical allocation,
expressed in basis points, with no positions or live execution.

`ExecutivePortfolioReadModel` preserves that meaning rather than relabeling allocation intent as
broker exposure or actual holdings.

Each allocation summary contains:

- explicit allocation reference;
- explicit source-decision reference;
- governance state;
- deterministic target weights in basis points;
- structured reason codes;
- evidence references.

Target weights must remain unique and sum exactly to 10,000 basis points.

The executive model contains no:

- position quantity;
- broker exposure;
- account number;
- balance/equity;
- order object;
- provider object.

## Risk projection

Current Risk Governance evaluates one deterministic concentration policy:

```text
peak weight > hard limit  -> BLOCKED
peak weight > soft limit  -> DEGRADED
otherwise                 -> APPROVED
```

`ExecutiveRiskConcentrationAssessment` projects exactly that rule. The public assessment carries:

- explicit risk-decision reference;
- allocation reference;
- policy reference;
- soft and hard single-target limits in basis points;
- observed peak weight in basis points;
- deterministic outcome;
- structured reasons;
- evidence references.

The contract independently verifies that the projected outcome matches the same threshold logic.
It cannot label an over-hard-limit allocation as approved.

## Aggregate risk state

`ExecutiveRiskReadModel` exposes descriptive aggregate state:

```text
clear
degraded
blocked
unknown
```

A `clear` projection cannot contain degraded or blocked assessments. A `blocked` projection must
contain at least one blocked assessment.

This state is read-only. It does not create execution authority and does not weaken Risk veto.

## Proprietary boundary

These read models are intended for the CEO proprietary governance surface only. They introduce no
client identity, client account state, settlement, entitlement, profit share, or Profit Vault data.

```text
CEO proprietary governance  X  Corporate Profit Vault
```

remains mandatory.

## Determinism and evidence

- immutable `dataclass(frozen=True, slots=True)` contracts;
- explicit UUID identities;
- strict integer basis points (`bool` is rejected by type checks);
- deterministic target, assessment, reason, and evidence ordering;
- duplicate identities rejected;
- evidence and structured reasons required for projected allocation/risk assertions;
- deterministic `logical_values()`;
- no implicit clock or UUID generation.

## Scope binding

```text
ExecutivePortfolioReadModel -> PORTFOLIO
ExecutiveRiskReadModel      -> RISK
```

Scope mismatch fails closed.

## CAPITAL_STATE and CEO_ACCOUNTS gate

The architecture requires future proprietary account views such as balance, equity, realized and
unrealized PnL, drawdown, and exposure. Those values must come from a separately governed,
provider-neutral financial/account snapshot boundary with explicit currency, identity, timestamps,
freshness and evidence semantics.

This delivery does not guess that boundary and does not reuse Client Profit Vault economics.

The next controlled financial step should therefore establish the canonical proprietary account /
capital snapshot contracts before projecting `CAPITAL_STATE` and `CEO_ACCOUNTS`.

## Safety

This delivery introduces no:

- provider or broker connectivity;
- positions or orders;
- submit/cancel/close command;
- Risk bypass;
- Production account;
- real capital activation;
- Client Profit Vault coupling;
- HTTP/WebSocket/gRPC;
- mobile activation;
- retry/polling/scheduler/thread.

MISSION-03 remains active and unchanged.

## Quality gate

```bash
ruff check .
mypy src tests
pytest --cov=src/qore --cov-report=term-missing
```

No suppression or gate weakening is authorized.
