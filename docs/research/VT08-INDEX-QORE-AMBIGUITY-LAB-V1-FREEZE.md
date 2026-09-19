# VT-08 Index QORE Ambiguity Lab V1 — pre-economic freeze

Status: **RESEARCH ONLY**. This is a QORE experimental search space, not a
claim about the TTrades source methodology and not a promotion artifact.

The retained 2024-08-13..2026-09-11 evidence is already consumed. It may be
used for development selection, but never as fresh or independent validation.
No fresh-holdout result may be opened until one candidate is frozen in a later
commit.

## Immutable universe

- markets: NAS100, SP500, US30 (CFD research proxies)
- anchors: 02:00, 06:00, 10:00 America/New_York
- sides: LONG and SHORT, resolved by the frozen four-case daily bias
- timeframe: M15 evidence, deterministic H4 reconstruction
- costs in this development stage: zero-cost structural-R replay
- same-bar ambiguity: STOP first
- no market, anchor, side, weekday, or date filtering is allowed

## Exhaustive finite grid (512 contracts)

1. closure: `C2_ONLY`, `C2_OR_C3_BODY_CLOSE`,
   `C2_OR_C3_BODY_ENGULF`, `C2_OR_C3_RANGE_ENGULF`
2. protected swing: `UNIQUE_ONLY`, `FIRST_CAUSAL`, `LATEST_CAUSAL`,
   `FARTHEST_STRUCTURAL`
3. stop: `PROTECTED_SWING_EXTREME`, `CISD_LEVEL`
4. target: `1.5R`, `2R`, `2.5R`, `3R`
5. lifecycle: `NEXT_H4_BOUNDARY`, `TWO_H4_BOUNDARIES`
6. daily cardinality: `UNIQUE_ONLY`, `FIRST_CHRONOLOGICAL`

`C2_OR_C3_*` always prefers a completed C2 when present and otherwise admits
the named completed-C3 formalization. These alternatives are deliberately
labelled QORE experiments. They do not resolve source ambiguity.

## Causal and fill rules

- all closures use completed bars only;
- the protected swing/CISD must be confirmed inside the completed closure H4;
- entry is the recorded open of the next H4 candle;
- invalid geometry abstains;
- stops and targets are frozen at entry;
- within each M15 bar, stop is evaluated before target;
- missing bars fail closed;
- first-chronological cardinality uses timestamp order, never outcome.

## Predeclared development eligibility

A variant is eligible for candidate freeze only if all are true:

- at least 120 trades overall;
- at least 25 trades per market;
- at least 20 trades per anchor;
- aggregate mean R > 0 and PF >= 1.05;
- second chronological half mean R > 0;
- at least three of four chronological quartiles have mean R > 0;
- every leave-one-market-out mean R > 0;
- every leave-one-anchor-out mean R > 0;
- max drawdown <= 12R.

Eligible variants are ranked lexicographically by: number of positive
quartiles (descending), worst leave-one-out mean R (descending), second-half
mean R (descending), aggregate mean R (descending), max drawdown (ascending),
then variant id (ascending). If none qualifies, the lab returns `NO_CANDIDATE`
and no economic rule is changed.

## Governance

- CIBO is excluded from signal selection and will be evaluated separately.
- this lab cannot set DEMO_ELIGIBLE, LIVE_AUTHORIZED, or PRODUCTION_AUTHORIZED;
- a selected variant is only a development hypothesis;
- selection consumes this retained window;
- fresh unseen data, stress, Monte Carlo, Risk, CIBO, and independent
  validation remain mandatory after a candidate freeze.

