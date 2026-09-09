# QORE Trader Lab Conditional Market-State Analytics 001

## Status and authority

This component is research-only Trader Lab infrastructure. It extends the existing
first-cohort historical replay; it does not create a second backtesting engine and
it cannot promote a Trader, issue an order, grant DEMO/LIVE authority, or authorize
Production/real capital.

The first cohort is VT-01, VT-08, VT-09, VT-17 and VT-31. The engine is reusable
for later canonical Traders and market families.

## Scientific question

The primary output is not a global PASS/FAIL. For every exact Trader version the
software must answer, with explicit sample sufficiency and provenance:

- under which market states does it show favorable outcomes;
- under which market states does it show adverse outcomes;
- where evidence is mixed or insufficient;
- how the opportunity -> setup -> fill -> outcome funnel behaves;
- whether apparent niches require a fresh untouched holdout before any promotion.

## Causal split

Every observation has two strictly separated sections.

### `decision_time_state`

Contains only information computable from candles closed at the exact decision
`as_of`. It includes UTC hour/weekday, DST-aware major-session context, execution
timeframe, trend/range/mixed direction, trend transition, volatility regime and
percentile, expansion/compression, momentum and acceleration, range position,
gap state and available H4 context/alignment.

No future bar, realized trade result, MAE/MFE, later chronological label or
post-decision path may enter this section.

### `outcome_evaluation`

Contains labels observed only after the decision freeze: fill state, return, exit
reason, bars-to-fill, holding bars, OHLC-extrema MAE/MFE and risk-normalized
excursions. A bounded contiguous forward-path diagnostic is retained for research
on abstentions and is explicitly marked `post_decision_oracle_only`.

This oracle cannot be consumed by a Trader or CIBO at decision time.

## Market-state classifier

Classifier version: `qore-trader-lab-market-state-v1`.

The initial deterministic classifier uses:

- 20-bar close-path efficiency for directional trend/range/mixed state;
- previous-vs-current 20-bar family comparison for transition state;
- normalized OHLC range baseline/recent comparison for low/normal/high volatility;
- rolling normalized-range percentile bucket;
- 20-bar baseline vs 3-bar recent expansion/compression;
- five-bar normalized momentum and acceleration/deceleration;
- 20-bar causal range position;
- contiguous-bar gap detection;
- H4 past-only trend/volatility and cross-timeframe alignment;
- DST-aware London, New York and Tokyo local-session windows.

Session labels are research classifier labels, not exchange-hours or holiday
trading authority.

## Conditional edge surfaces

The engine streams each observation through a fixed source-controlled set of
surfaces including direction, regime, transition, volatility, session/overlap,
hour, weekday, momentum, range position, gap state, cross-timeframe alignment,
expansion state and selected higher-order interactions.

Each cell retains the opportunity denominator and records evaluation failures,
abstentions, setups, fills, returns, Profit Factor, drawdown metrics, MAE/MFE,
bars-to-fill, holding bars and exit reasons.

Evidence labels are deliberately limited to:

- `FAVORABLE_EXPLORATORY`
- `ADVERSE_EXPLORATORY`
- `MIXED_UNCERTAIN`
- `INSUFFICIENT_EVIDENCE`

No label is certified. The initial minimum for a directional exploratory label is
10 filled trades, which is only a reporting floor and never a certification
threshold.

An `edge_state_index` makes favorable, adverse, mixed and insufficient regions
directly queryable while retaining the underlying surface and conditions.

## Opportunity denominator and abstention diagnostics

The replay records every eligible decision opportunity, not only executed trades.
That denominator allows separation of selection, direction, fill and lifecycle
behavior.

For abstentions, the engine may record a bounded forward-path oracle to identify
states followed by material movement. This is a hypothesis generator only; it is
not proof that the abstention was wrong, because setup direction, executable entry
and causal eligibility still require separate study.

## Exit-management diagnostics without trailing modification

The current engine does not apply a trailing stop or modify any Trader exit rule.
It does, however, measure OHLC-extrema MFE/MAE and counts stopped trades that had
previously achieved positive MFE or at least one initial risk unit of favorable
excursion. This preserves the original Trader baseline while making later exit or
protection experiments scientifically testable.

Any future trailing-stop experiment requires a separately versioned policy and
fresh comparison; it cannot rewrite this baseline retrospectively.

## Artifact model

To avoid retaining a multi-year five-Trader opportunity table in memory, detailed
observations are streamed as canonical JSON Lines (NDJSON). The summary report
contains per-Trader stream SHA-256 values, row counts, a bundle fingerprint,
conditional surfaces, diagnostics and a reproducibility fingerprint.

The CLI is:

```text
python -m qore.infrastructure.trader_lab.conditional_market_state_analytics \
  MARKET_EVIDENCE_JSON [OBSERVATIONS_NDJSON]
```

The JSON summary is written to stdout. If the second path is supplied, all exact
per-opportunity observations are streamed there in deterministic Trader/order
sequence.

## Anti-overfitting and holdout law

A conditional niche discovered from consumed evidence remains exploratory.
Combinatorial mining cannot certify it. Any proposed Operating Envelope or
capability claim derived from these results must be frozen as a hypothesis and,
where certification is intended, challenged against new previously untouched
holdout evidence.

`BACKTEST -> PAST-ONLY MARKET STATE -> OUTCOME -> CONDITIONAL SURFACE -> HYPOTHESIS`

is permitted.

`POST-HOC NICHE -> CERTIFIED CAPABILITY`

is prohibited.
