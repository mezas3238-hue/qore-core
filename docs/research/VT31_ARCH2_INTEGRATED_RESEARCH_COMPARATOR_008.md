# VT31 NAS100 — Integrated Research Comparator 008

**Status:** FROZEN DEVELOPMENT COMPARATOR — SIX-R ALL-FOLD SURVIVOR  
**Base comparator:** `VT31_AB_COMP007_RAPID_BREAKER_UNION_SURVIVOR`  
**Comparator ID:** `VT31_AB_COMP008_BULLISH_H1_MID_CONFIRMATION_SURVIVOR`  
**Source workflow:** `37512573476` — SUCCESS  
**Evaluated head:** `bf2e36da4d15247cdb4f18658be2fa04636b8593`

## Fixed delta from Comparator 007

Comparator 008 preserves the complete Comparator-007 position and admission
stack and adds exactly one predeclared admission conflict:

`BULLISH_H1_BREAKER_SHORT_MID_CONFIRMATION_CONFLICT`

Abstain only when all are true at entry time:

1. entry family = Breaker;
2. side = SHORT;
3. prior-day state = bullish;
4. cash-open state = bullish;
5. H1 state = bullish;
6. the pre-existing confirmation-latency bucket = `MID_6_10M`.

No H4, M15, volatility or reclaim-age condition is added.

The confirmation bucket existed before this hypothesis. No new numeric
threshold was introduced.

## Cross-fold adjudication

The exact same predicate ran unchanged on R5, R6, R8 and recent consumed.

Aggregate result:

- PF non-degrade: 4/4;
- mean-R non-degrade: 4/4;
- observed-DD non-degrade: 4/4;
- density floor: 4/4;
- winner preservation: PASS all folds;
- half-year mean/DD non-degrade: PASS;
- actuated partitions: 2;
- era PF >=1.50: PASS all folds;
- observed DD <=6R: PASS all folds;
- `development_survivor = true`;
- `six_r_all_fold_survivor = true`.

## R5

Comparator 008:

- wins: 12;
- losses: 22;
- PF: 4.8979153506;
- mean: +2.1978178576R/trade;
- observed DD: 5.0099030948R;
- MC positive terminals: 98.56%;
- MC p95 DD: 13.7388787597R;
- excluded versus Comparator 007: 1 loss / 0 winners;
- winner count preservation: 100%;
- winner-R preservation: 100%.

## R6

No actuation; Comparator 007 economics are preserved exactly:

- wins: 7;
- losses: 16;
- PF: 5.1405889146;
- mean: +2.7051847576R/trade;
- observed DD: 5.3944444444R;
- MC positive terminals: 98.97%;
- MC p95 DD: 7.4944444444R;
- winner count preservation: 100%;
- winner-R preservation: 100%.

## R8

No actuation; Comparator 007 economics are preserved exactly:

- wins: 8;
- losses: 13;
- PF: 6.9515788832;
- mean: +3.1203366255R/trade;
- observed DD: 5.0661261261R;
- MC positive terminals: 98.60%;
- MC p95 DD: 7.9494594595R;
- winner count preservation: 100%;
- winner-R preservation: 100%.

## Recent consumed

Comparator 008:

- wins: 8;
- losses: 23;
- PF: 2.4370966149;
- mean: +0.9351167074R/trade;
- observed DD: 5.1397523703R;
- MC positive terminals: 96.29%;
- MC p95 DD: 10.2795047406R;
- excluded versus Comparator 007: 2 losses / 0 winners;
- winner count preservation: 100%;
- winner-R preservation: 100%.

Recent owner-direction gates all pass:

- PF >=1.70;
- mean >=+0.15R/trade;
- observed DD <=6R;
- MC positive >=90%;
- MC p95 DD <=15R.

## Meaning of this freeze

The pure-edge observed-DD blocker is now closed on all four consumed
development partitions.

This does **not** certify VT31.

Comparator 008 is the fixed base for the final pre-holdout robustness and
runtime-parity program.

No further development tweak may be added casually. Any proposed change after
this point requires a separately predeclared gate and must justify why it is
necessary despite Comparator 008 already passing the sovereign 6R observed-DD
gate.

## Required work before Fresh Holdout

Before opening Fresh Holdout, the project must still:

- wire the exact Comparator-008 policy into the runtime path;
- prove replay/runtime semantic parity;
- audit maximum-intelligence accounting;
- audit categorical semantic parsers for substring collisions;
- freeze payoff calculation and result;
- freeze Sharpe formula/annualization and result;
- freeze Sortino formula and result;
- run degraded cost/slippage stress;
- run final temporal/OOS robustness;
- run final Monte Carlo/sequence robustness;
- compute final combined PF and expectancy;
- freeze exact code SHA, config and cognition fingerprints;
- freeze evidence exclusions;
- freeze the final certification candidate.

Only after those gates pass may the fresh sealed holdout be opened exactly once.

## Governance

Fresh Holdout remains sealed.

No sizing, dynamic sizing, leverage, compounding, portfolio weighting, capital
allocation rescue, absolute-volume engineering or CIBO rescue was used to
obtain this survivor.

Comparator 008 is not LIVE authorization, real-capital authorization or final
certification.
