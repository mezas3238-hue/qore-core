# QORE-TRADER-CATALOG-31-CAPABILITY-INVENTORY-001

Status: **RECOVERED AUDIT — Harness Batch 003 evidence adjudicated; no trader source implementation in this change.**

Package: `HARNESS-ENGINEER-QORE-TRADER-CATALOG-31-INVENTORY-001-BATCH-003`  
Parent: #469 · Primary: #477 · Related: #470, #473, #471, #472, #475

## 1. Exact binding and recovery provenance

- Repository: `mezas3238-hue/qore-core`
- START: `5a158ef0fb2e21db95f2be0685373780bf1ab197`
- START TREE: `5e2b37b23b01fe23fd373d39b01573e9607a73ad`
- Harness run: `33676959961`
- Artifact: `9865600957`
- Harness generation exit: `0`
- Workflow terminal failure: checkpoint-publication parser rejected an otherwise immutable binding line carrying the non-semantic suffix `VERIFIED_EXACT`.
- Recovery adjudication: all six unpublished agent lanes reached `COMPLETED`; no lane may be rerun merely because canonical publication failed.

The recovered Harness candidate was docs-only. Its agent-side quality gate recorded `ruff check .` PASS, `mypy src tests` PASS, and `pytest --cov=src/qore --cov-report=term-missing` with `4862 passed` and 87% aggregate coverage. Those results are historical evidence for the recovered START workspace; the materialized branch still requires its own exact-head CI before integration.

## 2. Executive finding

At this START, QORE has a generic Virtual Trader foundation, generic research/freeze/replay infrastructure, executive trader read models, fail-closed execution/risk seams, a DST-aware market clock, and cTrader DEMO M5 closed-OHLC ingress. It does **not** yet contain concrete methodology evaluators/producers for the 31 named traders.

VT-30 Trader Midpoints is a special case: its methodology-specific evaluator is still absent, but its supporting integration infrastructure is already installed in Core and MUST be reused. In particular, QORE retains native-BID/M5 market-evidence semantics, deterministic market-event replay, and DST-aware market-clock infrastructure explicitly created for the Midpoints path. Therefore:

`MIDPOINTS SUPPORTING INFRA PRESENT != MIDPOINTS EVALUATOR COMPLETE`

and

`SUPPORTING INFRA != TRADER LAB PASS != DEMO_ELIGIBLE`.

The existing governed Trader Midpoints ficha must be bound to the missing evaluator delta; engineering must not reinvent it from repository-local hints.

## 3. Shared capability baseline

Shared capabilities present or partially present:

- generic Virtual Trader projection contracts;
- immutable research strategy/config fingerprinting and run binding;
- deterministic replay ordering and historical dataset qualification;
- OOS / frozen-OOS / resampling and calibration scaffolds;
- order-intent side semantics, pre-trade safety, execution boundary, position lifecycle and realized PnL seams;
- DST-aware `America/New_York` wall-clock primitives;
- cTrader DEMO native M5 closed-OHLC capture.

Shared gaps before trader admission:

- no concrete 31-trader methodology evaluators;
- no complete Trader Lab lifecycle implementation for these traders;
- no fast-forward gate;
- no complete stress/adversarial gate;
- no trader opportunity-density counter;
- no complete numeric transaction-cost/slippage/spread model;
- no concrete CIBO Trader Manager selection state machine;
- no concrete indicator/liquidity library covering ATR/EMA/RSI/Bollinger/ADX/FVG/OB/MSS/BOS/sweeps/PDH-PDL;
- non-M5 data paths remain incomplete for many methodologies;
- synthetic VT-20..VT-28 require actual provider capability and canonical instrument identity.

## 4. Mandatory Trader Lab law

All 31 traders MUST enter Trader Lab individually before DEMO admission.

Canonical gate:

`METHODOLOGY -> VERSIONED IMPLEMENTATION -> REPLAY -> FAST_FORWARD -> OOS -> STRESS/ADVERSARIAL -> MONTE_CARLO -> RISK_REVIEWED -> CIBO_REVIEWED -> DEMO_ELIGIBLE`

No substitute is permitted:

- Harness completion is not Lab certification.
- Expert/Coder/Claude review is not Lab certification.
- Existing infrastructure is not Lab certification.
- CIBO preference is not Lab certification.
- Code merged to `main` is not Lab certification.

`NO DEMO_ELIGIBLE -> NO DEMO ADMISSION`.

The first DEMO target is five traders. If fewer than five qualify, QORE uses the smaller qualified set; the qualification standard is never lowered merely to fill five seats.

## 5. 31-trader capability inventory

Legend: `NONE` = no concrete methodology implementation at this START. `INFRA` = reusable supporting infrastructure exists but concrete evaluator is absent. `PROVIDER` = provider/instrument capability must be established first. `TF` = required timeframe/data path not yet fully wired. Every row remains `DEMO_ELIGIBLE=NO` until Trader Lab completes.

| ID | Trader | Code state | Primary readiness gap | First-DEMO disposition |
|---|---|---|---|---|
| VT-01 | NY Precision Core | NONE | ICT liquidity primitives, NY/session semantics, M3/H1 context | **FIRST COHORT** |
| VT-02 | Scherman — Divergencia S&P/VIX | NONE | VIX feed/semantics + divergence formalization | BLOCKED |
| VT-03 | Scherman — Trend Following | NONE | EMA/structure formalization + H1/H4/D1 | DEFER horizon |
| VT-04 | Scherman — Mean Reversion | NONE | indicators/S-R/rejection + H1/H4 | DEFER horizon |
| VT-05 | Scherman — Breakout | NONE | range/ATR/volume semantics + H1/H4 | DEFER horizon |
| VT-06 | Scherman — Cross-Asset Momentum | NONE | basket/correlation/ranking + multi-asset data | BLOCKED |
| VT-07 | Scherman — Anomalías de Mercado | NONE | calendar/FOMC/NFP data + pre-registration | BLOCKED |
| VT-08 | CRT 4H AMD | NONE | AMD/BOS/FVG/OB formalization + H4 aggregation | **FIRST COHORT** |
| VT-09 | Turtle Soup | NONE | false-break/session semantics + M15/H1 path | **FIRST COHORT** |
| VT-10 | Wyckoff | NONE | deterministic phase/Spring/SOS-SOW + volume | BLOCKED |
| VT-11 | Ondas Elliott | NONE | deterministic wave count + H4/D1/H1 | BLOCKED |
| VT-12 | VSA | NONE | tick-volume provenance + SOS/SOW/ND/NS | BLOCKED |
| VT-13 | Statistical Arbitrage | NONE | cointegration/z-score window + multi-leg lifecycle | BLOCKED |
| VT-14 | Swing Trend Following (Forex) | NONE | D1/H4 trend/pullback evaluator | DEFER horizon |
| VT-15 | Swing Trend Following (Índices) | NONE | D1/H4 + RTH calendar semantics | DEFER horizon |
| VT-16 | Swing Mean Reversion | NONE | H4/H1 deviation/rejection evaluator | DEFER horizon |
| VT-17 | QT Scalper | NONE | exact deterministic 90-minute cycle semantics | **FIRST COHORT** |
| VT-18 | QT Swing | NONE | daily-cycle + H1 evaluator | DEFER horizon |
| VT-19 | QT Position | NONE | weekly-cycle + H4 evaluator | DEFER horizon |
| VT-20 | Phantom-50 | NONE | PROVIDER synthetic identity/feed + M1 | BLOCKED PROVIDER |
| VT-21 | Specter-75 | NONE | PROVIDER synthetic + tick volume | BLOCKED PROVIDER |
| VT-22 | Vortex-100 | NONE | PROVIDER synthetic identity/feed | BLOCKED PROVIDER |
| VT-23 | Apex-300 | NONE | PROVIDER synthetic + volume | BLOCKED PROVIDER |
| VT-24 | Nova-600 | NONE | PROVIDER synthetic identity/feed | BLOCKED PROVIDER |
| VT-25 | Titan-1000B | NONE | PROVIDER synthetic + Wyckoff/volume | BLOCKED PROVIDER |
| VT-26 | Echo-300 | NONE | PROVIDER synthetic + Elliott count | BLOCKED PROVIDER |
| VT-27 | Pulse-600 | NONE | PROVIDER synthetic identity/feed | BLOCKED PROVIDER |
| VT-28 | Titan-1000C | NONE | PROVIDER synthetic identity/feed | BLOCKED PROVIDER |
| VT-29 | ICT | NONE | ICT primitives + Asia-Midpoint/daily-bias/H1 semantics | ALTERNATE |
| VT-30 | Trader Midpoints | **INFRA** | bind existing governed ficha to concrete evaluator/config/lifecycle; reuse market evidence/replay/clock | LAB REQUIRED; not first cohort |
| VT-31 | Silver Bullet | NONE | sweep/FVG/OB + exact NY-window membership | **FIRST COHORT** |

## 6. VT-30 correction to raw Harness interpretation

The raw unpublished Harness report labelled VT-30 `DOCS_ONLY`. That wording is rejected by integration adjudication because it collapses two different facts.

What GitHub supports:

- the concrete Trader Midpoints evaluator remains unimplemented;
- `src/qore/infrastructure/market_observation.py` contains native-BID/native-origin provenance semantics used by the Midpoints evidence path;
- `src/qore/infrastructure/market_event_replay.py` provides deterministic retained-event replay;
- `src/qore/infrastructure/market_clock_schedule.py` provides DST-aware wall-clock semantics;
- architecture records explicitly connect those foundations to future concrete Trader Midpoints evaluation.

Therefore the canonical state is:

`VT-30 = SUPPORTING_INFRA_PRESENT / CONCRETE_EVALUATOR_ABSENT / TRADER_LAB_NOT_YET_PASSED`.

Its detailed governed ficha is not to be reconstructed from repo-local documentation; it must be reused from the project methodology record.

## 7. First DEMO cohort target: five traders

Subject to individual Trader Lab PASS, the target cohort is:

1. **VT-01 NY Precision Core** — M5, bounded NY-session feedback, foundational liquidity family.
2. **VT-08 CRT 4H AMD** — M5 execution with H4 structural context; distinct AMD family.
3. **VT-09 Turtle Soup** — false-break reversal; M15 path must be implemented/qualified.
4. **VT-17 QT Scalper** — M5, high feedback density; exact 90-minute cycle semantics must be formalized before Lab.
5. **VT-31 Silver Bullet** — M5/M1, fixed NY windows, strong reuse of existing DST-aware clock.

Alternate: **VT-29 ICT**, primarily because of methodological overlap with VT-01 and additional Asia-Midpoint/daily-bias formalization.

Selection is for evidence velocity and methodological diversity, **not a claim of profitability**. Each candidate remains `DEMO_ELIGIBLE=NO` until its own Lab record closes.

## 8. Methodology normalization rules

Every ficha field must be classified before code as one or more of:

- `DETERMINISTIC_NOW`
- `REQUIRES_FORMALIZATION`
- `REQUIRES_EXTERNAL_DATA`
- `REQUIRES_PROVIDER_CAPABILITY`
- `REQUIRES_RESEARCH_VALIDATION`
- `INSUFFICIENT_EVIDENCE`

No qualitative phrase may silently become code. Examples requiring deterministic definitions include MSS/BOS/swing structure, Order Block selection, rejection candle, institutional impulse, Wyckoff phase quality, Elliott count quality, stable correlation, macro context, sentiment, Dead Day v2, session boundaries, tick-volume equivalence, and calendar/news exclusions.

Confidence weights in the fichas are methodology scores; they MUST NOT be laundered into calibrated probabilities unless separately validated.

## 9. Next implementation delta

The next engineering package should implement shared reusable primitives before duplicating them across five traders:

- versioned trader identity/config/state and explicit action/side semantics;
- deterministic OHLC liquidity primitives: swing pivots, FVG, sweeps, PDH/PDL and session extrema;
- methodology-neutral timeframe aggregation needed by the cohort;
- exact session/window membership using existing DST-aware Market Clock;
- opportunity-density measurement for the fast-DEMO gate;
- Trader Lab lifecycle/evidence binding with immutable methodology/config fingerprints;
- concrete evaluators for `VT-01`, `VT-08`, `VT-09`, `VT-17`, `VT-31` only after their ambiguous fields are formalized;
- CIBO Trader Manager remains advisory and cannot bypass Risk or Trader Lab.

The other 26 traders are not abandoned: the inventory is 31/31 and all are mandatory Trader Lab entrants as their implementation/data dependencies become satisfiable.

## 10. Safety and readiness invariants

`CATALOG ENTRY != IMPLEMENTED TRADER`  
`IMPLEMENTED TRADER != TRADER LAB PASS`  
`TRADER LAB PASS != PROFITABILITY`  
`DEMO_ELIGIBLE != DEMO_PROFITABLE`  
`CIBO MANAGEMENT != EXECUTION AUTHORITY`  
`CIBO MANAGEMENT != RISK BYPASS`  
`DEMO EVIDENCE != PRODUCTION AUTHORIZATION`  
`NO PRODUCTION ACCOUNTS / NO REAL CAPITAL / NO REAL-MONEY AUTONOMOUS EXECUTION`.

## 11. Recovery verdict

**INVENTORY RECOVERED / 31×N AUDIT MATERIALIZED / FIVE-TRADER TARGET DEFINED / 31×31 LAB ROUTING MANDATORY.**

Batch 003 lanes are permanently carry-forward evidence and MUST NOT be rerun. This document is an integration-authority recovery/adjudication of the unpublished Harness artifact; any subsequent candidate change must follow the normal exact-head QORE CI, freeze and reviewer gates.