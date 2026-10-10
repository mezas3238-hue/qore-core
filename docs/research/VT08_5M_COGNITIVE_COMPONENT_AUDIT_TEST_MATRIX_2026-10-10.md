# QORE CORE — VT08 Cognitive 5M — P0 Component Audit and Tests

**Date:** 2026-10-10  
**Ownership:** Arquitecto B, Cognitiva; [issue #763](https://github.com/mezas3238-hue/qore-core/issues/763).  
**Source methodology counterpart:** Arquitecto A [issue #762](https://github.com/mezas3238-hue/qore-core/issues/762), [draft PR #765](https://github.com/mezas3238-hue/qore-core/pull/765).  
**Cognitive branch/PR:** `agent/vt08-5m-cognition-replay-20261010`, [draft PR #764](https://github.com/mezas3238-hue/qore-core/pull/764).  
**Parent experiment:** [draft PR #634](https://github.com/mezas3238-hue/qore-core/pull/634).  
**Authorities:** GITHUB-ONLY, RESEARCH-ONLY, NO broker/capital/VPS/DEMO/LIVE/PRODUCTION, NO sealed seven-year outcome archive. 

## 1. Verification standard and result

**Do not assert '100% cognitive live integration' merely because unit tests pass.** "Functionally tested in a synthetic environment" and "consumed by an executable historical market replay" are distinct certifications.

**Completed GitHub verification run:** [#38072382710](https://github.com/mezas3238-hue/qore-core/actions/runs/38072382710), SHA `0f1034fa0e3db7c54a887a47086bc438bd7b5bc3`. Ruff PASS, Mypy PASS (**14 selected source files**), Pytest primary suite **158 passed, 3 skipped** (cross-branch-only tests intentionally skipped in primary suite), **3 additional cross-branch tests PASSED** against the **actual Architect A CandidateEvent module** pinned to A commit `6e537cd8a8a01d9817802383c736baf5688f2a0f`. No failed tests in this verified run.

**Latest exact-code verification after that hardening:** [#38072492922](https://github.com/mezas3238-hue/qore-core/actions/runs/38072492922), code SHA `86a907d4a702e67f88af492c0efb20216bca69fe`, **SUCCESS**: Ruff PASS, Mypy PASS (14 source files), primary Pytest **158 passed and 3 cross-branch-only skips**, followed by **3 passed** against the actual pinned Architect A module. All verification stages passed; **161 executed passing tests** across the two stages, with three tests deliberately skipped in the first stage because the real A module is checked in the second. Documentation commits afterward do not modify tested source code. The A→B envelope requires an explicitly frozen manifest SHA; since there is no signed A/B manifest yet, a caller cannot turn the current contract cognitive-ready by passing a boolean or arbitrary claimed hash.

Coverage percentages below are **statement coverage from the 158-test primary suite at the exact verified SHA**; they are not exhaustive real-market assurance.

| Cognitive module | Statement coverage | Verified behavioral evidence | Remaining external dependence |
|---|---:|---|---|
| Five-market research Situation Model / unknown memory envelope | **97%** | 5 market authority scopes, 15 market-anchor contexts, per-feature timestamps, no future bars, source H4 cycle and JSON fingerprints | Independent proof of source producer cutoffs |
| Original strategy identity memory | **97%** | Identity fingerprints, immutable Owner 01/05/09, source/broker boundary | Source-author adjudication on H4 filled lifecycle |
| Original CIBO Market Memory | **96%** | Memory validation, fingerprints and non-execution governance | Does NOT cover four new research markets |
| Original Trader Experience Memory | **92%** | Validated consumed research cells, side/market disjoint from trade authorization | New-market time-bounded experience not trained/approved |
| Combined cognitive memory | **97%** | Bundle validation, no runtime self-training or direct PnL-rule promotion | Genuine new 5M memories still `UNKNOWN_NOT_BOUND` |
| Original causal Situation Model | **96%** | Immutable evidence, outcome-leak rejection, authorized market/anchor guards | Feature values must come from actual as-of evidence |
| Sovereign Reasoning + Adversarial + Metacognition | **99%** | EXECUTE / WAIT / ABSTAIN, material contradictions, unknown evidence veto, unresolved bias/risk wait | Real producer must supply honest supported/unknown/contradictions |
| Hypothesis lifecycle | **97%** | WAIT, evolving confirmation, KILLED/no resurrection, stable source ID and genuinely new rearm | Source origin fingerprint must be durable across snapshots |
| Journey / Destination Intelligence | **98%** | PRE_ENTRY, ADVANCING, STALLED, EXHAUSTION_RISK, DESTINATION_REACHED, INVALIDATED, UNKNOWN | Chronological in-trade market/path evidence |
| Position Intelligence | **98%** | HOLD / PROTECT / REDUCE / EXIT proposals, monotonic stops, source-invalid/H4 expiry, no capital/order authorization | PROTECT/REDUCE not calibrated or applied to economic replay |
| Cognitive orchestration | **97%** | Sovereign `evaluate_cognitive_hypothesis` and `evaluate_in_trade_cognition` called with audit hashes | Producer->orchestrator binding on real historical events |
| Frozen architecture contracts | **96%** | No cross-trader logic/identity promotion, future info or runtime authority | No operational approval |
| Stateful cognitive consumed gate | **98%** | Cross-market global clock, immutable event identity, WAIT→EXECUTE, ABSTAIN killed, one execution/event, per-position traces; DST-fold test and 5-market multievent fixture | Current gate processes synthetic situations, not source fills/price-path economics |
| A→B CandidateEnvelope readiness layer | **94%** | Stable source_event_id vs mutable snapshot id, no unverified bias, no future source timestamp, no false LIVE or market authority | A V1 currently has `bias_feature_cutoff=UNATTESTED`; complete cognitive field evidence & signature missing |

**Approximate combined statement coverage** for the first 13 cognitive modules (excluding A→B readiness) is **97%** (871/898 statements). Including A→B readiness in the last audited run (82/87 after manifest hardening) yields approximately **96.7%** (953/985). Percentages are **coverage**, not a 100% functional guarantee.

### Evidence of actual A code compatibility

CI checks out a separate, read-only GitHub worktree at A commit `6e537cd8a8a01d9817802383c736baf5688f2a0f`. It loads **A's actual** `Vt08CandidateEventV1` class through an isolated Python module, constructs A's actual golden event, calls A `envelope()`, and subjects it to B's independent verifier. The tests prove:

1. A's structural `source_event_id` remains stable when only `evidence_sha256` mutates, while `event_id`/fingerprint changes.
2. B identifies the event and **refuses cognitive_ready** due to A's explicitly UNATTESTED daily bias and incomplete situation-field cutoffs, plus unsigned joint contract.
3. B rejects a forged future `cisd` cutoff.
4. This cross-branch check does **not** turn A's source candidates into fills and does **not** consume real historical closed-bar values.

## 1.A. New P0 finding: EXECUTE is **not** a FILLED position

**Discovered 2026-10-10 in the last code audit:** the earlier gate checked that a source event received `EXECUTE` before calling Position Intelligence, and took `entry_state=FILLED` from the Situation snapshot at face value. There was **no independent execution/fill record**. This allowed a forged or mistaken in-trade Situation to be assessed even if no order had filled. It is a material gap between Cognitive admission and economic replay.

**Implemented correction:** `vt08_cognitive_5m_consumed_gate_v1.py` now exposes immutable `Vt08ResearchFillEvidence`, `Vt08ResearchFillTrace`, `record_fill()`, and `fills` ledger. A position assessment **requires all** of:
- Same source event already passed a real Cognitive V1 `EXECUTE` and has not been KILLED or merely WAITING.
- A separate, research-only simulated fill event has been explicitly recorded: source-event ID, market, side, frozen source H4 cycle, unique fill ID, timestamp, price and nonempty lowercase SHA-256 evidence identifier; no broker-order authorization.
- Fill identity matches cognitive source identity; no cross-market, opposite-side or cross-cycle mutation.
- Fill timestamp no earlier than Cognitive EXECUTE and strictly before pending H4 expiry. The global replay clock cannot move backwards.
- No duplicate source fills or fill IDs. A position must be observed **after** the fill, with `FILLED` entry and active/open position states, exactly matching the recorded entry price and causal as-of.
- No automatic fill promotion from an EXECUTE. Cognitive entry decision and economic fill are separately recorded and reconciled.

**New code-and-tests CI:** [GitHub Actions #38078677701](https://github.com/mezas3238-hue/qore-core/actions/runs/38078677701), exact tested code/test SHA `91df65f15ea108110fa55140d33280aeea36b211`, **SUCCESS**: Ruff PASS, Mypy PASS for 14 sources, **166 passed / 3 skipped** in first test stage and **3 additional cross-branch tests passed** using actual A module frozen at SHA `6e537cd8a8a01d9817802383c736baf5688f2a0f`. Total **169 executed tests passed**. The three initial skips are the three same A-specific tests run separately. Gate statement coverage **96%** (184/192); percentages are not real-market certification.

**Boundary that remains:** A signed/audited real execution engine must eventually create fill records from actual chronological BID/ASK bars, slippage, broker costs and source entry/SL/TP authority. A caller-supplied 64-hex digest alone does NOT prove an actual broker fill or a data-root hash: these gate fixtures are **synthetic research data only**. B will not label historical economics as full-cognitive until source, execution and position ledgers can be reconciled event-by-event.

---

## 2. P0 root causes corrected in code

- Previously 4/5 research markets rejected by old Forex operational whitelist; now opt-in dedicated research-only Situation type without changing production authority.
- Existing `metacognition=UNKNOWN` could coexist with `EXECUTE` when `supporting_evidence=()`; now WAIT.
- A full-confirmation source with `risk_geometry_state=UNKNOWN` could execute, and `bias_state=UNRESOLVED` could pass through; now WAIT until decision-material support is resolved.
- R3.15 seven-market memory fingerprints could be falsely attributed to new research markets; now separate research strategy and memory fingerprints, explicit unknown for all five until temporal coverage is independently established.
- A source event could change market/side/anchor/profile/source-cycle/NY-date between WAIT updates; the research gate freezes these identities; same-source killed or executed hypotheses never rearm.
- A WAIT could outlive its H4 entry-expiry, or the producer could supply future evidence with a misleading top-level clock; the research gate enforces source H4 expiry for admission, per-feature timestamps, max cutoff equality, timezone-aware UTC and NY DST.
- In-trade evaluation could lack `position_state=OPEN` / `entry_state=FILLED`; now explicitly rejects non-admitted or non-open positions and any nonmonotonic as-of.
- Trace previously hid meta/adversarial and journey metadata; now preserves decision, meta state, challenges, evidence, memory fingerprints, journey/destination, management proposal, next stop and zero broker authority.
- A→B contract readiness is independently checked and **fails closed** on missing bias and cognition feature lineage; cannot treat the 1,514 experimental intracycle OHLC fills as cognitive.

## 3. What prevents 'full cognition 100% certified' today

**P0 / A->B integration:** A's proposed V1 is B01 positional C2/M15 only, presently `REVIEW_STATUS=PROPOSED_AWAITING_ARCHITECT_B_REVIEW`, contains only `source_h4/cisd/PS` feature times and **explicitly unattested daily bias cutoff**. B cannot safely produce all 27+ fields of Situation Model from that payload without fabrication. The final A/B signature manifest does not exist.

**P0 / Methodology:** Architect A separately researched intracycle C2 M15 and obtained **1,514 hypothetical terminal OHLC fills / 5 markets / consumed 1095D**; raw PF **0.712–1.139**, max DD per market **11.25–53.10R**, failing pre-registered PF>=1.80 and DD<=6R. These are methodology-only, **without complete cognition**, and not a candidate for certification. Source methods for C3, other families and actual target/H4 lifecycle remain under audit.

**P0 / Market cognition:** New-market Market Memory and Trader Experience are UNKNOWN, not trained/validated. 'The functions return a fingerprint' does not equal 'full genuine specialist market cognition'.

**P0 / End-to-end scientific replay:** Old #634 expansion backtests bypass `evaluate_cognitive_hypothesis` and `evaluate_in_trade_cognition`. No replay has yet demonstrated 100% cognitive evidence for all **actual** eligible source events, chronological in-trade updates, real BID/ASK/slippage/commission and matched methodology-only vs cognitive-on PF/DD. Such metrics **must not be invented**.

**P1 / Position policies:** HOLD/PROTECT/REDUCE/EXIT branches are unit-tested; the default policy deliberately keeps structural protection and reduction inactive pending VT08-specific validation. Source-controlled H4 exit currently involves a documented R3.2/R3.9 lifecycle conflict.

**P1 / Source authenticity:** The original primary TTrades video/framebook has not been independently re-hashed and frame-adjudicated by A. Causal cutoff producer attestation needs independent replay checks, not merely trusting timestamps it reports.

**P1 / Calibration and certification:** Owner's earlier density gate 50 trades/2Y was retired. A new numeric executable density criterion must be Owner-approved before final holdout. Old sealed seven-year outcomes remain unopened.

## 4. Next executable coordination sequence

1. Architect A supplies a **source-typed, temporally attested** `CandidateEvent` version for each justified family, including independently verified source-day/bias and Situation fields, stable source origin, time cutoffs and frozen source-specific stop/target/lifecycle. Do not pass SHAPE_ONLY events as fills.
2. Architect B creates a non-inventing A-to-Situation bridge and consumes **every** eligible candidate through the tested cognitive gate. Separate stage counts: methodology complete→cognitive EXECUTE/WAIT/ABSTAIN→orders→fills→terminal. Prove **no fallback**, **0% cognitive bypass**, **0 future leakage**.
3. Feed actual closed-bar position snapshots, compare four management proposals but apply only separately governed action; never widen stops or change quantity without authority.
4. Run matched consumed-development replay with raw equal-risk PF/DD + density under identical costs, anchors, profiles; then WFO, MC and final sealed validation only after source, cognition and gate freeze. Any falsified variant is retired, not tuned on sealed outcomes.

**Current verdict:** research module correctness significantly hardened and extensively tested, A real contract interoperability tested and fail-closed; **no full real-market cognitive integration, no 100% certification, no VPS or LIVE authority**.
