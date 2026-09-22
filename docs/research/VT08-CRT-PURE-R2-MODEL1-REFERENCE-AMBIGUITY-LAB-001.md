# VT08 CRT PURE — R2 MODEL #1 REFERENCE AMBIGUITY LAB 001

**Status:** CONSUMED RESEARCH EVIDENCE / NO POLICY PROMOTION  
**Run:** 35716776566 — SUCCESS  
**Evidence HEAD:** `d64db2f2779650abb906dd2d8549737816323f81`  
**Identity:** `VT08_CRT_PURE_R2_MODEL1_REFERENCE_AMBIGUITY_LAB_001`

## Purpose

RomeoTPT's source-closed Model #1 rule requires an M15 source candle to stab an
"old high" or "old low", followed by the corresponding body-close confirmation.
The reviewed primary corpus does not define a deterministic priority/ownership
algorithm when several prior highs/lows are eligible.

This lab therefore tests two **pre-declared engineering interpretations** without
promoting either from economic outcome:

- `UNTOUCHED_SWING_STRENGTH_1`
- `UNTOUCHED_SWING_STRENGTH_2`

Both policies are explicitly `ENGINEERING_AMBIGUITY_POLICY`, never RomeoTPT
source authority.

## Causal invariants

- M15 is aggregated only from complete 3 x M5 evidence.
- A swing reference becomes visible only after the required right-side M15
  confirmation candle(s) have closed.
- No future candle participates in reference creation.
- A reference is consumed on its first strict breach in this lab.
- Several references breached by the same source candle are deduplicated into
  one Model #1 source event.
- H4 CRT -> M15 Model #1 is retained.
- Confirmation requires a later M15 body close through the Model #1 source
  candle body boundary; wick-only confirmation is rejected.
- Replay fill is next contiguous M15 open after the confirmation close
  (`ENGINEERING_POLICY`).
- Stop is the Model #1 source-candle extreme.
- R1 50% destination is retained to isolate entry/reference behavior.
- R1 C3-close expiry is retained.
- Same-M15 stop/target ambiguity remains STOP_FIRST.
- BTCUSD uses the already-validated cTrader schedule-aware completeness
  semantics. No synthetic M5 is created.
- Policy promotion from PnL is prohibited.

## Exact results

### AUDUSD

Parent CRT events: **287**

| Policy | Trades | PF | Total R | Mean R | DD | Y1 PF / R | Y2 PF / R |
|---|---:|---:|---:|---:|---:|---:|---:|
| Swing 1 | 149 | 0.92748913 | -3.80311178 | -0.02552424 | 18.41327394R | 0.58309798 / -12.06311886R | 1.35128478 / +8.26000708R |
| Swing 2 | 102 | 1.21975804 | +6.55031673 | +0.06421879 | 8.19276216R | 0.72404664 / -4.39130610R | 1.78752231 / +10.94162283R |

AUDUSD is temporally unstable under both policies: both move from negative Year 1
to positive Year 2.

### USDJPY

Parent CRT events: **267**

| Policy | Trades | PF | Total R | Mean R | DD | Y1 PF / R | Y2 PF / R |
|---|---:|---:|---:|---:|---:|---:|---:|
| Swing 1 | 127 | 0.94842626 | -2.45442852 | -0.01932621 | 20.90575319R | 1.24636883 / +5.26150253R | 0.70588565 / -7.71593105R |
| Swing 2 | 95 | 1.05648811 | +1.80273361 | +0.01897614 | 16.33862802R | 1.53139679 / +7.79375450R | 0.65263323 / -5.99102089R |

USDJPY is also temporally unstable under both policies, but in the opposite
direction from AUDUSD: positive Year 1 deteriorates in Year 2.

### BTCUSD

Parent CRT events: **459**

| Policy | Trades | PF | Total R | Mean R | DD | Y1 PF / R | Y2 PF / R |
|---|---:|---:|---:|---:|---:|---:|---:|
| Swing 1 | 328 | 1.06212017 | +6.72259448 | +0.02049571 | 17.43822168R | 0.92646748 / -3.91468645R | 1.19346946 / +10.63728093R |
| Swing 2 | 218 | 1.37774167 | +22.19927761 | +0.10183155 | 12.29357644R | 1.19568644 / +5.93632639R | 1.57198458 / +16.26295122R |

BTCUSD is the only market where Swing 2 is positive in both one-year folds.
That observation is **not** authority to promote Swing 2.

## Combined chronological characterization

Combined metrics below are reconstructed directly from the three retained
`trades.jsonl` artifact ledgers and sorted by entry timestamp.

| Policy | Trades | Wins | Losses | PF | Total R | Mean R | Chronological DD | LS |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Swing 1 | 604 | 313 | 289 | 1.00223306 | +0.46505418 | +0.00076996 | 24.88612933R | 8 |
| Swing 2 | 415 | 233 | 180 | 1.25356972 | +30.55232795 | +0.07362007 | 9.90118833R | 6 |

Temporal folds:

| Policy | Y1 Trades | Y1 PF | Y1 R | Y1 DD | Y2 Trades | Y2 PF | Y2 R | Y2 DD |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Swing 1 | 303 | 0.89648967 | -10.71630278R | 18.35247338R | 301 | 1.10676378 | +11.18135696R | 16.70822544R |
| Swing 2 | 212 | 1.15330660 | +9.33877479R | 6.99466313R | 203 | 1.35609228 | +21.21355316R | 9.90118833R |

## Multiple Model #1 opportunities inside one parent CRT

The lab deliberately records distinct causal Model #1 events rather than forcing
one trade per H4 CRT.

### Swing 1

- AUDUSD: 149 trades across 112 parent CRTs; 28 parents have multiple entries;
  maximum 4.
- USDJPY: 127 trades across 96 parent CRTs; 25 parents have multiple entries;
  maximum 4.
- BTCUSD: 328 trades across 228 parent CRTs; 79 parents have multiple entries;
  maximum 5.

### Swing 2

- AUDUSD: 102 trades across 80 parent CRTs; 21 parents have multiple entries;
  maximum 3.
- USDJPY: 95 trades across 78 parent CRTs; 13 parents have multiple entries;
  maximum 4.
- BTCUSD: 218 trades across 177 parent CRTs; 36 parents have multiple entries;
  maximum 3.

This is relevant to later Journey/re-entry governance; the ambiguity lab itself
does not grant simultaneous-position or re-entry authority.

## Adjudication

### Finding 1 — reference semantics are economically material

The old-level formalization changes trade density, PF, total R, drawdown and
temporal behavior materially. Therefore `MODEL_1_REFERENCE_SELECTION` cannot be
treated as a harmless implementation detail.

### Finding 2 — Swing 2 cannot be selected because it made more money

Although Swing 2 is economically stronger in this consumed window, promoting it
for that reason would be outcome-aware selection / curve fitting and is forbidden.

### Finding 3 — the primary source still does not specify numeric swing strength

The source says old high / old low and describes the qualifying source candle and
confirmation behavior. No reviewed primary evidence says "strength 1",
"strength 2", nearest, most recent, or highest-priority pivot.

### Finding 4 — minimal semantic translation is a separate research identity

If engineering needs a deterministic characterization before primary closure,
`strength=1` is the minimal local-turning-point translation because it adds the
least extra persistence requirement beyond "old high/old low".

That does **not** make Swing 1 canonical or certified. It may only be used under a
separately named engineering-policy R2-A characterization. Swing 2 remains a
robustness/ambiguity control, not a promotable rule.

## Decision

- Keep `MODEL_1_REFERENCE_SELECTION = AMBIGUOUS` in source authority.
- Do not promote Swing 1 or Swing 2 from this lab.
- Preserve the full artifacts and hashes from run 35716776566.
- Permit a separately identified **R2-A minimal-reference characterization** using
  Swing 1 only because it is the least-assumptive deterministic translation, not
  because of its PnL.
- R2-A must remain research-only and cannot be called canonical CRT.
- Continue source research for old-level ownership, key-level context, Journey and
  re-entry semantics.
