# Trader Daily Cardinality Contract

Status: mandatory Human Owner execution policy for rebuilt research Traders.
Timezone boundary: `America/New_York`.

## Authority boundary

Economic execution authority belongs to:

`MarketDayId(trader_family, canonical_market, new_york_local_date)`.

It does **not** belong to a candle, H4 anchor, POI, candidate, scenario, entry family or
configuration replay.

Diagnostic accounting and economic accounting are different layers:

`WINDOW_EXAMINED -> MECHANICAL_CANDIDATE -> QUALIFIED_SETUP -> DAILY_SELECTION -> PENDING_ORDER -> FILLED_TRADE -> TERMINAL_TRADE`.

The first two layers may contain multiple records on one market-day. A methodology may
also identify multiple qualified setups before daily selection. The execution layer may
never contain more than one selected setup/order/fill/terminal trade for one
`MarketDayId`.

## Hard invariants

For every `MarketDayId`:

- `selected_setup_count <= 1`
- `pending_order_count <= 1`
- `filled_trade_count <= 1`
- `terminal_trade_count <= 1`

Across any aggregate:

- `selected_setup_count <= eligible_market_days`
- `pending_order_count <= eligible_market_days`
- `filled_trade_count <= eligible_market_days`
- `terminal_trade_count <= eligible_market_days`
- `daily_cardinality_violations == 0`

A violation is a hard research/CI failure. It cannot be repaired by reducing a report
counter after execution.

## Provenance

The one-trade-per-market-per-New-York-date ceiling is
`HUMAN_OWNER_EXECUTION_POLICY`. It is not automatically a TTrades source rule.

If source evidence later defines how to choose between multiple complete opportunities,
that rule must be separately sourced and versioned. Until then, no implicit priority such
as "earliest anchor wins" is authorized. The cardinality engine enforces a ceiling but
never chooses the winning setup itself.

## Dataset denominator

The maximum possible fill count is `SUM(eligible_market_days)` under the frozen dataset
eligibility contract. A requested lookback such as `730 days` is not itself an eligible-day
denominator.

Every backtest report must expose requested lookback, calendar span, observed market
dates, eligible/ineligible market-days, missing-data days and the completeness criteria
used to classify a day.

## Causality and identity

All candidates must have stable replay identity and evidence provenance. Duplicate
candidate identity is rejected. Daily grouping uses DST-aware New York conversion from an
aware timestamp. Future evidence, outcome-based selection and post-hoc candidate merging
are prohibited.

## Authority exclusions

This contract grants no Risk authorization, broker submission authority, `DEMO_ELIGIBLE`,
LIVE/Production authority or real-capital authority.
