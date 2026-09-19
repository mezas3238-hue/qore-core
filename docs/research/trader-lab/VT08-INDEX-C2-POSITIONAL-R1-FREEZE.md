# VT-08 Index C2 Positional R1 — Pre-Economic Freeze

Checkpoint: 2026-09-13

Status: RESEARCH ONLY / CONSUMED ENGINEERING WINDOW / NOT DEMO ELIGIBLE / NOT LIVE

## Purpose

Freeze a distinct executable research candidate for the VT-08 Futures/index family before inspecting any win/loss, profit factor, expectancy, or P&L produced by the retained NAS100/SP500/US30 evidence.

Parent research lineage: PR #534 at HEAD `8754f65d39e23d44e7fc41f3751072acc366b01a`.

This candidate does not modify the qualifying/certified Forex B01 lineage and does not touch PR #532 or PR #533.

## Candidate identity

- Candidate: `VT08_INDEX_C2_POSITIONAL_R1`.
- Trader code: `vt-08`.
- Markets: `NAS100`, `SP500`, `US30` only.
- Provider proxies observed in retained DEMO evidence: `USTEC`, `US500`, `US30`.
- Environment for research evidence: cTrader DEMO read-only only.
- Timezone: `America/New_York`.
- Owner operational entry anchors: `02:00`, `06:00`, `10:00` New York local time.
- LTF profile: M15 only.
- Scenario scope: completed Candle-2 reversal closure only.
- Candle-3 path: excluded / fail-closed in R1.

## Independently verified source authority

The following TTrades material was independently checked before this freeze:

- `Trading the 4-Hour Power of 3: Open, High, Low, Close Strategy` — source states that the 15-minute chart pairs with H4 and that 02:00/06:00/10:00 are key Futures anchors.
- `Mastering Important Time Levels in Trading with OHLC and Opposing Swings` — source lists 18:00 as daily open and 02:00/06:00/10:00/14:00 as H4 opens.
- `Understanding The Change in State of Delivery (CISD)` — source defines CISD as a close through the opening price of the opposing candle series and, for multiple candles, uses the first candle open.
- `Protected Swings in Trading` — source defines protected swings through liquidity interaction plus close through the opposing series and uses the protected swing as structural invalidation.
- `How Change in the State of Delivery (CISD) Confirms Swing Points` — source requires HTF Candle-2/Candle-3 closure plus LTF CISD before continuation is considered valid.
- `Positional Entries – Enter Before The Expansion` — source permits an entry at the open of a new higher-timeframe candle only after the fractal model is already complete and a protected swing exists.
- `The Only Trading Strategy You Need For 2026` — post-source author clarification supplies the mechanical four-case daily bias and a generic initial 2R objective.

Primary historical source remains `youtube:FAKWJ-1NlLE`, SHA-256 `bfe76fa4346ec4d7442886c21834aa26f0d82172bdb55666e8c77226cdf83271`.

## Frozen causal rules

### 1. Daily bias

Use only completed source-day evidence known before the entry anchor.

Source-day operational reconstruction for this candidate:

- source daily open reference: 18:00 New York;
- aggregate available M15 trading bars from 18:00 through the next 17:00 market close;
- require exactly 92 M15 bars for a complete ordinary session; incomplete/holiday sessions fail closed;
- use the latest two complete source days before the decision time.

Four-case bias:

1. current completed day closes above prior day high -> LONG;
2. current completed day closes below prior day low -> SHORT;
3. current completed day sweeps prior day low and closes back above it -> LONG;
4. current completed day sweeps prior day high and closes back below it -> SHORT;
5. conflict, both-side unresolved reversal, inside condition, or missing evidence -> ABSTAIN.

The 18:00 daily-open authority is source-supported; the exact 92-bar cTrader CFD session reconstruction is QORE operational formalization.

### 2. H4 reconstruction and entry anchors

Evaluate only decisions at 02:00/06:00/10:00 New York.

For each decision anchor:

- `Candle 2` is the immediately completed four-hour wall-clock interval ending at the decision anchor;
- `Candle 1` is the immediately preceding four-hour wall-clock interval;
- require 16 contiguous M15 bars in Candle 1 and 16 contiguous M15 bars in Candle 2;
- 22:00 may therefore appear as reconstruction-only H4 structure for a 02:00/06:00 decision. It is not promoted to an Owner operational entry anchor.

### 3. Deterministic POI family

R1 uses exactly one source-supported POI family: the previous H4 Candle-1 extreme.

- LONG candidate -> Candle 2 must sweep Candle-1 low;
- SHORT candidate -> Candle 2 must sweep Candle-1 high.

No FVG hierarchy, order-block hierarchy, SMT selection, or best-in-hindsight POI is allowed in R1.

### 4. Completed C2 closure

LONG C2:

- Candle 2 trades below Candle-1 low;
- Candle 2 does not also sweep Candle-1 high;
- Candle 2 closes back strictly inside Candle-1 range;
- daily bias is LONG.

SHORT C2:

- Candle 2 trades above Candle-1 high;
- Candle 2 does not also sweep Candle-1 low;
- Candle 2 closes back strictly inside Candle-1 range;
- daily bias is SHORT.

Both-side sweep or mismatch with daily bias -> ABSTAIN.

No shallow/large wick threshold is used. C3 is not implemented in R1.

### 5. M15 CISD and Protected Swing

Search only inside the completed Candle-2 M15 bars.

For LONG:

- opposing series = one or more consecutive down-close M15 candles;
- CISD level = open of the first candle in that opposing series;
- series extreme = minimum low of the series;
- the series extreme must trade below the Candle-1 low POI;
- a later M15 close inside Candle 2 must close above the CISD level;
- the series extreme becomes the protected low.

For SHORT, mirror the rule with up-close candles, maximum high, sweep above Candle-1 high, and close below the first opposing-series open.

Exactly one valid Protected Swing is required. Zero -> ABSTAIN. More than one -> ABSTAIN. No nearest/latest/deepest/best-in-hindsight selector is authorized.

### 6. Positional entry

After completed C2 + matching daily bias + M15 CISD + exactly one Protected Swing:

- entry reference = exact open of the new H4 candle at the 02/06/10 decision anchor;
- historical replay assumes fill at that OHLC open;
- broker order type is explicitly unresolved and is not inferred from replay.

### 7. Stop

- structural invalidation reference = Protected Swing extreme;
- historical replay uses that exact level with zero offset.

Source authority is the Protected Swing structural invalidation. Zero tick/pip/spread offset is QORE research containment because the source says beyond/beneath/above but does not quantify the offset.

### 8. Target

- fixed initial replay target = 2R from entry using the structural stop distance;
- applying fixed 2R to this narrow positional replay is a post-source author-supported formalization and a frozen research containment, not a claim that all TTrades targets are universally fixed 2R.

No target hierarchy or future-selected HTF objective is allowed.

### 9. Same-bar ambiguity

If stop and target are both touched inside the same M15 bar after entry, replay records STOP first. This is a conservative QORE execution containment.

### 10. Filled-trade lifecycle

If neither stop nor target is reached during the four-hour interval after entry, close the modeled position at the final M15 close immediately before the next H4 boundary.

This forced H4 exit is QORE research containment, not source authority.

### 11. Daily cardinality

Group eligible candidates by canonical market and New-York calendar date.

- exactly one eligible R1 candidate that day -> model it;
- zero -> no trade;
- more than one -> ABSTAIN for the day.

This deliberately fail-closes instead of retrospectively selecting 02, 06, or 10. It is Owner/QORE governance, not a TTrades universal rule.

## Explicit exclusions

R1 excludes:

- Candle 3 execution;
- numeric wick thresholds;
- SMT requirement;
- M5/M3 selection;
- FVG/POI hierarchy beyond the swept Candle-1 high/low;
- multiple-PS selection;
- stop offsets;
- body-stop refinement;
- dynamic/structural target hierarchy;
- re-entry;
- 14:00 operational entries;
- LIVE/production/broker authority.

## Economic governance

The retained 2024-08-13 through 2026-09-11 NAS100/SP500/US30 data is already consumed. It may now be used only for exploratory engineering/replay of this frozen R1 candidate.

No rule in this document may be changed because of the R1 economic result without creating a new candidate identity and a new pre-economic freeze.

Formal independent validation requires a genuinely fresh, pre-reserved unseen interval after R1 is frozen.

`DEMO_ELIGIBLE=false`

`LIVE_AUTHORIZED=false`

`PRODUCTION_AUTHORIZED=false`
