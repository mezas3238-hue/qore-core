# VT31 — Original ICT Silver Bullet: genuine causal FVG/DOL capacities and frozen 55/23 alignment

**Date:** 2026-10-09. **OPS Architect 2.** Branch `agent/vt31-architect-operations-cert-20261009`.  
**Owner instruction:** reproduce original ICT 2023 Silver Bullet as faithfully as demonstrable, without confusing raw FVG observations with true trades.  
**Primary source:** [ICT Silver Bullet Time Based Trading Model](https://www.youtube.com/watch?v=tRq1hyGGtl4). All source hours are **America/New_York**: London 03–04, NY AM 10–11, NY PM 14–15.  
**Frozen source:** `VT31_NAS100_OWNER_3Y_BASE_001`, NAS100 2023-10-01 inclusive → 2026-10-01 exclusive, **1,059,784 historical M1 candles**, immutable evidence artifact `11459859004`.  
**Immutable NY CONTROL:** 55 admitted actual historical trade rows from artifact `11459439466`, baseline commit `8f91ee489d33c1fa0b90972270d4ac6c32fcca32`.

## Experiments actually implemented / executed

1. **P0 causal PDH/PDL source-capacity runner:** [Run 37995626771, SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/37995626771), full 3Y actual M1, never outcome-aware at selection. Script `scripts/vt31_ict_silver_bullet_3y_pdh_pdl_causal_capacity_v1.py`. Uses previous NY-local trading day high/low obtained only *after completion of that day* (minimum 720 real M1 records, previous complete NY-local date no more than 4 calendar days earlier). Tests classic contiguous 3-closed-M1 wick-to-wick FVG, formation within exact source hour, target on correct side and **>=10 NAS100 projected index points** to previous-day high/low from the observed M1 close. Retains **first qualifying FVG** without peeking at later terminal outcome. Measures only later *midpoint price touches* as ex-post research, explicitly NOT actual broker fills.
2. **Directional causal correction:** [Run 37996161754, SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/37996161754), measured commit `354e824150d77ceae34196849f44d3111c7b1451`, artifact `11646409408`. The source now preserves the **first qualifying FVG independently per LONG and SHORT**. Both PDH (long) and PDL (short) hypotheses are observable, but the **authoritative directional choice needs a separate cognitive DOL producer**; no hindsight picks which side the trader would take. Synthetic two-sided and causality cases pass. Original global-first counts retained for audit compatibility, not execution authority.
3. **Frozen 55 NY trade / 23-loss join:** [Run 37996041411, SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/37996041411), using original 55-trade replay `11459439466`, strict pre-signal raw-FVG audit `11646815205` and directional DOL research artifact. Script `scripts/vt31_ict_silver_bullet_3y_frozen_alignment_v1.py`, no signal/metric alteration, strict timestamp/side identity and exact original DD arithmetic. A further latest-artifact pin/re-run was started after the strengthened two-direction unit fixture; verify its run before promoting report version.
4. **Architect 1 COG existing fill shadow is a DIFFERENT study**, [run 37994052776](https://github.com/mezas3238-hue/qore-core/actions/runs/37994052776). It revalidated 95 prospective fill opportunities against fresh canonical cognition at M1-open T and mapped 55 original admitted trades, **without changing actual execution**. Do not conflate its naive conditional deletion with an economic replay.

## Raw opportunity capacity, three independent source hours

| Source window in NY local time | Complete 60-M1 days | Days with first globally qualifying PDH/PDL FVG | Days with later in-hour MIDPOINT price touch (NOT fills) |
|---|---:|---:|---:|
| ICT London 03:00–04:00 | 774 | 773 | 656 |
| ICT NY AM 10:00–11:00 | 771 | 767 | 649 |
| ICT NY PM 14:00–15:00 | 741 | 740 | 643 |

The additional **first eligible FVG per side** observations are saved with full `ny_date / side / formation_utc / as-of DOL/ projected NAS100 points / prior NY date / later research touch` in the downloadable workflow artifact. These counts are **not executed or COG-admitted trades**, cannot be combined into 2,000+ trades, and cannot establish density, real win rate, Profit Factor or drawdown. The high raw rates demonstrate **over-abundant early technical patterns**, not the certified edge of original ICT.

**Hard limitations:** PDH/PDL is *one possible ICT liquidity family*, never a requirement for all authentic Silver Bullets. The 720-M1 day sufficiency heuristic is research coverage, not proof of the broker's full trading-day session. The experiment has not authenticated MSS/displacement, the next canonical cognitive DOL, stop swing structure, actual tick/BID-ASK fill, simultaneous stop/target resolution, spreads, commissions or market impact. No current source hypothesis can be directly sent as an order.

## Factual source-fidelity alignment against the frozen 55 NY controls

The join compares exact historical **signal-at** evidence, *not fill-at or terminal-label evidence*. The test uses first qualifying FVG **of the trade's side**, even though trading-side cognitive authority is not yet established. ALL correlations below are retrospective diagnostics, not an actionable filter.

| Research classification at signal time | All 55: trades / winners / nonwinners | Historic net 0.05R-friction stressed R | Of the worst 23-loss run: count / loss mass |
|---|---:|---:|---:|
| Same-side first PDH/PDL 10-point FVG already closed by signal (**UNLINKED**) | 30 / 4 / 26 | **-2.7065905494R** | 14 losses / **-12.6261271365R** |
| First qualified same-side FVG formed **after the signal** | 18 / 4 / 14 | **+16.7266582626R** | 8 losses / **-7.6824685818R** |
| No same-side PDH/PDL FVG hypothesis found in that source hour | 7 / 3 / 4 | **+11.4755835002R** | 1 loss / **-1.05R** |
| TOTAL unchanged | **55 / 11 / 44** | **+25.4956512133R** | **23 losses / -21.3585957183R** |

**Key scientific finding:** A naive rule to accept only the first already-confirmed same-side PDH/PDL-FVG hypothesis **at initial signal time** would retain just **4 of the frozen 11 winners**, excluding 7 winners, and would also exclude +28.20R of aggregate R from the other research groups. It **fails Core winner-preservation and ceiling aims**, even before considering actual rerouting, new fills, other legitimate ICT DOL families, or false eligibility from not verifying canonical cognitive intent. It is explicitly **REJECTED as a runtime rule**.

The earlier raw-FVG-only as-of-signal audit also found **22/55** (all Breaker) without an already closed same-direction FVG at signal time, and **33/55** with raw directional context but unlinked source. The stricter PDH/PDL first-candidate dataset asks a different question; do not mix these counts or treat a hypothesis as the trader's true selected liquidity draw.

## Cognition and execution integration truth

Architect 1's contemporaneous independent NY fill-time study confirms:
- 95 retrospective prospective M1-open fill opportunities; basic canonical cognition would `EXECUTE` on 62 and `WAIT/ABSTAIN` on 33.
- On original admitted 55, 35 would be kept and 20 would be rejected, including **2 historical winners**.
- The study's **12.4218745037R** drawdown from deleting realized rejected outcomes is explicitly a *mathematical diagnostic*, NOT changed-order replay, and still violates **DD <=6R**. Naive deletion reduces historical 55 control net R from +25.49565R to +22.74948R and leaves density far below >=400.

**Required actual integration sequence (NO fake success):**
1. **COG** deliver causal, session-aware authoritative `next_draw_on_liquidity` with producer / timestamp / target / source and independent direction, plus verified first FVG in the **chosen** suitable zone at signal and prospective fill, full canonical `reason()`, source-vs-TTrades distinction; NY original 09–10 mandatory raid is NOT universal original ICT source doctrine.
2. **OPS** use immutable 3Y NAS100 M1 to reconstruct a complete **source-qualified offer/order lifecycle** for London 03–04 NY, NY AM 10–11 NY, NY PM 14–15 NY; stop/target and intrabar BID-ASK/tick ambiguity *fail closed*. No source truth without DOL/MSS / structure.
3. **OPS + COG** join latest fill revalidation shadow to actual candidate order lifecycle; compare unchanged source control vs **real changed economic replay** with order cancellation and potential later fills. No disjoint historical deletion as substitute.
4. Run independent London and NY Core gates: continuous observed <=6R DD, >=400 genuinely filled 3Y operations per required model, PF/expectancy, Sharpe>=1.5, Sortino>=2, MC positive >=90%, MC p95 DD <=15R, 0.10R friction stress, winner preservation, regime/era, full source->cognition->actuation route parity; only then combine and consider untouched Fresh Holdout.

## Governance and classification

**Methodology source fidelity:** PARTIAL (clock and raw causal FVG proven; next DOL, structure, source-linked FVG and execution unproven).  
**NY economic control:** unchanged **FAIL** (55 genuine fills, DD 21.3585957R, ~0.562 Sharpe).  
**London economically executable trader:** NOT YET built/certified.  
**Dual-session certification:** LOCKED.  
**Fresh Holdout:** SEALED.  
**LIVE/FUNDED:** NOT AUTHORIZED.  
**Result:** source-capacity and retrospective loss attribution advances — *not a new profitable candidate*.
