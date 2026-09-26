# CE2I ADR-001 — CIBO Sizing Sovereignty and Self-Financing Capitalization

Status: **OWNER-DIRECTED / ACTIVE ARCHITECTURE / RESEARCH IMPLEMENTATION**

PR: #651

## Decision

Trader-owned sizing is deprecated as a future authority model.

The target architecture is:

```text
TRADER
  owns signal + entry + structural stop + target + certified lifecycle semantics
        |
        v
CIBO CE2I
  owns sizing + initial exposure + capitalization policy + exposure expansion
        |
        v
QORE RISK
  owns final monetary/margin/account admission and may ALLOW / REDUCE / REJECT
        |
        v
EXECUTION
```

Existing Trader sizing formulas remain only as **LEGACY BASELINE EVIDENCE** for reconstruction and
comparison. They are not the target authority contract.

## Owner objective

Start every valid opportunity with the **smallest methodology-compatible executable exposure**.

Then preserve the Trader's certified management procedure until the initial base-capital risk has
been recovered/protected.

Only after that recovery is causally verified may CIBO use CE2I capitalization tools to increase
economic output.

## Canonical lifecycle

### STAGE A — MINIMAL SEED

CIBO chooses the minimum viable executable volume:

```text
MINIMAL_SEED_VOLUME =
max(
    broker_minimum_volume,
    methodology_minimum_execution_steps * broker_volume_step
)
```

The seed must still be capable of expressing the Trader's certified lifecycle.

Example: if a certified lifecycle requires four executable quarter-legs, one broker step is not a
valid seed even if the broker technically accepts it.

The seed is rejected if its stop-risk or margin exceeds the currently authorized envelope.

### STAGE B — CERTIFIED RECOVERY

No CE2I expansion is allowed while base capital remains exposed to a negative reconciled economic
floor.

The Trader's certified lifecycle continues to own *how the position is managed*.

CIBO observes the lifecycle and computes the current economic floor from reconciled facts:

- realized PnL;
- remaining volume;
- current protected stop;
- worst-case stop PnL;
- commissions/fees/slippage reserve;
- other certified lifecycle state.

CIBO does not invent a recovery action that was not part of the certified Trader lifecycle.

### STAGE C — CAPITAL RECOVERY GATE

The initial capital is considered recovered only when authoritative evidence proves:

```text
RECONCILED_BASE_CAPITAL_AT_RISK <= 0
```

and any positive funding capacity is derived from:

```text
SELF_FINANCING_CAPACITY =
max(
    0,
    REALIZED_NET_PROFIT
  + PROTECTED_OPEN_ECONOMIC_FLOOR
  - COST_RESERVE
  - ALREADY_RESERVED_EXPANSION_RISK
)
```

A merely positive floating PnL is not sufficient.

A theoretical stop move that is not broker-confirmed/reconciled is not sufficient.

### STAGE D — SELF-FINANCING EXPANSION

After the recovery gate, CIBO may evaluate its CE2I toolbox.

The maximum new monetary loss introduced by an expansion must not exceed the currently proven
self-financing capacity, subject to QORE Risk.

Therefore:

```text
NEW_EXPANSION_RISK
<= SELF_FINANCING_CAPACITY
<= QORE_RISK_AUTHORIZED_CAPACITY
```

This means the expansion must be funded by already realized or protected economic gain rather than
silently re-risking the original seed capital.

## Hard prohibitions

CE2I V1 prohibits:

- martingale;
- loss-recovery sizing;
- averaging down merely because price moved against the entry;
- increasing size to recover a previous loss;
- increasing size while the reconciled economic floor is negative;
- treating floating profit as realized capital;
- counting the same protected/realized dollar twice;
- widening the Trader's stop to create expansion capacity;
- tightening the Trader's stop merely to manufacture more volume;
- changing the Trader's certified lifecycle to satisfy a CIBO sizing objective.

## What Trader still owns

Trader owns:

- whether a setup exists;
- side;
- entry geometry;
- structural invalidation;
- target geometry;
- certified management transitions;
- certified lifecycle semantics;
- signal cancellation/expiry semantics.

Trader does **not** own final volume in the target architecture.

Any Trader-produced risk scale or legacy requested volume becomes diagnostic metadata only.

## What CIBO owns

CIBO owns:

- initial seed volume;
- exposure budget selection;
- capital-efficiency comparison;
- margin-efficiency comparison;
- capitalization tool selection;
- self-financing expansion quantity;
- opportunity competition;
- reserve/optionality decisions;
- capital recycling recommendations;
- exposure de-escalation requests where methodology permits.

## What Risk owns

QORE Risk remains sovereign over:

- maximum monetary loss;
- account-wide headroom;
- margin headroom;
- provider constraints;
- correlation/concentration ceilings;
- reservation integrity;
- final authorized volume;
- hard account survival rules.

CIBO cannot override Risk.

## Migration rule

Current functions such as:

- `build_r34_risk_request`;
- `build_r38_risk_request`;
- `build_r43_risk_request`;
- `build_r38_gbpjpy_risk_request`;
- `build_r42_audjpy_risk_request`;
- VT31 certified-risk volume construction;
- VT08 symbol-BPS sizing;

are treated as **legacy sizing producers**.

The migration target is:

```text
LEGACY TRADER:
signal -> trader risk scale -> volume -> CiboRiskRequest

TARGET:
signal -> TraderOpportunityEnvelope
       -> CIBO Sizing Authority
       -> CiboRiskRequest
       -> QORE Risk
```

## Certification requirement

A Trader is not required to be re-certified merely because CIBO starts with less exposure, provided:

- signal geometry is unchanged;
- stop/target are unchanged;
- lifecycle semantics are unchanged;
- reduced initial exposure can still express every certified management action.

Any CE2I expansion changes the economic position path and therefore requires independent CE2I
validation before production use.

## Current implementation scope

PR #651 implements the authority contract and research logic only.

It does not change LIVE, VPS runtime or real capital by itself.

The legacy sizing reconstruction remains valuable because it provides the baseline against which
CIBO-owned sizing must be measured.
