# QORE NQ AM TEMPORAL LIQUIDITY REVERSAL V2 — 1Y METHODOLOGY HOLDOUT FREEZE

Identity: `QORE_NQ_AM_TEMPORAL_LIQUIDITY_REVERSAL_V2`  
Parent result: `QORE_NQ_AM_TEMPORAL_LIQUIDITY_REVERSAL_V1 = FALSIFIED_BEFORE_HOLDOUT`  
Tracker: #655  
Source video: `UVVmS0de0g0`  
Status: `CONSUMED_1Y_METHODOLOGY_HOLDOUT_ACTIVE / FRESH_CERTIFICATION_DEFERRED`

## 1. Why V2 exists

V1 produced zero trades on 247 consumed-development sessions because its source
translation used a prior RTH low where the reviewed operation explicitly uses a
prior daily / electronic-hours low. V2 is a new identity that repairs that
representation error. V1 remains immutable.

## 2. Owner evidence adjudication

For the immediate question — **does the methodology work?** — a previously
consumed year is explicitly acceptable.

Therefore the one-year interval below is now the active methodology holdout.
Its prior use elsewhere in QORE does not invalidate this feasibility/falsification
experiment. It only prevents the result from being called fresh OOS certification.

The experiment must report the FULL V2 result regardless of outcome.

## 3. Evidence identity

Research market: canonical `NAS100`  
Provider: cTrader DEMO  
Provider symbol: `USTEC`  
Resolution: M1  
Instrument limitation: `USTEC` is a CFD proxy and is **not** exchange NQ futures.

## 4. Frozen V2 mechanics

All market-clock rules use `America/New_York`, DST-aware.

### Electronic-hours daily representation

For each New York trade date `D`, construct the completed session:

`18:00 on D-1 -> 17:00 on D` (end exclusive)

### Daily context

For the most recent completed electronic-hours daily session `P` require:

- `P.close >= midpoint(P.high, P.low)`;
- `P.high > current 09:30 RTH open`.

### RTH gap delivery

Using prior RTH `16:14` settlement and current `09:30` open:

`gap = previous_settlement - current_09:30_open`

Require `gap > 0`.

Define:
- lowest octant = `open + gap/8`;
- lower quadrant = `open + gap/4`;
- downside 2x extension = `open - 2*gap`.

During `09:30 <= t < 09:35` FULL V2 requires:
- no M1 high reaches lower quadrant;
- no M1 close reaches lowest octant.

### Daily sell-side reference

From the prior five completed electronic-hours daily sessions:

1. retain daily lows below current 09:30 open;
2. remove lows already touched after their session close and before current 09:30;
3. retain lows within `gap/4` of the frozen 2x downside extension;
4. select minimum absolute distance to the extension; ties prefer the more recent day.

### Macro and rejection

The selected daily sell-side pool must remain unswept before `10:50`.

Require first penetration during:

`10:50 <= t < 11:00`

From first penetration through `11:00`, every M1 close must remain above:

`max(daily_reference_low, 2x_gap_extension)`.

Wicks may penetrate. Body acceptance below the confluence invalidates the setup.

### Inversion FVG and entry

Search the preceding 60 minutes for bearish M1 FVG:

`third.high < first.low`.

After the sweep, it becomes an inversion candidate only after an M1 close above
its upper boundary.

Entry occurs at the close of the first M1 bar, no later than `11:10`, that:
- overlaps the inverted FVG;
- closes at or above its midpoint.

One trade maximum per RTH day.

### Stop / target / lifecycle

- stop: macro sweep extreme minus one provider tick;
- target: pre-known current-day `09:30` RTH open;
- unresolved position: time exit by `12:00`;
- same-M1 stop/target collision: stop first;
- primary friction: `0.05R`;
- stress friction: `0.10R`.

## 5. No-hindsight laws

At entry V2 must not know:
- final low/high of day;
- later target reach;
- later MAE/MFE;
- later session close;
- later outcome label.

`LOW_OF_DAY` is evaluation language only.

## 6. Active consumed 1Y methodology holdout

Exact interval:

`2024-08-13 NY -> 2025-08-13 NY` (end exclusive)

This one contiguous year is already consumed QORE research evidence, and that is
acceptable by Owner order for the present methodology test.

Result label:

`CONSUMED_1Y_METHODOLOGY_HOLDOUT`

The FULL V2 identity is scored once under the frozen mechanics above.

## 7. Methodology adjudication

Required engineering gates:
- Ruff GREEN;
- mypy GREEN;
- focused causal tests GREEN;
- provider evidence acquisition CLEAN.

Economic evidence is reported with at least:
- trade count;
- primary total R;
- primary PF;
- max DD;
- win/loss;
- false-bottom rate;
- monthly/quarterly decomposition;
- MAE/MFE;
- stress result.

Predeclared interpretation thresholds remain:
- `trade_count >= 12`;
- `primary_total_r > 0`;
- `primary_pf > 1.0`.

Adjudication labels:
- `METHODOLOGY_SUPPORTED_ON_CONSUMED_1Y`;
- `METHODOLOGY_FALSIFIED_ON_CONSUMED_1Y`;
- `INSUFFICIENT_EXECUTABLE_SAMPLE`.

A negative result is retained; V2 is not retuned against the same FULL result.

## 8. Explanatory ablations

After FULL is retained, run:
- `NO_MACRO`;
- `NO_GAP_EXTENSION`;
- `NO_IFVG`;
- `NO_ACCEPTANCE_TEST`;
- `NO_RTH_GAP_CONTEXT`.

These explain where the chain creates/removes edge. They do not replace FULL V2.

## 9. Fresh certification

The prior candidate interval `2015-09-17 NY -> 2016-09-17 NY` is no longer a
prerequisite for the current experiment.

It may be used later only if an independent fresh-certification claim is desired
and provider availability permits it.

## 10. Authority

`DEMO_ELIGIBLE=false`  
`LIVE_AUTHORIZED=false`  
`REAL_CAPITAL_AUTHORIZED=false`  
`PRODUCTION_AUTHORIZED=false`

No merge without explicit Owner order.
