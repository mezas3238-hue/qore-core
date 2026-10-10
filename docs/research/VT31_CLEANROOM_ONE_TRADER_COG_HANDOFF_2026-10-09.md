# VT31 ICT Cleanroom — ONE Trader, London + New York — Arquitecto 1 COG

**2026-10-09 · Arquitecto 1 · Research only · No LIVE/MT5 orders · Not certified**

## Owner binding invariant

There is **exactly ONE QORE Trader identity: `VT31`**, instrument NAS100. Two *internal session models* share the same trader identity, market memory and eventual capital/risk state:

| Internal model | Original ICT source windows | Tagged as, NOT a separate trader |
| --- | --- | --- |
| London | **03:00–04:00 America/New_York** | `SessionId.LONDON` |
| New York | **10:00–11:00** and **14:00–15:00 America/New_York** | `SessionId.NY_AM`, `SessionId.NY_PM` |

NY AM / NY PM are subwindows inside ONE New York model. 3 source windows are **not** 3 traders; London+NY are **not** 2 traders. In scientific certification each internal session is evaluated independently, and the final combined system must also pass, but there is no double registration or separate equity book.

The research-only `VT31Trader` in `trader.py` owns precisely **one** `VT31CleanroomCognition` and maps both NY source windows to `NEW_YORK`. It consumes outside-window market M1 to maintain the *same* cognitive history. It enforces full-window startup, consistent M1 order, no duplicate session registration and fails **before** modifying memory for malformed input. `snapshot().registered_trader_count == 1` is an automated contract gate.

## CLEAN START — no old trader influences

COG branch: `agent/vt31-ict-cleanroom-cognition-single-trader-20261009` forked from new cleanroom OPS coordinator at commit `52c035f32cf481550f16fae5154598454a23fb07`. Never derived from legacy COG code, TTrades/R2.2, COMP008/009, previously-calibrated entry/exit gates or legacy economic parameters. Only NEW cleanroom `contracts.py`, `operations.py` from the other architect are imported and reused. The source unit tests inspect AST imports against old trader families.

**COG files added, no shared OPS edits**:
- `src/qore/infrastructure/traders/vt31_ict_cleanroom/cognition.py`
- `src/qore/infrastructure/traders/vt31_ict_cleanroom/trader.py`
- `tests/infrastructure/test_vt31_ict_cleanroom_cognition.py`
- `tests/infrastructure/test_vt31_ict_cleanroom_single_trader.py`
- `.github/workflows/vt31-ict-cleanroom-single-trader-cog-v1.yml`

## New causal COG, independent of old reason()

New cognitive entry facts exclusively from **closed NAS100 M1** with `close <= as_of`:

1. `LiquidityPool` immutable price/date/source provenance. Authentic verified frozen pools currently include: **prior FULL NY cash session** 09:30–16:00 NY only when all **390 contiguous M1** exist; Asia 00:00–03:00 NY only when 180 complete contiguous M1 exist; London early range 03:00–05:00 NY only when 120 complete contiguous M1 exist, available to NY windows. The cash-session level is **NOT** mislabelled as full 24h PDH/PDL. Missing pools are explicit unavailable.
2. M15/H1/H4 UTC-bucket diagnostics only from truly complete **15/60/240** contiguous M1 buckets, refusing stale current context; no last-month/year future aggregation. M15 and H1 required by this conservative research producer, H4 is an additional observation, not a fabricated mandatory gate.
3. `CausalSwingBreak` uses a local swing pivot whose right-hand confirming M1 candle has **already closed before** the subsequent M1 close crossing that level. Closed-M1 body displacement against prior 5 bodies has an explicit `1.25x` **research-only** threshold, not falsely presented as a universal 2023 ICT rule.
4. `VT31CleanroomCognition.assess(session, as_of)` creates the existing shared `CognitiveDecision` DTO only if complete context + a newly confirmed directional MSS + a timestamped future liquidity draw at least 10 projected index points away exist. Otherwise returns `CognitiveAssessment(decision=None, missing=...)` and OPS receives `AWAIT_COGNITION` rather than speculative fills.
5. Per-source provenance: native source family, confirmation time, structure pivot time, displacement research definition, verified HTF bucket labels and version `VT31_ICT_CLEANROOM_COG_V1`. `as_of` strictly equals the **latest M1 close**, not a retrospective exit outcome.

This is a first causal producer framework. It does **not** claim real market profitability, complete original ICT interpretation, fully authoritative DOL hierarchy or full-coverage H4 reasoning.

## Actual tests and first integration

- GitHub Actions cleanroom COG workflow: `vt31-ict-cleanroom-single-trader-cog-v1.yml`.
- **RUN 38013445043 PASS**: static Python compile, ruff, 23 pytest including OPS upstream contract, COG, and 1-trader orchestrator.
- Synthetic market-native proof: previous fully confirmed 390-M1 NY cash extreme, complete 180-M1 Asia range, correctly timestamped M15/H1, subsequent 03:00 London swing pivot, and a **later closed-M1 MSS + directional FVG** are consumed by **the existing OPS state machine** to produce research `RESEARCH_PENDING_CE` without a broker fill. Shared `VT31Trader` identity stays `VT31`.
- Time cutoff and adversarial cases: future observations cannot be queried as an earlier `as_of`; missing/stale HTF fail closed; partial previous cash day never yields false full prior cash pool; market gaps cannot fake a swing break; duplicate bars fail closed; a partial-window or gap-bar rejection does **not** contaminate the shared cognitive memory.
- London and NY AM/PM all pass through the one trader identity; three windows do not create duplicated trader instances. New York source time remains relative to America/New_York and US DST.

## Critical outstanding architectural review to OPS

1. **Review DTO / session grouping:** `contracts.CognitiveDecision(session)` is a source window, never a trader identifier. Our unified trader identifies one `VT31`; request OPS to enforce a single route/registry ID in future PAPER order-lifecycle, CIBO and QDLE interfaces. Do NOT introduce separate London/NY balances.
2. **Source doctrine:** Original ICT 2023 lesson establishes NY source clock, prospective directional DOL, FVG within window. Exact 1.25x displacement, five-body median, 390-M1 NY cash range, compulsory two-sided local-pivot MSS, strict CE midpoint, all-three-candles window and universal 10-point *profit* are not proven universal by the video. They are explicit auditable research hypotheses. OPS should not promote any as doctrine without evidence.
3. **Missing ICT-native sources:** original PDH/PDL dealing-day specification, full prior week, NWOG/NDOG, internal/external HTF liquidity hierarchy, ICT market structure scale, correlated index SMT evidence, real draw-to-liquidity selection, bias confidence and decay. These must be independently defined and verified as-of.
4. **Integration:** OPS has a separate cleanroom `order_lifecycle.py` + 3Y source runner in coordinator commits after our fork. Merge the COG PR into OPS cleanroom only after contract review; do not cherry-pick old COMP strategy source; rerun combined CI.
5. **Scientific gates:** realistic broker bid/ask/commission/tick path, genuine order placement/expiry, no intrabar path oracle; then independent 3Y NY/London sample, actual PF/DD/Sharpe/Sortino/MC. Both sessions and combined model must pass required Core gates. No fabricated trade count, no ability to certify from synthetic unit tests.

**Fresh Holdout sealed. No live authorization or risk/sizing/capital authority.**

**Collaboration wall:** GitHub Issue #727. New cleanroom coordinator draft PR #750 remains separate from this COG submission until reviewed.
