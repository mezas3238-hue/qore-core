# QORE NQ AM TEMPORAL LIQUIDITY REVERSAL V1 — METHODOLOGY VALIDATION CONTRACT

Identity: `QORE_NQ_AM_TEMPORAL_LIQUIDITY_REVERSAL_V1`  
Tracker: #653  
Source video: YouTube `UVVmS0de0g0`  
Status: DEVELOPMENT / 1Y CONSUMED METHODOLOGY REPLAY AUTHORIZED

## 1. Mission

Mechanize the reviewed NQ/NASDAQ AM liquidity-reversal operation as an
independent QORE Trader candidate and answer the immediate Owner question:

> Does this methodology show reproducible economic edge over a full one-year
> market interval?

The immediate experiment is allowed to use already-consumed NAS100 evidence.
Consumption history does NOT block methodology testing. It only changes the
epistemic label of the result.

This identity does not modify VT31 and does not inherit DEMO/LIVE authority.

## 2. Evidence modes

### A. 1Y methodology replay — ACTIVE
- may use already-consumed NAS100 evidence;
- must use one contiguous calendar year;
- candidate mechanics are frozen before the run;
- result answers methodology feasibility / falsification;
- result is labeled `CONSUMED_1Y_METHODOLOGY_REPLAY`;
- no claim of fresh OOS certification is made.

### B. Fresh certification — LATER / OPTIONAL
Fresh evidence is required only if the candidate later seeks an independent
certification claim. It is not a prerequisite for the current methodology test.

## 3. Market identity

- Canonical QORE market: `NAS100`.
- Repository provider mappings may expose `NAS100` or `USTEC` depending on
  evidence generation version; exact provider identity is retained in artifacts.
- cTrader CFD evidence is not exchange NQ futures evidence. The distinction must
  remain explicit.
- V1 direction: LONG only, matching the reviewed source case.
- New York timezone is DST-aware.

## 4. Decision-time causal chain

V1 may become eligible only through information available at decision time:

1. completed prior RTH session reference exists;
2. current RTH open at 09:30 New York is known;
3. an opening gap exists relative to the frozen prior RTH close;
4. price delivers lower from the RTH open toward pre-existing sell-side liquidity;
5. the sell-side reference is swept;
6. the sweep occurs in the frozen AM regime;
7. downside acceptance fails using completed M1 bars only;
8. bullish inversion-imbalance / reclaim evidence forms using completed M1 bars;
9. entry occurs only after that confirmation;
10. stop, targets and expiry are all known at entry.

No rule may use final low of day, final session range, later MFE/MAE, later target
reach, or another post-decision fact.

## 5. Clock semantics

- RTH open anchor: 09:30 New York.
- Reviewed macro window: 10:50 inclusive through 11:10 exclusive New York.
- V1 role of this macro is frozen before the 1Y replay.
- One executed opportunity maximum per New York trading date.

## 6. Mechanical primitives

The implementation exposes independently:
- prior RTH close and current RTH open;
- signed opening-gap geometry;
- octant/quadrant coordinates;
- completed prior-session/day sell-side references;
- first causal sweep timestamp/depth;
- M1 close-based acceptance/rejection;
- three-candle bullish FVG / inversion-FVG state;
- reclaim timestamp and entry envelope;
- structural invalidation below the swept extreme;
- pre-entry target ledger: relative/equal highs, mechanically defined wick CE,
  and 09:30 open;
- lifecycle/expiry.

Undefined source-language concepts fail closed; discretionary hindsight labels
may not be substituted.

## 7. One-year methodology replay

The one-year replay MAY be an already-consumed interval.

Selection rule:
- choose a contiguous one-year NAS100 M1 tranche for which retained/recoverable
  evidence is already known to exist;
- select the window based on availability/provenance, not observed candidate PnL;
- freeze the exact V1 mechanics before running the year;
- run FULL V1 once on that selected year;
- report the result whether positive or negative.

The current preferred evidence family is the already-consumed VT31 M1 historical
corpus because it is native M1 and was collected from the same QORE cTrader
research infrastructure.

## 8. Explanatory ablations

After the FULL 1Y result is retained, explanatory ablations may be run on the
same consumed year:
- NO_MACRO;
- NO_GAP_EXTENSION;
- NO_IFVG;
- NO_ACCEPTANCE_TEST;
- NO_RTH_GAP_CONTEXT.

Ablations explain the result; they do not rewrite the already-scored FULL V1.

## 9. Required result metrics

- eligible sessions and opportunity funnel;
- setups, trades and no-trades;
- win/loss/breakeven;
- gross and friction-adjusted R;
- PF and expectancy;
- max drawdown R;
- max losing streak;
- false-bottom rate;
- MAE/MFE and time-to-event;
- target attribution;
- monthly and quarterly stability;
- stress friction;
- deterministic same-bar collision policy;
- bootstrap/resampling uncertainty;
- evidence fingerprints and exact git SHA.

Primary adjudication:
- `METHODOLOGY_SUPPORTED_ON_CONSUMED_1Y`
- `METHODOLOGY_FALSIFIED_ON_CONSUMED_1Y`
- `INSUFFICIENT_EXECUTABLE_SAMPLE`

These labels are methodology evidence, not DEMO/LIVE certification.

## 10. Governance

`DEMO_ELIGIBLE=false`  
`LIVE_AUTHORIZED=false`  
`REAL_CAPITAL_AUTHORIZED=false`  
`PRODUCTION_AUTHORIZED=false`

No merge without explicit Owner order.
