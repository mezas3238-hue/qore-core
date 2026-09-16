# ICT TURTLE SOUP R4 — THREE-SOURCE ADJUDICATION

Date: 2026-09-15
Repository: `mezas3238-hue/qore-core`
Research line: `ICT_TURTLE_SOUP_R4`
Status: SOURCE ADJUDICATION ONLY — NO ECONOMICS

## Purpose

Adjudicate the three independent external research reports supplied by the owner (Claude, Perplexity, DeepSeek) against primary/near-primary ICT material and TTrades public source material. Consensus between models is not treated as evidence. Only source-backed rules may advance.

## Source hierarchy

1. Michael J. Huddleston / The Inner Circle Trader official material.
2. TTrades public material for the TTrades Fractal Model and its CISD/protected-swing formalizations.
3. Secondary sources only for discovery; they cannot promote a rule to canonical status when stronger source evidence is absent.

## Primary ICT findings

Official ICT Core Content, Month 04, Rejection Block describes Turtle Soup as a false breakout / violation of an old high or old low followed by rejection and meaningful repricing. The same teaching explicitly identifies equal highs as buy-side liquidity and refers to an old short-term high in a Turtle Soup sequence. Therefore Turtle Soup itself is a liquidity-raid/rejection event; C2, CISD, FVG, MSS, fixed timing, fixed swing age, and fixed R:R are not universal definitional requirements.

Official ICT videos also demonstrate named Turtle Soup examples during NQ Lunch Macro and NY PM. Therefore London/NY-AM-only validity is contradicted as a universal rule.

## TTrades findings accepted for the R4 execution family

### Higher-timeframe bias comes first

TTrades' London and Asia Fractal Model guides explicitly start with higher-timeframe / daily bias. The London guide states that the clock itself does not make the setup valid; higher-timeframe structure does. Asia is explicitly tradable when the higher-timeframe framework supports expansion.

For an intraday Daily -> H4 -> M15 implementation, Daily bias is source-supported. Monthly+Weekly+Daily simultaneous directional agreement is NOT established as a universal requirement.

### Candle 2 reversal closure

TTrades defines a Candle 2 closure as:

- sweep the previous candle high or low;
- close back inside the previous candle range;
- form at a higher-timeframe point of interest.

Bullish: `C2.low < C1.low and C2.close > C1.low`.
Bearish: `C2.high > C1.high and C2.close < C1.high`.

No source-backed minimum reclaim fraction is specified.

### Point of interest

TTrades states that Candle 2 closures matter at a higher-timeframe POI such as a swing high/low, fair value gap, or opposing candle. For the Turtle Soup family, a qualified relevant swing can itself be the POI; an extra FVG is not universally required.

### Relevant swings

TTrades explicitly rejects treating all highs/lows equally. A relevant swing is the contextual extreme of the move, supported by valid separation. There is no strict numerical separation formula.

TTrades also gives a practical Fractal Model lookback: use the current timeframe while looking back three HIGHER-timeframe candles, including the current parent candle, to frame relevant levels. This does not support R3's arbitrary local three-H4-bar extremum. For an H4 model, parent-timeframe context must come from Daily structure, not merely three neighboring H4 bars.

### CISD

TTrades defines CISD as a close through the opposing delivery candle series. With multiple candles, the opening price of the first candle in the contiguous opposing sequence is the key level.

Bullish: after a sweep / low, close above the first open of the down-close series that formed the low.
Bearish: after a sweep / high, close below the first open of the up-close series that formed the high.

A wick through the level is insufficient; closure matters.

For the TTrades Fractal Model, lower-timeframe CISD must confirm the higher-timeframe Candle 2 or Candle 3 closure. TTrades states that CISD without the higher-timeframe closure is ignored.

### Protected swing

TTrades defines protected lows/highs as the swing confirmed by CISD after the sweep or POI interaction. Protected swings provide structural invalidation and stop location.

The closest protected swing is not automatically the correct one; structure and expected delivery matter. However, the public sources do not provide a complete deterministic universal algorithm for choosing among multiple protected swings. Therefore R4 should bind the protected swing causally to the exact CISD that confirms the selected higher-timeframe reversal, rather than scan for the nearest available protected swing.

Stop buffer beyond the protected swing remains a QORE execution formalization; no universal numeric buffer is source-confirmed.

### Positional entry

TTrades explicitly defines positional entry as entry at the open of a new higher-timeframe candle, but only after the Fractal Model is already complete: valid higher-timeframe Candle 2/Candle 3 closure plus lower-timeframe CISD, with a valid protected swing already formed before the new candle opens.

Therefore H4 C3-open entry is source-valid only when all confirmation exists before that open.

### Targets / Draw on Liquidity

TTrades' target guidance uses higher-timeframe untouched highs/lows and prior higher-timeframe candle highs/lows. It explicitly aligns lower-timeframe entry with higher-timeframe target, e.g. 5m entry -> hourly swing, hourly setup -> daily swing, daily setup -> weekly swing.

TTrades also describes PDH/PDL as objective draws on liquidity and asks where the nearest obvious liquidity not yet taken is.

There is NO sufficiently supported rigid universal ranking `PWH > PDH > old swing > equal highs > session high` for all contexts. Do not hard-code such a hierarchy.

TTrades defines internal liquidity as FVG and external liquidity as swing highs/lows within its Fractal Model. Therefore the external report that labels PDH/PDL generically as IRL is rejected.

For the first R4 candidate, the target should be a pre-entry, untouched parent-timeframe liquidity objective in the direction of the Daily bias. Exact candidate-set and tie-breaking must be preregistered before economics.

### Sessions

Session is metadata/context, not a binary validity gate.

- TTrades explicitly permits Asia when HTF structure supports expansion.
- TTrades states in its London guide that the exact kill zone is not extremely important and that the clock itself does not make the setup valid.
- Official ICT has named Lunch Macro and NY PM Turtle Soup examples.

Therefore Asia, London and New York remain eligible. No session discovered from R2/R3 P&L may become an R4 inclusion filter.

## Claims rejected from the external reports

1. `Kill Zone mandatory` — rejected.
2. `Monthly + Weekly + Daily must all point same direction` — not established for the intraday R4 family.
3. `Fixed 2R minimum` — not a Turtle Soup / TTrades Fractal universal rule.
4. `Relevant swing = fixed 3-10 / 10-40 / 40+ bars` — unsupported.
5. `PDH/PDL are generically IRL` — contradicted by TTrades' own IRL/ERL definition; classification is structural/contextual, not a label attached to PDH/PDL.
6. `Bullish protected swing must universally be below 50% / bearish above 50%` — overformalized. TTrades says EQ relationship matters, but continuation material can invert the conventional premium/discount use. No universal selector is supported.
7. `C2 must have a bullish/bearish body` — not part of the exact C2 closure definition.
8. `C2 reclaim must exceed a numeric depth` — unsupported; forensic 0.451 vs 0.302 remains descriptive only.
9. `1-2 pip/tick sweep`, `wick > 50%`, fixed stop buffer — unsupported.
10. `FVG mandatory` — rejected; a swing high/low itself can be the POI.
11. `Turtle Soup definition requires CISD` — rejected as a universal ICT definition. CISD is required only for the selected TTrades execution family.
12. `Rigid DOL hierarchy weekly > daily > session` — unsupported as a universal ordering.

## Errors found in the external reports

- One report's four-case pseudocode contains impossible conditions (`close < PDL` and `close > PDL` simultaneously; mirror at PDH). It cannot be used.
- One report simultaneously recommends a 2R minimum and lists arbitrary R:R as do-not-implement. The 2R gate is rejected.
- One report claims `no rules invented` while introducing Monthly+Weekly+Daily alignment and other rules not established by cited primary material.

## Three-report consensus that survives source adjudication

The following common conclusions are retained:

1. R3 is missing source-faithful higher-timeframe narrative/bias.
2. R3's local three-H4 relevant-swing proxy is inadequate.
3. C2 sweep + close-inside is the correct TTrades reversal closure family.
4. CISD must use the correct opposing candle series and a close, not a wick.
5. Protected swing must be causally tied to the confirming CISD and used as structural invalidation.
6. Positional C3-open is valid only after the complete model exists.
7. R3's opposite-C1 target is too local relative to source-backed higher-timeframe targeting.
8. Asia/London/New York remain eligible; time is context.
9. No fixed R:R, fixed wick ratio, fixed sweep depth, fixed session gate, or post-hoc pair/side filter is authorized.

## Recommended R4 research identity

`ICT_TURTLE_SOUP_R4_D1_C2_H1_CISD_H4_C2_M15_CISD_POSITIONAL_DOL`

This identity intentionally separates Daily bias formation from intraday execution.

### Proposed source-bound sequence

1. **Daily bias / expected Daily C3**
   - completed Daily Candle 2 reversal closure at a qualified Daily POI;
   - lower-timeframe confirmation inside that Daily C2 (candidate confirmation timeframe must be frozen; H1 is source-consistent and practical);
   - protected Daily swing established before the next Daily candle opens.

2. **Intraday H4 setup inside the expected Daily expansion**
   - H4 relevant swing / POI framed using parent Daily context, not three neighboring H4 bars;
   - H4 Candle 2 sweeps H4 C1 and closes back inside C1 range;
   - M15 CISD inside H4 C2 confirms the selected H4 swing;
   - the CISD-created protected swing is frozen as invalidation.

3. **Entry**
   - positional entry at H4 C3 open only when the full H4 model is complete before the open.

4. **Target**
   - pre-entry untouched Daily liquidity objective in the Daily-bias direction;
   - do not default to opposite H4 C1;
   - no minimum-R gate.

5. **Session**
   - no inclusion/exclusion by Asia/London/New York;
   - session recorded diagnostically only.

## Remaining machine-formalization blockers before replay

These are not reasons to invent source claims. They must be preregistered as QORE formalizations or fail closed:

1. exact parent-window implementation for the H4 relevant swing using TTrades' three-higher-timeframe-candle framework;
2. exact tie-breaking when multiple untouched Daily target highs/lows coexist;
3. exact handling of multiple same-side pools swept by one C2;
4. exact stop execution convention around the protected swing (zero offset vs one native tick beyond);
5. treatment of doji candles inside an opposing CISD series;
6. data-gap and same-bar stop/target ordering rules.

These mechanics may be frozen prospectively, but none may be optimized on R2/R3 outcomes.

## Governance

- R2/R3 2020-07-01..2022-07-01 evidence remains consumed development only.
- No fresh OOS opened in this adjudication.
- No pair/side/session/hour selected from consumed performance.
- No merge.
- `DEMO_ELIGIBLE=false`
- `LIVE_AUTHORIZED=false`
- `REAL_CAPITAL_AUTHORIZED=false`
- `PRODUCTION_AUTHORIZED=false`
