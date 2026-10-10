# QORE Core — VT31 ICT Cleanroom Cognitive Component INPUT/OUTPUT/Call/Impact Audit

**2026-10-09 · Architect 1 COG · P0 · Source-only PAPER RESEARCH — NOT CERTIFIED**

## Owner requirement answered

The owner asked to observe **every** active VT31 cognitive component to establish (a) source **input**, (b) real **runtime call**, (c) **output**, (d) decision or causal abstention, and (e) actual **influence in an M1 entry candidate**.

Implemented an **opt-in, bounded, passive runtime I/O audit** in the clean-room **single** VT31 trader, without importing legacy modules:
- `src/qore/infrastructure/traders/vt31_ict_cleanroom/cognitive_telemetry.py`
- Hooks into actual `VT31CleanroomCognition.observe_closed_m1` (native market input, HTF closures and source pool confirmation/sweep), actual `VT31CleanroomCognition.assess` (M15/H1/H4, available DOL, M1 MSS+displacement, persisted thesis, target arbitration, decisions/abstentions), and actual `VT31Trader.on_closed_m1` -> independently OPS-owned `IctSilverBulletOperations.on_closed_m1` (M1 FVG and source candidate).
- NEW tests `tests/infrastructure/test_vt31_ict_cleanroom_cognitive_telemetry.py`; COG source CI and full 3Y Fast Runner verify calls, passive observer parity and prospective candidate source-lineage timestamp. Every actual recorded candidate includes source M1-close, original M1 MSS timestamp, DOL family/target/confirmation time, side, as-of observation and NO BROKER FILL flag.
- `cognitive_component_io_audit` embedded in the exact 3Y replay JSON, with complete per-component `calls_observed`, `input_present`, `output_present`, `selected_for_decision`, `reached_first_suitable_FVG`, `blocking_observations` plus session-specific status histograms and bounded sample traces. **No old replay, no post-trade hindsight labels.**

**Scientific meaning:** "reasoning" in this cleanroom currently means *deterministic, inspectable causal evaluation of M1 inputs* with explicit decisions/abstentions, **NOT proof of an LLM independent thinking agent**. "Influence" means mandatory *algorithmic input/gate participation and objective candidate lineage*, **not proven financial alpha or formal ablation causality**. Unconnected modules are shown honestly as **0 calls**, never silently credited.

## TRUE measured 3Y source & code verification

- Exact source `VT31_NAS100_OWNER_3Y_BASE_001`, artifact `11459859004`, SHA256 `0563370fd021ad091392eb26f60cda0d3356d38c801fc1c2083cceafc5043cfa`.
- 2023-10-01T00:00Z through 2026-10-01T00:00Z excluding end, **1,059,784** actual chronological NAS100 M1 bars, America/New_York DST.
- **Verified GREEN actual native sensor run:** [38018396602 SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/38018396602), source commit `3b4cc40b30ba6e40ada4256fe53464ed531e7a16`, artifact `11657056859`; **32/32** fast-run fixture tests, source exact hash, all governance checks, complete results and artifact. Runtime **59.404 seconds**. This is a performance observation, not a controlled benchmark.
- Exactly **ONE `VT31`**, TWO session models London and NY; three NY-local source windows. Complete 60-M1 windows **774 London**, **771 NY AM**, **741 NY PM**; **137,160** actual COG assess calls and exactly **137,160** OPS M1 source calls. Market-M1 input sensor executed **1,059,784** times, no missing M1, no synthetic fills.

## Per-component status and source impact

| Native runtime sensor | Actual calls | Produced outputs / valid source | Selected for COG decision | Contributed to an OPS first-suitable FVG | Interpretation |
|---|---:|---:|---:|---:|---|
| M1 market input | 1,059,784 | 1,059,784 | — | market-wide provenance | Verified feed, ONE trader memory |
| M15 HTF completed/context | 207,153 | 207,153 | 62,885 | 2,140 | Required availability/context gate, **never M15 entry FVG** |
| H1 HTF completed/context | 154,123 | 154,005 | 62,885 | 2,140 | Required availability/context gate, **never H1 execution** |
| H4 HTF completed/context | 140,966 | 140,492 | **0** | **0** | ACTIVE sensor **but read-only descriptive context**, not a decision gate |
| Prior completed NY cash-session liquidity | 139,445 | 125,190 | 29,882 | **908** | Real source, not a universal full-24h PDH claim |
| Asian NY-clock source liquidity | 140,057 | 79,225 | 23,303 | **708** | Source may be swept before later source hour |
| Early London NY-clock liquidity | 140,029 | 40,502 | 13,201 | **524** | Not available to London as source before its range closes |
| Swept-liquidity revocation | 3,501 | 3,501 | 3,501 revoked | 0 | This is a source **invalidation action**, not an entry reason |
| M1 MSS/displacement | **137,160** | **37,645** fresh M1 shifts | 62,885 including retained thesis | 2,140 | Actual structural source; 1.25-body median heuristic must be validated |
| Persisted M1 thesis revalidation | 137,160 | 47,110 survived updates | 37,775 decisions via retained source | candidate linkage instrumented separately | Preserves source MSS time; may revoke DOL/pivot |
| DOL directional choice | **137,160** | **62,885** | 62,885 | **2,140** | Explicit price-family/side/confirmation lineage |
| Final cognitive decision/abstention | **137,160** | **62,885** valid-M1 *observations* | 62,885 | **2,140** | Decision calls are per M1, NOT unique independent trades |
| OPS closed-M1 FVG source | **137,160** | **7,463** raw directional source gaps | 2,140 first suitable | **2,140** | First suitable M1 gap still must prove bid/ask fill |
| OPS research candidate | **137,160** | **2,140** source proposals | 2,140 | **2,140** | **Not 2,140 actual orders/trades** |
| BID/ASK fill path | **0** | **0** | 0 | 0 | **NOT_CONNECTED** to this source replay |
| Broker execution ACK | **0** | **0** | 0 | 0 | **NOT_CONNECTED** |
| CIBO/QDLE economics/sizing | **0** | **0** | 0 | 0 | **NOT_CONNECTED** |

**Important counting note:** native liquidity and HTF component `calls` count both their *actual M1 source formation/mitigation events* and their repeated *M1-session contextual evaluations*, so calls can exceed the 137,160 cognitive assessments. A selected/valid cognitive event is still not a separate trade. Repeated outputs are not 62,885 unrelated orders. H4 truly executed and produced output but currently **did not change an entry decision** (context diagnostic only).

**Source candidates by session:** 766 London, 721 NY AM, 653 NY PM = **2,140** source-candidate windows. By actually selected DOL family: **908 NY cash, 708 Asia, 524 London**. Source 3-bar M1 FVG count 7,463 raw, but **5,183 raw FVG M1 observations** specifically encountered *missing COG decision* (902 London + 1,824 NY AM + 2,457 NY PM): blocked conditions, **not 5,183 losses or unique cancelled trades**.

## Critical P0 — Actual source pending after cognition revoked

The sensors independently reproduce and materially size the previously reported OPS-owned fault: source `RESEARCH_PENDING_CE` may remain live as **a research hypothesis**, while the true COG decision is `None` because DOL/MSS availability was lost.

| ICT window | M1 observations with OPS pending but COG absent | **Unique source FVG candidates** affected |
|---|---:|---:|
| London | **1,775** | **253** |
| NY AM | **2,914** | **339** |
| NY PM | **2,959** | **345** |
| **TOTAL** | **7,648** | **937** |

The **937** distinct FVG-source hypotheses represent roughly **43.8% of 2,140** research candidates, NOT verified broker orders and NOT realized trading losses. The 7,648 measure repeated M1 states after cognition is unavailable, not 7,648 independent orders. This is a severe **research lifecycle/source validation** bug warranting OPS fail-closed repair and tests before any paper order simulation or LIVE.

The emitted event examples carry both the original selected FVG clock and first later M1 with COG missing plus the M1 missing reason. Example: selected London `2023-10-02T07:41Z`, pending without COG by `07:50Z` on `CONFIRMED_DISPLACEMENT_MSS`; **broker fill NOT PROVEN**.

**OPS coordination:** [GitHub Issue #727 comment 6092991050](https://github.com/mezas3238-hue/qore-core/issues/727#issuecomment-6092991050). Architect 2 owns changes in `operations.py`, order cancel/expiry and `SourceLimitOrderAudit` / broker ACK races. COG sensors explicitly do NOT silently rewrite the OPS state and do not claim to have fixed that P0.

## Next scientific and integration gates

1. Architect 2 repair **COG lost => source pending invalidated** (without auto-liquidating an already ACK-confirmed filled position) and cancel paper pending candidate with a broker-safe ACK race; rerun exactly the same 3Y M1 with the same sensors, compare **unique P0 candidates before and after**. Expected hard gate: **zero false research pending without a valid as-of COG source**, not merely zero exception logs.
2. Native H4 should remain a diagnostic (not selected as a gate) **unless** an independently specified higher-timeframe source rule explicitly needs its actual input for a DOL; do not manufacture "power of cognition" from a module that is called but not part of the decision. For original 2023 ICT source fidelity validate hierarchy of relevant PDH/PDL, weekly dealing range and true next DOL.
3. If user wants **true reasoning beyond deterministic code**, separately define a cognitive agent interface with questions, hypothesis output, justification and counterfactual branch calls, reproducibility and decision audit. Mere sensor calls cannot prove an independent language-model agent ran.
4. Connect source-candidate to real bid/ask quote, confirmed PAPER/MT5 execution, stop/target and costs before calculating PF/DD/Sharpe/Sortino or granting any money authority. One VT31 book across London + NY; no separate trader per session.
5. Do formal **causal ablation replay** per active gate, same M1 market, with alternative lost/disabled components; sensor pass alone proves an upstream necessary condition under present implementation, not how much risk-adjusted profit it adds. Old immutable R2.2 replay must not re-enter.

**Certification:** NOT PASSED. **Fresh Holdout:** SEALED. **LIVE/QDLE/CIBO exposure:** NONE. **Actual fills:** 0 proved. **PF/DD:** NOT COMPUTABLE.


## FINAL STRICT PASS — FRESH MSS vs PERSISTED MSS candidate attribution

One additional sensor refinement separates a first-suitable source FVG whose **M1 MSS/displacement is newly confirmed on the very same M1 close**, versus whose **original M1 MSS was confirmed on a prior closed M1 and its DOL/structure revalidated** at the later actual FVG close. This is owner-requested **genuine influence on the entry source**, not a synthetic reason-code.

**Latest exact code [GitHub Actions #38018545147 SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/38018545147):** commit `4e7c84a07f08cdc6a7e18d2737cd3f60a40b4d5c`; output artifact `11657726407`; **33/33 tests pass** (new adversarial delayed-FVG input/output sensor), source hash verified, complete 1,059,784 true M1, unchanged base opportunities and source candidate count; **40.978 seconds** measured. Source-trace example now says `M1_MSS_source=CURRENT_M1_NEW` or `PRIOR_M1_REVALIDATED` alongside the original `structure_break_confirmed_at`.

| Original ICT M1 source window | New MSS and first suitable FVG at same M1 close | Historical confirmed MSS revalidated into later M1 FVG | Total source FVGs |
|---|---:|---:|---:|
| London | **303** | **463** | 766 |
| New York AM | **293** | **428** | 721 |
| New York PM | **300** | **353** | 653 |
| **TOTAL** | **896** | **1,244** | **2,140** |

**Critical scientific conclusion:** **1,244 of 2,140 (58.13%) source FVG candidates** concretely relied on *retained as-of-valid prior M1 MSS* rather than same-bar MSS confirmation. This demonstrates that persistent cognition is **actually exercised** and impacts first-suitable source candidate formation. It does NOT establish 1,244 real fills, signal wins, predictive profitability or causal ablation alpha.

The 937 unique P0 pending-without-cognition source FVGs and 7,648 repeated invalid pending M1 observations were **replicated unchanged** in this latest fully strict/green run, independently of MSS origin classification. OPS owns the fail-closed source/pending fix; cannot promote source research into execution until corrected.

**Correction/qualification to any earlier run:** the run-38018396602 sensor output is valid and green; final `38018545147` supersedes it only for the added *fresh-MSS vs revalidated-MSS* impact attribution, without changing source M1, decisions, 2,140 source FVGs or deduplicated P0 counts.
