# QORE Core · VT31 Original ICT Silver Bullet Fidelity — Source & Implementation Truth

**Date:** 2026-10-09  
**Lane:** OPS (Architect 2), coordinated with COG (Architect 1) via Issue #727.  
**One trader:** `VT31_NAS100` with internal `VT31_LONDON` and `VT31_NY` operating models. `VT31_NY_AM` and `VT31_NY_PM` are source-lesson *windows* inside NY, not separate traders.  
**GOVERNANCE:** 3Y consumed data; pure edge only; Fresh Holdout SEALED; real capital/LIVE NOT AUTHORIZED; VT31 NOT CERTIFIED.  
**Primary source, Michael J. Huddleston / The Inner Circle Trader:** [2023 ICT Mentorship - ICT Silver Bullet Time Based Trading Model (2023-05-14)](https://www.youtube.com/watch?v=tRq1hyGGtl4) (`youtube:tRq1hyGGtl4`).

## 0. Owner directive — EXACT SOURCE FIDELITY FIRST

The Owner requires VT31 to reproduce **ICT's actual Silver Bullet methodology**, not merely share the strategy name or optimize a TTrades derivative until its metrics look good. Source rules must be traceable to the original lesson, and machine formalizations must be distinguishable from explicitly taught doctrine.

**SOURCE TRUTH HIERARCHY**:
1. `ICT_2023_EXPLICIT`: primary 2023 Silver Bullet lecture `tRq1hyGGtl4`.
2. `ICT_2023_CONTEXTUAL`: illustrated but not universally mandated context (MSS, raid, particular DOL examples).
3. `QORE_OBJECTIVE_FORMALIZATION`: necessary causal machine interpretations not specified numerically by ICT (e.g. exact 3-candle wick FVG, first-FVG identity, provenance).
4. `TTRADES_VARIANT`: independently taught TTrades methodology `youtube:o0v4KQxZbpU` used by current VT31 source `vt31_silver_bullet_r2_2.py`.
5. `QORE_RESEARCH/OWNER_VARIANT`: risk/coverage/sensor studies, not primary source authority.

**No layer 4/5 rule may be silently relabeled as mandatory ICT doctrine.** A strict ICT source gate may require objective proof of a lesson precondition but not manufacture extra mandatory barriers merely because they improved prior profits.

## 1. Primary-source rules and audited state

| Topic | Primary-ICT 2023 source | Current VT31 observation / work |
|---|---|---|
| London hour | **03:00-04:00 America/New_York** | OLD `07:00-08:00 ref ->08:00-09:00 Europe/London` V0 hypothesis was NOT source faithful, since NY/UK DST mismatches. CORRECTED by `vt31_london_session_contract_v1.py`. |
| NY AM hour | **10:00-11:00 America/New_York** | Existing NY TTrades engine uses 10-11 window. Clock matches, source geometry differs. |
| NY PM hour | **14:00-15:00 America/New_York** | Missing as a separately evaluated operational window. It must be considered under VT31_NY for full three-window fidelity, without fabricating new trades or weakening NY gates. |
| Session timezone | Local NY clocks follow US DST, never fixed EST/UTC | Corrected London contract uses `ZoneInfo("America/New_York")` for SOURCE clock and `ZoneInfo("Europe/London")` only for display/operational timezone. |
| Primary directional thesis | Establish **next draw on liquidity (DOL)** before selecting an entry | Current `next_structural_target` missing in 3,219/3,219 old sensor calls. COG must produce causal DOL from prior day/session/week highs/lows, NWOG or documented preexisting imbalances, not terminal PnL. |
| Projected potential | For indices expect **>=10 index points** projected *price-delivery framework*; not mandatory 10 points captured or a 10-point FVG | New source gate checks DOL-to-observed-price projected index points and distinguishes target framework from actual realized trade. Conversion per broker instrument points must be explicit. |
| Entry price delivery | Look for **a classic FVG formed inside the hour** in the direction of expected DOL, with a retracement/entry inside the suitable zone | New causal M1 3-candle FVG census and strict preadmission source contract. One raw FVG alone does not constitute an executable setup. |
| FVG priority | ICT discusses **first FVG within the suitable entry price zone** | Require event provenance, no manual `TRUE` from future bars; exactly chosen family must link to actual causal FVG. |
| MSS, sweep, raid | Important and often illustrated context; original source does **not** establish a universal mandatory sweep of the immediately preceding clock-hour 09-10 range for all 2023 Silver Bullets | Existing TTrades requires raid of `09:00-10:00 NY` H1 reference, and accepts Breaker/Order Block/FVG families. Source distinction must remain explicit. Do not delete good methodology blindly; compare a separate unchanged-source CONTROl vs primary-ICT source candidate. |
| Structural stop and exit | Stop/target must follow observed market structure and DOL, with post-window position life possible | COG canonical `PositionAction`, causal post-entry management, fill-time revalidation and execution parity still mandatory. Do not force-close at end of Silver Bullet formation window. |
| Trade frequency | ICT discusses availability of Silver Bullet setups across markets and hours, not a guarantee that a single asset produces a specific count | Owner target ~450 real trades/3Y and current machine floor >=400 remain gates, but **never** synthesize/extrapolate FVG raw counts into trades to satisfy a density objective. |

## 2. Implemented THIS engineering session

### P0.1 corrected clock (code, pass)
- `src/qore/infrastructure/traders/vt31_london_session_contract_v1.py`.
- UK/US DST disagreement tested (2026-03-10 and 2026-10-26 London 07:00; 2026-03-30 London 08:00). All are **03:00 NY**, the real source clock.
- `VT31_NY_AM=10-11`, `VT31_NY_PM=14-15` added as read-only source window definitions; PM is not yet an executable model.
- UTC-closed M1 and prospective fill guards. Preceding context H1 is optional, NOT authoritative entry veto.
- CI **SUCCESS**: [37993168871](https://github.com/mezas3238-hue/qore-core/actions/runs/37993168871).

### P0.2 Original-ICT source-only 3Y FVG capacity — Trader Lab Fast Runner, pass
- `scripts/vt31_ict_silver_bullet_3y_source_fidelity_probe_v1.py`.
- Frozen M1 artifact `11459859004`, **1,059,784 exact NAS100 M1 bars**; no data reacquisition.
- CI **SUCCESS**: [37993358126](https://github.com/mezas3238-hue/qore-core/actions/runs/37993358126); output artifact `11646505633`.
- In source 2023 time windows (all NY local):

| Source clock model | 60-M1 complete session days | Days with at least 1 raw FVG | Total raw 3-bar wick-gap events |
|---|---:|---:|---:|
| London 03-04 NY | 774 | 774 | 11,769 |
| NY AM 10-11 NY | 771 | 771 | 11,123 |
| NY PM 14-15 NY | 741 | 741 | 10,312 |

**These are NOT trades**; no DOL, >=10 projected-point test, first-FVG/source-link, MSS, risk geometry, fill, or full cognition established for those observations. No density, PF/DD, Sharpe, MC or certification may be inferred from this raw census.

### P0.3 Source eligibility/research-only contract — pass
- `src/qore/infrastructure/traders/vt31_ict_silver_bullet_source_contract_v1.py`.
- Validates exact window, three closed causal M1 FVG candles, directional gap, prospective retracement inside gap, structural stop observed and correct side, explicit producer + timestamp + family of DOL, DOL position in thesis direction, **>=10 projected NAS100 index points** from as-of price, first suitable FVG source proof, no future candles and fill-before-expiry.
- Never authorizes an order: `actionable_trade_authority=False`, `certified=False`.
- CI **SUCCESS**: [37993530065](https://github.com/mezas3238-hue/qore-core/actions/runs/37993530065).
- The source contract is necessarily stricter operationally where evidence is missing (fail closed) but does **not** claim MSS, TTrades mandatory hour raid, fixed H1 stop nor breaker/OB as unconditional ICT prerequisites.

### P0.4 Fidelity check against ACTUAL 55 NY baseline trades — pass
- `scripts/vt31_ict_silver_bullet_ny_3y_admitted_trade_fidelity_audit_v1.py`.
- Exact same immutable 3Y market artifact plus frozen NY 55-trade ledger artifact `11459439466`.
- Strictly detects a *directional raw FVG that CLOSED at or before the historical signal timestamp*, not using future bars; never alters outcomes or signals.
- CI [37993673013](https://github.com/mezas3238-hue/qore-core/actions/runs/37993673013) **SUCCESS** (initial full baseline); exact Decimal M1 comparison added as a follow-up.
- Results from frozen 55:
  - **33/55 signals** had an earlier closed same-direction raw FVG in their 10-11 NY window, **UNLINKED** to actual setup identity.
  - **22/55 signals** had **NO same-direction already-closed raw FVG by their signal**.
  - **Breaker 36:** 22 without earlier directional FVG and 14 with raw unlinked FVG.
  - **FVG 19:** all 19 with prior raw FVG context (but direct source linkage not yet independently proven).

**Interpret carefully:** 22 signals currently lack basic FVG evidence **at signal time**. This is not proof those eventual *fills* could never satisfy ICT; a valid FVG could form later between signal and prospective fill. Full fill-time source reconstruction is mandatory. The 33 favorable raw FVG contexts likewise do **not** prove a genuine ICT Silver Bullet because the actual chosen source FVG identity, DOL, framework and execution are not yet all evidenced.

## 3. Conflict resolution: TTrades original NY control vs primary ICT doctrine

The current canonical NY `vt31_silver_bullet_r2_2.py` includes:
- Source `youtube:o0v4KQxZbpU`, `METHODOLOGY_ID=ttrades-am-silver-bullet-nq-r2.2`.
- **Hard** 09-10 NY H1 completed range.
- **Hard** raid of that range, first side/cross-side ambiguity suppression.
- Structural confirmation and selectable **Breaker / Order Block / Fair Value Gap**.
- Opposite frozen 09-10 reference boundary as default target.
- Restriction to 10-11 NY, no original-ICT London clock or NY PM setup model.

These are **legitimate variant assumptions where disclosed**, but they are NOT a proved exact implementation of the original ICT 2023 source. The Owner requests conversion to a faithful source model. Do not silently alter prior economic baselines; establish an independent `ICT_SOURCE_TRUE_CONTROL` on frozen 3Y first, then compare against `TTRADES_CURRENT_CONTROL` with complete identical evidence and Core gates.

## 4. Required integration next (hard P0)

**Architect 1 (COG):**
1. Produce `primary_next_draw_on_liquidity` with family/source, causal observed_at and target as-of, from prior day/week/session H/L, NWOG and recorded imbalance, with explicit NA only when genuine absence. This is more important than a higher PF obtained via filters.
2. Rebuild max cognition with source type and explicit `session_model_id` `VT31_LONDON`, `VT31_NY_AM`, `VT31_NY_PM` and legitimate market context. Avoid NY cash-open assumptions inside London.
3. Produce causal FVG identity + first-in-entry-zone proof and structural MSS/displacement/sweep context without assuming a mandatory 09-10 reference raid for original-ICT London/NY PM.
4. Close fill-time thesis revalidation and zero-call paths while preserving all winning-trade counts/R; provide full source->cognition->PositionAction->route->executed telemetry.

**Architect 2 (OPS):**
1. Implement source-faithful objective 3-year event lifecycle, *no output trades before DOL and FVG admission are verified*.
2. Reconstruct all 55 baseline NY fills: source signal FVG at signal vs actual fill, prefill matured FVG, DOL, 10-pt projected room, choice of first qualified gap, full source provenance; record missing reasons per trade (not just aggregate).
3. Build original-ICT `VT31_LONDON` 03-04 NY 3Y truthful source ledger; London reference **not** a forced 07-08 London range.
4. Build `VT31_NY` original-ICT 10-11 AM and 14-15 PM as separate sub-windows; preserve one trader identity, independently assess sub-window interactions, no double signals.
5. Trader Lab Fast Runner: CONTROL vs SOURCE_TRUE candidates on same frozen 3Y evidence and realistic next-valid-open M1 execution; full sensory chain. NO arbitrary trade-count enhancement or outcome-hindsight rules.
6. Run frozen gate matrix for NY and London independently: true density >=400 where feasible, PF and positive expectancy, hard continuous observed DD <=6R, Sharpe >=1.50, Sortino >=2, MC positive >=90%, MC p95 DD <=~15R, cost stress, temporal/regime, no leakage, exact replay/runtime parity. Combined model ONLY after both pass.
7. A good original ICT copy may still be unprofitable on a given market. Source fidelity is a **methodology** acceptance check, **not** evidence of economic edge/certification.

## 5. State machine

```
PRIMARY ICT LECTURE SOURCE FREEZE (DONE)
      -> NY/UK DST SOURCE CLOCK (DONE, PASS)
      -> 3Y ORIGINAL ICT RAW FVG CAPACITY (DONE, PASS - NOT TRADES)
      -> SOURCE AUDIT OF 55 NY ENTRIES (DONE, 22 EARLY FVG GAPS OPEN)
      -> FIRST FVG + DOL + FRAMEWORK + FULL COGNITION producer truth (OPEN)
      -> SOURCE-TRUE CAUSAL LONDON + NY AM + NY PM OPERATIVE LEDGERS (OPEN)
      -> FILL / POSITION ACTION / M1 EXECUTION (OPEN)
      -> TRADER LAB FULL 3Y REAL ECONOMICS (OPEN)
      -> INDEPENDENT FULL CORE CERTIFICATION (OPEN)
      -> COMBINED SYSTEM CERTIFICATION (LOCKED)
      -> FRESH HOLDOUT / LIVE (SEALED / PROHIBITED)
```

**No future result, even a green raw-FVG test, is to be called `VT31_CERTIFIED` or `SILVER_BULLET_100_PERCENT_REPRODUCTION` without proving every source and Core gate.**
