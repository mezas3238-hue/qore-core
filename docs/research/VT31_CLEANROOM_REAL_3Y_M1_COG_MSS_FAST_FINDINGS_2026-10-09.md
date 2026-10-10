# VT31 original ICT cleanroom — ONE Trader 3Y Native COG/MSS/FVG Replay Findings

**Date:** 2026-10-09 · **COG architect:** 1 · **Scope:** full 3Y *consumed development* NAS100 source science.
**Owner invariant:** **ONE QORE trader `VT31`**, two session models (London / New York), three ICT windows (London 03–04, NY AM 10–11, NY PM 14–15, `America/New_York`). NY AM/PM are internal parts of ONE New York session model. `M1` is the actual operating source timeframe, HTF M15/H1/H4 are context only.

## Scientific provenance and immutable evidence

- New cleanroom branch: `agent/vt31-ict-cleanroom-cognition-single-trader-20261009`. New standalone source codes only; old R2.2, TTrades, COMP008/009, R5/R8 and old cognitive replay were not imported.
- Original owner-consumed 3Y NAS100 `VT31_NAS100_OWNER_3Y_BASE_001` from 2023-10-01 UTC (inclusive) to 2026-10-01 UTC (exclusive).
- Exact market evidence GitHub artifact `11459859004`; SHA256 **`0563370fd021ad091392eb26f60cda0d3356d38c801fc1c2083cceafc5043cfa`**; exact artifact digest verified before execution; 1,059,784 M1 in chronological `ijson` stream.
- Initial new COG source 3Y [GitHub Actions #38015895375 SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/38015895375), measured commit `48b5f1a5424eee26105b7fd17f94e5671b1b6724`, artifact `11656261420`.
- **Final M1 MSS -> later M1 FVG 3Y [GitHub Actions #38016018096 SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/38016018096), measured commit `6dc2d06cae4b0cdeb58ff20c405389bb833c9679`, artifact `11655822086`.**
- Companion cleanroom strict tests [#38016018091 SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/38016018091): **28 tests pass**, compile and Ruff all green. Isolated test explicitly proves M1 MSS in one completed M1 and suitable FVG in a later M1, no invented second MSS, plus cancellation when DOL liquidity gets swept or structure pivot is lost.

## Fixed P0 defects identified by the two architects

1. **Liquidity target integrity:** a 120-bar excerpt can no longer be called a completed previous NY cash session or full-day PDH. New source only admits **a fully observed 390-closed-M1 09:30–16:00 NY CASH pool**, fully observed 180-M1 Asia or 120-M1 London reference. The NY CASH pool is explicitly NOT the canonical 24h PDH/PDL source; precise HTF liquidity taxonomy remains open. Friday may be latest completed cash session after Sunday futures-market partial activity.
2. **Already-swept target suppression:** as soon as a subsequent closed M1 wick crosses confirmed liquidity, the previously unswept pool is **consumed, never retroactively resurrected**. Direct historical function and incremental online source agree in provenance/parity synthetic tests.
3. **Fast cognition:** market memory is ONE persistent trader instance. The previous implementation rescanned up to 22,000 bars for M15/H1/H4 and source pools **at every candidate minute**. Now a bounded online index keeps closed HTF buckets, confirmed source ranges and consumed-pool status in per-bar updates; MSS only examines a bounded recent tail. No subsequent M1 can access future market bars, and gap/partial sessions fail closed.
4. **Real M1 continuity:** confirmed bullish/bearish M1 structure shift is stored as a **single source-window thesis** (not another trader) and re-assessed at each subsequent closed M1. `CognitiveDecision.observed_at` refreshes, but `structure_break_confirmed_at`, swing confirmation, native draw family and price remain historically frozen. When DOL is swept, a pivot close reverses, or an opposing M1 MSS emerges, the old thesis cannot simply be recycled. The OPS source machine can now recognize FVG in the later M1 candle.
5. **No execution fabrication:** existing OPS `IctSilverBulletOperations` produces only a first suitable source FVG **RESEARCH candidate**. `SourceLimitOrderAudit` belongs to OPS and separately requires real bid/ask quotes plus external ACK to prove execution; this run never creates fills/orders/risk/performance. The current clock and full-three-candle requirement are declared conservative QORE research formalizations, not unsupported universal ICT claims.

## Actual 3Y source-level evidence

| Original ICT time window (America/New_York) | Complete 60-M1 session dates | Initial native COG source FVG candidates | Updated preserved-MSS source FVG candidates | Difference |
|---|---:|---:|---:|---:|
| London 03–04 | **774** | 693 | **766** | +73 |
| New York AM 10–11 | **771** | 605 | **721** | +116 |
| New York PM 14–15 | **741** | 554 | **653** | +99 |
| **Total windows** | **2,286** | **1,852** | **2,140** | **+288** |

**This is NOT 2,140 trades!** A source FVG candidate exists on 2,140 complete source-hour *opportunities*. Broker fills proven: **0**; paper fills proven: **0**; actual authorized orders: **0**. FVG counts and source-qualified candidates are *not* independent realized trades. There are no 3Y PF, DD, Sharpe, expectancy or drawdown claims. High source candidate coverage (~94% of complete source hours) is a methodology-quality research flag: it does **not** prove valid original ICT entries or profitable execution; review first suitable FVG zone, actual MSS/PDH hierarchy and realistic liquidity draw.

### The new cognitive inputs do exist for all three original windows

| Evidence | London | NY AM | NY PM |
|---|---:|---:|---:|
| Closed-M1 cognitive evaluations | **46,440** | **46,260** | **44,460** |
| As-of valid DOL/MSS decisions observed on M1 (non-independent) | 27,986 | 19,297 | 15,602 |
| First suitable FVG proposals (one maximum per complete hour) | **766** | **721** | **653** |

The DOL/MSS decision counts are observations repeatedly carried inside M1 windows, **not separate trade signals**. The source-only negative-control from OPS had ZERO cognition and therefore ZERO admitted FVGs and ZERO broker fills; it is intentionally not a competing trade-performance replay.

### Full replay performance: real 1,059,784 M1

- Initial indexed native COG 3Y source replay: **42.747 seconds**.
- Updated persistent M1 MSS 3Y source replay: **30.537 seconds**.
- This is speed telemetry observed in distinct GitHub Action runs, **not** a statistically controlled performance benchmark. It demonstrates that complete 3Y native-cognition research runs without the earlier O(history x each source M1) bottleneck. Do not infer economic alpha from speed.

## Code/files changed in architect-owned COG branch

- `src/qore/infrastructure/traders/vt31_ict_cleanroom/cognition.py`: immutable native DOL/pools, consumed-status proof, source/MSS timestamp parity, fast incremental HTF state, **M1 thesis persisted to next M1**, research-only entry decision.
- `src/qore/infrastructure/traders/vt31_ict_cleanroom/trader.py`: exactly ONE VT31; NY AM+PM inside one New York model; singleton cognition, fast session detection and incomplete-M1 market-only scientific observation.
- `scripts/vt31_ict_cleanroom_cog_real_3y_fast_v1.py`: source-hash-checked immutable genuine 3Y M1 streaming to one trader, full/partial hour attribution, no modeled trade economics, no legacy imports.
- `.github/workflows/vt31-ict-cleanroom-cog-real-3y-fast-v1.yml`: checkout, strict source hash, compile, Ruff, 28 cleanroom tests, true historical replay, CI controls and immutable artifact.
- `tests/infrastructure/test_vt31_ict_cleanroom_cognition.py`: direct vs indexed market state parity, no partial previous pool, swept liquidity nonresurrection, future M1 exclusion, gap/stale HTF fail closed, M1 MSS and later-FVG proof.
- `tests/infrastructure/test_vt31_ict_cleanroom_single_trader.py`: one trader and single NY model, source-DST clock and shared memory, no corruption when rejecting mid-window or missing M1.
- `docs/research/VT31_CLEANROOM_ONE_TRADER_COG_HANDOFF_2026-10-09.md`: original coordinator handoff.

**OPS-owned shared `contracts.py`, `operations.py`, `order_lifecycle.py`, `m1_execution.py`, registry and 3Y OPS source control were not modified by COG.**

## Open P0 matters: do NOT promote

1. Architect 2 to review [draft COG PR #751](https://github.com/mezas3238-hue/qore-core/pull/751), merge cleanroom changes with its independent M1 formal contract, order lifecycle and 3Y source control; verify combined global CI. COG did not independently certify new OPS-side changes after its own branch fork.
2. Verify ICT-native authoritative DOL beyond research prior NY cash/Asia/London pools (genuine PDH/PDL/week, relevant unmitigated FVG/HTF targets, market dealing ranges), full inter-market structure, source FVG geometry and MSS displacement assumptions; avoid overpermissive 94% of windows. HTF buckets may compare nonconsecutive market days after long closures; should be separated from direct entry triggers as context and audited.
3. Actual bid/ask/tick quotes and broker ACKs; no OHLC wick assumed a fill. Margin/sizing from QDLE and economic management by CIBO only **after** sufficient confidence and explicit separate authorization. One VT31 exposure book across both session models.
4. Run truly changed-execution 3Y development replay with trade IDs, entry/exit, commission, objective PF, Drawdown, Sharpe/Sortino/MonteCarlo, robust density; independently analyze London vs NY (AM+PM) and then unified combined exposure. Gates remain unpassed until demonstrated.
5. Fresh Holdout SEALED; no live/VPS/funded authority; no reuse of old 55-trade R2.2 as reconstructed performance, only historical audit evidence.

**Truthful state:** causal cognition and source opportunities demonstrated on complete 3Y M1. Actual profitable/economic VT31 trading and Core certification remain **NOT PROVEN**.


## Additional cross-architect blocking integration finding: COG revocation after FVG

A distinct **P0 gap** was verified directly in the independently OPS-owned `operations.py`: if an FVG has been selected and, on a later completed M1, the `CognitiveAssessment.decision` becomes `None` because its DOL was swept, structure thesis revoked or mandatory context unavailable, the existing OPS source processor currently invalidates the pending research source only when it receives a *non-None alternative* cognitive decision with changed side/target. There is no guaranteed fail-closed transition merely because cognition goes missing. Some `RESEARCH_PENDING_CE` states can therefore survive the loss of their originally validated cognitive thesis until separate FVG-zone invalidation or hour expiry. This does NOT certify the present source-lifecycle behavior.

COG formally reported the ownership-safe fix and adversarial test to OPS via [Issue #727 (comment 6092603037)](https://github.com/mezas3238-hue/qore-core/issues/727#issuecomment-6092603037). OPS must own `operations.py` and the paper order-cancel/ACK reconciliation, enforcing explicit `SOURCE_INVALIDATED` when previously admitted cognition becomes unavailable; no hidden broker fill. Only after this safety-path test passes should source-pending terminal distributions be treated as operative evidence.
