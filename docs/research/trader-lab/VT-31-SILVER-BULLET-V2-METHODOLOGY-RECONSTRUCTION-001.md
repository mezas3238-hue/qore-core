# VT-31 Silver Bullet V2 — Methodology Reconstruction Record

Status: **RESEARCH CANDIDATE — NO DEMO/LIVE/REAL-CAPITAL AUTHORITY**

Primary source: TTrades, `ICT Silver Bullet Strategy - No Daily Bias | With Backtest!`

Source identity: `youtube:o0v4KQxZbpU`

Source duration: `00:29:08`

Scope of this reconstruction: **AM session only**, exactly as the supplied source teaches and backtests it.

## 1. Evidence discipline

Rules are classified as:

- `EXPLICITLY_STATED`: verbally stated as a rule/framework requirement.
- `VISUALLY_DEMONSTRATED`: unambiguously demonstrated on the chart/backtest.
- `REQUIRES_FORMALIZATION`: observed preference or ambiguous execution detail that the source does not define sufficiently for a deterministic production rule.

No `REQUIRES_FORMALIZATION` item may be silently promoted into a mandatory methodology rule.

## 2. Source-confirmed contract

### 2.1 Market

`EXPLICITLY_STATED`

- This source focuses on **NQ / NASDAQ only**.
- The video explicitly says it has **not** been tested on Forex in this work.
- Therefore this exact V2 candidate must not infer multi-market authority from the generic Silver Bullet name.

Operational research policy for the canonical 11-market matrix:

- `NAS100`: supported research market for this source-derived candidate.
- `EURUSD`, `GBPUSD`, `USDJPY`, `AUDUSD`, `USDCAD`, `XAUUSD`, `SP500`, `GBPJPY`, `AUDJPY`, `US30`: `UNSUPPORTED_METHOD_MARKET` for this exact source contract unless a later primary methodology source explicitly expands the allowed universe.

### 2.2 Time and session

`EXPLICITLY_STATED` + `VISUALLY_DEMONSTRATED`

- AM Silver Bullet entry window: **10:00–11:00 New York local wall-clock time**.
- Entries must occur inside that window.
- A pending entry that has not filled by 11:00 is cancelled; it is not allowed to fill after the window.
- A position filled before 11:00 may remain open after the window; one demonstrated trade reaches its target on the following day.
- This reconstruction therefore separates **entry/fill admissibility** from **position exit time**.

The implementation uses `America/New_York` wall-clock semantics so the 10:00–11:00 market session follows the New York clock across DST. The source repeatedly frames the window as the New York AM session and demonstrates July/August examples at the same local wall-clock time.

### 2.3 Reference range

`EXPLICITLY_STATED` + `VISUALLY_DEMONSTRATED`

At 10:00 New York time:

1. Take the fully closed **09:00–10:00 H1 candle**.
2. Freeze its high and low for the session.
3. Do not replace those levels with generic swing highs/lows.

The prior-hour range is the directional framework and the draw-on-liquidity pair for the AM model.

### 2.4 Mandatory liquidity event

`EXPLICITLY_STATED` + `VISUALLY_DEMONSTRATED`

- Price must take one side of the 09:00 H1 range during the 10:00–11:00 window.
- A mere touch/equal high is not treated as a sweep; price must trade strictly beyond the level.
- If neither side is taken during the window, there is no trade.

Direction after the raid:

- raid above the 09:00 H1 high -> seek a **SHORT** toward the 09:00 H1 low;
- raid below the 09:00 H1 low -> seek a **LONG** toward the 09:00 H1 high.

No independent daily-bias filter is required by this source; the source title and framework intentionally demonstrate the model without daily bias.

### 2.5 Lower-timeframe execution

`EXPLICITLY_STATED` + `VISUALLY_DEMONSTRATED`

- Execution analysis is performed on **M1**.
- A range raid alone is insufficient for entry.
- After the raid, the presenter waits for evidence of reversal/structure delivery in the opposite direction.
- Repeated examples require a close through a local structural level / breaker condition and/or aggressive displacement before considering an entry.
- Entry evidence must be **post-raid**; a pre-existing FVG/order block is not sufficient merely because it exists historically.

Examples repeatedly demonstrate:

- displacement in the reversal direction;
- close through a local structural level (the source uses language such as `break structure`, `close below the low that made the new high`, or the mirrored bullish condition);
- breaker-block entries;
- fair-value-gap entries;
- order-block/mitigation entries nested in a breaker context.

### 2.6 Target

`EXPLICITLY_STATED` + `VISUALLY_DEMONSTRATED`

The target is the **opposite side of the frozen 09:00 H1 range**:

- SHORT after high raid -> target the 09:00 H1 low.
- LONG after low raid -> target the 09:00 H1 high.

This replaces V1's fixed `2R` target for this source-derived candidate.

### 2.7 Initial invalidation / stop

`VISUALLY_DEMONSTRATED`

The source repeatedly places the initial stop beyond the raid/swing extreme used by the setup:

- SHORT -> stop at/above the relevant swept high / setup swing high.
- LONG -> stop at/below the relevant swept low / setup swing low.

The implementation must bind the invalidation to the actual post-09:00-range raid structure, not to an unrelated historical swing.

### 2.8 Research trade management

`EXPLICITLY_STATED` for the backtest demonstrated in this source:

- Risk shown in the external backtest: 1% per trade.
- Once the trade reaches **3R**, the backtest moves the stop to breakeven.

QORE Trader methodology code does **not** acquire quantity/Risk sovereignty from this statement. Position sizing remains outside Trader authority. The `3R -> breakeven` rule belongs to the research execution/lifecycle model and must be modeled explicitly if the backtester claims to reproduce the video's reported results.

## 3. Items that require formalization before they may become universal mandatory rules

The source is discretionary in several places. These observations are retained but must not be converted into hidden thresholds:

1. **Sweep depth** — the presenter dislikes `shallow` sweeps but gives no numeric minimum.
2. **Aggressive displacement magnitude** — repeatedly preferred, but no numerical body/range threshold is defined.
3. **Entry-model priority** — breaker, FVG and order-block/mitigation entries are all used; the source does not define one universal deterministic priority when several coexist.
4. **Premium/discount / sell-side-of-curve preference** — the presenter avoids entries that have already moved too far toward the target, but gives no exact threshold.
5. **Minimum reward-to-risk** — low R:R is sometimes rejected as unattractive, but no universal hard minimum is frozen in the framework.
6. **One trade vs multiple attempts per window** — the video does not state a universal maximum number of attempts as a formal rule.
7. **Exact breaker-block price** — block selection is demonstrated visually but not defined as one exact body/wick/midpoint formula.

These remain `REQUIRES_FORMALIZATION`; research code must either fail closed on ambiguous cases or expose the operationalization as an explicit versioned research parameter rather than claiming the source stated it.

## 4. V1 vs source-confirmed V2

| Dimension | VT-31 V1 | Source-confirmed V2 contract | Behavioral consequence |
|---|---|---|---|
| Market | generic | NQ/NASDAQ source scope | other 10 canonical markets abstain for this source candidate |
| Window | 10–11 + 14–15 NY | 10–11 NY AM only | PM setups removed |
| Reference liquidity | generic detected swing | exact 09:00–10:00 H1 high/low | directional framework changes materially |
| Execution timeframe | M5 with nominal M1 label | M1 | structure and entry chronology become materially finer |
| Sweep | generic false-break of swing | strict take/raid of one frozen H1 side | unrelated swings no longer qualify |
| Sequence | generic sweep + any historical FVG | H1 side raid -> post-raid reversal/structure/displacement -> entry model | pre-raid FVG reuse prohibited |
| Entry | FVG midpoint only | breaker/FVG/order-block family demonstrated; exact priority governed | V1 misses valid demonstrated entry families and can use invalid stale FVGs |
| Stop | swept generic swing level | actual setup/raid extreme | invalidation binds to the demonstrated AM event |
| Target | fixed 2R | opposite 09:00 H1 side | economics and holding time change materially |
| Fill after window | not methodology-bound | prohibited | stale post-11:00 fills removed |
| Lifecycle | fixed generic backtest | source backtest moves to BE at 3R | reproduction requires a different research execution model |

## 5. Golden source cases to preserve in tests

The fidelity suite must prove at minimum:

- 09:00 H1 high/low are selected by New York local time.
- strict high raid -> SHORT direction; strict low raid -> LONG direction.
- equal high/low touch without a strict breach -> no raid.
- no raid by 11:00 -> abstain.
- pre-raid FVG cannot justify a setup.
- raid without post-raid structural reversal/displacement -> abstain.
- M5-only execution evidence -> fail/abstain; V2 requires M1 execution semantics.
- target equals the opposite 09:00 H1 boundary, not fixed 2R.
- 10:59:xx valid entry/fill may survive after 11:00; an unfilled pending entry must expire at 11:00.
- New York DST boundaries retain 10:00–11:00 wall-clock semantics.
- unsupported method market -> explicit `UNSUPPORTED_METHOD_MARKET`, never an invented trade.
- future/still-open candle -> rejected.

## 6. Authority

This reconstruction changes methodology identity and therefore creates a **new Trader version**. It does not overwrite or reinterpret VT-31 V1 historical evidence.

`V1 RESULTS APPLY TO V1`

`NEW METHODOLOGY -> NEW VERSION`

`RESEARCH CANDIDATE != DEMO_ELIGIBLE`

`VIDEO FIDELITY != ECONOMIC VALIDATION`

`NO FRESH HOLDOUT -> NO PROMOTION`
