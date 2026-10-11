# QORE SCALPER — A1 full cognitive handoff port ready for Trader integration review

**Date:** 2026-10-10 | **Owner:** A1 / issue #756 / PR #758 | **Methodology peer:** A2 / PR #759 and canonical issue #755 / PR #761 | **Master:** PR #623.  
**Branch:** `agent/scalper-architect-a-cognition-20261010`. **Research-only; PR OPEN DRAFT; no VPS, live, sizing, QORE Risk override, merge or production authorization.**

## Answer to the Owner's architectural defect

The V49 9/9 native-M1 structural replay [#38053946695](https://github.com/mezas3238-hue/qore-core/actions/runs/38053946695) ran 2,020 selected trades and reported **PF 0.66446 / DD 236.134R gross**, but did **not** invoke `build_master_cognitive_frame`. The legacy V50-G [#38053723674](https://github.com/mezas3238-hue/qore-core/actions/runs/38053723674) used an **incomplete** V50 cognitive snapshot, allocating `CapitalizerExperienceMemory()` anew and static `WELL_SUPPORTED` to every candidate, and selected **94 trades** under the cognitive+geometry arm. Neither measured how a fully wired nine-market cognitive Trader performs.

**This project now provides a concrete, typed A1-to-Trader handoff component, *not* another strategy filter claiming restored edge.**

## Code and exact calling contract

### `src/qore/infrastructure/trader_lab/capitalizer_a1_trader_cognition_port.py`

**Function `prepare_trader_cognition_packet(barrier, settled_memory, exposure_intents=())`:**

- Accepts a complete, **externally evidenced** `A1MultiHypothesisBarrier`: the nine-market `CapitalizerGlobalWorldModel`, all nine market perceptions and regime hypotheses, as-of causal cross-market graph, cognitive pressure facts, **all** source opportunities at the same confirmed M1 instant, source-ID census and independent H1→M15→M1 confirm clocks, individual cognitive context and `source_rule_id`.
- Calls `replay_multi_hypothesis_evidence` → real `evaluate_full_frame_research_batch` → **actual `build_master_cognitive_frame` for each candidate** → Metacognition/adversarial reasoning/real source WHY/causal settled-only loss memory. The output retains one `A1TraderCognitiveCandidate` per source opportunity, no deduplication by symbol.
- Calls `assess_joint_competition_barrier` to add contemporaneous same-market hypotheses, causal links between markets, evidence gaps, pairwise factor exposure if **externally supplied** side and `Decimal` risk-R, and MAX3 **capacity** pressure. **Source policy ranking is unresolved**: other DECISION markets are made FOCUSED during each individual candidate projection. This is not a globally simultaneous Master Frame calculation.
- Returns `A1TraderCognitionPacket` indexed by **original `source_opportunity_id`**, exact same decision time, source rule and hypothesis IDs, H1/M15/M1 causal clocks, `PASS_TO_STRATEGY`/WAIT/ABSTAIN, WHY and uncertainty, pair peers, previous chosen-settled history and explicit `trader_review_status`.

**Function `advance_trader_cognition(state, barrier, newly_settled=(), exposure_intents=())`:**

- Manages an **immutable, caller-held `A1TraderCognitionState`**: strictly increasing decision barriers, source-ID nonreuse across barriers, settled execution receipts that must reference a *previously observed* candidate with `PASS_TO_STRATEGY`, and no duplicate execution/source.
- Requires every claimed external chosen and settled receipt to name `execution_id`, original `source_opportunity_id`, a QORE Risk receipt identifier, external order/fill provenance identifier, actual entry/exit clocks, when the settlement was actually confirmed, and finite realized R. A negative R must carry exact matching `CapitalizerLossCause` and causal label. **These identifiers are declarations by the upstream adapter; neither external broker nor QORE Risk receipts can be authenticated by the A1 port itself.**
- The actual exit clock and the distinct confirmation clock remain **both preserved**. `A1SettledChosenTrade.confirmed_at` in `capitalizer_a1_full_frame_research_adapter.py` gates all learning: ONLY settlements whose confirmation is *strictly earlier* than the new decision can enter `CapitalizerLossMemory` and influence actual `assess_adversarial_candidate` / `assess_cognitive_gate`. **Tied/current/future ACKs never teach**.
- No synthetic losses from unseen/missed/counterfactual trades. No self-learning of hindsight, no belief generator, no fabricated `WELL_SUPPORTED`, no risk sizing, no applied exits and **no extra session slots**.

### Encapsulated status, explicitly NOT a trade permission

A cognitive PASS becomes `SOURCE_METHOD_ARBITRATION_REQUIRED`; WAIT and ABSTAIN become `COGNITIVE_WAIT_RESEARCH` / `COGNITIVE_ABSTAIN_RESEARCH`. In every packet, `execution_authorized=False` for each row, `global_arbitration_complete=False`, `physical_risk_checked=False`, `economic_trades_executed=False`, `live_integration_authorized=False`. The external Trader and QORE Risk must decide separately and record their authority.

**Do not use `PASS_TO_STRATEGY` as BUY/SELL, `pair.requires_joint_review` as a universal rejection, or MAX3 slot pressure as a zero-opportunity signal.** No silent deletion of source IDs, and no no-op fake production readiness.

## Integration steps for next architect (must each be evidenced)

1. Native synchronized M1 ingestion for nine symbols, **real H1/M15 evidence** and the independently corrected `_untouched_h1_target_fast` decision frontier from methodology A2. Build true `A1MultiHypothesisBarrier` with per-source data and source-ledger rule IDs. Never synthesize nine-market readiness or approximate M1 from M5.
2. Route **every** original source opportunity into `advance_trader_cognition`, respecting same-instant grouping and exact historical denominators. Persist immutable cursor, all returned candidate IDs, WHY and decision_time plus source market/session.
3. Request A2 author-fidelity signoff on joint same-market arbitration and TTrades alternatives. Integrate separately a reproducible as-of, independent policy that decides among multiple PASS candidates without filtering 90% of the baseline or selecting the best outcome in hindsight.
4. Integrate external **verified** Trader decision receipts, QORE Risk admission, actual execution IDs, broker timestamps, physical BID/ASK/spread/commission/slippage and independently verified settlements. The A1 port accepts metadata but **does not verify broker validity or compute fills**. Replay genuinely executed settlements through `advance_trader_cognition` before following decisions.
5. Compare on **identical 9/9 native-M1 source opportunity IDs**: structural V49 vs full cognition including memory-on/off and joint-review-on/off, accounting for source method, stop/target/entry controls. Report original winners retained (>=934 of 1,167) and original winner mass retained (>=415.74848564900598R of 461.94276183222887R) as a guard, NOT an automatic performance claim. Require DD target 3–5R, absolute <=6R, net PF, expectancy, Sharpe, Sortino, OOS, costs, liquidity and stress.
6. Fail closed on any evidence shortfall. No certification, no VPS/production or PR merge on unit tests, count recovery or partial economic improvements alone.

## Regression coverage and verified limits

New direct tests in `tests/infrastructure/trader_lab/test_capitalizer_master_cognitive_frame.py`: 3-source same-instant full-frame packets, all original source IDs/WHY and nonexecution, previously chosen actually settled loss → next-barrier exact failure fingerprint ABSTAIN while another hypothesis stays PASS, memory-off ablation, positive settlement no loss teaching, unseen execution, reused opportunity, duplicate receipt, same-clock future acknowledgment, risk/execution loss mismatches, and nine-source burst (36 simultaneous pairs; one MAX3 slot; **zero** selected or sent orders; order-permutation invariance). An additional test verifies actual exit precedes but is *not confused with* settlement knowledge, and ACK strictly before the new decision is required.

**These are synthetic test fixtures for a real cognitive call graph, NOT a historical 9/9 Master Frame replay and NOT a validation of realized economic edge.** The source candidate fixture labels `TTRADES_REVIEW_PENDING` are honest unresolved author evidence placeholders.

**CI** (complete SHA/run to fill with verified GitHub Actions outcome on the exact code) — do not infer pass from initiated jobs. Earlier full repo CI GREEN is [#38058863160](https://github.com/mezas3238-hue/qore-core/actions/runs/38058863160) at port code + initial five tests, before the knowledge-clock refinement. The new tests and actual-exit/knowledge separation must additionally pass current SHA in its own CI.

**Delivery:** A1 cognitive *port and state contract prepared for research integration*; Trader pipeline not yet connected to full nine-market time series; **not certified and no production authority**.
