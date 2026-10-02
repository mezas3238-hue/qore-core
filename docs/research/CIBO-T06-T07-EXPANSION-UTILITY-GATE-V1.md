# CIBO T06/T07 Expansion Utility Gate V1

Status: **PREREGISTERED / ENGINE IMPLEMENTED / REAL ECONOMIC EVIDENCE REQUIRED**

Identity:

`CIBO_T06_T07_NONCOMPENSATORY_EXPANSION_UTILITY_GATE_V1`

## Scope

This gate closes the comparison-law ambiguity for:

- T06 — Profit-Funded Expansion;
- T07 — Protected-Capacity Expansion.

It does not close either workstream economically.

The existing burned calibration already proves source/lifecycle causality but
explicitly leaves incremental economic utility uncalibrated. The existing
expansion proposal engine proves reservation and Risk-handoff mechanics. This
gate defines how fresh provider-valid economic evidence must later be judged.

Canonical engine:

`src/qore/infrastructure/cibo_expansion_utility_gate.py`

## Same-population law

Control and treatment must use exactly the same:

- causal population SHA-256;
- provider-economics SHA-256;
- causal horizon and qualification protocol upstream.

T06 and T07 may not be mixed in one gate report.

There must be exactly one control.

## Safety is non-compensatory

A treatment fails safety if it worsens any of:

- peak plausible loss;
- settlement-path drawdown;
- peak margin occupancy;
- capital lock-up duration;
- maximum recovery duration;
- provider failure incidence;
- minimum realized capital;
- optionality preserved.

More realized return or productivity cannot compensate a safety deterioration.

## Strict economic improvement

Only after safety is no worse may a treatment become:

`ELIGIBLE_FOR_FURTHER_RESEARCH`

At least one strict improvement is required in:

- realized net delta;
- capital productivity per risk-minute;
- minimum realized capital;
- optionality preserved.

This status is research eligibility only. It is not a winner, certification,
production promotion, or runtime policy.

## T06 law

T06 may use only already-reconciled realized profit as the economic funding
concept.

It cannot claim:

- original base as self-financing expansion capital;
- floating PnL as spendable capital;
- protected-capacity semantics;
- broker guarantee semantics.

The exact source/reservation lifecycle remains governed by the existing
`cibo_ce2i_expansion_proposal.py` contract and independent QORE Risk.

## T07 law

T07 must identify its protected source as **accounting/economic protection**.

Accounting-protected or policy-protected capital is not automatically
broker-guaranteed.

A broker-guarantee claim is admissible only when a canonical independent
evidence SHA-256 exists. Absence of that evidence means no broker-guarantee
claim.

## Governance

The gate forbids:

- synthetic values;
- future leakage;
- productive authority;
- weighted-score rescue;
- production promotion;
- certification-ready output.

The sealed 2017H1 holdout is not part of this development criterion.

## Terminal implications

After real provider-valid evidence becomes available:

- a treatment with safety deterioration is rejected;
- a safe treatment with no strict economic improvement is rejected;
- a safe treatment with strict improvement is only eligible for the next
  preregistered OOS/stress/temporal-replication stage.

T06/T07 remain open until the full fresh OOS, stress and temporal replication
requirements in the master ledger are satisfied or the candidate is
falsified and closed.
