# QORE CAPITALIZER — V48 SOURCE-FAITHFUL RECONSTRUCTION & DIFFERENTIAL AUDIT

Status: PRE-ECONOMIC / RESEARCH ONLY  
Program: `V48 — ICT/TTRADES SOURCE-FAITHFUL SCALPER RECONSTRUCTION & DIFFERENTIAL AUDIT`  
Fresh Holdout 2014-09-17 -> 2016-09-17: **SEALED_UNTOUCHED**  
Parent generation: `V47_S2_REJECTED_BY_OWNER_INSUFFICIENT_DENSITY`

## 1. Purpose

V48 does not attempt to rescue V47, tune thresholds, inspect Fresh Holdout economics, or manufacture trade density.

Its first job is to answer one question:

> Which rules are actually required by ICT/TTrades, which are contextual or alternative execution techniques, and which were added or over-composed by QORE?

Every future productive rule must be classified as one of:

- SOURCE_EXPLICIT
- SOURCE_STRONGLY_IMPLIED
- INTERPRETATION
- QORE_ENGINEERING_RULE
- UNRESOLVED

INTERPRETATION, QORE_ENGINEERING_RULE, and UNRESOLVED may not silently become universal hard gates.

## 2. Initial source pack — first authoritative findings

### TTrades Scalping Model

Primary source:
https://ttrades.com/ttrades-scalping-model-simple-day-trading-strategy/

Explicit source structure:

- Daily = broader directional context.
- Hourly = scalping bias.
- 15M = swing structure.
- 1M = execution.
- The lesson states that the one-minute chart is where the trade is executed, not where the decision is made.
- M1 continuation behavior is illustrated with FVG interaction, CISD, and protected-swing formation.

V48 interpretation boundary:

The lesson does **not** establish that M1 MSS AND FVG AND OB AND CISD AND protected swing must all be independent mandatory gates on every trade. Exact execution-family semantics remain subject to source resolution, but the current QORE superintersection is not source-proven by this lesson.

### TTrades Asia

Primary source:
https://ttrades.com/how-to-trade-asia-using-the-ttrades-fractal-model/

The source explicitly describes **two primary ways** to trade Asia:

1. positional entry when the higher-timeframe framework/protected swing is already complete; OR
2. wait for a 4H Candle-2 closure, then use the 15M fractal model for confirmation/entry.

Therefore a universal H1 -> M15 -> M1 path for Asia is source-conflicting.

### TTrades London

Primary source:
https://ttrades.com/how-to-trade-london-using-ttrades-fractal-model/

The source explicitly describes:

Daily bias -> let Daily wick form -> 4H swing/wick structure -> 15M protected-swing/CISD confirmation -> continuation/expansion.

Therefore a universal H1 -> M15 -> M1 path for London is source-conflicting.

### TTrades New York manipulation

Primary source:
https://ttrades.com/daily-profile-understanding-the-new-york-manipulation/

The source describes sweep -> CISD -> expansion and states that entries can be refined with:

- FVG;
- Order Block;
- or the trader's choice of an entry model.

This is direct evidence that at least this TTrades New York framework treats entry models as plural techniques rather than a mandatory FVG AND OB intersection.

### TTrades Failure To Manipulate

Primary source:
https://ttrades.com/how-to-trade-breakouts-failure-to-manipulate/

Core identity:

- a high/low is taken;
- the expected reversal does not confirm;
- continuation becomes the hypothesis;
- higher-timeframe bias supplies the reason;
- lower-timeframe structure confirms the continuation/protected swing.

The source explicitly says FTM is not a standalone model. It does **not** in this source establish the entire V47 downstream M1 superintersection as mandatory.

### ICT primary material

Primary retained source:
https://www.youtube.com/watch?v=tmeCWULSTHc

ICT 2022 Mentorship remains authoritative primary material for the ICT side of the reconstruction. V48 has **not yet** completed timestamp-level binding for every current QORE ICT field. Those requirements remain UNRESOLVED in V48 until exact primary-source provenance is attached.

## 3. Differential audit — current QORE vs source

### Mismatch A — universal session grammar

Current file:
`src/qore/infrastructure/trader_lab/capitalizer_source_strategy_grammar_v2.py`

Current module description declares TTrades as:

`H1 -> M15 -> M1 scalp execution sequence`

This is not universally source-faithful across the intended three-session trader.

Evidence:

- Asia has positional OR 4H->15M routes.
- London uses Daily->4H->15M.
- Generic/NQ scalping can use H1->15M->1M.

Conclusion:

`UNIVERSAL_H1_M15_M1_SESSION_GRAMMAR = SOURCE_CONFLICT`

### Mismatch B — M1 became a second Trader

Current file:
`src/qore/infrastructure/trader_lab/capitalizer_dual_source_entry_acceptance_v1.py`

Current acceptance requires all of:

- M1 MSS;
- M1 FVG;
- M1 Order Block;

while also requiring the full upstream ICT + TTrades inventory.

TTrades Scalping Model says the one-minute chart is the execution timeframe after the narrative is already clear and lists continuation behaviors such as FVG interaction, CISD, and protected swing.

Conclusion:

`M1_PROMOTED_TO_SECOND_DECISION_SYSTEM = SOURCE_SUPPORT_NOT_ESTABLISHED`

### Mismatch C — dual-source superintersection

The same gate requires simultaneously:

- ICT liquidity reference;
- ICT raid;
- ICT MSS;
- significant displacement;
- ICT FVG in displacement;
- PD-array retrace;
- no-chase;
- TTrades HTF closure;
- TTrades CISD;
- TTrades protected swing;
- TTrades continuation;
- wick formation;
- M1 MSS;
- M1 FVG;
- M1 OB;
- structural stop/target validity.

V48 has not found source support that every item is an independent mandatory AND for every route/session/entry model.

Conclusion:

`DUAL_SOURCE_SUPERINTERSECTION_ALL_MANDATORY = SOURCE_SUPPORT_NOT_ESTABLISHED`

## 4. Immediate architecture consequence

Do **not** relax thresholds.

Do **not** simply delete gates.

Instead reconstruct:

```text
SESSION
  -> NARRATIVE
  -> BIAS / DRAW
  -> SESSION-SPECIFIC STRUCTURAL MODEL
  -> CHOOSE VALID ENTRY ROUTE
  -> ROUTE-SPECIFIC REQUIRED FACTS
  -> STRUCTURAL STOP
  -> STRUCTURAL TARGET
  -> EXACT EXECUTION
```

The key change is not "OR everything".

The key change is:

> Requirements belong to a route. Alternative routes must not be collapsed into one global AND.

## 5. Next source-resolution work

1. Bind the exact 2026 TTrades Scalping Model PDF/video claims into a line-by-line rule ledger.
2. Resolve positional-entry invariants and whether they apply only to Asia or more broadly.
3. Resolve New York route families: H1->15M->1M scalp, daily-profile reversal, continuation, and any market-specific NQ rules.
4. Resolve FTM exact minimum continuation proof and valid execution families.
5. Re-open ICT 2022 primary videos/transcripts and bind exact timestamps for liquidity, MSS/displacement, FVG/PD-array, entry, stop, and target claims.
6. Build the Opportunity Survival & Information Matrix before any new economics.
7. Build source graph vs current QORE graph by session and route.
8. Only after source closure, design V48 candidate architecture and run density/causal feasibility.
9. Fresh Holdout remains sealed until final architecture, rules, costs, ranking, stop/target policy, and HEAD are frozen.

## 6. Governance

V48-A authorizes no:

- economics;
- Fresh Holdout;
- certification;
- promotion;
- merge;
- DEMO;
- LIVE;
- VPS;
- production;
- real capital.

V45-V47 evidence remains preserved and falsified/rejected history.
