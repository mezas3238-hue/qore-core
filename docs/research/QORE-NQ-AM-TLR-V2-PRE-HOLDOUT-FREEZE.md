# QORE NQ AM TEMPORAL LIQUIDITY REVERSAL V2 — PRE-HOLDOUT FREEZE

Identity: `QORE_NQ_AM_TEMPORAL_LIQUIDITY_REVERSAL_V2`  
Parent result: `QORE_NQ_AM_TEMPORAL_LIQUIDITY_REVERSAL_V1 = FALSIFIED_BEFORE_HOLDOUT`  
Tracker: #655  
Source video: `UVVmS0de0g0`  
Status: `CONSUMED_DEVELOPMENT_ONLY / FRESH_1Y_HOLDOUT_SEALED`

## 1. Why V2 exists

V1 was not rejected because of losing economics. It produced zero trades before the
fresh holdout and exposed a source-translation defect: it modeled the source
liquidity reference as a prior RTH low even though the reviewed operation explicitly
uses a prior **daily / electronic-hours low**.

V2 is a new scientific identity. V1 remains immutable. No V1 result is rewritten.
The fresh 1Y holdout was never opened by V1.

## 2. Evidence identity

Research market: canonical `NAS100`  
Provider: cTrader DEMO  
Provider symbol: `USTEC`  
Resolution: M1  
Instrument limitation: `USTEC` is a CFD proxy and is **not** exchange NQ futures.

A positive USTEC result does not by itself validate exchange-futures execution or
microstructure equivalence.

## 3. Frozen V2 mechanics

All market-clock rules use `America/New_York`, DST-aware.

### Electronic-hours daily representation

For each New York trade date `D`, V2 constructs a completed daily session:

`18:00 on D-1 -> 17:00 on D` (end exclusive)

The completed session contributes only facts available before the next RTH decision:
its high, low and final observed close.

### Daily context

Let the most recent completed electronic-hours daily session be `P`.
V2 requires:

- `P.close >= midpoint(P.high, P.low)`; and
- `P.high > current 09:30 RTH open`.

This is QORE's frozen causal discretization of the source's higher-timeframe bullish
context. It is not claimed to be a universal ICT rule.

### RTH gap delivery

Using the previous RTH `16:14` settlement and current `09:30` RTH open:

`gap = previous_settlement - current_09:30_open`

Require `gap > 0`.

Define:

- lowest octant = `open + gap/8`;
- lower quadrant = `open + gap/4`;
- downside 2x opening-gap extension = `open - 2*gap`.

During `09:30 <= t < 09:35` FULL V2 requires:

- no M1 high reaches the lower quadrant; and
- no M1 close reaches the lowest octant.

### Daily sell-side reference

From the prior five completed electronic-hours daily sessions:

1. retain daily lows below the current 09:30 open;
2. remove a daily low if any later provider M1 low has touched or penetrated it
   from that daily session's 17:00 close through the current 09:30 open;
3. among remaining daily lows, retain only those within one opening-gap quadrant
   (`gap/4`) of the frozen 2x downside extension;
4. select the candidate with minimum absolute distance to the extension; ties prefer
   the more recent daily session.

The `gap/4` tolerance is a preregistered QORE discretization of the source example's
statement that the daily low and 2SD level are sharing the same price business. It is
not attributed to the source author as a universal numeric threshold.

### Macro and rejection

FULL V2 requires the selected daily sell-side pool to remain unswept before `10:50`.

Require first penetration during:

`10:50 <= t < 11:00`

From first penetration through `11:00`, every M1 close must remain above:

`max(daily_reference_low, 2x_gap_extension)`.

Wicks may penetrate. Body acceptance below the confluence invalidates the setup.

### Inversion FVG and entry

Search the preceding 60 minutes for a bearish M1 FVG:

`third.high < first.low`.

After the sell-side sweep, the bearish FVG becomes an inversion candidate only after
an M1 close above its upper boundary.

Entry occurs at the close of the first M1 bar, no later than `11:10`, that:

- overlaps that inverted FVG; and
- closes at or above its midpoint.

One trade maximum per RTH day.

### Stop / target / lifecycle

- structural stop: macro sweep extreme minus one provider tick;
- economic target: the pre-known current-day `09:30` RTH open;
- unresolved position: time exit by `12:00`;
- same-M1 stop/target collision: stop first;
- primary friction: `0.05R`;
- stress friction: `0.10R`.

The 09:30-open target is QORE's V2 falsification target for this source operation; it
is not a claim that every source-author execution always exits there.

## 4. No-hindsight laws

At entry V2 must not know:

- the final low or high of day;
- later target reach;
- later MAE or MFE;
- later session close;
- later macro behavior;
- any final outcome label.

`LOW_OF_DAY` is evaluation language only. It is never an input feature.

Appending bars after the bounded AM lifecycle must not change the already-frozen
entry or resolved outcome.

## 5. Consumed development evidence

Development interval:

`2024-08-13 NY -> 2025-08-13 NY` (end exclusive)

This interval is already consumed NAS100 research evidence and is used only for
engineering, source-fidelity falsification and the preregistered pre-holdout gate.
It can never become fresh V2 evidence.

## 6. Preregistered development gate

FULL V2 may advance toward the fresh holdout only if all of the following are true:

- Ruff: GREEN;
- mypy: GREEN;
- focused causal tests: GREEN;
- provider evidence acquisition: CLEAN;
- `trade_count >= 12`;
- `primary_total_r > 0`;
- `primary_pf > 1.0`.

This gate is fixed before the V2 consumed-development replay.

If it fails:

`QORE_NQ_AM_TEMPORAL_LIQUIDITY_REVERSAL_V2 = FALSIFIED_BEFORE_HOLDOUT`

and the fresh holdout remains sealed. No parameter rescue under V2 is authorized.

## 7. Explanatory ablations

Run only on consumed development evidence:

- `FULL`
- `NO_MACRO`
- `NO_GAP_EXTENSION`
- `NO_IFVG`
- `NO_ACCEPTANCE_TEST`
- `NO_RTH_GAP_CONTEXT`

Ablations have zero promotion/selection authority. They explain where the chain
constrains evidence; they may not be substituted for FULL after seeing results.

## 8. Fresh 1Y holdout

The candidate interval remains reserved and SEALED:

`2015-09-17 NY -> 2016-09-17 NY` (end exclusive)

This interval is not automatically opened merely because V2 exists. If V2 passes the
consumed-development gate, a final V2-specific pre-open commit must bind the exact
code/config fingerprint before any economic holdout data are exposed.

A boundary-only M1 provider-availability audit is permitted after that final freeze.
If provider M1 history cannot cover the exact interval:

`NO_FRESH_1Y_HOLDOUT_AVAILABLE`

and the program stops rather than substituting M5 or a consumed year.

If availability passes, the economic holdout is opened exactly once and becomes
permanently consumed immediately after that run.

## 9. Authority

`DEMO_ELIGIBLE=false`  
`LIVE_AUTHORIZED=false`  
`REAL_CAPITAL_AUTHORIZED=false`  
`PRODUCTION_AUTHORIZED=false`

No merge without explicit Owner order.
