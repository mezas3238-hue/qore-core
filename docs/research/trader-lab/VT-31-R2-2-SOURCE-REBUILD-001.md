# VT-31 R2.2 — Primary Audio + Visual Source Rebuild

Status: **RESEARCH ONLY / DRAFT / NO DEMO OR LIVE AUTHORITY**

Primary source: `1000856441.mp4`, SHA-256 `bd729056fadc30d20045e4677240b3a6cbb65123ced317e7413b6ffe81936ddf`, `youtube:o0v4KQxZbpU`.

PR #517 at `5335f2fcd7593df04fb0f1277fdb5d1c185d8553` is retained as the forensic baseline. Its successful run `34660383434` produced artifact `10287780783`; retained economics are 113 setups, 90 fills, 11 targets, 70 stops, 9 breakevens, 12.2222% target win rate, -0.3817768522R expectancy and 34.3599167004R maximum drawdown. Those numbers are descriptive baseline evidence only and are invalid for final qualification after methodology changes.

## Frozen source model

- NQ/NAS100 only; H1 reference and M1 execution.
- Complete closed 09:00–10:00 America/New_York reference range.
- Setup formation only from 10:00 inclusive to 11:00 exclusive.
- Strict penetration is the conservative sweep formalization; equality/touch is not a sweep.
- High raid implies SHORT and target at frozen reference low; low raid implies LONG and target at frozen reference high.
- Post-raid structural close is a `SOURCE_FORMALIZATION` of repeated displacement behavior, not a numeric definition of aggressive displacement.
- Breaker, Order Block and Fair Value Gap are source-supported entry families.
- Pending order expires at 11:00; a filled position is not force-closed at 11:00.
- 3R arms break-even. No partials/trailing/time exit are added.
- Stop reference is the methodological swing extreme; no ATR/tick/arbitrary buffer is introduced.

## Primary visual re-adjudication

The original video was re-inspected around 02:26–02:56, 05:31–06:01, 07:18–07:43, 08:23–08:34, 10:32–10:49, 12:03–12:15, 16:07–17:14, 19:18–20:01, 21:12–21:37, 22:31–23:10, 24:02–24:14 and 25:14–25:18.

The charts repeatedly show entry zones and position tools, but do not demonstrate a universal Breaker-body midpoint, Order-Block-body midpoint or FVG consequent-encroachment rule. A specific example around 21:24 visibly uses a LIMIT order; that proves LIMIT appears in source examples but does not establish one universal exact price formula across all families.

## Three-layer architecture

### Layer 1 — Source model

The evaluator emits source structure and `EntryEvidence` zones/candles. Source entry evidence deliberately has **no `entry_price` field**.

### Layer 2 — Source ambiguity

Still unresolved: exact Breaker price, exact Order Block price, universal FVG executable price, family priority, re-entry, quantitative displacement threshold and exact stop tolerance. Both reference sides swept is source-ambiguous and therefore fails closed instead of using `FIRST_SWEEP_WINS`.

### Layer 3 — QORE execution policy

The first fresh replay pre-registers `qore-vt31-r2.2-zone-midpoint-ce-earliest-v1` only as a research translation for baseline comparability. It is fingerprinted with `source_rule=false`: Breaker body midpoint, unique Order Block body midpoint, FVG consequent encroachment, fail-closed simultaneous non-equivalent family prices, swing extreme with no invented buffer, conservative same-bar ordering.

Economics under this profile qualify the **operational profile**, never the unresolved TTrades source geometry itself.

## Human Owner cardinality

QORE imposes maximum one filled trade per NAS100 / America_New_York local date as `HUMAN_OWNER_EXECUTION_POLICY`. It is not attributed to TTrades. The replay emits `Vt31MarketDayLedger`; CI fails on any daily cardinality violation.

## Holdout governance

The fresh 760-day campaign is research evidence. Any strategy hypothesis derived from it consumes that OOS evidence; a changed strategy requires a new previously unseen holdout before independent validation.
