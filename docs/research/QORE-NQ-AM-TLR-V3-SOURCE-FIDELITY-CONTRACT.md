# QORE NQ AM TEMPORAL LIQUIDITY REVERSAL V3 — SOURCE FIDELITY CONTRACT

Identity: `QORE_NQ_AM_TLR_V3_SOURCE_CENSUS_001`  
Tracker: #656  
Parent: #653 / #655  
PR: #654  
Source video: `UVVmS0de0g0`  
Status: `RESEARCH_ONLY / SOURCE_EVENT_CENSUS`

## 1. Trigger

The V2 consumed one-year methodology workflow `36502262855` completed GREEN at
SHA `37ea33b1ac8f5f2353fafc58953f62b00c3e99d6`, but FULL V2 produced zero
trades on 247 evaluated sessions. All explanatory ablations also produced zero
trades.

The correct response is not to relax V2 until it trades. V3 separates source
facts, QORE mechanization and proxy limitations before another executable Trader
identity can exist.

## 2. Epistemic classes

Every retained concept belongs to exactly one class:

- `SOURCE_EXPLICIT`: directly stated in the reviewed source material.
- `QORE_MECHANIZATION`: deterministic translation required to make a source
  concept machine-testable; not attributed to the source as a universal rule.
- `DIAGNOSTIC_ONLY`: retained for event incidence / falsification and forbidden
  from selecting a promoted rule from observed P&L.
- `OUTCOME_ONLY`: known only after the causal event and never an entry input.
- `PROXY_LIMITATION`: evidence limitation that blocks source-equivalence claims.

## 3. Source-explicit ledger

The reviewed operation explicitly provides the following observable chain:

1. RTH opening-gap identity uses the prior RTH final print around 16:14 New York
   and the current 09:30 New York RTH open.
2. A gap-down / discount RTH opening gap is graded by octants and quadrants.
3. Failure of the initial opening delivery to reach the lower quadrant, together
   with candle bodies failing to hold at/above the lowest octant, is used as
   evidence of weakness and lower delivery.
4. A pre-existing prior daily low is treated as sell-side liquidity / downside
   draw.
5. That daily low and a two-standard-deviation opening-gap level occupy the same
   price neighborhood in the reviewed example.
6. Price trades down into the `10:50-11:10` New York macro.
7. Wicks may trade through the daily-low / 2SD area while bodies failing to close
   at/below it are interpreted as bullish rejection.
8. A bearish fair-value gap from the delivery leg can become an inversion fair
   value gap after bullish reclaim.
9. Participation may occur inside that inversion FVG even when the absolute low
   was not obtained.
10. Relative equal highs, wick consequent encroachment and the 09:30 opening
    price are discussed as upside objectives / management references.

## 4. Rules NOT source-explicit and therefore removed from V3 admission

The following V2 choices remain evidence about V2 but are not source laws:

- previous ETH daily close must be at/above its daily midpoint;
- previous ETH daily high must exceed the current 09:30 open;
- the daily low must be selected by minimum distance to 2SD;
- `gap/4` is a universal allowed daily-low/2SD distance;
- the daily low must remain completely unswept until 10:50;
- first penetration must occur only in `10:50-11:00`;
- the source opening signature is exactly the first five M1 bars;
- every valid source operation exits entirely at the 09:30 open.

Those may be measured as QORE diagnostics, but V3 cannot silently promote them.

## 5. Proxy source limitation

Current one-year evidence is cTrader DEMO `USTEC` CFD. The source execution is
exchange NQ futures on a specific contract.

Therefore:

`USTEC_PROXY_EVIDENCE != EXACT_NQ_CONTRACT_EVIDENCE`

Contract basis, session marks, prior daily lows and RTH opening gaps may differ.
V3 proxy census may quantify incidence, but it cannot prove source-instrument
equivalence.

## 6. Outcome-blind proxy census

The consumed one-year interval remains:

`2024-08-13 NY -> 2025-08-13 NY` (end exclusive)

For every RTH day and every prior-five electronic-hours daily low, retain
decision-time fields without selecting one "best" level:

- RTH gap direction and size;
- lowest-octant / lower-quadrant levels;
- opening-signature state after 1, 2 and 5 completed M1 bars;
- prior daily-low identity and whether it was untouched before 09:30;
- continuous absolute and gap-normalized distance from daily low to 2SD;
- first RTH touch time;
- touch during full `10:50-11:10` macro;
- body acceptance/rejection after touch;
- causal IFVG availability by 11:10.

After the causal event, retain separately as `OUTCOME_ONLY`:

- whether the 09:30 open was reached by 12:00;
- whether price made a lower low before reaching that target.

No P&L, Profit Factor or trade-selection optimization is permitted in this census.

## 7. Predeclared distance bins

Continuous distance remains authoritative. For descriptive incidence only, report
the following fixed normalized bins:

- `<=0.125 gap`;
- `<=0.25 gap`;
- `<=0.50 gap`;
- `<=1.00 gap`;
- `>1.00 gap`.

No bin becomes a Trader threshold because it has more favorable outcomes.

## 8. Exact NQ evidence gate

Repository inspection confirms that QORE has a non-production TradeStation
futures adapter contract, but no authenticated TradeStation historical-data
HTTP/OAuth client is currently implemented on this branch.

V3 must not fabricate NQ evidence or claim an authenticated provider run.

A future exact-NQ acquisition implementation requires:
- provider credentials supplied through repository secrets;
- read-only historical market-data authority;
- explicit futures contract mapping / rollover identity;
- M1 chronology and session semantics;
- immutable evidence hashes;
- no order/execution authority.

## 9. Promotion law

A V3 executable Trader may be frozen only after the event census and source-rule
ledger establish a mechanically observable event family with enough incidence for
a one-year test.

No V2 threshold rescue is authorized.

## 10. Authority

`DEMO_ELIGIBLE=false`  
`LIVE_AUTHORIZED=false`  
`REAL_CAPITAL_AUTHORIZED=false`  
`PRODUCTION_AUTHORIZED=false`

No merge without explicit Owner order.
