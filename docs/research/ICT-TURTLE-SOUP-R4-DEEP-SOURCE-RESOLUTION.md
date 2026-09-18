# ICT Turtle Soup R4 — deep source resolution

Date: 2026-09-15
Research line: `ICT_TURTLE_SOUP_R4`
Status: source research only; no economic replay; no fresh OOS

## Mission
Resolve the three source questions left after R3 forensics and the three-model adjudication:
1. exact Daily Bias family to use for a machine-executable R4;
2. exact Relevant Swing / POI semantics;
3. exact Ideal Formation relationship among C2/C3 closure, CISD and Protected Swing.

Source hierarchy: official ICT primary material -> public TTrades material -> QORE formalization only where source semantics remain non-numeric.

## 1. ICT primary anchor — what Turtle Soup actually is

Official ICT 2016 Core Content, Month 04, Rejection Block, republished on ICT official YouTube in 2022, explicitly describes old highs/lows being violated and rejected as Turtle Soup / false breakouts. The same lesson uses old short-term highs and equal highs as liquidity examples. Therefore:

- Turtle Soup itself is a liquidity violation / false-breakout rejection around meaningful pre-existing highs/lows.
- It is not universally defined by CISD, FVG, MSS or a kill-zone clock.
- The liquidity anchor may be an old high/low, an old short-term high/low, or clustered/equal highs/lows when they are meaningful in context.
- No source-backed fixed bar-age threshold is authorized.

Primary reference:
- ICT Mentorship Core Content - Month 04 - ICT Rejection Block: https://www.youtube.com/watch?v=oALYX0HCSYw

## 2. Daily Bias — source resolution

TTrades provides multiple ways to form daily bias. QORE must not pretend there is one universal ICT/TTrades formula.

### 2.1 Broad source facts

TTrades repeatedly states:
- bias comes before lower-timeframe execution;
- bias can be built from swing points, candle closures, equilibrium, internal/external liquidity and phases of price;
- the most straightforward mechanical family is a higher-timeframe Candle 2 or Candle 3 closure at a meaningful POI, then lower-timeframe CISD to validate the swing;
- a Daily C2 closure can be validated on Hourly;
- after a confirmed Daily C2/C3 reversal, the next Daily candle is the expansion candle of interest.

References:
- https://ttrades.com/the-best-timeframes-for-ttrades-fractal-model-simple/
- https://ttrades.com/easy-daily-bias-a-mechanical-trading-framework/
- https://ttrades.com/ict-daily-bias-most-simple-mechanical-framework/
- https://ttrades.com/how-to-trade-london-using-ttrades-fractal-model/
- https://ttrades.com/how-change-in-the-state-of-delivery-confirms-swing-points/
- https://ttrades.com/fractal-model-playbook-aligning-daily-hourly-and-5-minute-charts/

### 2.2 Selected R4 bias family

For the first R4 candidate, use one narrow source-valid Daily bias family rather than mixing every TTrades bias method:

`DAILY_IDEAL_C2_REVERSAL_BIAS`

Bullish:
1. Daily C1 low is at a meaningful Daily POI / relevant liquidity context.
2. Daily C2 trades below C1 low.
3. Daily C2 closes back above C1 low (reversal closure).
4. Inside that Daily C2, aligned Hourly price closes through the correct down-close series that created the Daily C2 low.
5. That confirms the Daily protected low.
6. Daily C3 is the expected expansion candle; intraday longs may be sought only while this Daily expansion expectation remains structurally valid.

Bearish is symmetric.

This is deliberately narrower than all possible Daily bias methods. It is chosen because it is mechanical, source-backed, fractal, and directly compatible with a Turtle Soup reversal research identity.

### 2.3 What is NOT authorized as Daily Bias

Do not require all Monthly + Weekly + Daily candles to point in the same direction.
Do not hard-code a universal four-case table as the only form of bias.
Do not use a fixed minimum R:R to decide bias.
Do not convert session time into bias.
Do not derive bias from R3 winner/loser pockets.

## 3. Relevant Swing — source resolution

TTrades defines a basic swing structurally:
- bullish swing point: a low with a higher low on each side;
- bearish swing point: a high with a lower high on each side.

But not every basic swing is relevant.

A Relevant Swing:
- represents the current extreme in context;
- stands apart from nearby structure;
- is not merely a failure swing sitting in front of more meaningful same-side liquidity;
- has valid separation.

TTrades explicitly says there is no strict numerical formula for valid separation.

Reference:
- https://ttrades.com/relevant-swings-which-swing-highs-and-lows-matter-in-trading/

### 3.1 Fractal lookback framework

TTrades supplies a practical parent-timeframe window: look back three higher-timeframe candles including the current one and focus on the meaningful extremes inside that context. Examples in the source include Hourly contextualized by three Daily candles and Daily contextualized by three Monthly candles.

This is not the same as R3's `three adjacent H4 bars` rule.

### 3.2 R4 deterministic use

For an H4 Turtle Soup execution layer:
- parent context = Daily;
- consider confirmed H4 swing points contained inside the current three-Daily-candle context window;
- long-side anchor must be the meaningful lower extreme in that context, not a nearer failure swing that leaves more meaningful sell-side liquidity directly behind it;
- short-side anchor is symmetric;
- if two same-side candidate swings remain structurally indistinguishable because valid separation is qualitative, fail closed as `AMBIGUOUS_RELEVANT_SWING`.

The mapping `H4 context -> three Daily candles` is a QORE application of TTrades' published fractal lookback principle and must be labelled `QORE_FORMALIZATION_REQUIRED`, not claimed as a verbatim universal rule.

## 4. Point of Interest — source resolution

TTrades Candle 2 closures require a higher-timeframe POI. Public TTrades material identifies swing highs/lows, FVGs and opposing candles as valid contexts. A later TTrades POI framework gives a continuation search order from a protected swing toward current range:
1. FVG first;
2. if absent, swing high/low;
3. if absent, CISD level.

References:
- https://ttrades.com/understanding-candle-2-closures-within-the-fractal-model/
- https://ttrades.com/the-only-points-of-interest-that-actually-matter-for-trading/

For Turtle Soup R4, a source-qualified Relevant Swing / external-liquidity level can itself be the causal POI. An additional FVG is not universally required.

## 5. CISD — exact causal binding

TTrades defines CISD using the opening price of an opposing delivery series:
- bearish-to-bullish: series of down-close candles, then close above the opening price of that series;
- bullish-to-bearish: series of up-close candles, then close below the opening price of that series;
- with multiple candles, the opening price of the first candle in the sequence is the key level.

Critically, for swing confirmation TTrades requires the series that CREATED the selected high/low. It is not enough to find any nearby opposing sequence.

References:
- https://ttrades.com/understanding-the-change-in-state-of-delivery-cisd/
- https://ttrades.com/how-change-in-the-state-of-delivery-confirms-swing-points/

Aligned-timeframe rule:
- Daily closure -> Hourly CISD inside that Daily candle;
- H4 closure -> M15 CISD inside that H4 candle.

If the aligned lower-timeframe CISD is missing, TTrades explicitly says to ignore the setup.

## 6. Ideal Formation — decisive resolution

TTrades Ideal Formation is the key R4 upgrade.

An Ideal Formation occurs when a Candle 2 or Candle 3 closure also confirms a Protected Swing by closing through the opposing series responsible for the swing.

Reference:
- https://ttrades.com/ttrades-ideal-formation-high-probability-swing-points/

### 6.1 Ideal Candle 2

Bullish:
1. price trades into a meaningful POI;
2. liquidity beneath a relevant low is swept;
3. HTF Candle 2 produces the reversal closure;
4. the aligned lower timeframe closes through the correct down-close series that created the low;
5. the low is now a confirmed protected swing;
6. Candle 3 is the expected expansion candle.

Bearish is symmetric.

This is the preferred first R4 execution family because R3 forensics found that standard C2 closure quality and CISD persistence were still weak. The selection is source-driven: TTrades explicitly identifies Ideal Formations as higher-confirmation swing structures.

### 6.2 Ideal Candle 3 is a separate family

If Candle 2 establishes intent but does not confirm the protected swing and Candle 3 later completes the opposing-series closure, the setup becomes an Ideal Candle 3 formation and Candle 4 is the continuation candle.

Do not silently combine Ideal C2->C3 entry and Ideal C3->C4 entry into one economic candidate. They have different information sets and lifecycle timing.

For the first R4 candidate:
- include Ideal C2 only;
- reserve Ideal C3 for a separate candidate identity if later researched.

## 7. Protected Swing and positional entry

A protected swing exists only after the relevant opposing delivery has been closed through. For positional entry, TTrades requires the Fractal Model to be complete and the protected swing to exist BEFORE the new higher-timeframe candle opens.

References:
- https://ttrades.com/protected-swings-understanding-trends-and-invalidations/
- https://ttrades.com/positional-entries-enter-before-the-expansion/

Thus for H4 Ideal C2:
- M15 swing confirmation must be complete before H4 C3 open;
- only then is H4 C3 positional entry source-valid.

Execution semantics already frozen separately:
- long stop = one native tick below protected low;
- short stop = one native tick above protected high.

The one-tick offset is QORE execution formalization, not an ICT/TTrades methodological claim.

## 8. Draw on Liquidity / target relationship

TTrades target guidance uses higher-timeframe liquidity that already exists:
- untouched swing highs/lows;
- previous higher-timeframe candle highs/lows;
- lower-timeframe execution targets the aligned higher-timeframe swing.

Examples include 5M entry -> Hourly target, Hourly setup -> Daily target, Daily setup -> Weekly target.

References:
- https://ttrades.com/how-to-set-price-targets-using-the-fractal-model/
- https://ttrades.com/internal-external-liquidity-using-the-ttrades-fractal-model/

For H4/M15 R4 execution, Daily untouched liquidity remains the target context. Do not mechanically revert to the opposite H4 C1 extreme.

## 9. Time/session resolution

Session is context, not pattern validity.

TTrades explicitly allows Asia execution when higher-timeframe expansion is supported and describes the 4H->15M model as one of the Asia execution paths. London material also states that higher-timeframe structure, not the clock itself, validates the setup.

References:
- https://ttrades.com/how-to-trade-asia-using-the-ttrades-fractal-model/
- https://ttrades.com/how-to-trade-london-using-ttrades-fractal-model/

R4 therefore keeps Asia, London and New York eligible. Confirmation timeframe may vary by session in discretionary TTrades guidance, but the first machine candidate should not introduce a session-dependent timeframe switch unless separately frozen and justified. The fixed H4->M15 execution family is retained for comparability and determinism.

## 10. Recommended first R4 candidate identity

`ICT_TURTLE_SOUP_R4_D1_IDEAL_C2_H1_CISD__H4_IDEAL_C2_M15_CISD__POSITIONAL_DAILY_DOL`

Pre-entry causal chain:

`Daily meaningful POI/relevant liquidity`
`-> Daily C2 Turtle-Soup/reversal closure`
`-> H1 CISD through the exact series that created the Daily C2 extreme`
`-> confirmed Daily protected swing / Daily C3 expansion bias`
`-> during Daily C3, H4 meaningful relevant-swing/POI interaction`
`-> H4 C2 Turtle-Soup/reversal closure aligned with Daily bias`
`-> M15 CISD through the exact series that created the H4 C2 extreme`
`-> confirmed H4 protected swing`
`-> H4 C3 positional entry`
`-> stop one native tick beyond H4 protected swing`
`-> pre-entry primary untouched Daily DOL`

No clock/session gate.
No fixed R:R gate.
No fixed swing-age bars.
No numeric reclaim threshold.
No mandatory FVG.
No arbitrary pip/ATR stop buffer.
No target reselection after entry.

## 11. Fail-closed states for preregistration

- `NO_DAILY_POI`
- `NO_DAILY_C2_REVERSAL`
- `NO_H1_CAUSAL_CISD`
- `NO_DAILY_PROTECTED_SWING`
- `AMBIGUOUS_RELEVANT_SWING`
- `NO_H4_POI`
- `NO_H4_C2_REVERSAL`
- `NO_M15_CAUSAL_CISD`
- `NO_H4_PROTECTED_SWING`
- `AMBIGUOUS_PRIMARY_DOL`
- `ENTRY_OPEN_THROUGH_PROTECTED_SWING`
- `ENTRY_OPEN_AT_OR_THROUGH_DOL`
- `DATA_GAP`
- `AMBIGUOUS_CISD_SERIES`

## 12. Remaining source uncertainty

Still underdetermined by public source material:
- a numeric formula for valid separation;
- a universal numeric definition of small vs large wick;
- a universal ranking among multiple equally relevant Daily liquidity targets;
- whether the first R4 candidate should adapt the confirmation timeframe by session rather than use fixed H1/M15 alignments;
- management after partial targets, BE, trailing or re-entry.

These uncertainties do not prevent a deterministic first R4 candidate if handled fail-closed and preregistered before any economics.

## Governance

This document does not authorize replay, promotion or capital deployment by itself.
R2/R3 evidence remains consumed development only.
No pair/side/hour/session filters are authorized.
No economics were inspected to choose numeric thresholds.
`DEMO_ELIGIBLE=false`
`LIVE_AUTHORIZED=false`
`REAL_CAPITAL_AUTHORIZED=false`
`PRODUCTION_AUTHORIZED=false`
