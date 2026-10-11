# QORE Scalper A1 — Prequential Settled-Loss Cognition and Chronological Evidence Replay

**Date:** 2026-10-10. **Architect:** A1 Cognition. **GitHub:** issue #756 / draft PR #758. Cross-review A2: issue #757 / draft PR #759. Parent: draft PR #623. **Research only:** no VPS, live orders, broker gateway, trading permission, risk authority, source-methodology rule changes, holdout or certification.

## Problem and verified source behavior

The original V50-G market replay (`capitalizer_v50_cognitive_geometry_economics.py`) constructs `CapitalizerExperienceMemory()` anew for each opportunity and injects `CapitalizerEpistemicReadiness.WELL_SUPPORTED` as a constant. It uses the V50 bridge and geometry, not an actual nine-market Master Frame for every historical M1 opportunity. Previously, independent A1 `evaluate_full_frame_research_batch` invoked `build_master_cognitive_frame` using supplied nine-market evidence but used its `A1CausalSettledMemory` **only to count historical settlements**. Therefore a PASS/ABSTAIN change caused by genuine loss-cause memory had not been demonstrated.

## Changes implemented on A1 research branch

1. `src/qore/infrastructure/trader_lab/capitalizer_a1_full_frame_research_adapter.py`, commit `63e6129b3756005548d2699e8f6c40d88bdbe8e1`: an externally validated, *selected and actually settled* `A1SettledChosenTrade` may contain a real `CapitalizerLossCause` with matching execution ID. `A1CausalSettledMemory.as_of(decision_at)` reveals settlements with **exit_at strictly earlier than decision_at**, never current/future outcomes, counterfactual losers or same-clock exits. Adapter builds `CapitalizerLossMemory` from these chosen closed losses, injects it into an immutable copy of `CapitalizerGlobalWorldModel` using `dataclasses.replace`, and calls the **real `build_master_cognitive_frame`**. Unverifiable preloaded world loss-memory is rejected instead of merged. The sovereign gate can now ABSTAIN on an *exact unresolved failure fingerprint without a genuinely new causal event*. No new arbitrary numeric recovery restriction, strategy filter or capital allocation change.
2. `tests/infrastructure/trader_lab/test_capitalizer_master_cognitive_frame.py`, commit `7b6ad4a36384306818b338269814a33da53283e9` and later `f3e39527ce72a5f8a08cb01f6cf839c97b4e4e0c`: tests before settlement, exact-time tie, after settlement, wrong source/execution ID, unproven `world.loss_memory`, unrelated market and true new-cause override. Crucially, the same candidate context has `PASS_TO_STRATEGY` without the as-of loss and `ABSTAIN` with the evidenced closed prior loss; removing memory restores PASS. This is a **unit-level causal ablation**, not evidence of improved returns.
3. `src/qore/infrastructure/trader_lab/capitalizer_a1_chronological_cognitive_replay.py`, commit `7b324b3c5eec073761842f1f5901d5d050f432fe`: adds opt-in `A1ObservedNineMarketBarrier` and `replay_observed_cognitive_barriers`. Its inputs must be actual observed and complete nine-market world/perception/regime/cross-market/pressure/context/source-binding evidence; it **does not invent** that evidence or synthesize M1 bars from M5. Iterates strictly forward in time, calls Master Frame for each barrier, enforces source-ID and output parity, and emits each `source_opportunity_id` and deterministic `PASS_TO_STRATEGY / WAIT / ABSTAIN` WHY result. Missing market evidence, time reversal, equal-time ungrouped barriers, duplicate IDs and impossible candidate coverage fail closed rather than silently dropping opportunities.
4. Quality repair `f83ce4cac2c310d9b3cde588bdb1e2110cec5570` sorts research memory imports; new tests include a two-barrier memory ablation with four source identities, and regression rejections for missing ninth market, reversed sequence, ties and duplicate IDs.

## Formal causal contracts

- Observation and source confirmations must not exceed `decision_at`. All timestamps timezone aware; H1/M15/M1 only. The previously implemented V50 H1 future terminal right-censor remains in force.
- Memory is immutable and comes from **chosen previously settled** executions only. `exit_at < decision_at` (strict), including when two candidate evaluations share a clock boundary. `loss_cause.loss_id == chosen execution_id`.
- Unresolved loss memory is a cognitive *observation*. It may cause adversarial ABSTAIN only through original `assess_adversarial_candidate` and `assess_cognitive_gate`, not by hidden outcome-aware filtering or a new economic policy. An actually new causal event is independently assessed; previous losses do not trigger an unconditional session veto.
- All candidate outputs remain advisory; `economic_admission_changed=False`, `winner_selected=False`, `outcome_visible=False`, `grants_capital_authority=False`. QORE Risk continues sovereign. MAX3 remains ceiling, not quota.
- The replay spine refuses simultaneous competing **multiple distinct source candidates for a single market** when the external world model cannot represent each hypothesis independently. This is a **known unresolved density/representation blocker**; it does not discard them or claim that the source should generate fewer opportunities.
- Caller still must attest genuinely observed nine-market inputs and that chosen settlements were actually selected. These source/receipt reconciliations are not yet wired into an immutable historical replay.

## Official GitHub Actions: GREEN (exact SHA)

**Commit:** `f3e39527ce72a5f8a08cb01f6cf839c97b4e4e0c`.

- [QORE Scalper Cognition A1 Audit, run 38052161104](https://github.com/mezas3238-hue/qore-core/actions/runs/38052161104): **SUCCESS**, Ruff full repo PASS, Mypy `src tests` **1,625 source files no issues**, pytest focused **38 passed**.
- [Scalper A1 Causal Research Quality, run 38052161139](https://github.com/mezas3238-hue/qore-core/actions/runs/38052161139): **SUCCESS**, branch-only focused tests, tooling.
- Earlier failed runs relate to import order and missing test type annotation, repaired in subsequent SHA. Do not conflate GREEN with full 9/9 replay, five corrected-core economic workflows, source-faithfulness or Trader Lab certification.

## P0 next: objective certification blockers

1. **Real synchronized nine-market bar/frontier builder**: consume actual M1 evidence, daily DST/session clock, previously closed H1 and M15, native/finer M1; provenance check every input, no fake GOOD/KNOWN, no M5-to-M1 fabrication.
2. **Multi-hypothesis same-symbol concurrency**: represent multiple source-complete H1/M15/M1 opportunities at the same timestamp/market without discarding alternatives or incorrectly shrinking density; define competition identity independently of source validity.
3. **True execution settlement reconciliation**: external selected execution ID, entry/exit receipts, loss fingerprint cause, duplicate prevention, as-of isolation across market/session/era and proper resolution/expiration of prior failures. Preserve all non-selected counterfactuals *only* for after-the-fact analysis.
4. **Controlled A/B and per-layer ablation** against exact same population and chronology, including loss memory, Master Brain, perceptions, regime, adversarial, pressure, metacognition, opportunity competition and position/exposure; preregister before reopening outcomes. Record `caller -> input -> as-of provenance -> WHY -> action` on **every** candidate, including WAIT and ABSTAIN.
5. **Economic falsification**: nine markets and all sessions, density by era, baseline winner count >=80% and positive winner R >=90%, PF, expectancy, Sharpe, Sortino, cost stress, max DD <=6R (target 3–5R), independent quality/replay artifacts. The rejected 90-trade V50-G architecture must never be promoted to solve DD cosmetically.
6. **A2 author-method review**: no change to source trigger families/POI, HTF state, M1 stop/target or H1 target fast path without B provenance and independent signoff; integrate B's causal target repair deliberately, without silent merge.

**Status:** new causal loss-memory-to-Master-Frame effect and chronological evidence harness implemented and focused CI GREEN. **Real historical full integrated Master Frame replay NOT YET run; economic metrics not measured; author fidelity pending; Scalper NOT CERTIFIED.**
