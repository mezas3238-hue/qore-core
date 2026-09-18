# ICT Turtle Soup R3 — Pre-Economic Candidate Freeze

Date: 2026-09-15
Candidate identity: `ICT_TURTLE_SOUP_R3_H4_C2_M15_CISD`
Research parent: `ICT_TURTLE_SOUP_R3_SOURCE_BOUND`

## Governance boundary

This document freezes the first executable R3 candidate before any R3 economic replay is opened. It is derived from primary ICT Turtle Soup/rejection material plus TTrades Candle-2 / CISD / protected-swing execution material. It is not a claim that every rule below is the only canonical ICT implementation.

The consumed R2 Forex holdout `[2020-07-01, 2022-07-01)` may be replayed only as consumed development evidence. It cannot become a fresh holdout for R3. No result from that interval may modify this identity in place.

## Source model separated into three layers

1. **Turtle Soup liquidity event** — `PRIMARY_ICT_CONFIRMED`:
   pre-existing meaningful high/low liquidity is run/violated and the move fails/rejects.
2. **Reversal confirmation** — `TTRADES_CORROBORATED` for this candidate:
   higher-timeframe Candle-2 reversal closure plus lower-timeframe CISD / protected swing.
3. **Historical execution containment** — explicitly frozen QORE mechanics:
   enter at the next H4 open, use the confirmed protected swing as structural invalidation, target the opposite side of the swept prior H4 range, and contain the trade to that next H4.

## Time/session policy

**No clock-time or session is an inclusion/exclusion rule.**

The candidate may form during Asia, London, New York AM, New York PM, lunch, rollover-adjacent evidence, or another clock bucket if the full source-bound methodology completes and market data are valid.

Session/hour are diagnostic labels only and cannot suppress an otherwise valid setup. This is deliberate: methodology governs eligibility; clock labels do not.

## Frozen market/data scope for the first replay

First consumed-development cohort:

- AUDJPY
- AUDUSD
- EURUSD
- GBPJPY
- GBPUSD
- USDCAD
- USDJPY

Input: the exact retained provider-native BID M5 evidence already opened by R2 from the Core holdout carrier. No recollection and no data substitution.

Evaluation interval for this consumed replay only: `[2020-07-01T00:00:00Z, 2022-07-01T00:00:00Z)`.

## Timeframe construction

### H4

`ICT_COMPATIBLE_QORE_FORMALIZATION`

Provider-native M5 bars are aggregated into exact contiguous New-York-local four-hour candles beginning at:

`00:00, 04:00, 08:00, 12:00, 16:00, 20:00 America/New_York`.

Each H4 requires exactly 48 contiguous M5 bars. Incomplete/discontinuous H4 evidence fails closed.

### M15

Provider-native M5 bars are aggregated into exact contiguous M15 bars. Every M15 requires exactly three M5 bars. Missing/discontinuous evidence fails closed.

No M5 interpolation is used to manufacture missing prices.

## Relevant H4 liquidity reference

TTrades states that not every swing high/low is relevant and teaches contextual relevant swings. For this candidate the deterministic historical formalization is frozen as follows before economics:

- Let `C1` be the completed H4 candle immediately preceding candidate Candle 2.
- Let the relevant-window be the three completed H4 candles ending at `C1`.
- A candidate LONG may reference `C1.low` only when `C1.low` equals the minimum low of that three-H4 window.
- A candidate SHORT may reference `C1.high` only when `C1.high` equals the maximum high of that three-H4 window.
- Exact ties are retained as stacked/equal liquidity; no arbitrary price tolerance is invented.
- No generic completed session high/low becomes eligible merely because a clock-defined session ended.

The three-H4 mechanical window is `ICT_COMPATIBLE_QORE_FORMALIZATION`; it operationalizes relevant-swing context without selecting an age/lookback from R2 P&L.

## H4 Candle-2 reversal closure

`TTRADES_CORROBORATED`

### Bullish

`C2.low < C1.low` **and** `C2.close > C1.low`.

The sell-side liquidity under the relevant C1 low is swept and C2 closes back inside the prior H4 range.

### Bearish

`C2.high > C1.high` **and** `C2.close < C1.high`.

The buy-side liquidity above the relevant C1 high is swept and C2 closes back inside the prior H4 range.

If the same C2 satisfies both bullish and bearish closures, the candidate abstains `AMBIGUOUS_BOTH_SIDES` rather than inventing intrabar priority.

A same-candle reclaim is therefore required in **this specific C2 candidate**, because that is the chosen TTrades Candle-2 reversal-closure model; this is not represented as a universal definition of all ICT Turtle Soup variants.

## M15 CISD confirmation inside C2

`TTRADES_CORROBORATED`

CISD must be causally completed inside the same H4 C2 that swept the relevant liquidity.

For LONG:

1. find the first M15 within C2 that trades below `C1.low`;
2. identify the maximal contiguous down-close candle series immediately feeding that sweep leg; if the sweep M15 itself is a down-close candle, it belongs to the series;
3. CISD threshold = opening price of the **first** candle in that contiguous down-close series;
4. require a completed M15 close above that threshold before C2 closes.

For SHORT use the exact mirror with contiguous up-close candles and a completed M15 close below the first candle's open.

No CISD completed after the C2 boundary belongs to this candidate. Dojis do not form an opposing candle series.

## Protected swing

`TTRADES_CORROBORATED` concept + deterministic QORE historical level.

After CISD is confirmed:

- LONG protected swing = lowest M15 low from the beginning of the opposing series through the CISD-confirmation bar, inclusive;
- SHORT protected swing = highest M15 high over the same causal segment.

Exactly this level is the R3 historical structural invalidation. No pip/tick offset, ATR buffer or retrospective widening is applied.

## Entry

`ICT_COMPATIBLE_QORE_FORMALIZATION`

Entry occurs at the opening price of the immediately following completed H4 (`C3`) after C2 has closed with the required reversal closure and internal M15 CISD.

This intentionally uses the TTrades Candle-2 -> Candle-3 continuation relationship while avoiding an invented intrabar broker order type. It is not described as the only valid live ICT entry style.

If a contiguous C3 open is unavailable, abstain.

## Stop / invalidation

Initial stop is exactly the protected-swing level.

- LONG requires `protected_swing < entry`.
- SHORT requires `protected_swing > entry`.

Non-positive risk fails closed.

No break-even, trailing, partial, CIBO overlay, re-entry, risk-width filter or stop offset exists in R3.

## Target

`ICT_COMPATIBLE_QORE_FORMALIZATION` consistent with the primary ICT opposing-liquidity narrative.

The pre-existing target is the opposite extreme of C1:

- LONG after sweeping `C1.low` targets `C1.high`;
- SHORT after sweeping `C1.high` targets `C1.low`.

The target must lie favorably beyond the entry. Otherwise the setup abstains `NO_CAUSAL_OPPOSING_TARGET`.

There is **no minimum projected R gate**. R2's frozen 1.5R threshold is removed because it was a QORE research parameter, not part of this source-bound R3 identity.

Projected R is reported diagnostically only.

## Lifecycle and intrabar containment

The trade is contained to C3:

- target or structural stop may resolve inside C3;
- adverse gap through stop exits at observed M5 open;
- favorable gap through target is capped at the frozen target;
- unresolved same-M5 stop+target contact resolves STOP first;
- if neither is hit, exit at C3 close.

This C3 containment is `ICT_COMPATIBLE_QORE_FORMALIZATION`, frozen before economics.

## Cardinality

At most one R3 trade per symbol per C2/C3 candidate cycle. Both-side ambiguity abstains. No symbol, side, hour or session can be selected retrospectively.

## Friction / stress

For comparability with the consumed R2 research evidence only:

- gross: `0.00R/trade`
- primary normalized friction: `0.05R/trade`
- stress: `0.10R/trade`

These are research-normalized deductions, not broker spread/commission claims.

## Mandatory reporting

Report at minimum:

- candidate census and all abstention reasons;
- trades / wins / losses / flats;
- gross and primary/stress total and mean R;
- profit factor;
- max drawdown and longest losing streak;
- symbol and side breadth;
- H4-open/session/hour diagnostic buckets;
- projected-R distribution (diagnostic only);
- stop/target/time-exit census;
- leave-one-symbol-out totals;
- chronological year/quarter stability.

## Advancement rule

The first `[2020-07-01, 2022-07-01)` R3 replay is **consumed development evidence only** because the raw market data were already opened under R2/VT-08. It can falsify R3 but cannot independently validate or approve it.

If this exact frozen candidate is not economically credible on consumed development, mark it rejected and do not repair it in place.

If it is economically credible, freeze the exact candidate fingerprint and use a different untouched evidence interval for Walk Forward / independent holdout. The consumed R2 holdout can never be relabeled fresh.

`DEMO_ELIGIBLE=false`
`LIVE_AUTHORIZED=false`
`REAL_CAPITAL_AUTHORIZED=false`
`PRODUCTION_AUTHORIZED=false`
