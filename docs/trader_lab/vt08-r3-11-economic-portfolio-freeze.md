# VT-08 R3.11 — Economic Portfolio Freeze

Checkpoint: 2026-09-12

Status: RESEARCH / GOVERNANCE FREEZE ONLY

This document freezes the current VT-08 R3.11 portfolio hypothesis so that subsequent research cannot silently rewrite the economic structure after seeing additional outcomes.

## Frozen working architecture

### Candidate A — CORE

Scope:
- AUDJPY SHORT
- GBPUSD SHORT

Role:
- Conservative core economic sleeve.
- Current consumed-data account replay: approximately +10.61% on normalized $100,000 research equity under the R3.11 fixed-risk replay.
- Current observed max drawdown: approximately 4.92%.
- Current observed profit factor: approximately 1.360.
- Trade count: 117.

Interpretation:
- Candidate A is NOT discarded.
- Candidate A is retained as the lower-frequency / lower-drawdown core hypothesis.
- Candidate A is not independently validated and is not DEMO_ELIGIBLE.

### GBPJPY — RETURN ENHANCER

Scope:
- GBPJPY LONG
- GBPJPY SHORT

Role:
- Incremental return sleeve layered on top of Candidate A.
- Must be evaluated as an additive sleeve, including its marginal return, marginal drawdown, concurrency, correlation, cost sensitivity, and portfolio heat impact.
- It is not allowed to rewrite VT-08 source semantics.
- It is not independently validated and is not DEMO_ELIGIBLE.

### Candidate B — COMBINED PORTFOLIO

Definition:
- Candidate A core
- plus GBPJPY LONG
- plus GBPJPY SHORT

Equivalent scope:
- AUDJPY SHORT
- GBPUSD SHORT
- GBPJPY LONG
- GBPJPY SHORT

Role:
- Combined portfolio hypothesis.
- Current consumed-data account replay: approximately +21.24% on normalized $100,000 research equity under the R3.11 fixed-risk replay.
- Current observed max drawdown: approximately 6.59%.
- Current observed profit factor: approximately 1.345.
- Trade count: 229.

Interpretation:
- Candidate B is NOT a replacement that invalidates Candidate A.
- Candidate B is the portfolio extension of A through the GBPJPY return-enhancer sleeve.
- Candidate B currently produces more aggregate account growth but also higher drawdown and concurrency.
- Candidate B is not independently validated and is not DEMO_ELIGIBLE.

## Frozen decision

The architecture to preserve is:

A = CORE.

GBPJPY = RETURN ENHANCER.

B = COMBINED PORTFOLIO.

Future work must compare:
1. Core-only account economics (A).
2. Marginal economics of GBPJPY as a sleeve.
3. Combined portfolio economics (B).
4. Whether GBPJPY should receive the same, lower, or dynamically capped risk allocation under portfolio Risk.

## Governance restrictions

This freeze DOES NOT authorize:
- merge;
- READY state;
- DEMO_ELIGIBLE;
- LIVE or real capital;
- access to protected unseen holdout data;
- post-hoc anchor changes;
- post-hoc lifecycle changes;
- source-methodology mutation;
- automatic rejection of the remaining seven-market research universe.

The seven-market universe remains the research universe. The A / GBPJPY / B structure is a deployment-economics hypothesis discovered from consumed data and must be validated separately.

## Required next research

Before any fresh holdout is opened, R3.11 must determine:
- marginal return and marginal drawdown of GBPJPY relative to A;
- portfolio heat and concurrent exposure under fixed-risk sizing;
- market/currency correlation and clustered loss behavior;
- market-specific execution-cost sensitivity expressed coherently in account/R economics;
- whether a lower GBPJPY risk allocation can preserve most of B's return while keeping drawdown closer to A;
- multiplicity/data-snooping governance;
- exact primary/challenger preregistration.

This document is a research governance freeze, not proof of profitability.
