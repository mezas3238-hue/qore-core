# VT31 / NAS100 — M1 is the PRIMARY Silver Bullet trading timeframe

**Architect 2 OPS — 2026-10-09.** Original ICT Silver Bullet clean-room reset.  
**Single trader identity:** `VT31` for NAS100, two INTERNAL models (London, New York), three original ICT source hours NY local: 03–04 / 10–11 / 14–15. **No independent M1 trader; VT31 itself trades from M1 evidence**.  
**GitHub OPS branch:** `agent/vt31-ict-cleanroom-rebuild-20261009`.  
**Authoritative source of methodological doctrine:** [ICT Silver Bullet 2023](https://www.youtube.com/watch?v=tRq1hyGGtl4). Policies not literally established there remain QORE research hypotheses.

## Absolute owner requirement: M1 execution, higher timeframes context only

| Element | Timeframe | Causal evidence | Responsible architect |
|---|---|---|---|
| Entry structural swing / MSS | **M1** | Previously confirmed swing + later closed M1 break and displacement | Architect 1 COG |
| FVG that creates Silver Bullet setup | **M1** | Three consecutive **closed M1** candles, price gap between candle 1 and 3, confirmed only at close of third M1 | Architect 2 OPS |
| First suitable FVG and price zone | **M1** | Selected source gap must align with then-available directional DOL and price zone; never winner-picked | OPS + COG |
| Pending entry confirmation | **M1 / bid-ask tick** | Signal formed after M1 close; quote side-aware limit touch is NOT a broker fill | Architect 2 OPS |
| Later M1 post-entry context | **M1** | Broker-reconciled position/price chronology with fresh cognitive assessment; NOT historical label | OPS + COG |
| Contextual liquidity / range and bias | M15/H1/H4 | CLOSED and as-of M1 aggregated HTF bars, true session liquidity source identity; does NOT directly create an entry | Architect 1 COG |

No synthetic `M5` or `M15` candle may ever substitute a `M1Bar` in the operational gap producer. The original windows are in NY local time with US DST; London UK-local fixed clocks are not accepted.

## Actual source changes

**NEW:** `src/qore/infrastructure/traders/vt31_ict_cleanroom/m1_execution.py` exports explicit machine-readable `required_timeframe_contract()`, `ClosedM1Fvg` and `confirmed_m1_fvg()`.

- `ENTRY_TIMEFRAME='M1'`, `STRUCTURE_TIMEFRAME='M1'`, `FVG_TIMEFRAME='M1'`, `HTF_CONTEXT_ONLY=('M15','H1','H4')`.
- Rejects any non-`M1Bar` as source candle; validates uninterrupted **60-second** minute bars and the 3-M1 source clock, gap direction and closed third candle time.
- All three closed M1 candles fully inside one ICT original window is a **conservative research policy**, not claimed as a primary-source universal; the candidate still needs validated DOL and MSS/entry zone.
- Keeps quote/tick order execution independent: price touches never imply broker fills.

**MODIFIED NEW CLEANROOM, NOT LEGACY:** `src/qore/infrastructure/traders/vt31_ict_cleanroom/operations.py` now **routes every source FVG to this same M1 producer**, removing duplicated raw FVG detection rules. Its `snapshot()` advertises primary `execution_timeframe='M1'`, `structure_execution_timeframe='M1'`, `fvg_timeframe='M1'`, `higher_timeframes_role='CONTEXT_ONLY'`, and `formed_by_closed_m1=true`.

**NEW TESTS:** `tests/infrastructure/test_vt31_ict_cleanroom_m1_execution.py`, verifying original NY/DST 10:00 source clock, consecutive genuine closed M1, FVG confirmation only after third M1 closes, M5 rejection, M15/H1 rejected as entry generators, cross-boundary conservative rules, no submitted orders/fills, one stable `VT31` identity.

**ACTUAL CI**: [38015845365 SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/38015845365). Additional global QORE CI [38015849968](https://github.com/mezas3238-hue/qore-core/actions/runs/38015849968) must be checked for terminal status before promotion.

## Important shared COG/OPS open requirement: MSS may PRECEDE FVG by multiple M1 closes

COG branch `agent/vt31-ict-cleanroom-cognition-single-trader-20261009` currently computes causal local M1 swings/MSS, then emits `CognitiveDecision` mainly at the **current M1 break**. A first suitable FVG can form later (e.g., **10:01 M1 displacement MSS → 10:03 completed M1 FVG**). A missing fresh COG decision on 10:03 results in OPS `AWAIT_COGNITION` and potential loss of legitimate source setups.

**Fix required by Architect 1 COG, not by OPS duplicating its logic**: keep `M1_MSS_CONFIRMED` state with original `structure_break_confirmed_at`, refresh `observed_at` and critically **revalidate** the liquidity draw, swing/structure and context at each subsequent closed M1; invalidate or expire if the draw is consumed, thesis reverses, M1 structure breaks, or the source window ends. Do NOT blindly reuse old cognitive permission or trust future outcome. Explicit joint test with MSS at T, FVG at T+2 M1, separate stale draw/sweep scenario, and compare cogn-produced vs OPS-consumed source identity.

OPS already posted cooperative request in [Issue #727](https://github.com/mezas3238-hue/qore-core/issues/727#issuecomment-6092524800). No edits to Architect 1's claimed COG code.

## Remaining scientific and deployment limits

The M1 CI certifies **timeframe wiring / source shape** only. It cannot certify profitability, MSS-to-FVG continuous cognition, paper/tick/bid-ask broker execution, risk budget, account balances, capital compounding, position management or fully faithful source doctrine.

Full 3Y NAS100 M1 source-only negative control already passed [38013301255](https://github.com/mezas3238-hue/qore-core/actions/runs/38013301255) with 1,059,784 M1 and **zero invented trades without cognition**. Full new COG+OPS chronology and economic broker-friction tests must be run *after* Architect 1 integration.

**ONE VT31. M1 primary. London + New York internal. NO LIVE. Not certified. Fresh Holdout SEALED.**
