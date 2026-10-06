# CIBO GEN-C10 — CAPITAL DIGITAL TWIN V1 PREREGISTRATION

Status: PREREGISTERED / RESEARCH-ONLY / SHADOW / NO PRODUCTIVE AUTHORITY

Policy identity:

`CIBO_GENC10_CAUSAL_CAPITAL_DIGITAL_TWIN_V1`

Frozen at:

`2026-09-30T07:35:00Z`

Frozen semantic digest:

`sha256:d9f8eac29481e502c1f45e8eb1c4f59c6aaa90bfa63ca0dcb067ee7b5620cc0b`

## Research purpose

GEN-C10 creates a causal, account-local Digital Twin of CIBO capital state and
allows explicit hypothetical capital-world transitions without mutating any
productive policy.

It is not a sizing engine, not Risk, not Execution, and not an optimizer.

## Observed state

The observed twin must bind:

- current original/base realized capital;
- reconciled Compound Portfolio economic value;
- protected floor and its policy/broker classifications;
- compound capital states and generations;
- active T19 stop-risk and margin use/headroom;
- non-fungible Capital Source Ledger dimensions;
- provider/account capability evidence;
- currently known capital options only;
- Integrated Capital Truth and Compound Cycle digests.

No evidence produced after the twin capture time may be included.

## Non-fungibility law

Source Ledger dimensions remain separate:

- BASE_RISK_CAPITAL;
- ECONOMIC_PROFIT_CAPITAL;
- RELEASED_RISK_HEADROOM;
- MARGIN_HEADROOM;
- PORTFOLIO_OFFSET;
- RISK_TRANSFER_CAPACITY.

GEN-C10 must never add these dimensions into a fictitious global cash total.

## Scenario worlds

V1 supports explicit worlds:

- AGGRESSIVE_GROWTH;
- BALANCED;
- DEFENSIVE;
- CRISIS;
- OPPORTUNITY_SCARCITY;
- OPPORTUNITY_ABUNDANCE.

These names are scenario identities, not market-probability claims.

## Flow law

All hypothetical realized-capital transitions use one of three flow kinds:

1. INTERNAL_TRANSFER
   - moves existing compound economic value between allowed buckets;
   - cannot reclassify original base in V1;
   - cannot withdraw a protected-floor bucket.

2. SETTLED_GAIN
   - is the only mechanism allowed to increase realized capital;
   - enters REALIZED_PROFIT only.

3. REALIZED_LOSS
   - is the only mechanism allowed to destroy realized capital;
   - may consume ORIGINAL_BASE or DEPLOYED_COMPOUND_CAPITAL only.

Required identity:

`ENDING_REALIZED = STARTING_REALIZED + SETTLED_GAINS - REALIZED_LOSSES`

Residual must equal exactly zero.

## Capacity shocks

Stop-risk and margin capacity are tracked independently from realized cash.

A world may declare explicit signed changes to:

- total stop-risk capacity;
- used stop-risk capacity;
- total margin capacity;
- used margin capacity.

Projected used capacity may never exceed projected total capacity.

## Future-opportunity firewall

A twin may carry only options already known at capture time.

Worlds may:

- remove known options;
- keep known options;
- declare an anonymous hypothetical new-option count.

Worlds may not inject real future opportunity identities or outcomes.

## Provider changes

A world that changes provider constraints requires a separate evidence SHA.

No provider capability may be invented merely because the scenario benefits
from it.

## V1 scientific claims

V1 may claim only:

- state conservation;
- account isolation;
- timestamp causality;
- source-dimension non-fungibility;
- scenario accounting consistency;
- provider evidence binding;
- no future leakage;
- no productive authority.

V1 must keep false:

- calibrated transition uncertainty;
- market probability;
- economic value demonstrated;
- OOS pass;
- stress pass;
- temporal replication pass;
- certification readiness.

## Promotion law

Any future GEN-C10 version that changes flow semantics, allows protected-floor
release, introduces calibrated transition probabilities, or changes provider
assumptions requires a new policy identity, digest and freeze.
