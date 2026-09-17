# CIBO Atlas — VT-31 Eight-Ledger Evidence Contract

Status: CONSUMED-ONLY RESEARCH / NO_R9_NOT_CERTIFIED

This contract makes CIBO Atlas a replayable market laboratory. It does not select a candidate, change a trader, open fresh evidence, or authorize live/production trading.

## Identity and joins

Every independent market episode uses a stable `episode_id` keyed by market, New York date, first breach side and first breach timestamp. Trader overlays retain the definitive `root_id`. All outputs preserve `market`, `ny_date`, `partition`, and America/New_York timestamps so ledgers can be joined without fuzzy matching.

## Data admission

- Reference range: 09:00–10:00 America/New_York.
- Trader-comparable admission: frozen consumed `gap05` reference policy.
- Setup/session observation: 10:00–11:00 must contain all 60 M1 bars.
- Lifecycle research: 10:00–16:00, with explicit coverage metadata.
- Strict60 Atlas remains a separate data-quality control.
- Consumed partition ownership is local-date contiguous: R8-fresh < 2018-05-19; R6 2018-05-19 through 2020-06-16; R5 >= 2020-06-17.
- No pre-2016 fresh region is opened.

## The eight ledgers

### 1. MARKET_JOURNEY_LEDGER
One row per independent market episode. Records reference range, first breach, confirmation when source reconstruction exists, objective reach, departure pivot, post-objective extreme, path coverage and ordered milestones.

### 2. STRUCTURE_TOUCH_LEDGER
One row per structure-zone/event touched within an episode. Source-coherent Breaker / Order Block / FVG zones are reconstructed with the frozen VT-31 source mechanics. Liquidity sweep/reclaim events are recorded separately. Fields include formation time, first/last touch, touch episodes, bars touched, maximum zone penetration, dwell minutes and whether the structure was the last touch before departure.

### 3. PRE_DEPARTURE_SEQUENCE_LEDGER
One row per episode that reaches the opposite 09:00 boundary. Stores the ordered observed event sequence from first breach through the last unbroken reaction pivot to objective, including source-zone touches, sweep/reclaim events and displacement events. It does not infer hidden market intent.

### 4. DEPARTURE_TIMING_LEDGER
One row per completed reversal episode. Stores New York date/time, weekday, 5/15/30-minute buckets, breach→departure latency, departure→objective latency, and root overlays showing whether the frozen trader had already stopped before the eventual source objective.

### 5. TARGET_DESTINATION_LEDGER
One row per episode. Stores opposite 09:00 boundary availability/reach, time-to-objective, extension beyond the boundary in 09:00-range units, post-objective extreme time, and normalized extension ladders. Trader overlays preserve fixed target R and source-boundary R, so CIBO can test whether 2R was short/long without assuming a replacement target.

### 6. CROSS_INDEX_JOURNEY_LEDGER
One row per New York date with cross-index coverage. Compares NAS100/SP500/US30 breach direction, breach time, departure time, objective time, agreement/divergence, observed leader/laggard and lead/lag minutes. A leader is an observed timing fact, not a trading recommendation.

### 7. DAILY_PATH_LEDGER
One row per admitted market/day. Stores observed daily/M1 coverage, 09:00 reference geometry, 10:00–16:00 range, first breach, both-side behavior, source-objective completion and descriptive day regime (`inside-reference`, `one-sided-expansion`, `two-sided-expansion`, `reversal-completion`). Compression/lateral labels are geometric proxies only.

### 8. TRADER_MARKET_SYNC_LEDGER
One row per definitive terminal root (618 expected). Joins trader pre-entry geometry and terminal result to the independent market episode: whether entry occurred before/after final departure pivot, terminal family, whether trader had already stopped before eventual source objective, source-boundary distance in R, market extension after objective and pre-entry compression/rotation proxy.

## Timing classes and leakage

Fields are tagged conceptually as:

- `PRE_ENTRY_OBSERVABLE`: available no later than the frozen signal timestamp.
- `POST_OUTCOME_RESEARCH`: objective reach, MFE/extension, departure pivot discovered retrospectively, terminal labels, and any event after signal.

No `POST_OUTCOME_RESEARCH` field may become a live rule directly. Any proposed specialist repair must be causal/methodology-bound, finite and predeclared, then evaluated leakage-free in walk-forward before any new identity is frozen.

## Governance

All ledgers require:

- `research_only = true`
- `selection_prohibited = true`
- `opens_new_holdout = false`
- `candidate_status = NO_R9_NOT_CERTIFIED`
- `live_authorized = false`
- `production_authorized = false`

A positive market, weekday, time bucket, structure or target ladder is descriptive evidence only and cannot be promoted directly.
