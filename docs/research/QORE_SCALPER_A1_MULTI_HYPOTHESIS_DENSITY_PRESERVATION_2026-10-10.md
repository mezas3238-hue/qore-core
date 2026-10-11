# Scalper A1 — Same-minute, same-market multi-hypothesis cognitive census

**Date:** 2026-10-10 · **Workstream:** Architect A1, PR #758, issue #756 · **Cross-review:** Architect B, PR #759, issue #757 · **Parent:** PR #623 (DRAFT / UNMERGED). GitHub-only, research-only, no VPS, broker, production, promotion or capital authority.

## P0 root cause and design choice

The frozen nine-market `CapitalizerGlobalWorldModel` stores one `CapitalizerMarketWorldState` per market and therefore only ONE `DECISION` hypothesis per market at the same instant. The earlier `evaluate_full_frame_research_batch` refuses duplicate same-symbol bindings. Turning that representational limit into a rejection rule would destroy potentially source-valid M1 opportunities and could repeat the Owner-rejected low-density 90-trade failure.

**New solution is observational, never silent elimination:** `src/qore/infrastructure/trader_lab/capitalizer_a1_multi_hypothesis_research.py` implements an opt-in, lossless **multi-hypothesis cognitive census**:

- Each `A1SourceHypothesisAlternative` has a unique `source_opportunity_id`, market, individual hypothesis and source-event identities, mandatory source-rule reference and explicit timezone-aware **H1 → M15 → M1** confirmation ancestry. Dates must be causal, ordered and close no later than `decision_at`. Every alternative has its own `CapitalizerCandidateCognitiveContext` and evidence-provenance obligation. Placeholder rule labels are allowed only in synthetic tests, **not proof of author fidelity**.
- `A1MultiHypothesisBarrier` has one immutable observed nine-market world, perceptions, regime hypotheses, cross-market graph, pressure, and **declared full input source-ID census**. Missing, duplicated, ungrouped or cross-barrier-repeated IDs fail closed rather than disappearing from metrics.
- For each alternative, the driver **projects** a copy of the immutable nine-market world where only that alternative's market is `DECISION`; other contemporaneous `DECISION` markets are temporarily `FOCUSED` only for *this independent investigation*. It binds the alternative's specific hypothesis/source event and invokes the existing `evaluate_full_frame_research_batch` → `build_master_cognitive_frame` → adversarial/metacognition/sovereign gate. The original world is never mutated. The same immutable selected-settled-only loss memory `exit_at < decision_at` is visible to each alternative, with no intra-barrier hindsight updates.
- `A1MultiHypothesisEvidence` records each unique candidate, its H1/M15/M1 provenance and its separate deterministic `PASS_TO_STRATEGY / WAIT / ABSTAIN` and WHY. Exact source-set/row parity is mandatory. It **explicitly locks** `global_opportunity_arbitration_resolved=False`, `trade_selected=False`, `economic_admission_changed=False`, `actual_historical_replay_completed=False`.

**Important:** A `PASS_TO_STRATEGY` under an *independent projected world* is not an actual global cross-market ranking/admission. Projection does not assess simultaneity between alternative hypotheses from the same market, nor adjudicate cross-market factor exposure competition correctly. It is not a trading policy and must never be used to exceed MAX3. The next architecture must solve global multi-hypothesis arbitration using the *full* simultaneous opportunity set while preserving candidate count and market interactions.

## Implemented code and regression evidence

- `4dc43510180c93a649ffcc8b0f6731bbf3ff9d51`: original alternative-preserving cognitive census.
- `bfd8b337313cfdde5c4a67fd77b96c2d5c366b1c`: carry every alternative's H1/M15/M1/source-rule ancestry alongside output, with fail-closed parity.
- `84d1718ad77954e6443815aebda921dd042919a1`: regression tests for two AUDJPY alternatives + one USDJPY alternative in the same instant, causal *same-market* settled-loss ablation, missing/duplicate IDs, future H1/M1, repeated time barrier, future perception. **Official [A1 focused run 38053716565](https://github.com/mezas3238-hue/qore-core/actions/runs/38053716565) SUCCESS; [A1 full-source run 38053716593](https://github.com/mezas3238-hue/qore-core/actions/runs/38053716593) SUCCESS.** They are software quality gates, not return/edge results.
- `4b08d44048bca3ec46e70dc598486e3655fa1599`: stress fixture with **nine distinct M1 source alternatives in one minute**, including eight from AUDJPY; verifies input permutation independence, lossless nine-ID accounting, and no execution-authority claim even when observed research world has only ONE session execution slot left. CI for this more recent commit must be independently checked before calling HEAD GREEN.

## True candidate-count competition pressure (research-only, no ranking)

Additional code `4a1a7bd7eb954e4d04a2310c6268d5d95bafe73e` plus test `35f012704fc6743d0e58ea1c4e439d68b5b6d812` adds `A1MultiHypothesisCompetitionDemand` to the census. Unlike `build_opportunity_competition_state(world)`, whose input World Model represents just one DECISION item per symbol, this diagnostic counts **every distinct source candidate**:

- `presented_source_count` and `source_counts_by_market` preserve the actual denominator and same-symbol multiplicity;
- `pass_source_ids` retain unique individually supported cognitive candidates, with `WAIT`/`ABSTAIN` still represented in the full ledger;
- `available_session_slots` reads the immutable current ledger; `arbitration_required = len(pass_source_ids) > available_session_slots` observes genuine pressure, but `selected_source_id` must remain `None`;
- the nine-candidate test records **8 AUDJPY + 1 USDJPY**, **9** independent PASS dispositions, **1** session execution slot left, `arbitration_required=True` and **zero** execution authorization. This does not imply 9 trades or that the real cross-market competition would PASS 9.
- input permutation does not alter the decision IDs or competition-demand report.

**Official GitHub Actions GREEN on exact code SHA `35f012704fc6743d0e58ea1c4e439d68b5b6d812`:** [full A1 Cognition Audit #38054014954](https://github.com/mezas3238-hue/qore-core/actions/runs/38054014954) SUCCESS (Ruff complete repo, Mypy 1,626 files, 42 focused pytest) and [A1 Research Quality #38054015028](https://github.com/mezas3238-hue/qore-core/actions/runs/38054015028) SUCCESS. This strengthens the capacity audit only; it is **not source-fidelity, PnL or historical replay certification**.

## Scientific and methodology limitations

1. Research fixtures are synthetic. No actual historical nine-market M1 source census or observed market-state importer has been connected; coverage cannot yet be called 9/9 historical.
2. No real executed-trade receipt was reconciled with the selected closed-only memory; synthetic settled losses merely falsify whether the existing Master Frame responds causally in unit tests.
3. The projection temporarily focuses other decision markets. This MUST be transparently reported; individual PASS counts cannot be equated to real simultaneous competition outcomes or used to claim improved PF, expectancy, Sharpe, Sortino or DD.
4. The author source-rule ledger and `_untouched_h1_target_fast` causal correction remain in B's separate research branch and require review before integration. Do not use a fixture's route label as an ICT/TTrades verification.
5. A true global causal scheduler still needs multiple candidate hypotheses per market per instant, fair arbitration without lookahead, explicit provenance and every candidate's `WHY`, session MAX3 as ceiling only, open positions, underlying-factor exposure and daily journey.
6. Before any strategy/economic freeze: same-denominator baseline-vs-integrated nine-market replay, winner count >=80%, positive winner R >=90%, real density, provider-portable costs, PF, Sharpe, Sortino and max observed DD <=6R (operational target 3–5R). Reject density-destructive 90-trade candidate.

**Status:** cognitive *census representation* defect partly solved with an independently validated research harness; **global competition and real market ingestion remain blocking P0**, so full cognitive integration and Trader Scalper certification are NOT complete.
