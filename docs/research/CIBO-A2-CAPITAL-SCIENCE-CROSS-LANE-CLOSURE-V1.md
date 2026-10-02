# CIBO A2 Capital Science — Cross-Lane Closure V1

Status: **A2 LOCAL ENGINEERING CLOSURE / PHASE22 OUTCOME SCIENCE STILL FAIL-CLOSED**

Owner lane: Architect A2 — Capital Science

Branch:

`agent/cibo-architect-a2-capital-science-001`

## Purpose

Close the two explicit A1↔A2 scientific-interface gaps without transferring
ownership and without weakening the Phase22 one-shot scientific boundary.

## Gap 1 — historical COMPOUND_ENGINE lineage

Implemented:

`src/qore/infrastructure/cibo_a2_phase22_historical_compound.py`

The adapter consumes canonical
`VersionedPhase22HistoricalReplayEvidenceBook` outcomes and creates Compound
source lots only from positive realized replay PnL.

It deliberately does **not** create, require, infer or relabel historical broker:

- position ids;
- deal ids;
- order ids;
- fill ids.

The adapter proves:

- realized-profit-only source capital;
- floating PnL excluded;
- one source outcome can create at most one source lot;
- total lot capital equals the positive realized source PnL;
- decision-before-outcome chronology;
- deterministic replay;
- no fabricated historical execution identity.

It emits a JSON-compatible receipt for the exact A1 consumer contract:

`CIBO_A1_PHASE22_HISTORICAL_COMPOUND_LINEAGE_DEPENDENCY_V1`.

## Gap 2 — INTERNAL_CAPITAL_MARKET / GEN-C6 receipt

Implemented:

`src/qore/infrastructure/cibo_a2_internal_capital_market_phase22_receipt.py`

The receipt binds an exact true-scarcity decision population to:

- source workstream `INTERNAL_CAPITAL_MARKET`;
- exact A2 source HEAD;
- exact artifact digest;
- canonical Phase22 manifest digest;
- source-population digest;
- deterministic decision-population digest;
- frozen `GENC6_POLICY_ID`;
- exact `genc6_policy_sha256()`;
- outcome-freeze preservation;
- capital-conservation checks.

The builder rejects:

- non-scarcity rows;
- duplicate decision identity;
- outcome-present-at-seal decisions;
- policy drift;
- any control/treatment/reserve amount above available capital;
- runtime/Risk/execution/LIVE/real-capital authority.

## Ownership

A2 owns:

- `COMPOUND_ENGINE`;
- `INTERNAL_CAPITAL_MARKET`.

A1 remains a read-only consumer. These receipts do not allow A1 to close or
modify either source workstream.

## Scientific boundary

This closure removes local cross-lane engineering debt. It does **not** invent
the Phase22 V2 outcome population and does not convert missing fresh evidence
into a scientific PASS.

The 17 A2 Capital Science workstreams still require their canonical Phase22
scientific outcome receipts before they may move from external-blocked state to
`COMPLETED_AND_PROVEN` or `FALSIFIED_AND_CLOSED`.

## Governance

- Master Ledger modified: **false**
- Phase22 V2 one-shot consumed by A2: **false**
- Integrator branch modified: **false**
- VPS touched: **false**
- FundedNext LIVE touched: **false**
- real capital used: **false**
- productive authority: **false**
- certification claimed: **false**
