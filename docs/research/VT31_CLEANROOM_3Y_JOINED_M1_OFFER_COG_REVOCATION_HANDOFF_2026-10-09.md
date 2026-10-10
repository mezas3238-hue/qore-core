# VT31 Silver Bullet ORIGINAL — cleanroom joined M1 / COG / OPS / 3Y scientific handoff

**2026-10-09 · Owner-approved full VT31 reset · Architect 2 OPS and Architect 1 COG · P0 SCIENCE / NO LIVE.**  
Repository `mezas3238-hue/qore-core`. Coordinator branch `agent/vt31-ict-cleanroom-rebuild-20261009`, draft [PR #750](https://github.com/mezas3238-hue/qore-core/pull/750). Cognition PR [#751](https://github.com/mezas3238-hue/qore-core/pull/751) was integrated into isolated coordinator using reviewed two-parent source commits `02ad7f3d1f7b065d9ee224032a404f4e85da04b0` and latest sensors merge `26adc8a446b38d4e5bf7f03243bee6a6c724e83b`. **Neither commit modifies `main` or the VPS.** Historical R2.2 / COMP codes were removed as trading authority on the cleanroom branch; frozen development market data remains usable as source evidence.

## Binding single-trader original Silver Bullet chart
- Trader registry identity **ONE `VT31` for NAS100**, ONE cognitive memory, no separate London/NY equities.
- Internal session models **London and New York**; NY has two windows AM/PM. NY-local source windows `03:00-04:00`, `10:00-11:00`, `14:00-15:00`, US DST correct.
- **M1 IS PRIMARY operational chart** for pivots/MSS, displacement, first suitable 3 closed M1 FVG, formation clock and entry eligibility. Higher M15/H1/H4 are HTF contextual liquidity / bias, NEVER M1 entry triggers. Bid/ask quotes and true trade events need their own timestamps and bid-ask side (ASK for LONG limit; BID for SHORT).
- Actual ICT video https://www.youtube.com/watch?v=tRq1hyGGtl4 remains doctrine. Strict all-three-candles-inside-hour / sole CE entry / displacement threshold 1.25x body median / mandatory local MSS all remain explicit QORE research **operational formalizations**, not necessarily universal primary-video rules.
- True historical sources: frozen `VT31_NAS100_OWNER_3Y_BASE_001`, SHA256 `0563370fd021ad091392eb26f60cda0d3356d38c801fc1c2083cceafc5043cfa`, GitHub artifact `11459859004`, Oct 2023 to Sep 2026, **1,059,784 M1**.
- Full source coverage: London **774** windows, NY AM **771**, NY PM **741**; exactly **2,286** complete source hours; 2 NY AM and 4 NY PM days missing full 60-M1 coverage kept separate.

## Source and offer discoveries — NOT broker trades

**Joint source-only as-of replay:** [GitHub Actions 38018158261 SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/38018158261), source artifact `11657475856`. Source candidate totals **766 London**, **721 NY AM**, **653 NY PM** = **2,140** independent complete-hour first suitable M1 FVG proposals. This is nearly every complete original ICT hour and itself warrants future doctrine/zone-permissiveness scientific review; high *source capacity* is not trading alpha. Fresh holdout SEALED.

**Audited source-order FVG ledger with quote lifecycle:** [38018330376 SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/38018330376), artifact `11657660972`; read-only `SourceLimitOrderAudit`, explicitly no broker order routing:
- **2,140** M1 source-hypothesis offers; **2,084** finally source-invalidation; **46** ambiguous OHLC same-minute paths; **10** source-hour expiry.
- First revocation reason forensic: 928 absent current COG proof; 337 current DOL changed; **819 invalidated solely because a later same-direction M1 MSS happened after a valid chosen FVG**. The last rule was an ungrounded architecture restriction, not a universal original ICT cancellation.
- M1 touch counting originally included touches AFTER cancellation; this was a forensic censoring bug, not a real fill. Corrected audit never counts prices after source termination as live eligibility.

**Second trial removes automatic revocation for another same-direction M1 MSS**, while keeping causal COG revocation, changed DOL and missing current-M1 source fail-closed:
- CI [38018602495 SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/38018602495), artifact `11657461650`.
- Reconstructed **2,140** source candidates unchanged (zero hindsight candidate selection).
- Final origin status: **2,076 SOURCE_INVALIDATED**, **46 AMBIGUOUS_PRICE_PATH**, **17 WINDOW_EXPIRED**, **1 RESEARCH_TOUCH_NOT_FILL** terminal at end hour. These are labels for a **research offer**. No broker order placed.
- Source invalidation reasons: **1,587 COG decision revoked / unavailable** (could be DOL swept/pivot lost/missing context), **489 DOL/target/side changed**. No automatic invalidation for supportive later MSS.
- **301** raw M1 CE overlaps while source was still eligible are observable market-price evidence **NOT bid/ask fills**.
- **737** CE overlap observations on the exact M1 candle in which the source was revoked are intra-minute-path **UNRESOLVED** (tick order not available); never counted as fills.
- Price touches AFTER source invalidation excluded. Since quote/tick timeline is absent, no proof of actual broker fill, no complete P&L or stop/target economics, no PF/DD/Sharpe/Sortino.
- Full source M1 records have exactly fields `open,high,low,close,opened_at,closed_at,period`; **NO historical timestamped bid/ask tick stream or MT5 order receipts** in this frozen artifact.
- VPS `vps-vrix` checked via authorized Desktop Commander, currently **OFFLINE**; cannot inspect/export its MT5 quote/tick/commission history in this turn. Do not copy old lots or invent spreads. A broker-specific point-value/symbol specification is also necessary for real NAS100 lotage/risk.

## Independent cognitive component I/O instrumentation

Architect 1 implemented a completely new opt-in **passive sensor** `cognitive_telemetry.py` (all M1 inputs, closed M15/H1/H4 context, prior NY cash/Asian/London unswept pools, M1 MSS/displacement, revalidated M1 thesis, DOL selected, final cognitive abstain/approval, OPS FVG and candidate, bidask/ACK/QDLE not connected). 3Y source-only COG run [38018396602 GREEN](https://github.com/mezas3238-hue/qore-core/actions/runs/38018396602) showed **937 distinct source FVG proposals** exposed to a later `COG=None` while OPS erroneously still remained `RESEARCH_PENDING_CE` (7,648 repeated M1 pending observations, not trades). OPS verified and repaired this exact P0 in `operations.py`, requiring as-of fresh M1 `CognitiveDecision` on every closed bar, rejecting stale decision, fail-closed when missing/changed. No real fills. **FINAL VERIFIED P0 RESULT:** joined real 3Y M1 passive sensor [GitHub Actions 38018856150 — SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/38018856150), source artifact **`11657187430`**:
- Actual **1,059,784** M1 market feed sensor calls.
- Actual **137,160** distinct closed-M1 cognitive assessments and **137,160** M1 OPS FVG source calls across 2,286 fully covered source hours.
- **2,140** source-only first suitable FVG proposals still selected (766 London, 721 NY AM, 653 NY PM): same as pre-repair, so no deliberate deletion of historically losing/winning candidates.
- Critically, **`p0_pending_without_cog_unique_candidate_sources = {}`** and **`p0_pending_without_cog_m1_observations = 0`**, down from the prior **937 distinct sources / 7,648 repeated pending M1 observations**. This closes the narrowly scoped prefill **P0 pending-source-lives-after-cognition-revoked** integrity bug scientifically on the frozen 3Y M1 source. No broker fill, risk budget or P&L is inferred.
- Bid/ask fill sensor **0 connected calls**; broker execution ACK sensor **0 connected calls**, honestly reflected as NOT_CONNECTED, not ignored.

Architect 2 patched COG-owned type *annotations only* after two-parent integration to satisfy QORE strict global mypy; updated a COG passive telemetry test on OPS branch that previously asserted old OPS bug was present. The new test instead requires `SOURCE_INVALIDATED` and **zero** `P0_PENDING_WITHOUT_COG` when cognition disappears, while retaining independent instrumentation. Peer-review requested in Issue #727.

## Source audit code and exact tests

- `src/qore/infrastructure/traders/vt31_ict_cleanroom/{contracts,m1_execution,operations,cognition,trader,cognitive_telemetry,order_lifecycle}.py` all brand new source namespaces, **no old VT31 imports**.
- `scripts/vt31_ict_cleanroom_joint_m1_offer_audit_fast_v1.py`: full source M1 to fresh COG+OPS, per-candidate identities, causal source removal, conservative M1 raw OHLC CE touch while eligible, explicit same-candle path ambiguity. Outputs `events[]` ledger, source invalidation reason breakdown, no actual fills.
- Workflows `.github/workflows/vt31-ict-cleanroom-{joined-3y-fast-v1,joint-m1-offer-funnel-fast-v1}.yml` (actual full 3Y on every causally relevant change); `vt31-ict-cleanroom-m1-primary-v1.yml` and independent order-lifecycle tests.
- Global QORE CI has massive unrelated full pytest suite and may run beyond source-fast checks; do not claim green until latest SHA is verified on `QORE CI`.

## P0 next verified execution pathway

1. Validate merged passive sensor after OPS revocation; fail if *any* pending source remains with `COG=None` across 1,059,784 bars. Surface missing-cognition reasons and revisit overpermissive 94% source-hour coverage through **primary original ICT source fidelity** and a prospective scientific study, not posthoc loss pruning.
2. Produce/get **historical time-indexed MT5 NAS100 bid/ask tick data** (or verified independent quote store) and actual fee / point / lot / swap/margin symbol specification from a connected funded account or authorized source. No genuine fills from M1 mid-price. Use one-trader bid/ask offer-and-ACK lifecycle and physical volume/commission/fee accounting. Capture uncertain same-M1 limit/stop ordering honestly.
3. After quote source exists, run independent bid/ask + commission/slippage+SL/TP+QDLE-compatible **PAPER economic replay** with true one-trader cross-London/NY capital and shared exposure, count actual executed offers; PF, max chronological DD, expectation, Sharpe, Sortino, Monte Carlo and Core gate density cannot otherwise be calculated.
4. Validate individual London vs NY (NY AM/PM internal segments) and combined; 6R DD gate etc. Owner 2023 ICT primary source should supersede unsupported DeepSeek assertions. Fresh holdout SEALED. **NO LIVE / VPS execution authority**.

**Status: cleaned one-trader M1 source/COG integration verified, source offer audit on frozen 3Y verified; real trade execution and certification BLOCKED ON ACTUAL HISTORICAL QUOTES.** No old 55 trades treated as new historical performance.
