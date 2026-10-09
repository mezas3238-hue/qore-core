# VT31_LONDON — Frozen 3Y M1 Coverage & Causal Session Control V0

**Date:** 2026-10-09  
**Lane:** OPS / Architect 2  
**System identity:** ONE VT31_NAS100 Trader, internal model `VT31_LONDON`; `VT31_NY` remains separate.  
**Source evidence:** `VT31_NAS100_OWNER_3Y_BASE_001`; 2023-10-01 inclusive to 2026-10-01 exclusive.  
**Source artifact:** `11459859004`, same as NY (not Fresh Holdout).  
**Verified London coverage workflow:** [37991228778](https://github.com/mezas3238-hue/qore-core/actions/runs/37991228778) @ `d978361a5faaa13cb62644e6f05d89370db5a14d`, **SUCCESS**.  
**Clock unit-test workflow:** [37991437891](https://github.com/mezas3238-hue/qore-core/actions/runs/37991437891) @ `b01d6f32be89f53d2091b8c37107e3130cdb3b4e`, **SUCCESS**.

## 1. M1 evidence truth, not trade counts

Streaming proof processed **1,059,784 actual NAS100 M1 candles** across **936 London-local calendar dates with any bars** in the frozen 3Y development set. No backfilled market minutes and no alteration of the shared 3Y evidence.

| London local reference -> execution *diagnostic only* | Fully observed 60+60 M1 days |
|---|---:|
| 06:00-07:00 -> 07:00-08:00 | 773 |
| 07:00-08:00 -> 08:00-09:00 | **774** |
| 08:00-09:00 -> 09:00-10:00 | 773 |
| 09:00-10:00 -> 10:00-11:00 | 771 |

For the 07:00 reference / 08:00 execution pilot: 452 complete days are BST (UTC+1) and 322 are GMT (UTC+0). Across all dates with data, the UK-offset split is 544 BST / 392 GMT.

**IMPORTANT:** 774 is a **bar coverage count**, NOT a source opportunity count, executable signal count, trade count, realized win count, or certification pass. The separate London capacity/attrition map has not yet been built.

## 2. Proposed genuine London clock V0 (predeclared control for development)

A dedicated standalone clock contract now exists at:

`src/qore/infrastructure/traders/vt31_london_session_contract_v1.py`

Pilot definition, all time in `Europe/London` **civil wall time**:

- **Reference** 07:00 <= t < 08:00, exactly 60 consecutive closed M1 candles.
- **Execution / entry opportunity** 08:00 <= prospective fill open < 09:00.
- **Pending-entry cutoff** 09:00 (exclusive). An existing open position is not forcibly closed at 09:00; it remains under the canonical causal position engine, subject to structure/targets/exits.
- **UK DST** resolved from real IANA `Europe/London` offsets; it uses different UTC times in BST and GMT; never translate from a fixed New York UTC offset.
- **Causality**: require fully closed observations available no later than decision as-of; thesis confirmation observable inside execution; actual prospective fill open at/after decision and before 09:00; no same-bar high/low/close information.
- **Cognitive authority**: this clock **does NOT select trades**. Full canonical `reason_position` / maximum cognition / `PositionAction` must be adapted by Architect 1 without an NY-clock sidecar.
- **Structural lifecycle/rearm**: no duplicate thesis/event allowed; distinct rearm requires a newly observed structural event and new confirmation (not an arbitrary delay). Must be implemented and audited before any London candidate.
- **Eligible-session convention**: freeze each day whose validated reference and execution M1 evidence is complete; this is only a possible denominator for risk-adjusted stats, not proof a trade occurred. Normalize across years and BST/GMT.

This 07/08/09 London-local specification is a **V0 development hypothesis**, not a proven Silver Bullet London methodology specification or certification freeze. Before full London code is promoted, confirm source-methodology validity of these exact London-native windows and whether execution/fill/cutoff/rearm semantics differ from NY. A superficially renamed NY strategy is FORBIDDEN.

## 3. Unit/cognition integration gates

Current clock self-test proves:
- UK DST spring transition and fall transition genuinely shift the UTC clock;
- a full contiguous 60-bar reference requirement, no partial hour shortcut;
- inclusive execution start and exclusive pending cutoff;
- no prospective entry on a future/unclosed source bar;
- no naive timestamps.

Still required from the two architects:
1. **COG**: replace `decision_minute_ny`/NY-specific premarket and cash-open semantics with explicit session-model-aware producers where valid; preserve all core cognition and sensor actuation parity; no default NY states silently passed to London.
2. **OPS**: implement genuine London source -> raid -> structural confirmation -> FVG/Breaker/OB as methodologically warranted -> reasoning -> prospective fill -> structural terminal and canonical post-entry management.
3. **OPS**: complete the full 3Y source/attrition/opportunity-capacity map; truthful London control replay; individual PF, expectancy, payoff, DD <=6R, Sharpe >=1.5, Sortino >=2, MC positive >=90%, MC p95 DD <=~15R, stress, annual/regime robustness and genuine density >=400.
4. **BOTH**: tests for UK/US mismatch weeks, duplicated events, missing M1 and causal session handoff.
5. **DUAL**: no integrated live candidate until NY and London each independently pass development gates.

## 4. Final status

London data-coverage probe PASS; London UK DST clock contract self-test PASS. **VT31_LONDON operating signals/replay not yet implemented**; no session certification and no change to `VT31_NY`'s failed economics. Fresh Holdout SEALED; live/capital authorization FALSE.
