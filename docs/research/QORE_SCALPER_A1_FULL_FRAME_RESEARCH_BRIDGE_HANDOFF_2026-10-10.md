# SCALPER A1 — Full-frame causal research bridge and verified CI failure repair

Date: 2026-10-10. Owner: Cognitive Architect A, canonical draft PR #758.
Parent: draft PR #623. Method cross-review: draft PR #759.
Scope: **GitHub research only. NO VPS / LIVE / merge / production. NOT CERTIFIED.**

## 1. Exact quality findings (observed, not inferred)

Official GitHub Actions QORE CI run [38043850123](https://github.com/mezas3238-hue/qore-core/actions/runs/38043850123) used SHA `002a804a65dd4642b543f025aa6f29fa0c5d78b3` and concluded **FAILURE**:

- Ruff **SUCCESS**.
- Mypy **SUCCESS**.
- Pytest **FAILURE**: 7,823 passed, 2 failed, 8 warnings.
- `test_capitalizer_v51_multi_era_repair.py::test_preservation_reports_winner_mass_and_loss_recall`: expectation erroneously asserted winner-R mass ratio 1 while fixture gives candidate winner R 3 + 2 = 5 versus matched baseline 2 + 1 = 3, so correct ratio is 5/3. This is *not* a win-preservation percentage capped at 100%. Test fixed commit `3586ae3922c95b0013b9d9d3eb84fd83f797250f`. Economic calculation unchanged.
- `test_capitalizer_v54_structural_partial_runner.py::test_partial_runner_realizes_half_t1_plus_half_runner`: invalid synthetic second OHLC candle had low 100.1 above open 100. Fix uses opening price 102 after first close 102, leaving high 104.1, low 100.1, close 104 and assertions unchanged. Companion BE fixture also explicitly opens at 102. Test fixed commit `ac8b93008589691529c399d0b22e594f41fa2c7e`.

No new CI GREEN or economic improvement is claimed until GitHub Actions checks the exact updated SHA.

## 2. Implemented separate, opt-in research adapter (NOT a replay strategy)

`src/qore/infrastructure/trader_lab/capitalizer_a1_full_frame_research_adapter.py`, commit `deb8d6494e36bd8222377f010a6ee81512262375`.

- Receives source candidate IDs and timestamped nine-market `CapitalizerGlobalWorldModel`, observed perceptions, regimes, cross-market causal graph, pressure, candidate contexts and immutable chosen-settlement memory.
- Rejects duplicate source IDs, duplicate source market bindings, mismatched time-barrier confirmations, candidate-context timing mismatch and missing provenance.
- Calls the existing production-class `build_master_cognitive_frame` and `explain_all_candidates` for **actual pre-strategy cognition**. The frame enforces nine markets, no future perceptions/regimes/graph, relevant DECISION contexts, metacognition, adversarial reasoning, competition and cognitive sovereignty. Emits source-ID keyed gate + deterministic WHY/uncertainty.
- `A1CausalSettledMemory.as_of` exposes only already-selected, fully settled executions whose exit timestamp is **strictly earlier** than the decision timestamp. Same-time ties remain invisible; no terminal result is included in pre-entry output, no runtime mutation or self-learning.
- Does NOT change source V49 or V50-G opportunity selection, stops/targets, MAX3, trade economics, admission, ranking, sizing, or risk authority. **No nine-market historical replay has yet driven this adapter**; functional integration into the replay and actual memory contribution to cognitive gate are **still pending**. Its settled-memory field currently contributes auditable history *count only*, not autonomous learning or memory-informed market decisions.
- Cannot claim any performance benefit, density preservation, ablation result, or true full-system wiring until real raw nine-market decision-time snapshots are supplied and source-to-execution joins are verified.

Added real-frame fixture-based regression cases to `test_capitalizer_master_cognitive_frame.py` in commit `22357c1b140e25bc024b8db96f6c3107a52cb21e`: successful nine-market frame invocation and WHY, reject missing market/future perception/duplicate ID/mismatched timestamp/incomplete provenance, settled-only memory with same-clock tie excluded, zero economic/selection authority.

## 3. P0 integration still necessary

1. Build real synchronized M1 market observation barrier from all nine independent streams and session-clock/DST. No synthetic `KNOWN`, perception, regimes or market brains. Validate no leaks from `V49Opportunity.h1_state_until` or H1 target witness future touch data (B-owned source fix).
2. Bind each V49 source opportunity to one live-at-decision world candidate context; preserve any multiple candidates from a single market through an explicit queue rather than collapsing silently. If multiple same-market candidates share one barrier, the research adapter currently rejects duplicates; the scheduler must queue them deterministically with full denominator. Do **not** use its single-market restriction as an admission filter.
3. Supply settled-only actual executed/selected outcomes into a causally versioned evidence store. Map loss cause / market-state profiles to frame world state with strict as-of; never learn rejected candidates' theoretical outcomes. Freeze/update knowledge exclusively after actual settlement.
4. Record differential against unchanged V49 and V50-G on **exactly the same source population**: input IDs, bridge vs Master Frame disposition, FIRST/LATER READY, WAIT/ABSTAIN, accepted/executed, winner identities/R and loss-recall; report zero-trade denominators, PF/DD/Sharpe/Sortino by 9 markets and eras.
5. A/B with all layers plus layer-wise ablations, frozen policy, real costs and no outcome-aware ranking. Separate capacity from economics, and do not promote 90-trade V50-G.
6. Validate corrected-core V50-R, V51, V53, V54-A, V54-B matrix Jobs and artifacts; check QORE CI on **exact head SHA**; request B's methodological signoff before any source gate changes.

## 4. Governed status

Pre-entry trace V50-G: PARTIAL_V50_BRIDGE_ONLY.
Opt-in full-frame adapter: added, tests committed, GitHub CI revalidation pending.
Persistent cognitive learning connected to trade outcomes: NOT IMPLEMENTED.
Nine-market actual replay: NOT EXECUTED.
PF / DD / winner mass for this variant: NOT MEASURED.
Author fidelity: A2 audit PENDING.
Scalper certification / live permission: DENIED.

Keep both PRs DRAFT and #623 UNMERGED.


## 5. Verified quality checkpoint after the fixes

At exact head `6fb52aa09ca05d34287a351ce8bfbae56e762812`:

- [A1 causal research focused run #38047414620](https://github.com/mezas3238-hue/qore-core/actions/runs/38047414620): **SUCCESS**, Ruff PASS, Mypy adapter PASS, 15 focused tests PASS.
- [QORE Scalper Cognition A1 Audit #38047414634](https://github.com/mezas3238-hue/qore-core/actions/runs/38047414634): **SUCCESS**, repository-wide Ruff PASS, Mypy `src tests` **1,624 files, PASS**, targeted causal cognition and multi-era regressions **34 PASS**.
- The older official global QORE CI run #38043850123 remains **FAILURE at its old SHA** (7,823 passed and two now-corrected fixture/expectation failures). Do not project A1 focused GREEN to whole-suite global CI or corrected-core nine-market replays.
- These results verify tests and typing, not nine-market real-data operation, author fidelity, economic preservation or certification.

Next required evidence: rerun *global* CI and V50-R/V51/V53/V54-A/V54-B 9-market aggregate on the integrated frozen A+B candidate. The quality run IDs above belong to A1 head only.
