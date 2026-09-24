# VT08 Cognitive Expansion 5M — Candle 3 Closure Opportunity Audit V1

Status: **PRE-ECONOMIC / SHAPE-ONLY / SOURCE-ADJUDICATION**

## Primary-source basis

TTrades primary material states:

- Candle 2 closure is a reversal closure.
- When Candle 2 fails to give the required closure, Candle 3 may still confirm.
- Bullish C3 closure: Candle 3 closes over the body of Candle 2.
- Bearish C3 closure: Candle 3 closes below the body of Candle 2.
- The C3 closure occurs without sweeping Candle 2 high or low.
- A valid swing also requires a point of interest.
- After a C2/C3 higher-timeframe closure, lower-timeframe CISD is required before
  looking for continuation.
- A completed C2 or C3 closure plus lower-timeframe CISD can support a positional
  entry at the next higher-timeframe open.

Primary sources:
- TTrades, "Candle 3 Closure: A Complete Guide to Identifying Continuations and
  Reversals", 2025-12-03.
- TTrades, "How Change in the State of Delivery (CISD) Confirms Swing Points",
  2026-01-10.
- TTrades, "Positional Entries – Enter Before The Expansion", 2026-08-08.

## Why this audit is shape-only

Current VT08 B01 has a narrow previous-H4-extreme POI containment. TTrades C3
allows a broader point-of-interest framework, including FVGs, swing highs/lows
and CISD-based areas.

That POI hierarchy must be implemented causally before a C3 can become an
executable candidate.

Therefore this audit only measures the higher-timeframe **C3 closure shape**.
It does not create a trade, stop, target or PF.

## Frozen C3 shape formalization

At the Candle 4 open decision boundary:

- C1 = H4 opened 12 hours before decision.
- C2 = H4 opened 8 hours before decision.
- C3 = H4 opened 4 hours before decision.
- daily bias must already be resolved.
- C2 must NOT already provide the required same-side C2 reversal closure.
- C3 must remain within Candle 2's high/low range (no Candle 2 extreme sweep).
- bullish bias: C3 close > max(C2 open, C2 close).
- bearish bias: C3 close < min(C2 open, C2 close).

These are **closure-shape opportunities**, not executable setups.

## Output

Count by market and 01/05/09 anchor:
- complete C1/C2/C3 sequences;
- resolved bias;
- C2 already-valid same-side closures;
- C2 failure categories;
- C3 closure shapes;
- unique NY dates with a C3 shape;
- shape density/year and 2Y equivalent.

No PnL is read.

## Governance

- shape_only=true
- point_of_interest_bound=false
- lower_timeframe_cisd_bound=false
- executable_candidate=false
- pnl_read=false
- methodology_changed=false
- live_authorized=false
