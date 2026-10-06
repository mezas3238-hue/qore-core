# CIBO T14/T15 Causal Pareto Utility Gate V1

Status: **PREREGISTERED / ENGINE IMPLEMENTED / REAL OOS EVIDENCE REQUIRED**

Identity:

`CIBO_T14_T15_CAUSAL_PARETO_UTILITY_GATE_V1`

## Why this gate exists

T14 already has dynamic de-risking mechanics and forward position-path readiness.

T15 already has known-option reservation/realization evidence, but its own audit
correctly states that observing a later option does not identify the causal
effect of having reserved capital for it.

This gate freezes the utility comparison law before qualifying outcomes are used
to promote either tool.

## Shared comparison law

Every control/treatment pair must use the same:

- causal population SHA-256;
- provider-economics SHA-256;
- causal horizon SHA-256.

T14 and T15 are evaluated separately and may not be mixed in one report.

No weighted score is permitted.

## T14 — Dynamic De-risking

T14 may reduce/release exposure but may not:

- widen or manufacture the Trader structural stop;
- override Trader methodology;
- override QORE Risk;
- introduce recovery sizing;
- use a future opportunity oracle;
- synthesize missing economics.

The treatment must be Pareto no-worse than control for:

- realized net delta;
- peak plausible loss;
- settlement-path drawdown;
- peak margin occupancy;
- minimum realized capital;
- maximum recovery time;
- optionality preservation.

After all no-worse gates pass, at least one strict utility improvement is
required. Eligible strict dimensions include lower loss/DD/margin/recovery,
higher minimum capital, higher capital productivity, greater optionality, or
more stop-risk-minutes safely released.

Therefore T14 cannot claim success merely by reducing exposure.

## T15 — Optionality

T15 must satisfy all shared Pareto rules and must additionally bind the same
pre-decision known-option set SHA-256 for control and treatment.

Most importantly:

`KNOWN_OPTION_REALIZATION != CAUSAL_UTILITY_IDENTIFICATION`

A treatment is rejected as:

`REJECTED_CAUSAL_IDENTIFICATION`

unless its causal effect has been identified by the legal comparison design.

This prevents a future candidate from being used as an oracle or from being
credited to a reserve decision merely because it later appeared.

Once causal identification is valid, strict improvement may include a greater
number of known options that remained executable, but only if all Pareto
no-worse conditions also hold.

## Status semantics

Possible treatment states:

- `REJECTED_CAUSAL_IDENTIFICATION`
- `REJECTED_GOVERNANCE`
- `REJECTED_PARETO_DETERIORATION`
- `REJECTED_NO_STRICT_UTILITY_IMPROVEMENT`
- `ELIGIBLE_FOR_FURTHER_RESEARCH`

`ELIGIBLE_FOR_FURTHER_RESEARCH` is not:

- a winner;
- runtime promotion;
- certification;
- authority to alter Trader/Risk/Execution.

## Holdout and evidence

The 2017H1 sealed holdout is excluded from development.

Fresh OOS, stress and temporal replication are still required by the master
ledger before T14 or T15 can receive a terminal scientific disposition.
