# VT08 INDEX — CIBO MARKET EXPLANATION CONTRACT 001

## Purpose

CIBO must explain the complete observed market journey around VT-08 Index opportunities. The purpose is not to optimize V7 retrospectively, but to transform consumed NAS100/SP500/US30 evidence into a governed description of what the market typically did before entry, at reaction, during expansion, at stop, after stop, and toward subsequent structural boundaries.

This contract is diagnostic and explanatory only. It does not authorize LIVE, real capital, production, target changes, stop changes, market deletion, anchor deletion, or automatic strategy mutation.

## Required explanation for every reconstructed opportunity

CIBO must be able to answer all of the following when evidence exists:

1. **Pre-entry condition**
   - Was price balanced/accumulating or already displaced?
   - Four-hour pre-entry range, directional efficiency, balance score, body-direction flips and inside-bar rate.
   - Prior H4 range regime: compressed / normal / expanded.
   - Relevant source-day context and weekday.

2. **Reaction location / structure**
   - Frozen V7 POI family.
   - Mechanically observed FVG context.
   - Mechanically observed local liquidity sweep context.
   - Previous H4 directional extreme and previous source-day directional extreme when observable.
   - Order Block and Breaker Block MUST remain `UNRESOLVED_SOURCE_DEFINITION_NOT_AUTOMATED` until a separate source-definition freeze provides reproducible semantics.

3. **Reaction time**
   - New York reaction hour.
   - Minutes from H4 open to POI touch where available.
   - Minutes from H4 open to CISD.
   - Minutes from CISD to continuation.
   - Minutes from executable signal to 0.5R / 1R / 1.5R / 2R / 2.5R / 3R / 4R / 5R where reached.

4. **Path before expansion**
   - Maximum adverse excursion before the first +1R expansion.
   - Structure observed around that adverse extreme.
   - Whether price swept local liquidity before expansion.
   - Whether an FVG was present near the reaction.
   - No observed structure may be stated as causal merely because it co-occurred.

5. **Target / destination atlas**
   - Natural favorable excursion distribution, not only the frozen 2R target.
   - Probability and median time to multiple R-levels under complete observable horizons.
   - Distance and time to previous H4 directional extreme.
   - Distance and time to previous source-day directional extreme.
   - Session/source-day boundary behavior.
   - Horizon completeness must be proven before a non-hit is counted. Weekend closure or dataset truncation must never be interpreted as target failure.

6. **Stop afterlife**
   - Whether the trader was stopped.
   - What price did after the stop using the original entry/risk frame.
   - Whether +0.5R / +1R / +2R / +3R was later reached.
   - Minutes after stop to those levels.
   - Separate `bad thesis` from the descriptive class `direction later correct but entry/timing/invalidation path adverse`; CIBO may describe this distinction but may not change the stop automatically.

7. **Cross-index explanation**
   - What NAS100, SP500 and US30 were doing at the same observable timestamp.
   - 60-minute and 240-minute pre-entry returns.
   - Relative-strength / dispersion state.
   - Peer directional alignment.
   - Whether the stopped/expanding market was leading, lagging or diverging descriptively.
   - Multi-index loss clusters must be represented as correlated portfolio events, not independent mistakes.

8. **Weekday and regime behavior**
   - Source-day range relative to trailing completed source days.
   - Directional efficiency.
   - Compressed / normal / expanded regime mix by Monday–Friday.
   - Trade journey by weekday only when the forward path has complete market-observation coverage.
   - No weekday may become a trading filter from consumed evidence alone.

9. **Market-specific behavior**
   - NAS100, SP500 and US30 must be modeled and explained separately.
   - The same setup token may have different behavior by market and era.
   - CIBO must report disagreement rather than average the three indices into a false universal conclusion.

10. **Evidence and uncertainty**
    - Every explanation distinguishes mechanically observed fact, statistical association, source-supported concept, unresolved concept and causal hypothesis.
    - Insufficient or truncated evidence returns an explicit unresolved/evidence-gap state.
    - A descriptive relationship becomes an accepted CIBO lesson only through existing governed sufficient-evidence semantics.

## Required CIBO narrative shape

A future read-only explanation may state, for example:

> NAS100 entered long at 08:45 New York after a compressed four-hour state. The latest mechanically observed pre-entry event was a low-side liquidity sweep; an FVG was also present. The adverse reaction extreme occurred at 09:15. CISD-to-continuation latency was 15 minutes. SP500 and US30 were aligned but NAS100 was lagging over the previous four hours. The trade stopped before +0.5R, but price later reached the previous H4 high and +2R from the original entry frame. This is a consumed-evidence description, not proof that the sweep caused the move or that the stop should be changed.

The exact values must come from governed evidence. CIBO must never fabricate a structure or causal relation to complete the narrative.

## Horizon discipline

Forward journey statistics must distinguish:

- wall-clock elapsed time;
- observed M15 market bars;
- source-day/session boundary;
- weekend/maintenance closure;
- dataset-end truncation.

A missing future path is not a negative outcome. Any target hit-rate denominator must explicitly prove sufficient observable forward coverage or count a confirmed hit.

## Governance

- All current source periods are consumed evidence.
- V7 remains frozen and unchanged.
- Pattern findings are hypotheses, not automatic rules.
- Any entry/stop/target/market/session/day adaptation creates a new candidate identity.
- Such a candidate must be frozen before a genuinely unseen validation partition is opened.
- `LIVE_AUTHORIZED = FALSE`.
- `REAL_CAPITAL_AUTHORIZED = FALSE`.
- `PRODUCTION_AUTHORIZED = FALSE`.
