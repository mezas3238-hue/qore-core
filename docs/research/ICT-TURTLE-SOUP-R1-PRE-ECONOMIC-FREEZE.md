# ICT Turtle Soup R1 — Pre-Economic Freeze

Issue: #572
Identity: `ICT_TURTLE_SOUP_R1_CISD_SESSION`
Canonical trader code: `CODE_UNASSIGNED`

This freeze is committed **before** any ICT Turtle Soup R1 economic replay.

## Scope

Markets (research proxies):

- `NAS100`
- `SP500`
- `US30`

Timeframe: `M5`
Timezone: `America/New_York` (DST-aware)
Sides: LONG + SHORT

## Session construction

### London liquidity range

Completed M5 bars whose New-York-local open is:

`02:00 <= t < 05:00`

Define:

- `LONDON_HIGH = max(high)`
- `LONDON_LOW = min(low)`

Missing or non-contiguous London M5 evidence => abstain for that symbol/date.

### New York AM event / execution window

Completed M5 bars whose New-York-local open is:

`08:30 <= t < 11:00`

No R1 event is opened outside this interval. Any still-open R1 trade is flattened at the close of the final completed M5 bar before 11:00.

## Bullish R1

1. During NY AM, price trades strictly below `LONDON_LOW`.
2. Record the most adverse low of the sweep sequence.
3. A completed M5 candle closes strictly back above `LONDON_LOW` (reclaim).
4. Identify the maximal contiguous bearish-body M5 series (`close < open`) immediately feeding the sweep leg. The CISD threshold is the **open of the earliest candle in that series**.
5. After the sweep, a completed M5 candle closes strictly above the CISD threshold.
6. Enter LONG at the **next M5 open**. If no next M5 bar exists inside NY AM, abstain.
7. Stop = most adverse sweep low observed through the CISD close minus one instrument tick.
8. Target = `LONDON_HIGH`.
9. If target <= entry, abstain.
10. If `(target-entry)/(entry-stop) < 1.5`, abstain.

## Bearish R1

Exact mirror:

1. sweep strictly above `LONDON_HIGH`;
2. adverse sweep high;
3. completed close strictly back below `LONDON_HIGH`;
4. maximal contiguous bullish-body series (`close > open`) feeding the sweep; threshold = earliest series candle open;
5. completed close strictly below threshold;
6. enter SHORT at next M5 open inside NY AM;
7. stop = adverse sweep high + one instrument tick;
8. target = `LONDON_LOW`;
9. target must be strictly below entry;
10. projected R to target must be >= 1.5R.

## Candle / causality rules

- Only completed candles can confirm reclaim or CISD.
- Entry never occurs at the same close that confirms CISD.
- Doji (`close == open`) is not part of an opposing candle series.
- No future candle may alter an already-identified CISD threshold.
- A sweep and reclaim may occur in the same completed M5 candle, but CISD still requires a completed causal close and entry remains next-bar-open.
- If stop and target are both contained in the same post-entry M5 bar and no finer immutable chronology is available, adjudicate STOP first.
- Gap through stop exits at the observed bar open (adverse slippage retained).
- Gap through target is capped at the frozen target (no favorable windfall assumption).
- Missing M5 bars or session discontinuity => fail closed.

## Cardinality

At most one candidate per symbol / New-York date.

If both bullish and bearish candidates become eligible in the same symbol/date, status is `AMBIGUOUS_BOTH_SIDES` and no trade is generated.

If multiple same-side candidates would exist, only the first fully confirmed causal sequence is eligible; after an entry or explicit ambiguity the session is closed to further R1 entries.

## Management

Frozen R1 management:

- structural sweep stop only;
- opposite London liquidity target only;
- NY-AM time containment exit;
- no BE;
- no trailing;
- no partial;
- no re-entry;
- no CIBO signal mutation.

## Costs and stress

Economic replay, once data provenance is bound, must report at minimum:

- gross R;
- primary cost model;
- stress cost model;
- PF;
- expectancy/trade;
- max drawdown R;
- longest losing sequence;
- side / market / quarter stability;
- leave-one-market-out;
- positive-gain concentration.

Cost values are **not yet frozen** because instrument-specific spread/tick/commission provenance must be recovered from the retained index data pipeline before economics. No economic result may be opened until that cost addendum and the temporal partitions are frozen.

## Data partitions / OOS

No globally fresh OOS is assigned in this commit.

Existing NAS100/SP500/US30 historical evidence previously accessed by VT-08 may be used only as **consumed development / Walk-Forward research** for ICT R1. It must not be relabeled as globally unseen validation.

Before economic replay, a data-census addendum must freeze:

- exact provider/artifact identities;
- development interval;
- Walk-Forward folds;
- primary/stress costs;
- a genuinely untouched or prospective final OOS policy.

## Advancement prerequisites

No candidate/config freeze or OOS opening unless consumed-evidence Walk Forward passes all preregistered gates to be defined in the data-census addendum. No market, side, weekday, or session filtering may be selected from observed P&L.

## Authority

- `DEMO_ELIGIBLE=false`
- `LIVE_AUTHORIZED=false`
- `REAL_CAPITAL_AUTHORIZED=false`
- `PRODUCTION_AUTHORIZED=false`
